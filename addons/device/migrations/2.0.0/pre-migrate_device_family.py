from odoo.db.schema import table_exists
from odoo.libs.sql import SQL
from odoo.tools.module_data import _rename_table_with_dependents, rename_model

# Base 1.94 renamed the module rows first; every xml id here is read under
# its module's new name.
MODELS = (
    ("remote.device.category", "device.kind"),
    ("remote.device", "device.device"),
    ("remote.config", "device.profile"),
    ("mixin.remote.data.log", "mixin.device.data.log"),
    ("remote.data.log", "device.data.log"),
    ("remote.data.log.report", "device.data.log.report"),
    ("remote.gps.data.processor", "device.gps.data.processor"),
    ("remote.data.log.gps", "device.data.log.gps"),
    ("remote.gps.data.validator", "device.gps.data.validator"),
    ("remote.data.log.gps.report", "device.data.log.gps.report"),
    ("remote.state.boundary", "device.state.boundary"),
    ("remote.weekday", "device.weekday"),
    ("remote.client.visit", "device.client.visit"),
    ("remote.geo.fence", "device.geo.fence"),
    ("remote.machine.bucket", "device.machine.bucket"),
    ("remote.machine.reading", "device.machine.reading"),
    ("remote.machine.workorder", "device.machine.workorder"),
    ("remote.call.recording", "device.call.recording"),
    ("remote.call.log", "device.call.log"),
    ("remote.gps.speed.day", "device.gps.speed.day"),
    ("remote.gps.speed.alert", "device.gps.speed.alert"),
    ("remote.gps.speed.event", "device.gps.speed.event"),
    ("remote.client.visit.rebuild.wizard", "device.client.visit.rebuild.wizard"),
)

