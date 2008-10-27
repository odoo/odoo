# -*- encoding: utf-8 -*-
{
    "name" : "Event",
    "version" : "0.1",
    "author" : "Tiny",
    "category" : "Generic Modules/Association",
    "description": """Organization and management of events.

    This module allow you
        * to manage your events and their registrations
        * to create retro planning for managing your events
        * to use emails to automaticly confirm and send acknowledgements for any registration to an event
        * ...

    Note that:
    - You can define new types of events in
                Events \ Configuration \ Types of Events
    - You can access pre-defined reports about number of registration per event or per event category in :
                Events \ Reporting
""",
    "depends" : [
        "project","crm","base_contact","account_budget",
    ],
    "demo_xml" : ["event_demo.xml"],
    "init_xml" : ["event_data.xml"],
    "update_xml" : [
        "event_wizard.xml",
        "event_view.xml",
        "event_sequence.xml",
        "security/event_security.xml",
        "security/ir.model.access.csv",
    ],
    "active" : False,
    "installable" : True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

