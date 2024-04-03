# -*- coding: utf-8 -*-


def migrate(cr, version):
    """ From 12.0, to saas-13.3, l10n_ch_swissqr_template
    used to inherit from another template. This isn't the case
    anymore since https://github.com/odoo/odoo/commit/719f087b1b5be5f1f276a0f87670830d073f6ef4
    (made in 12.0, and forward-ported). The module will not be updatable if we
    don't manually clean inherit_id.
    """
    cr.execute("""
        update ir_ui_view v
        set inherit_id = NULL, mode='primary'
        from ir_model_data mdata
        where
        v.id = mdata.res_id
        and mdata.model= 'ir.ui.view'
        and mdata.name = 'l10n_ch_swissqr_template'
        and mdata.module='l10n_ch';
    """)