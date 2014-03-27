# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class EmailTemplateWizard(osv.TransientModel):
    """A wizard allowing to create an email.template from a mass mailing. This wizard
    allows to simplify and direct the user in the creation of its template without
    having to tune or hack the email.template model. """
    _name = 'mailing.email.template.wizard'

    def default_get(self, cr, uid, fields, context=None):
        res = super(EmailTemplateWizard, self).default_get(cr, uid, fields, context=context)
        if res.get('mass_mailing_id') and not 'name' in res:
            mailing_ng = self.pool['mail.mass_mailing'].name_get(cr, uid, [res.get('mass_mailing_id')], context=context)
            res['name'] = mailing_ng[0][1]
        return res

    def _get_model_list(self, cr, uid, context=None):
        return self.pool['mail.mass_mailing']._get_mailing_model(cr, uid, context=context)

    # indirections for inheritance
    _model_list = lambda self, *args, **kwargs: self._get_model_list(*args, **kwargs)

    _columns = {
        'name': fields.char('Name', required=True),
        'body': fields.html('Body'),
        'template_id': fields.many2one('email.template', 'Basis Template'),
        'mass_mailing_id': fields.many2one('mail.mass_mailing', 'Mass Mailing', required=True),
        'attachment_ids': fields.many2many(
            'ir.attachment', 'email_template_wizard_attachment_rel', 'email_template_id',
            'attachment_id', 'Attachments'),
    }

    def on_change_template_id(self, cr, uid, ids, template_id, context=None):
        if template_id:
            template = self.pool['email.template'].browse(cr, uid, template_id, context=context)
            return {'value': {'body': template.body_html, 'attachment_ids': [(4, att.id) for att in template.attachment_ids]}}
        return {}

    def create_template(self, cr, uid, ids, context=None):
        EmailTemplate = self.pool['email.template']
        for wizard in self.browse(cr, uid, ids, context=context):
            model_ids = self.pool['ir.model'].search(cr, uid, [('model', '=', wizard.mass_mailing_id.mailing_model)], context=context)
            values = {
                'name': wizard.name,
                'model_id': model_ids[0],
                'body_html': wizard.body,
                'use_in_mass_mailing': True,
                'use_default_to': True,
                'attachment_ids': [(4, attach.id) for attach in wizard.attachment_ids],
            }
            tpl_id = EmailTemplate.create(cr, uid, values, context=context)
            self.pool['mail.mass_mailing'].write(cr, uid, [wizard.mass_mailing_id.id], {'template_id': tpl_id}, context=context)
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.mass_mailing',
            'res_id': wizard.mass_mailing_id.id,
            'target': 'current',
            'context': context,
        }
