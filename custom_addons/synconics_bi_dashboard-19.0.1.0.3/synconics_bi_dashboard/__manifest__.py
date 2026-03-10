{
    "name": "Synconics BI Dashboard",
    "summary": """Synconics BI-Dashboard gives you a 360° view of your business with smart, interactive, and fully customizable dashboards for Odoo ERP. Get real-time insights with sales dashboards, inventory dashboards, project dashboards, finance dashboards, and KPI tracking all in one place. Drag Charts, multiple dashboards, dynamic filters, and drill-down analysis make it easy to visualize data, track performance, and make informed decisions. Synconics Dashboard, Dashboard, dashboard, Bi Dashboard, BI-Dashboard, Synconics Bi-Dashboard, Advance Dashboard, Odoo, CRM, Sales, Inventory, MRP, Bi Dashboard.
Transform your data into compelling dashboard visualizations
Build powerful dashboard charts that transform complex data into clear, actionable insights.
dashboard
Dashboard
bi dashboard
synconics
Synconics
Synconics Technologies
Bi Dashboard
BI dashboard
Bi dashboard
Bi-dashboard
KPI
Graph
Charts
CRM Dashboard
crm dashboard
sales dashboard
Graphs
Real-time Dashboard
Performance Tracking
Business Analytics
Executive Dashboard
Management Dashboard
Strategic Planning
Decision Making
Data Analysis
Insights
Custom Dashboard
Interactive Dashboard
Dynamic Reports
Drill-down Reports
Multi-user Dashboard
Role-based Dashboard
Customizable Widgets
Sales Dashboard
Inventory Dashboard
Financial Dashboard
HR Dashboard
CRM Dashboard
Project Dashboard
Manufacturing Dashboard
BI Tool
Report Builder
Visual Analytics
Data Dashboard
Business Reports
Summary Reports
Overview Dashboard
""",
    "description": """
Build powerful dashboard charts that transform complex data into clear, actionable insights.
synconics
BI Dashboard v19.0
Odoo Dashboard
dashboard
Dashboard
Dashboards
Analytics
Reporting
Business Intelligence
KPI Dashboard
Metrics
Data Visualization
Charts
Graphs
Real-time Dashboard
Performance Tracking
Business Analytics
Executive Dashboard
Management Dashboard
Strategic Planning
Decision Making
Data Analysis
Insights
Custom Dashboard
Interactive Dashboard
Dynamic Reports
Drill-down Reports
Multi-user Dashboard
Role-based Dashboard
Customizable Widgets
Sales Dashboard
Inventory Dashboard
Financial Dashboard
HR Dashboard
CRM Dashboard
Project Dashboard
Manufacturing Dashboard
BI Tool
Report Builder
Visual Analytics
Data Dashboard
Business Reports
Summary Reports
Overview Dashboard
    """,
    "author": "Synconics Technologies Pvt. Ltd.",
    "website": "https://www.synconics.com",
    "category": "web",
    "version": "1.0.3",
    "depends": ["web", "mail"],
    "external_dependencies": {"python": ["imgkit"]},
    "assets": {
        "web.assets_backend": [
            "synconics_bi_dashboard/static/src/lib/html2canvas.js",
            "synconics_bi_dashboard/static/src/lib/jspdf.js",
            "synconics_bi_dashboard/static/src/lib/amcharts/index.js",
            "synconics_bi_dashboard/static/src/lib/amcharts/xy.js",
            "synconics_bi_dashboard/static/src/lib/amcharts/exporting.js",
            "synconics_bi_dashboard/static/src/lib/amcharts/map.js",
            "synconics_bi_dashboard/static/src/lib/amcharts/worldLow.js",
            "synconics_bi_dashboard/static/src/lib/amcharts/radar.js",
            "synconics_bi_dashboard/static/src/lib/amcharts/flow.js",
            "synconics_bi_dashboard/static/src/lib/amcharts/percent.js",
            "synconics_bi_dashboard/static/src/lib/amcharts/hierarchy.js",
            "synconics_bi_dashboard/static/src/lib/themes/**/*",
            "synconics_bi_dashboard/static/src/lib/gridstack/**/*",
            "synconics_bi_dashboard/static/src/js/dashboard_form_view.js",
            "synconics_bi_dashboard/static/src/scss/dashboard_form_view.scss",
            "synconics_bi_dashboard/static/src/js/form_dashboard_preview.js",
            "synconics_bi_dashboard/static/src/xml/form_dashboard_preview.xml",
            "synconics_bi_dashboard/static/src/js/fa_icon_widget.js",
            "synconics_bi_dashboard/static/src/xml/fa_icon_widget.xml",
            "synconics_bi_dashboard/static/src/js/dashboard_chart_wrapper.js",
            "synconics_bi_dashboard/static/src/scss/dashboard_chart_wrapper.scss",
            "synconics_bi_dashboard/static/src/xml/dashboard_chart_wrapper.xml",
            "synconics_bi_dashboard/static/src/js/dashboard_amcharts.js",
            "synconics_bi_dashboard/static/src/xml/dashboard_amcharts.xml",
            "synconics_bi_dashboard/static/src/js/dashboard_selection/*",
            "synconics_bi_dashboard/static/src/components/**/*",
            "synconics_bi_dashboard/static/src/components/KPILayouts/**/*",
            "synconics_bi_dashboard/static/src/components/TileLayouts/**/*",
        ]
    },
    "cloc_exclude": [
        "static/src/lib/**/*",
    ],
    "data": [
        "security/dashboard_security.xml",
        "security/ir.model.access.csv",
        "data/mail_template.xml",
        "views/ir_ui_menu_views.xml",
        "wizard/dashboard_access_view.xml",
        "wizard/mail_compose_message_views.xml",
        "views/dashboard_view.xml",
        "data/dashboard_data.xml",
        "views/dashboard_chart_view.xml",
        "views/res_users_view.xml",
    ],
    "images": ["static/description/main_screen.gif"],
    "license": "OPL-1",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "application": True,
    "auto_install": False,
}
