import logging

from odoo import models, SUPERUSER_ID
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class ApiAlien(models.AbstractModel):
    _name = 'kw.api.alien'
    _inherit = ['kw.datetime.extract.mixin', ]
    _description = 'API alien'

    def api_get_inbound_field_pairs(self, rec, **kw):
        if hasattr(rec, 'kw_api_get_inbound_field_pairs'):
            return rec.kw_api_get_inbound_field_pairs(**kw)
        return {f: f for f in rec._fields}

    def api_get_outbound_field_pairs(self, rec, **kw):
        if hasattr(rec, 'kw_api_get_outbound_field_pairs'):
            return rec.kw_api_get_outbound_field_pairs(**kw)
        return [{'field_name': f, 'api_name': f} for f in rec._fields]

    def api_get_data(self, rec, **kw):
        if hasattr(rec, 'kw_api_get_data'):
            return rec.kw_api_get_data(**kw)
        return [self.api_get_record_value(obj, **kw) for obj in rec]

    def api_get_record_value(self, rec, **kw):
        if hasattr(rec, 'kw_api_get_record_value'):
            return rec.kw_api_get_record_value(**kw)
        if not rec:
            return False
        rec.ensure_one()
        outbound_field_pairs = kw.get('outbound_field_pairs')
        if not outbound_field_pairs:
            outbound_field_pairs = self.api_get_outbound_field_pairs(rec, **kw)
        res = {'id': rec.id, 'write_date': rec.write_date, }
        for field in outbound_field_pairs:
            res.update(self.api_get_field_value(rec, **field))
        return res

    # pylint: disable=too-many-branches, too-many-statements
    def api_get_field_value(self, rec, field_name, api_name='', **kw):
        if hasattr(rec, 'kw_api_get_field_value'):
            return rec.kw_api_get_field_value(
                field_name=field_name, api_name=api_name, **kw)
        if not rec:
            return {}
        rec.ensure_one()
        if not hasattr(rec, str(field_name)):
            return {}
        api_name = api_name or field_name
        res = {api_name: getattr(rec, field_name)}
        field = rec._fields[field_name]
        if field.translate:
            res = self.api_get_translations(rec, field_name, api_name)
        elif field.type == 'many2one':
            res = {
                api_name: self.api_get_short_value(getattr(rec, field_name))}
        elif field.type in ['many2many', 'one2many', ]:
            field_value = getattr(rec, field_name)
            res = {api_name: []}
            for x in field_value:
                res[api_name].append(self.api_get_short_value(x))
        elif field.type == 'binary':
            if rec._name == 'ir.attachment':
                domain = [('id', '=', rec.id)]
            else:
                domain = [('res_id', '=', rec.id),
                          ('res_model', '=', rec._name),
                          ('res_field', '=', field_name), ]
            attachment = self.env['ir.attachment'].sudo().search(
                domain, limit=1, order='create_date DESC')
            if attachment.file_size:
                burl = self.env['ir.config_parameter'].sudo().get_param(
                    'web.base.url')
                url = f'{burl}/kw_api/image/{rec._name}/{rec.id}/{field_name}'
            else:
                url = False
            res = {
                f'{field_name}_url': url,
                f'{field_name}_updated': attachment.write_date,
                f'{field_name}_checksum': attachment.checksum,
                f'{field_name}_file_size': attachment.file_size,
                f'{field_name}_mimetype': attachment.mimetype, }
        if field.type in ['char', 'text']:
            false_if_empty = bool(self.env['ir.config_parameter'].sudo(
            ).get_param(key='kw_api.kw_api_use_false_if_empty'))
            if not false_if_empty:
                for item in res:
                    if not res[item]:
                        res[item] = ''
        return res

    def api_get_short_value(self, rec, **kw):
        if hasattr(rec, 'kw_api_get_short_value'):
            return rec.kw_api_get_short_value(**kw)
        if not rec:
            return {}
        rec.ensure_one()
        res = {'id': rec.id, }
        if hasattr(rec, 'name'):
            res.update(self.api_get_translations(rec, 'name'))
        # name = record.name if hasattr(record, 'name')
        # else record.name_get()[0][1]
        return res

    def api_get_translations(self, rec, field_name, api_name='', **kw):
        if hasattr(rec, 'kw_api_get_translations'):
            return rec.kw_api_get_translations(
                field_name=field_name, api_name=api_name, **kw)
        rec.ensure_one()
        api_name = api_name or field_name
        field = rec._fields[field_name]
        res = {api_name: getattr(rec, field_name), }
        if not field.translate:
            return res
        for lang in self.env['res.lang'].sudo().search([]):
            res[f'{api_name}_{lang.iso_code}'] = getattr(
                rec.with_context(lang=lang.code), field_name)
        return res

    def api_search(self, model_name, **kw):
        model = self.env[model_name].with_user(kw.get('user', SUPERUSER_ID))
        if hasattr(model, 'kw_api_search'):
            return model.kw_api_search(**kw)
        domain = kw.get('domain', [])
        if isinstance(domain, str):
            try:
                domain = safe_eval(domain)
            except Exception as e:
                _logger.debug(e)
                domain = []
        if kw.get('update_date'):
            update_date = kw.get('update_date')
            update_date = self.kw_mining_datetime(update_date, silent='True')
            domain.append(('write_date', '>', update_date))
        return model.search(domain)

    def prepare_inbound_x2many_data(self, model_name, data, **kw):
        m = self.env[model_name].sudo()
        if hasattr(m, 'prepare_inbound_x2many_data'):
            return m.prepare_inbound_x2many_data(data, **kw)
        for x in data.keys():
            if m._fields[x].type in ['many2many', 'one2many', ]:
                data[x] = self.prepare_inbound_x2many_field(
                    model_name, x, data[x], **kw)
        return data

    def prepare_inbound_x2many_field(
            self, model_name, field_name, data, **kw):
        m = self.env[model_name].sudo()
        if hasattr(m, 'prepare_inbound_x2many_field'):
            return m.prepare_inbound_x2many_field(data, **kw)
        res = []
        for line in data:
            if 'id' in line.keys():
                res.append((1, line['id'], line))
            else:
                res.append((0, 0, line))
        return res


class ApiMixin(models.AbstractModel):
    _name = 'kw.api.model.mixin'
    _inherit = ['kw.datetime.extract.mixin', ]
    _description = 'API model mixin'
