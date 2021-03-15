from odoo import models, fields, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import RedirectWarning2
import inspect

class RedirectWizard(models.TransientModel):
    _name = "redirect.wizard"
    _description = "redirect"
    method = fields.Char()
    records = fields.Char()
    context = fields.Text()
    arguments = fields.Text()
    text = fields.Char(readonly=True)

    def check_confirm(self, redirect_text, *args, redirect_records=None, redirect_method=None, **kwargs):
        if not redirect_records or not redirect_method:
            frame = inspect.currentframe().f_back
            redirect_method = redirect_method or frame.f_code.co_name
            argspec = inspect.getfullargspec(getattr(frame.f_locals["self"], redirect_method))
            kwargs = {kw: frame.f_locals.get(kw) for kw in argspec.args}
            args = frame.f_locals.get(argspec.varargs) or []
            redirect_records = kwargs.pop('self')
        if not self._is_redirected(redirect_records, redirect_method):
            raise RedirectWarning2(
                *args,
                redirect_text=redirect_text,
                redirect_records=redirect_records,
                redirect_method=redirect_method,
                **kwargs,
            )

    def redirect(self, *args, redirect_text, redirect_records, redirect_method, **kwargs):
        context = dict(self.env.context)
        func_key = '%s.%s' % (redirect_records._name, redirect_method)
        redirected = context.setdefault('redirected', {})
        redirected.setdefault(func_key, self._format_record(redirect_records.browse()))
        redirected[func_key] = self._format_record(
            self._parse_model(redirected[func_key]) | redirect_records
        )
        redirect_id = self.create({
            'method': redirect_method,
            'records': self._format_record(redirect_records),
            'context': context,
            'text': redirect_text,
            'arguments': {
                'args': args,
                'kwargs': kwargs,
            }
        })
        return {
            'name': _('Confirm'),
            'res_model': 'redirect.wizard',
            'res_id': redirect_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def confirm(self):
        arguments = safe_eval(self.arguments)
        context = safe_eval(self.context)
        records = self._parse_model(self.records).with_context(context)
        getattr(records, self.method)(*arguments['args'], **arguments['kwargs'])
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _is_redirected(self, records, method):
        redirected = self.env.context.get('redirected', {})
        func_key = '%s.%s' % (records._name, method)
        return records in self._parse_model(redirected.get(
            func_key,
            self._format_record(records.browse()),
        ))

    def _parse_model(self, rec_string):
        model_name, model_ids = rec_string.split('|')
        ids = [int(i) for i in model_ids.split(',') if i]
        return self.env[model_name].browse(ids)

    def _format_record(self, records):
        return f"{records._name}|{','.join(str(id) for id in records.ids)}"
