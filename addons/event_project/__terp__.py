# -*- encoding: utf-8 -*-
{
    "name" : "Event - Project",
    "version" : "0.1",
    "author" : "Tiny",
    "category" : "Generic Modules/Association",
    "description": """Organization and management of events.

    This module allow you to create retro planning for managing your events.
""",
    "depends" : [
        "project_retro_planning","event",
    ],
    "demo_xml" : [],
    "init_xml" : [],
    "update_xml" : [
        "event_wizard.xml",
        "event_view.xml",
    ],
    "active" : False,
    "installable" : True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

