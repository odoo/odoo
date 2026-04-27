from odoo.tests import common


class MarketingAutomationWACase(common.TransactionCase):

    @classmethod
    def setUpWhatsapp(cls):
        cls.wa_tracked_btn_url = 'https://www.tracked.button.com'
        cls.wa_tracked_body_url = 'https://www.tracked.body.com'
        cls.wa_dynamic_btn_url = 'https://www.dynamic.com'

    @classmethod
    def _create_wa_template(cls, model, user=None, **template_values):
        vals = {
            'button_ids': [
                (0, 0, {
                    'button_type': 'url',
                    'name': 'url_tracked',
                    'sequence': 0,
                    'url_type': 'tracked',
                    'website_url': cls.wa_tracked_btn_url,
                }),
                (0, 0, {
                    'sequence': 1,
                    'button_type': 'url',
                    'name': 'url_dynamic',
                    'url_type': 'dynamic',
                    'website_url': cls.wa_dynamic_btn_url,
                }),
            ],
            'model_id': cls.env['ir.model']._get_id(model),
            'name': f'WA Template for {model}',
            'phone_field': 'phone',
            'status': 'approved',
            'wa_account_id': cls.whatsapp_account.id,
        }
        vals.update(**template_values)
        if 'body' not in vals:
            vals.update({
                'body': 'Hello {{1}}',
                'variable_ids': [
                    (0, 0, {
                        "name": "{{1}}",
                        "line_type": "body",
                        "field_type": "free_text",
                        "demo_value": "your much wow template value",
                    }),
                ],
            })
        return cls.env['whatsapp.template'].create(vals)
