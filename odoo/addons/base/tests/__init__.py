# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import common
from . import test_avatar_mixin
from . import test_ir_access_token
from . import test_ir_actions
from . import test_ir_actions_report
from . import test_ir_asset
from . import test_ir_attachment
from . import test_ir_config_parameter
from . import test_ir_cron
from . import test_ir_default
from . import test_ir_embedded_actions
from . import test_ir_filters
from . import test_ir_http
from . import test_ir_mail_server
from . import test_ir_mail_server_smtpd
from . import test_ir_model
from . import test_ir_module
from . import test_ir_qweb
from . import test_ir_qweb_fields
from . import test_ir_sequence
from . import test_ir_ui_menu
from . import test_ir_ui_view
from . import test_res_company
from . import test_res_config
from . import test_res_country
from . import test_res_currency
from . import test_res_groups
from . import test_res_groups_data
from . import test_res_lang
from . import test_res_partner
from . import test_res_partner_addresses
from . import test_res_partner_bank
from . import test_res_users
from . import test_res_users_has_group
from . import test_wizard_base_partner_merge


def warmup_cache(env, suite, _logger):
    has_http_case = suite.has_http_case()
    if has_http_case:
        _logger.info('Pregeneration assets_bundles')
        env['ir.qweb']._pregenerate_assets_bundles()
        env.cr.commit()
    _logger.info('Populating routing cache')
    env['ir.http'].routing_map()

    _logger.info('Populating _get_group_definitions cache')
    env['res.groups']._get_group_definitions()
    _logger.info('Populating _get_allowed_models cache')
    admin = env.ref('base.user_admin')
    admin_env = env(env.cr, admin.id, {})
    admin_env['ir.model.access']._get_allowed_models('read')
    admin_env['ir.model.access']._get_allowed_models('write')
    admin_env['ir.model.access']._get_allowed_models('create')
    admin_env['ir.model.access']._get_allowed_models('unlink')

    _logger.info('Populating ir.rule and ir.model.fields cache')
    for model in env:
        if model in ('res.partner', 'res.company', 'ir.ui.view', 'product.template'):
            _logger.info('Populating ir.model.fields cache for model %s' % model)
            # this list of model was taken taking using the top  number of call of _get_fields_cached
            for lang in None, 'en_US':
                env['ir.model.fields'].with_context(lang=lang)._get_fields_cached(model)
        if model in ('mail.message.subtype', 'discuss.channel', 'stock.route', 'res.company', 'res.partner'):
            _logger.info('Populating ir.rule cache for model %s' % model)
            # this list of model was taken taking using the top  number of call of _compute_domain
            admin_env['ir.rule']._compute_domain(model, 'read')
            admin_env['ir.rule'].with_context(allowed_company_ids=admin_env.user._get_company_ids())._compute_domain(model, 'read')
