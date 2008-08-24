# -*- encoding: utf-8 -*-
{
    "name":"Dashboard for CRM Configuration",
    "version":"1.0",
    "author":"Tiny",
    "category":"Board",
    "depends":["board","crm_configuration"],
    "demo_xml":["board_crm_demo.xml"],
    "update_xml":["board_crm_statistical_view.xml",
                  "board_crm_view.xml"
                  ],
    "description": """
This module implements a dashboard for CRM that includes:
    * My Leads (list)
    * Leads by Stage (graph)
    * My Meetings (list)
    * Sales Pipeline by Stage (graph)
    * My Cases (list)
    * Jobs Tracking (graph)
    """,
    "active":False,
    "installable":True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

