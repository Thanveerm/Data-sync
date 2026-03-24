from odoo import models, fields, api, _
from odoo.exceptions import UserError
import xmlrpc.client
import logging

_logger = logging.getLogger(__name__)


class ServerSyncConfig(models.Model):
    _name = 'server.sync.config'
    _description = 'Server Sync Configuration'

    name = fields.Char(string='Configuration Name', required=True)
    source_url = fields.Char(string='Source Server URL', required=True, help='e.g., http://localhost:8069')
    source_db = fields.Char(string='Source Database', required=True)
    source_username = fields.Char(string='Source Username', required=True)
    source_password = fields.Char(string='Source Password', required=True)
    target_url = fields.Char(string='Target Server URL', required=True, help='e.g., http://localhost:8070')
    target_db = fields.Char(string='Target Database', required=True)
    target_username = fields.Char(string='Target Username', required=True)
    target_password = fields.Char(string='Target Password', required=True)
    active = fields.Boolean(string='Active', default=True)
    last_sync_date = fields.Datetime(string='Last Sync Date', readonly=True)
    sync_count = fields.Integer(string='Total Synced Records', readonly=True, default=0)

    def test_source_connection(self):
        self.ensure_one()
        try:
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(self.source_url))
            uid = common.authenticate(self.source_db, self.source_username, self.source_password, {})
            if uid:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Source server connection successful!'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError(_('Authentication failed for source server'))
        except Exception as e:
            raise UserError(_('Source server connection failed: %s') % str(e))

    def test_target_connection(self):
        self.ensure_one()
        try:
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(self.target_url))
            uid = common.authenticate(self.target_db, self.target_username, self.target_password, {})
            if uid:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Target server connection successful!'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError(_('Authentication failed for target server'))
        except Exception as e:
            raise UserError(_('Target server connection failed: %s') % str(e))

    def action_open_sync_wizard(self):
        self.ensure_one()
        return {
            'name': _('Sync Data'),
            'type': 'ir.actions.act_window',
            'res_model': 'server.sync.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_config_id': self.id}
        }
