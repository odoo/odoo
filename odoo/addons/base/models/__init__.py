from . import assetsbundle

from . import ir_model_common
from . import ir_model
from . import ir_model_fields

from . import mixin_hierarchy
from . import ir_model_fields_selection
from . import ir_model_reflection
from . import ir_model_access
from . import ir_model_data
from . import ir_sequence

from . import ir_ui_menu
from . import ir_ui_view_custom
from . import ir_ui_view
from . import ir_ui_view_base
from . import ir_ui_view_name_manager
from . import ir_asset_paths
from . import ir_asset

from . import mixin_table_inheritance_root
from . import ir_actions_actions
from . import ir_actions_path
from . import ir_actions_act_window_view
from . import ir_actions_act_window
from . import ir_actions_act_window_close
from . import ir_actions_act_url
from . import ir_actions_client
from . import ir_actions_todo
from . import ir_actions_server
from . import ir_actions_server_history
from . import ir_actions_embedded
from . import ir_actions_report

from . import ir_attachment_storage
from . import ir_attachment
from . import ir_attachment_assets
from . import ir_binary
from . import ir_egress

from . import mixin_recurrence_interval
from . import mixin_recurrence_anchored
from . import mixin_recurrence_rule
from . import mixin_recurrence_occurrence
from . import ir_cron
from . import ir_job
from . import ir_autovacuum

from . import ir_filters
from . import ir_default
from . import ir_rule
from . import ir_config_parameter


from . import ir_fields

from . import ir_qweb
from . import ir_qweb_assets
from . import ir_qweb_assets_import_map
from . import ir_qweb_assets_served_libs
from . import ir_qweb_assets_esbuild
from . import ir_qweb_assets_esbuild_circuit
from . import ir_qweb_fields

from . import ir_http
from . import ir_logging

from . import ir_module
from . import mixin_module_link
from . import ir_module_module_dependency
from . import ir_module_module_exclusion
from . import ir_demo
from . import ir_demo_failure

from . import properties_base_definition
from . import mixin_properties_base_definition
from . import report_paperformat

from . import ir_profile
from . import mixin_image
from . import mixin_avatar
from . import mixin_catalog
from . import mixin_lifecycle
from . import mixin_merge
from . import mixin_favorite
from . import mixin_user_favorite
from . import mixin_band
from . import mixin_color
from . import mixin_tag
from . import mixin_tag_nested
from . import tag_tag

from . import mixin_format_vat_label
from . import mixin_format_address
from . import res_partner_tag
from . import res_partner_industry
from . import res_country
from . import res_lang
from . import phone_number
from . import res_partner
from . import res_partner_identifier
from . import res_partner_identifier_type

# After res_partner: mixin.recurrence.rrule takes its timezone selection
# from _selection_timezones, so importing it earlier evaluates res_partner
# before the mixins it inherits are registered. The other recurrence mixins
# are imported before ir_cron, which inherits the interval one.
from . import mixin_recurrence_rrule


from . import res_bank
from . import res_config
from . import res_currency
from . import res_company

from . import res_groups_privilege
from . import res_groups
from . import res_users_log
from . import res_users_login_cooldown
from . import res_users
from . import res_users_identitycheck
from . import res_users_apikeys
from . import res_users_settings
from . import res_users_deletion
from . import res_device

from . import decimal_precision

from . import kpi_provider
