{
    'name': 'RealTime Product and Loyalty POS sync',
    'version': '16.1.1',
    'description': 'RealTime Product and Loyalty Pos Sync',
    'author': 'Gladdema',
    'website': 'xxx',
    'depends': [
        'pos_loyalty'
    ],
    'data': [
        'security/auth_user_token_security.xml',
        'security/ir.model.access.csv',
        'views/auth_user_token_views.xml',
        'views/auth_user_token_menu.xml',
       
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}