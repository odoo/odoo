
{
    'name': 'PDF Viewer',
    'version': '1.1',
    'category': 'Tools',
    'description': """
PDF Viewer
==========

Install the appropriate plugins if your PDF documents are not displaying properly

For Firefox
----------- 
https://addons.mozilla.org/En-us/firefox/addon/pdfjs/

For Chrome
----------
https://chrome.google.com/webstore/detail/chrome-office-viewer/gbkeegbaiigmenfmjfclcdgdpimamgkj?utm_source=chrome-ntp-icon
    """,
    "author": "OpenERP SA",
    "website": "http://www.openerp.com",
    "depends": ["web","report"],
    "data":["views/pdf_viewer_assets.xml"],
    'installable': True,
    'auto_install': True,
}
