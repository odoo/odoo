# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

def _set_fiscal_country(env):
    """ Sets the fiscal country on existing companies when installing the module.
    That field is an editable computed field. It doesn't automatically get computed
    on existing records by the ORM when installing the module, so doing that by hand
    ensures existing records will get a value for it if needed.
    """
    env['res.company'].search([]).compute_account_tax_fiscal_country()


def _migrate_email_templates_to_body_view(env):
    """Set body_view_id on existing templates without clearing body_html.

    This preserves user customizations while enabling view inheritance for new
    installs. Existing body_html takes priority over body_view_id.
    """
    template_view_mapping = [
        ('account.email_template_edi_invoice', 'account.email_body_edi_invoice'),
        ('account.mail_template_data_payment_receipt', 'account.email_body_payment_receipt'),
        ('account.email_template_edi_credit_note', 'account.email_body_edi_credit_note'),
        ('account.email_template_edi_self_billing_invoice', 'account.email_body_edi_self_billing_invoice'),
        ('account.email_template_edi_self_billing_credit_note', 'account.email_body_edi_self_billing_credit_note'),
        ('account.mail_template_einvoice_notification', 'account.email_body_einvoice_notification'),
        ('account.mail_template_invoice_subscriber', 'account.email_body_invoice_subscriber'),
    ]
    for template_xmlid, view_xmlid in template_view_mapping:
        template = env.ref(template_xmlid, raise_if_not_found=False)
        view = env.ref(view_xmlid, raise_if_not_found=False)
        if template and view and not template.body_view_id:
            template.body_view_id = view


def _account_post_init(env):
    _set_fiscal_country(env)
    _migrate_email_templates_to_body_view(env)


# imported here to avoid dependency cycle issues
# pylint: disable=wrong-import-position
from . import controllers
from . import models
from . import demo
from . import wizard
from . import report
from . import tools
