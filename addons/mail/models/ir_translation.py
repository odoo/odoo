# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import AccessError


class IrTranslation(models.Model):
    _inherit = 'ir.translation'

    def create(self, vals_list):
        translations = super().create(vals_list)
        translations._check_is_dynamic()
        return translations

    def write(self, vals):
        res = super().write(vals)
        self._check_is_dynamic()
        return res

    def _check_is_dynamic(self):
        # if we don't modify translation of at least a model that inherits from mail.render.mixin, we ignore it
        # translation.name can be a path, and so not in the pool, so type(None) will exclude these translations.
        translations_for_mail_render_mixin = self.filtered(
            lambda translation: issubclass(type(self.env.get(translation.name.split(',')[0])), self.pool['mail.render.mixin'])
        )
        if not translations_for_mail_render_mixin:
            return

        # if we are admin, or that we can update mail.template we ignore
        if self.env.is_admin() or self.env.user.has_group('mail.group_mail_template_editor'):
            return

        # Check that we don't add qweb code in translation when you don't have the rights

        # prefill cache
        ids_by_model_by_lang = {}
        tuple_lang_model_id = translations_for_mail_render_mixin.mapped(
            lambda translation: (translation.lang, translation.name.split(',')[0], translation.res_id)
        )
        for lang, model, _id in tuple_lang_model_id:
            ids_by_model_by_lang.setdefault(lang, {}).setdefault(model, set()).add(_id)
        for lang in ids_by_model_by_lang:
            for res_model, res_ids in ids_by_model_by_lang[lang].items():
                self.env[res_model].with_context(lang=lang).browse(res_ids)

        for trans in translations_for_mail_render_mixin:
            res_model, res_id = trans.name.split(',')[0], trans.res_id
            rec = self.env[res_model].with_context(lang=trans.lang).browse(res_id)

            if rec._is_dynamic():
                group = self.env.ref('mail.group_mail_template_editor')
                more_info = len(self) > 1 and ' [%s]' % rec or ''
                raise AccessError(
                    _('Only users belonging to the "%(group)s" group can modify translation related to dynamic templates.%(xtra)s',
                      group=group.name,
                      xtra=more_info
                    )
                )
