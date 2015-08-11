# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Manufacturing Operations',
    'version': '1.0',
    'category': 'Manufacturing',
    'description': """
This module adds state, date_start, date_stop in manufacturing order operation lines (in the 'Work Orders' tab).
================================================================================================================

Status: draft, confirm, done, cancel
When finishing/confirming, cancelling manufacturing orders set all state lines
to the according state.

Create menus:
-------------
    **Manufacturing** > **Manufacturing** > **Work Orders**

Which is a view on 'Work Orders' lines in manufacturing order.

Add buttons in the form view of manufacturing order under workorders tab:
-------------------------------------------------------------------------
    * start (set state to confirm), set date_start
    * done (set state to done), set date_stop
    * set to draft (set state to draft)
    * cancel set state to cancel

When the manufacturing order becomes 'ready to produce', operations must
become 'confirmed'. When the manufacturing order is done, all operations
must become done.

The field 'Working Hours' is the delay(stop date - start date).
So, that we can compare the theoretic delay and real delay. 
    """,
    'website': 'https://www.odoo.com/page/manufacturing',
    'depends': ['mrp'],
    'data': [
        'data/report_paperformat.xml',
        'security/ir.model.access.csv',
        'mrp_operation_data.xml',
        'mrp_operations_workflow.xml',
        'mrp_operations_view.xml',
        'mrp_operations_report.xml',
        'report/mrp_workorder_analysis_view.xml',
        'views/report_wcbarcode.xml',
        'mrp_operations_workflow_instance.xml'
    ],
    'demo': [ 
             'mrp_operations_demo.yml'
    ],
    'test': [ 
        'test/workcenter_operations.yml',
    ],
    'installable': True,
    'auto_install': False,
}