XMLIDS = (
    (
        "agro_surface_device_gps_geoengine",
        "access_remote_device_agro_user",
        "access_device_device_agro_user",
    ),
    (
        "agro_surface_device_gps_geoengine",
        "access_remote_geo_fence_agro_user",
        "access_device_geo_fence_agro_user",
    ),
    (
        "agro_surface_device_gps_geoengine",
        "access_remote_weekday_agro_user",
        "access_device_weekday_agro_user",
    ),
    (
        "agro_surface_device_gps_geoengine",
        "remote_geo_fence_agro_company_rule",
        "device_geo_fence_agro_company_rule",
    ),
    (
        "agro_surface_device_gps_geoengine",
        "remote_geo_fence_view_form_planting",
        "device_geo_fence_view_form_planting",
    ),
    (
        "asset_gps",
        "view_remote_data_log_gps_report_list_asset",
        "view_device_data_log_gps_report_list_asset",
    ),
    (
        "asset_gps",
        "view_remote_data_log_gps_report_pivot_asset",
        "view_device_data_log_gps_report_pivot_asset",
    ),
    (
        "asset_gps",
        "view_remote_data_log_gps_report_search_asset",
        "view_device_data_log_gps_report_search_asset",
    ),
    ("asset_gps", "view_remote_device_form_asset", "view_device_device_form_asset"),
    (
        "asset_gps",
        "view_remote_device_kanban_gps_dashboard_asset",
        "view_device_device_kanban_gps_dashboard_asset",
    ),
    (
        "asset_gps_geoengine",
        "access_remote_gps_speed_alert_manager",
        "access_device_gps_speed_alert_manager",
    ),
    (
        "asset_gps_geoengine",
        "access_remote_gps_speed_alert_user",
        "access_device_gps_speed_alert_user",
    ),
    (
        "asset_gps_geoengine",
        "access_remote_gps_speed_day_user",
        "access_device_gps_speed_day_user",
    ),
    (
        "asset_gps_geoengine",
        "access_remote_gps_speed_event_user",
        "access_device_gps_speed_event_user",
    ),
    (
        "asset_gps_geoengine",
        "action_remote_gps_speed_alert",
        "action_device_gps_speed_alert",
    ),
    (
        "asset_gps_geoengine",
        "action_remote_gps_speed_day",
        "action_device_gps_speed_day",
    ),
    (
        "asset_gps_geoengine",
        "action_remote_gps_speed_event",
        "action_device_gps_speed_event",
    ),
    (
        "asset_gps_geoengine",
        "menu_remote_gps_speed_alert",
        "menu_device_gps_speed_alert",
    ),
    ("asset_gps_geoengine", "menu_remote_gps_speed_day", "menu_device_gps_speed_day"),
    (
        "asset_gps_geoengine",
        "menu_remote_gps_speed_event",
        "menu_device_gps_speed_event",
    ),
    (
        "asset_gps_geoengine",
        "view_remote_client_visit_list_asset",
        "view_device_client_visit_list_asset",
    ),
    (
        "asset_gps_geoengine",
        "view_remote_client_visit_search_asset",
        "view_device_client_visit_search_asset",
    ),
    (
        "asset_gps_geoengine",
        "view_remote_device_geoengine_asset",
        "view_device_device_geoengine_asset",
    ),
    (
        "asset_gps_geoengine",
        "view_remote_device_search_gps_trail_asset",
        "view_device_device_search_gps_trail_asset",
    ),
    (
        "asset_gps_geoengine",
        "view_remote_gps_speed_alert_list",
        "view_device_gps_speed_alert_list",
    ),
    (
        "asset_gps_geoengine",
        "view_remote_gps_speed_alert_search",
        "view_device_gps_speed_alert_search",
    ),
    (
        "asset_gps_geoengine",
        "view_remote_gps_speed_day_graph",
        "view_device_gps_speed_day_graph",
    ),
    (
        "asset_gps_geoengine",
        "view_remote_gps_speed_day_list",
        "view_device_gps_speed_day_list",
    ),
    (
        "asset_gps_geoengine",
        "view_remote_gps_speed_day_search",
        "view_device_gps_speed_day_search",
    ),
    (
        "asset_gps_geoengine",
        "view_remote_gps_speed_event_graph",
        "view_device_gps_speed_event_graph",
    ),
    (
        "asset_gps_geoengine",
        "view_remote_gps_speed_event_list",
        "view_device_gps_speed_event_list",
    ),
    (
        "asset_gps_geoengine",
        "view_remote_gps_speed_event_search",
        "view_device_gps_speed_event_search",
    ),
    (
        "asset_gps_hr",
        "view_remote_data_log_gps_report_list_operator",
        "view_device_data_log_gps_report_list_operator",
    ),
    (
        "asset_gps_hr",
        "view_remote_data_log_gps_report_pivot_operator",
        "view_device_data_log_gps_report_pivot_operator",
    ),
    (
        "asset_gps_hr",
        "view_remote_data_log_gps_report_search_operator",
        "view_device_data_log_gps_report_search_operator",
    ),
    ("asset_gps_hr", "view_remote_device_form_hr", "view_device_device_form_hr"),
    (
        "asset_gps_hr",
        "view_remote_device_kanban_gps_dashboard_hr",
        "view_device_device_kanban_gps_dashboard_hr",
    ),
    ("asset_gps_hr", "view_remote_device_list_hr", "view_device_device_list_hr"),
    ("asset_gps_hr", "view_remote_device_search_hr", "view_device_device_search_hr"),
    (
        "project_task_device_visit",
        "access_remote_client_visit_rebuild_wizard_manager",
        "access_device_client_visit_rebuild_wizard_manager",
    ),
    (
        "project_task_device_visit",
        "action_remote_client_visit_rebuild_wizard",
        "action_device_client_visit_rebuild_wizard",
    ),
    (
        "project_task_device_visit",
        "menu_remote_client_visit_rebuild_wizard",
        "menu_device_client_visit_rebuild_wizard",
    ),
    (
        "project_task_device_visit",
        "remote_client_visit_rebuild_wizard_view_form",
        "device_client_visit_rebuild_wizard_view_form",
    ),
    ("device", "access_remote_config_manager", "access_device_profile_manager"),
    ("device", "access_remote_config_user", "access_device_profile_user"),
    ("device", "access_remote_data_log_manager", "access_device_data_log_manager"),
    (
        "device",
        "access_remote_data_log_report_manager",
        "access_device_data_log_report_manager",
    ),
    (
        "device",
        "access_remote_data_log_report_user",
        "access_device_data_log_report_user",
    ),
    ("device", "access_remote_data_log_user", "access_device_data_log_user"),
    ("device", "access_remote_device_category_manager", "access_device_kind_manager"),
    ("device", "access_remote_device_category_user", "access_device_kind_user"),
    ("device", "access_remote_device_manager", "access_device_device_manager"),
    ("device", "access_remote_device_user", "access_device_device_user"),
    ("device", "action_remote_config", "action_device_profile"),
    ("device", "action_remote_dashboard", "action_device_dashboard"),
    ("device", "action_remote_data_log", "action_device_data_log"),
    ("device", "action_remote_data_log_report", "action_device_data_log_report"),
    (
        "device",
        "action_remote_data_log_report_device",
        "action_device_data_log_report_device",
    ),
    (
        "device",
        "action_remote_data_log_report_type",
        "action_device_data_log_report_type",
    ),
    (
        "device",
        "action_remote_data_log_report_volume",
        "action_device_data_log_report_volume",
    ),
    ("device", "action_remote_device", "action_device_device"),
    ("device", "group_remote_manager", "group_device_manager"),
    ("device", "group_remote_user", "group_device_user"),
    ("device", "menu_remote_config", "menu_device_profile"),
    ("device", "menu_remote_configuration", "menu_device_profileuration"),
    ("device", "menu_remote_dashboard", "menu_device_dashboard"),
    ("device", "menu_remote_data_analytics", "menu_device_data_analytics"),
    ("device", "menu_remote_data_log_analysis", "menu_device_data_log_analysis"),
    ("device", "menu_remote_data_log_log", "menu_device_data_log_log"),
    ("device", "menu_remote_data_type_analysis", "menu_device_data_type_analysis"),
    ("device", "menu_remote_data_volume_analysis", "menu_device_data_volume_analysis"),
    ("device", "menu_remote_device", "menu_device_device"),
    (
        "device",
        "menu_remote_device_activity_analysis",
        "menu_device_device_activity_analysis",
    ),
    ("device", "menu_remote_device_category", "menu_device_kind"),
    ("device", "menu_remote_devices", "menu_device_devices"),
    ("device", "menu_remote_general_iot_analysis", "menu_device_general_iot_analysis"),
    ("device", "menu_remote_gps_raw_data", "menu_device_gps_raw_data"),
    ("device", "menu_remote_root", "menu_device_root"),
    ("device", "module_category_remote_remote", "module_category_device_device"),
    ("device", "remote_dashboard_graph_view", "device_dashboard_graph_view"),
    ("device", "remote_dashboard_kanban_view", "device_dashboard_kanban_view"),
    ("device", "remote_dashboard_pivot_view", "device_dashboard_pivot_view"),
    ("device", "remote_data_log_company_rule", "device_data_log_company_rule"),
    (
        "device",
        "remote_data_log_report_company_rule",
        "device_data_log_report_company_rule",
    ),
    ("device", "remote_device_category_action", "device_kind_action"),
    ("device", "remote_device_category_view_form", "device_kind_view_form"),
    ("device", "remote_device_category_view_kanban", "device_kind_view_kanban"),
    ("device", "remote_device_category_view_tree", "device_kind_view_tree"),
    ("device", "remote_device_company_rule", "device_device_company_rule"),
    (
        "device",
        "res_groups_privilege_remote_remote",
        "res_groups_privilege_device_device",
    ),
    ("device", "view_remote_config_form", "view_device_profile_form"),
    ("device", "view_remote_config_list", "view_device_profile_list"),
    ("device", "view_remote_config_search", "view_device_profile_search"),
    ("device", "view_remote_data_log_form", "view_device_data_log_form"),
    ("device", "view_remote_data_log_graph", "view_device_data_log_graph"),
    ("device", "view_remote_data_log_pivot", "view_device_data_log_pivot"),
    (
        "device",
        "view_remote_data_log_report_graph_bar",
        "view_device_data_log_report_graph_bar",
    ),
    (
        "device",
        "view_remote_data_log_report_graph_line",
        "view_device_data_log_report_graph_line",
    ),
    (
        "device",
        "view_remote_data_log_report_graph_pie",
        "view_device_data_log_report_graph_pie",
    ),
    (
        "device",
        "view_remote_data_log_report_graph_source",
        "view_device_data_log_report_graph_source",
    ),
    ("device", "view_remote_data_log_report_list", "view_device_data_log_report_list"),
    (
        "device",
        "view_remote_data_log_report_pivot",
        "view_device_data_log_report_pivot",
    ),
    (
        "device",
        "view_remote_data_log_report_search",
        "view_device_data_log_report_search",
    ),
    ("device", "view_remote_data_log_search", "view_device_data_log_search"),
    ("device", "view_remote_data_log_tree", "view_device_data_log_tree"),
    ("device", "view_remote_device_form", "view_device_device_form"),
    ("device", "view_remote_device_kanban", "view_device_device_kanban"),
    ("device", "view_remote_device_list", "view_device_device_list"),
    ("device", "view_remote_device_search", "view_device_device_search"),
    (
        "device_access_control",
        "acl_remote_config_webhook",
        "acl_device_profile_webhook",
    ),
    (
        "device_access_control",
        "acl_remote_device_category_webhook",
        "acl_device_kind_webhook",
    ),
    ("device_access_control", "acl_remote_device_webhook", "acl_device_device_webhook"),
    (
        "device_access_control",
        "remote_config_isapi_access",
        "device_profile_isapi_access",
    ),
    (
        "device_access_control",
        "remote_device_category_access_control",
        "device_kind_access_control",
    ),
    (
        "device_access_control",
        "view_remote_device_form_inherit_access",
        "view_device_device_form_inherit_access",
    ),
    (
        "device_access_control",
        "view_remote_device_search_inherit_access",
        "view_device_device_search_inherit_access",
    ),
    ("device_dav_sync", "view_remote_config_form_dav", "view_device_profile_form_dav"),
    ("device_dav_sync", "view_remote_device_form_dav", "view_device_device_form_dav"),
    (
        "device_dav_sync",
        "view_remote_device_search_dav",
        "view_device_device_search_dav",
    ),
    (
        "device_gps",
        "access_remote_data_log_gps_manager",
        "access_device_data_log_gps_manager",
    ),
    (
        "device_gps",
        "access_remote_data_log_gps_report_manager",
        "access_device_data_log_gps_report_manager",
    ),
    (
        "device_gps",
        "access_remote_data_log_gps_report_user",
        "access_device_data_log_gps_report_user",
    ),
    (
        "device_gps",
        "access_remote_data_log_gps_user",
        "access_device_data_log_gps_user",
    ),
    ("device_gps", "action_remote_data_log_gps", "action_device_data_log_gps"),
    (
        "device_gps",
        "action_remote_data_log_gps_report",
        "action_device_data_log_gps_report",
    ),
    (
        "device_gps",
        "action_remote_data_log_gps_report_activity",
        "action_device_data_log_gps_report_activity",
    ),
    (
        "device_gps",
        "action_remote_data_log_gps_report_distance",
        "action_device_data_log_gps_report_distance",
    ),
    (
        "device_gps",
        "action_remote_data_log_gps_report_fuel",
        "action_device_data_log_gps_report_fuel",
    ),
    (
        "device_gps",
        "action_remote_data_log_gps_report_speed",
        "action_device_data_log_gps_report_speed",
    ),
    ("device_gps", "action_remote_device_gps", "action_device_device_gps"),
    ("device_gps", "action_remote_gps_config", "action_device_gps_config"),
    ("device_gps", "group_remote_gps_manager", "group_device_gps_manager"),
    ("device_gps", "group_remote_gps_user", "group_device_gps_user"),
    (
        "device_gps",
        "menu_remote_data_log_gps_report_activity",
        "menu_device_data_log_gps_report_activity",
    ),
    (
        "device_gps",
        "menu_remote_data_log_gps_report_distance",
        "menu_device_data_log_gps_report_distance",
    ),
    (
        "device_gps",
        "menu_remote_data_log_gps_report_fuel",
        "menu_device_data_log_gps_report_fuel",
    ),
    (
        "device_gps",
        "menu_remote_data_log_gps_report_main",
        "menu_device_data_log_gps_report_main",
    ),
    (
        "device_gps",
        "menu_remote_data_log_gps_report_speed",
        "menu_device_data_log_gps_report_speed",
    ),
    ("device_gps", "menu_remote_gps_analysis", "menu_device_gps_analysis"),
    ("device_gps", "menu_remote_gps_analysis_daily", "menu_device_gps_analysis_daily"),
    ("device_gps", "menu_remote_gps_analysis_fuel", "menu_device_gps_analysis_fuel"),
    ("device_gps", "menu_remote_gps_config", "menu_device_gps_config"),
    ("device_gps", "menu_remote_gps_raw_data", "menu_device_gps_raw_data"),
    ("device_gps", "menu_remote_gps_trackers", "menu_device_gps_trackers"),
    ("device_gps", "menu_remote_gps_tracking_logs", "menu_device_gps_tracking_logs"),
    (
        "device_gps",
        "remote_data_log_gps_company_rule",
        "device_data_log_gps_company_rule",
    ),
    (
        "device_gps",
        "remote_data_log_gps_report_company_rule",
        "device_data_log_gps_report_company_rule",
    ),
    (
        "device_gps",
        "view_remote_config_form_inherit_gps",
        "view_device_profile_form_inherit_gps",
    ),
    (
        "device_gps",
        "view_remote_config_list_inherit_gps",
        "view_device_profile_list_inherit_gps",
    ),
    (
        "device_gps",
        "view_remote_config_search_inherit_gps",
        "view_device_profile_search_inherit_gps",
    ),
    ("device_gps", "view_remote_data_log_gps_form", "view_device_data_log_gps_form"),
    (
        "device_gps",
        "view_remote_data_log_gps_report_graph_activity",
        "view_device_data_log_gps_report_graph_activity",
    ),
    (
        "device_gps",
        "view_remote_data_log_gps_report_graph_distance",
        "view_device_data_log_gps_report_graph_distance",
    ),
    (
        "device_gps",
        "view_remote_data_log_gps_report_graph_fuel",
        "view_device_data_log_gps_report_graph_fuel",
    ),
    (
        "device_gps",
        "view_remote_data_log_gps_report_graph_speed",
        "view_device_data_log_gps_report_graph_speed",
    ),
    (
        "device_gps",
        "view_remote_data_log_gps_report_list",
        "view_device_data_log_gps_report_list",
    ),
    (
        "device_gps",
        "view_remote_data_log_gps_report_pivot",
        "view_device_data_log_gps_report_pivot",
    ),
    (
        "device_gps",
        "view_remote_data_log_gps_report_search",
        "view_device_data_log_gps_report_search",
    ),
    (
        "device_gps",
        "view_remote_data_log_gps_report_search_activity",
        "view_device_data_log_gps_report_search_activity",
    ),
    (
        "device_gps",
        "view_remote_data_log_gps_report_search_by_vehicle",
        "view_device_data_log_gps_report_search_by_vehicle",
    ),
    (
        "device_gps",
        "view_remote_data_log_gps_search",
        "view_device_data_log_gps_search",
    ),
    ("device_gps", "view_remote_data_log_gps_tree", "view_device_data_log_gps_tree"),
    ("device_gps", "view_remote_device_form", "view_device_device_form"),
    (
        "device_gps",
        "view_remote_device_kanban_gps_dashboard",
        "view_device_device_kanban_gps_dashboard",
    ),
    ("device_gps", "view_remote_device_list", "view_device_device_list"),
    ("device_gps", "view_remote_device_search", "view_device_device_search"),
    (
        "device_gps_geoengine",
        "access_remote_client_visit_manager",
        "access_device_client_visit_manager",
    ),
    (
        "device_gps_geoengine",
        "access_remote_client_visit_user",
        "access_device_client_visit_user",
    ),
    (
        "device_gps_geoengine",
        "access_remote_geo_fence_editor",
        "access_device_geo_fence_editor",
    ),
    (
        "device_gps_geoengine",
        "access_remote_geo_fence_manager",
        "access_device_geo_fence_manager",
    ),
    (
        "device_gps_geoengine",
        "access_remote_geo_fence_user",
        "access_device_geo_fence_user",
    ),
    (
        "device_gps_geoengine",
        "access_remote_state_boundary_manager",
        "access_device_state_boundary_manager",
    ),
    (
        "device_gps_geoengine",
        "access_remote_state_boundary_user",
        "access_device_state_boundary_user",
    ),
    (
        "device_gps_geoengine",
        "access_remote_weekday_manager",
        "access_device_weekday_manager",
    ),
    (
        "device_gps_geoengine",
        "access_remote_weekday_user",
        "access_device_weekday_user",
    ),
    (
        "device_gps_geoengine",
        "action_remote_client_visit",
        "action_device_client_visit",
    ),
    (
        "device_gps_geoengine",
        "action_remote_device_gps_map",
        "action_device_device_gps_map",
    ),
    (
        "device_gps_geoengine",
        "group_remote_gps_geofence_editor",
        "group_device_gps_geofence_editor",
    ),
    ("device_gps_geoengine", "menu_remote_client_visit", "menu_device_client_visit"),
    (
        "device_gps_geoengine",
        "raster_layer_remote_data_log_gps_carto_dark",
        "raster_layer_device_data_log_gps_carto_dark",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_data_log_gps_carto_light",
        "raster_layer_device_data_log_gps_carto_light",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_data_log_gps_esri_satellite",
        "raster_layer_device_data_log_gps_esri_satellite",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_data_log_gps_google_hybrid",
        "raster_layer_device_data_log_gps_google_hybrid",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_data_log_gps_google_sat",
        "raster_layer_device_data_log_gps_google_sat",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_data_log_gps_google_terrain",
        "raster_layer_device_data_log_gps_google_terrain",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_data_log_gps_osm",
        "raster_layer_device_data_log_gps_osm",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_data_log_gps_topo",
        "raster_layer_device_data_log_gps_topo",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_device_carto_dark",
        "raster_layer_device_device_carto_dark",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_device_carto_light",
        "raster_layer_device_device_carto_light",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_device_esri_satellite",
        "raster_layer_device_device_esri_satellite",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_device_google_hybrid",
        "raster_layer_device_device_google_hybrid",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_device_google_sat",
        "raster_layer_device_device_google_sat",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_device_google_terrain",
        "raster_layer_device_device_google_terrain",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_device_osm",
        "raster_layer_device_device_osm",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_device_topo",
        "raster_layer_device_device_topo",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_geo_fence_carto_dark",
        "raster_layer_device_geo_fence_carto_dark",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_geo_fence_carto_light",
        "raster_layer_device_geo_fence_carto_light",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_geo_fence_esri_satellite",
        "raster_layer_device_geo_fence_esri_satellite",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_geo_fence_google_hybrid",
        "raster_layer_device_geo_fence_google_hybrid",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_geo_fence_google_sat",
        "raster_layer_device_geo_fence_google_sat",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_geo_fence_google_terrain",
        "raster_layer_device_geo_fence_google_terrain",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_geo_fence_osm",
        "raster_layer_device_geo_fence_osm",
    ),
    (
        "device_gps_geoengine",
        "raster_layer_remote_geo_fence_topo",
        "raster_layer_device_geo_fence_topo",
    ),
    (
        "device_gps_geoengine",
        "remote_client_visit_company_rule",
        "device_client_visit_company_rule",
    ),
    (
        "device_gps_geoengine",
        "remote_geo_fence_company_rule",
        "device_geo_fence_company_rule",
    ),
    (
        "device_gps_geoengine",
        "vector_layer_remote_data_log_gps_points",
        "vector_layer_device_data_log_gps_points",
    ),
    (
        "device_gps_geoengine",
        "vector_layer_remote_device_client_locations",
        "vector_layer_device_device_client_locations",
    ),
    (
        "device_gps_geoengine",
        "vector_layer_remote_device_location",
        "vector_layer_device_device_location",
    ),
    (
        "device_gps_geoengine",
        "vector_layer_remote_geo_fence_boundaries",
        "vector_layer_device_geo_fence_boundaries",
    ),
    (
        "device_gps_geoengine",
        "view_remote_client_visit_list",
        "view_device_client_visit_list",
    ),
    (
        "device_gps_geoengine",
        "view_remote_client_visit_search",
        "view_device_client_visit_search",
    ),
    (
        "device_gps_geoengine",
        "view_remote_data_log_gps_map",
        "view_device_data_log_gps_map",
    ),
    (
        "device_gps_geoengine",
        "view_remote_device_form_geofence",
        "view_device_device_form_geofence",
    ),
    (
        "device_gps_geoengine",
        "view_remote_device_geoengine",
        "view_device_device_geoengine",
    ),
    (
        "device_gps_geoengine",
        "view_remote_device_search_gps_trail",
        "view_device_device_search_gps_trail",
    ),
    (
        "device_gps_geoengine",
        "view_remote_geo_fence_form",
        "view_device_geo_fence_form",
    ),
    (
        "device_gps_geoengine",
        "view_remote_geo_fence_kanban",
        "view_device_geo_fence_kanban",
    ),
    ("device_gps_geoengine", "view_remote_geo_fence_map", "view_device_geo_fence_map"),
    (
        "device_gps_geoengine",
        "view_remote_geo_fence_search",
        "view_device_geo_fence_search",
    ),
    (
        "device_gps_geoengine",
        "view_remote_geo_fence_tree",
        "view_device_geo_fence_tree",
    ),
    (
        "device_machines",
        "access_remote_device_mrp_user",
        "access_device_device_mrp_user",
    ),
    (
        "device_machines",
        "access_remote_machine_bucket_manager",
        "access_device_machine_bucket_manager",
    ),
    (
        "device_machines",
        "access_remote_machine_bucket_mrp_user",
        "access_device_machine_bucket_mrp_user",
    ),
    (
        "device_machines",
        "access_remote_machine_bucket_user",
        "access_device_machine_bucket_user",
    ),
    (
        "device_machines",
        "access_remote_machine_reading_manager",
        "access_device_machine_reading_manager",
    ),
    (
        "device_machines",
        "access_remote_machine_reading_user",
        "access_device_machine_reading_user",
    ),
    (
        "device_machines",
        "access_remote_machine_workorder_manager",
        "access_device_machine_workorder_manager",
    ),
    (
        "device_machines",
        "access_remote_machine_workorder_mrp_user",
        "access_device_machine_workorder_mrp_user",
    ),
    (
        "device_machines",
        "access_remote_machine_workorder_user",
        "access_device_machine_workorder_user",
    ),
    ("device_machines", "action_remote_machine_bucket", "action_device_machine_bucket"),
    (
        "device_machines",
        "action_remote_machine_bucket_from_device",
        "action_device_machine_bucket_from_device",
    ),
    (
        "device_machines",
        "action_remote_machine_devices",
        "action_device_machine_devices",
    ),
    ("device_machines", "menu_remote_machine", "menu_device_machine"),
    ("device_machines", "menu_remote_machine_bucket", "menu_device_machine_bucket"),
    (
        "device_machines",
        "menu_remote_machine_bucket_section",
        "menu_device_machine_bucket_section",
    ),
    (
        "device_machines",
        "remote_machine_workorder_action",
        "device_machine_workorder_action",
    ),
    (
        "device_machines",
        "remote_machine_workorder_menu",
        "device_machine_workorder_menu",
    ),
    (
        "device_machines",
        "remote_machine_workorder_view_form",
        "device_machine_workorder_view_form",
    ),
    (
        "device_machines",
        "remote_machine_workorder_view_graph",
        "device_machine_workorder_view_graph",
    ),
    (
        "device_machines",
        "remote_machine_workorder_view_list",
        "device_machine_workorder_view_list",
    ),
    (
        "device_machines",
        "remote_machine_workorder_view_pivot",
        "device_machine_workorder_view_pivot",
    ),
    (
        "device_machines",
        "view_remote_device_form_inherit_remote_machines",
        "view_device_device_form_inherit_device_machines",
    ),
    (
        "device_machines",
        "view_remote_device_list_inherit_remote_machines",
        "view_device_device_list_inherit_device_machines",
    ),
    (
        "device_machines",
        "view_remote_machine_bucket_form",
        "view_device_machine_bucket_form",
    ),
    (
        "device_machines",
        "view_remote_machine_bucket_list",
        "view_device_machine_bucket_list",
    ),
    (
        "device_machines",
        "view_remote_machine_bucket_search",
        "view_device_machine_bucket_search",
    ),
    ("device_machines", "view_remote_machine_list", "view_device_machine_list"),
    (
        "device_mobile",
        "access_remote_call_log_manager",
        "access_device_call_log_manager",
    ),
    ("device_mobile", "access_remote_call_log_user", "access_device_call_log_user"),
    (
        "device_mobile",
        "access_remote_call_recording_manager",
        "access_device_call_recording_manager",
    ),
    (
        "device_mobile",
        "access_remote_call_recording_user",
        "access_device_call_recording_user",
    ),
    ("device_mobile", "action_remote_call_log", "action_device_call_log"),
    ("device_mobile", "action_remote_call_recording", "action_device_call_recording"),
    ("device_mobile", "menu_remote_call_log", "menu_device_call_log"),
    ("device_mobile", "menu_remote_call_recording", "menu_device_call_recording"),
    ("device_mobile", "rule_remote_call_log_company", "rule_device_call_log_company"),
    (
        "device_mobile",
        "rule_remote_call_recording_company",
        "rule_device_call_recording_company",
    ),
    (
        "device_mobile",
        "view_partner_form_remote_calls",
        "view_partner_form_device_calls",
    ),
    ("device_mobile", "view_remote_call_log_form", "view_device_call_log_form"),
    ("device_mobile", "view_remote_call_log_list", "view_device_call_log_list"),
    ("device_mobile", "view_remote_call_log_search", "view_device_call_log_search"),
    (
        "device_mobile",
        "view_remote_call_recording_form",
        "view_device_call_recording_form",
    ),
    (
        "device_mobile",
        "view_remote_call_recording_list",
        "view_device_call_recording_list",
    ),
    (
        "device_mobile_speech",
        "view_remote_call_log_form_speech",
        "view_device_call_log_form_speech",
    ),
    (
        "device_mobile_speech",
        "view_remote_call_recording_form_speech",
        "view_device_call_recording_form_speech",
    ),
    (
        "device_modbus",
        "view_remote_config_form_modbus",
        "view_device_profile_form_modbus",
    ),
    (
        "device_modbus",
        "view_remote_device_form_modbus",
        "view_device_device_form_modbus",
    ),
    ("device_mqtt", "view_remote_config_form_mqtt", "view_device_profile_form_mqtt"),
    ("device_mqtt", "view_remote_device_form_mqtt", "view_device_device_form_mqtt"),
    (
        "device_websocket",
        "view_remote_config_form_websocket",
        "view_device_profile_form_websocket",
    ),
)

