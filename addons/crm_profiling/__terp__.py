# -*- encoding: utf-8 -*-
{
    "name" : "crm_profiling management",
    "version" : "1.3",
    "depends" : ["base", "crm"],
    "author" : "Tiny",
    "description": """
    This module allow users to perform segmentation within partners. 
    It use the profiles criteria from the earlier segmentation module and improve it thanks to the new concept of questionnaire. You can now regroup questions into a questionnaire and directly use it on a partner.

    It also has been merged with the earlier CRM & SRM segmentation tool because they were overlapping. 

    
    The menu items related are in "CRM & SRM\Configuration\Segmentations\"


    * Note: this module is not compatible with the module segmentation, since it's the same which has been renamed.
    """,
    "website" : "http://tinyerp.com/",
    "category" : "Generic Modules/Project & Services",
    "init_xml" : [],
    "demo_xml" : ["crm_profiling_demo.xml"],
    "update_xml" : [
        "security/ir.model.access.csv",
        "crm_profiling_view.xml",
    ],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

