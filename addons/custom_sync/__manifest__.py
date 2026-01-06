{
    'name': 'Joker Sync Engine',
    'version': '19.0.1.0.0',
    'category': 'Technical',
    'summary': 'Enterprise-Community Odoo Senkronizasyon Motoru',
    'description': """
        Joker Sync Engine
        =================
        Bu modül Odoo Enterprise ve Community sürümleri arasında 
        çift yönlü veri senkronizasyonu sağlar.
        
        Özellikler:
        -----------
        * XML-RPC tabanlı bağlantı
        * Otomatik veri çekme (pull)
        * Değişiklik bildirimi (push)
        * Conflict resolution
        * Zamanlanmış görevler
    """,
    'author': 'Joker Grubu',
    'website': 'https://www.jokergrubu.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale',
        'stock',
        'purchase',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/sync_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