RELATIONS = (("remote_geo_fence_weekday_rel", "device_geo_fence_weekday_rel"),)

REPORT_VIEWS = ("remote_data_log_report", "remote_data_log_gps_report")


def migrate(cr, version):
    if not version:
        return
    # A materialized report is rebuilt by its mixin under the new name; a
    # rolling report is a table and is renamed with its rows.
    for view in REPORT_VIEWS:
        cr.execute("SELECT 1 FROM pg_matviews WHERE matviewname = %s", [view])
        if cr.fetchone():
            cr.execute(SQL("DROP MATERIALIZED VIEW %s CASCADE", SQL.identifier(view)))
    for old, new in MODELS:
        rename_model(cr, old, new)
        cr.execute(
            "UPDATE integration_exchange SET origin_model = %s WHERE origin_model = %s",
            [new, old],
        )
    for old, new in RELATIONS:
        if table_exists(cr, old) and not table_exists(cr, new):
            _rename_table_with_dependents(cr, old, new)
            cr.execute(
                "UPDATE ir_model_fields SET relation_table = %s "
                "WHERE relation_table = %s",
                [new, old],
            )
            cr.execute(
                "UPDATE ir_model_relation SET name = %s WHERE name = %s", [new, old]
            )
    for module, old, new in XMLIDS:
        cr.execute(
            "UPDATE ir_model_data SET name = %s WHERE module = %s AND name = %s "
            "AND NOT EXISTS (SELECT 1 FROM ir_model_data d "
            "WHERE d.module = %s AND d.name = %s)",
            [new, module, old, module, new],
        )
        cr.execute(
            "UPDATE ir_ui_view SET key = %s WHERE key = %s",
            [f"{module}.{new}", f"{module}.{old}"],
        )
