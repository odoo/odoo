{
    'name': 'Via Multi-Tenancy S3',
    'version': '19.0.1.0.0',
    'category': 'Technical',
    'summary': 'Multi-tenant S3 path isolation for via-suite',
    'description': '''
        Adds tenant isolation to fs_storage S3 paths.
        
        Features:
        - Automatic tenant detection from database name
        - S3 path prefixing: tenants/{tenant}/attachments/...
        - Path traversal attack prevention
        - Cross-tenant access validation
    ''',
    'author': 'ViaFronteira',
    'website': 'https://viafronteira.com',
    'depends': ['fs_storage', 'fs_attachment'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
