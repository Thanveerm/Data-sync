{
    'name': 'Data Sync Server',
    'version': '16.0.1.0.0',
    'category': 'Tools',
    'summary': 'Sync data from source server to target server',
    'description': """
        Module to sync account.analytic.line data from one server to another
        based on date range selection.
    """,
    'author': 'Thanveer',
    'depends': ['base', 'analytic', 'hr_timesheet'],
    'data': [
        'security/ir.model.access.csv',
        'views/sync_config_views.xml',
        'wizard/sync_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
