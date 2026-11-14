# -*- coding: utf-8 -*-
{
    "name": "School eLearning",
    "version": "19.0.1.0.0",
    "category": "Education/eLearning",
    "summary": "Integration between School Management and eLearning (website_slides)",
    "description": """
School eLearning Integration
============================
Inherits and extends Odoo's core eLearning (website_slides) to link:
* eLearning Courses (slide.channel) with University Subjects, Teachers, and Class Sections.
* University Subjects with course material, statistics, and eLearning navigation.
* University Class Sections with assigned course channels.
    """,
    "author": "Harvard University",
    "license": "LGPL-3",
    "depends": [
        "website_slides",
        "school_management",
    ],
    "data": [
        "views/slide_channel_views.xml",
        "views/subject_views.xml",
        "views/class_section_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
