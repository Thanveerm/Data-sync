from odoo import models, fields, api, _
from odoo.exceptions import UserError
import xmlrpc.client
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class ServerSyncWizard(models.TransientModel):
    _name = 'server.sync.wizard'
    _description = 'Server Sync Wizard'

    config_id = fields.Many2one('server.sync.config', string='Sync Configuration', required=True)
    start_date = fields.Datetime(string='Start Date', required=True)
    end_date = fields.Datetime(string='End Date', required=True)
    sync_log = fields.Text(string='Sync Log', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('syncing', 'Syncing'),
        ('done', 'Done'),
        ('error', 'Error')
    ], default='draft', string='State')
    records_synced = fields.Integer(string='Records Synced', readonly=True, default=0)
    records_failed = fields.Integer(string='Records Failed', readonly=True, default=0)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise UserError(_('Start date must be before end date'))

    def _connect_to_source(self):
        self.ensure_one()
        try:
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(self.config_id.source_url))
            uid = common.authenticate(
                self.config_id.source_db,
                self.config_id.source_username,
                self.config_id.source_password,
                {}
            )
            if not uid:
                raise UserError(_('Failed to authenticate with source server'))
            
            models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(self.config_id.source_url))
            return uid, models
        except Exception as e:
            raise UserError(_('Source server connection error: %s') % str(e))

    def _connect_to_target(self):
        self.ensure_one()
        try:
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(self.config_id.target_url))
            uid = common.authenticate(
                self.config_id.target_db,
                self.config_id.target_username,
                self.config_id.target_password,
                {}
            )
            if not uid:
                raise UserError(_('Failed to authenticate with target server'))
            
            models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(self.config_id.target_url))
            return uid, models
        except Exception as e:
            raise UserError(_('Target server connection error: %s') % str(e))

    def _get_field_mapping(self):
        return [
            'name',
            'date',
            'unit_amount',
            'project_id',
            'task_id',
            'employee_id',
            'company_id',
            'currency_id',
            'amount',
            'account_id',
            'department_id',
            'tag_ids',
        ]

    def _prepare_sync_values(self, source_uid, source_models, record_data, target_uid, target_models):
        vals = {}
        
        for field in self._get_field_mapping():
            if field in record_data and record_data[field]:
                if field in ['project_id', 'task_id', 'employee_id', 'company_id', 
                             'currency_id', 'account_id', 'department_id']:
                    if isinstance(record_data[field], list) and len(record_data[field]) > 0:
                        source_record_id = record_data[field][0]
                        source_record_name = record_data[field][1]
                        
                        model_map = {
                            'project_id': 'project.project',
                            'task_id': 'project.task',
                            'employee_id': 'hr.employee',
                            'company_id': 'res.company',
                            'currency_id': 'res.currency',
                            'account_id': 'account.analytic.account',
                            'department_id': 'hr.department',
                        }
                        
                        related_model = model_map.get(field)
                        if related_model:
                            try:
                                target_record_ids = target_models.execute_kw(
                                    self.config_id.target_db,
                                    target_uid,
                                    self.config_id.target_password,
                                    related_model,
                                    'search',
                                    [[['name', '=', source_record_name]]],
                                    {'limit': 1}
                                )
                                
                                if target_record_ids:
                                    vals[field] = target_record_ids[0]
                                else:
                                    _logger.warning(f'Related record not found in target for {field}: {source_record_name}')
                            except Exception as e:
                                _logger.error(f'Error mapping {field}: {str(e)}')
                
                elif field == 'tag_ids':
                    if isinstance(record_data[field], list) and len(record_data[field]) > 0:
                        tag_ids = []
                        for tag_id in record_data[field]:
                            try:
                                tag_data = source_models.execute_kw(
                                    self.config_id.source_db,
                                    source_uid,
                                    self.config_id.source_password,
                                    'account.analytic.tag',
                                    'read',
                                    [tag_id],
                                    {'fields': ['name']}
                                )
                                
                                if tag_data:
                                    tag_name = tag_data[0]['name']
                                    target_tag_ids = target_models.execute_kw(
                                        self.config_id.target_db,
                                        target_uid,
                                        self.config_id.target_password,
                                        'account.analytic.tag',
                                        'search',
                                        [[['name', '=', tag_name]]],
                                        {'limit': 1}
                                    )
                                    
                                    if target_tag_ids:
                                        tag_ids.append(target_tag_ids[0])
                            except Exception as e:
                                _logger.error(f'Error mapping tag: {str(e)}')
                        
                        if tag_ids:
                            vals[field] = [(6, 0, tag_ids)]
                
                else:
                    vals[field] = record_data[field]
        
        return vals

    def action_sync_data(self):
        self.ensure_one()
        
        try:
            self.write({'state': 'syncing', 'sync_log': 'Starting sync process...\n'})
            
            source_uid, source_models = self._connect_to_source()
            target_uid, target_models = self._connect_to_target()
            
            log_messages = []
            log_messages.append(f'Connected to source and target servers successfully.')
            log_messages.append(f'Fetching records from {self.start_date} to {self.end_date}...')
            
            domain = [
                ('create_date', '>=', self.start_date.strftime('%Y-%m-%d %H:%M:%S')),
                ('create_date', '<=', self.end_date.strftime('%Y-%m-%d %H:%M:%S'))
            ]
            
            record_ids = source_models.execute_kw(
                self.config_id.source_db,
                source_uid,
                self.config_id.source_password,
                'account.analytic.line',
                'search',
                [domain]
            )
            
            log_messages.append(f'Found {len(record_ids)} records to sync.')
            
            if not record_ids:
                self.write({
                    'state': 'done',
                    'sync_log': '\n'.join(log_messages) + '\nNo records found to sync.'
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Info'),
                        'message': _('No records found in the specified date range.'),
                        'type': 'info',
                        'sticky': False,
                    }
                }
            
            fields_to_read = self._get_field_mapping()
            
            records_data = source_models.execute_kw(
                self.config_id.source_db,
                source_uid,
                self.config_id.source_password,
                'account.analytic.line',
                'read',
                [record_ids],
                {'fields': fields_to_read}
            )
            
            synced_count = 0
            failed_count = 0
            
            for record_data in records_data:
                try:
                    vals = self._prepare_sync_values(source_uid, source_models, record_data, target_uid, target_models)
                    
                    if vals:
                        new_id = target_models.execute_kw(
                            self.config_id.target_db,
                            target_uid,
                            self.config_id.target_password,
                            'account.analytic.line',
                            'create',
                            [vals]
                        )
                        
                        if new_id:
                            synced_count += 1
                            log_messages.append(f'✓ Synced record: {record_data.get("name", "N/A")} (ID: {new_id})')
                        else:
                            failed_count += 1
                            log_messages.append(f'✗ Failed to create record: {record_data.get("name", "N/A")}')
                    else:
                        failed_count += 1
                        log_messages.append(f'✗ No valid data to sync for record: {record_data.get("name", "N/A")}')
                        
                except Exception as e:
                    failed_count += 1
                    log_messages.append(f'✗ Error syncing record {record_data.get("name", "N/A")}: {str(e)}')
                    _logger.error(f'Sync error: {str(e)}')
            
            log_messages.append(f'\n=== Sync Summary ===')
            log_messages.append(f'Total records found: {len(record_ids)}')
            log_messages.append(f'Successfully synced: {synced_count}')
            log_messages.append(f'Failed: {failed_count}')
            
            self.config_id.write({
                'last_sync_date': fields.Datetime.now(),
                'sync_count': self.config_id.sync_count + synced_count
            })
            
            self.write({
                'state': 'done',
                'sync_log': '\n'.join(log_messages),
                'records_synced': synced_count,
                'records_failed': failed_count
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sync Complete'),
                    'message': _(f'Synced {synced_count} records successfully. {failed_count} failed.'),
                    'type': 'success' if failed_count == 0 else 'warning',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            error_msg = str(e)
            _logger.error(f'Sync failed: {error_msg}')
            self.write({
                'state': 'error',
                'sync_log': (self.sync_log or '') + f'\n\nERROR: {error_msg}'
            })
            raise UserError(_('Sync failed: %s') % error_msg)
