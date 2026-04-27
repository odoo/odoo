# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.


def post_init_hook(env):
    # UNSPSC category codes can be used in Mexico.
    product_unspsc = env['product.unspsc.code'].search([('active', '=', False), ('code', '=ilike', '%00')])
    product_unspsc.active = True

    # Initialize move mx payement_method_id after data files have been loaded.
    l10n_mx_edi_payment_method_id = env.ref('l10n_mx_edi.payment_method_otros', raise_if_not_found=False)
    if l10n_mx_edi_payment_method_id:
        env.cr.execute("""UPDATE account_move set l10n_mx_edi_payment_method_id = %s""", [l10n_mx_edi_payment_method_id.id])
