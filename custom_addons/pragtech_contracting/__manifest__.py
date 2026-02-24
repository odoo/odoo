{
    'name': 'Construction Sub Contracting Management',
    'version': '18.0.1.0.0',
    'category': 'Construction',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'summary': 'This Module Adds a drop-down for service links in systray Bookmarks odoo bookmarks Construction Sub-Contracting Management construction contracting construction management odoo construction',
    'description': """
Construction Sub Contracting Management
=======================================
<keywords>
Construction Sub-Contracting Management
construction contracting
construction management
odoo construction
contracting
    """,
    'depends': [
        'base',
        'sales_team',
        'pragtech_ppc',
        'stock',
        'account',
        'payment'
    ],
    'data': [
        'wizard/stage_transaction_wizard.xml',
        'security/user_groups.xml',
        'security/ir.model.access.csv',
        'reports/report_work_order.xml',
        'reports/report_ra_bill.xml',
        'reports/report_workorder_summary.xml',
        'reports/report_Rabill_summary.xml',
        'reports/report_incomplete_wo.xml',
        'reports/report_contractor_payment.xml',
        'reports/report_grn.xml',
        'views/contractor_view.xml',
        'views/labour_quotation.xml',
        'views/labour_quotationcomparison_view.xml',
        'views/partner_view.xml',
        'wizard/labour_requisition_wizard.xml',
        'views/workorder_view.xml',
        'views/labour_requisition.xml',
        'wizard/work_completion_wizard.xml',
        'views/work_completion.xml',
        'views/transaction_view.xml',
        'views/retention_view.xml',
        'views/advance_view.xml',
        'views/credit_recovery_view.xml',
        'views/debit_recovery_view.xml',
        'views/ra_bill.xml',
        'views/sequence_view.xml',
        'views/report.xml',
        'views/account_invoice_vews.xml',
        'wizard/wizard_workorder_summary.xml',
        'wizard/wizard_rabill_summary.xml',
        'wizard/wizard_incomplete_wo.xml',
        'wizard/wizard_contractor_payment.xml',
        'wizard/wizard_grn_report.xml',
    ],

    'images': ['images/Animated-Construction-purchase.gif'],
    'live_test_url': 'https://www.pragtech.co.in/company/proposal-form.html?id=103&name=construction-subcontracting',
    'license': 'OPL-1',
    'price': 243.50,
    'currency': 'USD',
    'installable': True,
    'auto_install': False,
}
