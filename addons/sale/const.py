# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Mapping of config parameters to the crons they toggle.
PARAM_CRON_MAPPING = {
    'sale.async_emails': 'sale.send_pending_emails_cron',
    'sale.automatic_invoice': 'sale.send_invoice_cron',
}
