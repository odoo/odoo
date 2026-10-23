import json
import logging
import math

import psycopg2
from html2text import html2text

from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.http import request
from odoo.osv.expression import AND
from odoo.tools import format_datetime

from odoo.tools.safe_eval import safe_eval
from odoo.tools.safe_eval import time as safe_eval_time
from odoo.tools.safe_eval import datetime as safe_eval_datetime
from odoo.tools.safe_eval import dateutil as safe_eval_dateutil
from odoo.tools.safe_eval import pytz as safe_eval_pytz
from odoo.tools.safe_eval import json as safe_eval_json

from odoo.addons.base.models.res_partner import _tz_get


_logger = logging.getLogger(__name__)


class CustomEndpoint(models.Model):
    _name = 'kw.api.custom.endpoint'
    _description = 'API custom endpoint'

    name = fields.Char(
        required=True, )
    active = fields.Boolean(
        default=True, )
    api_name = fields.Char(
        required=True, )
    kind = fields.Selection(
        default='fields', selection=[
            ('fields', _('Fields')), ('function', 'Function')])
    is_paginated = fields.Boolean(
        default=True, )
    model_id = fields.Many2one(
        comodel_name='ir.model', required=True, ondelete='cascade',
        # domain=[('transient', '=', False), ('is_abstract', '=', False)])
        domain=[('transient', '=', False), ])
    model_id_field = fields.Char(
        string='Model ID Field',
        default='id')
    field_ids = fields.One2many(
        comodel_name='kw.api.custom.endpoint.field',
        inverse_name='endpoint_id', )
    url = fields.Char(
        compute='_compute_url', )
    is_list_enabled = fields.Boolean(
        default=True, )
    is_get_enabled = fields.Boolean(
        default=True, )
    is_create_enabled = fields.Boolean()

    is_update_enabled = fields.Boolean()

    is_delete_enabled = fields.Boolean()

    is_token_required = fields.Boolean()

    is_api_key_required = fields.Boolean(
        default=True, )
    is_json_required = fields.Boolean(
        default=True, )
    is_cors_required = fields.Boolean()

    description = fields.Text(
        compute='_compute_description', )
    domain = fields.Char()

    model_model = fields.Char(
        related='model_id.model', )
    response_function = fields.Char()

    force_response_tz = fields.Selection(
        selection=_tz_get, )

    logging_is_required = fields.Boolean(default=True)
    log_expire_days = fields.Integer(default=1)

    logs_count = fields.Integer(string='Logs count',
                                compute='_compute_logs_count')

    def _compute_logs_count(self):
        for rec in self:
            rec.logs_count = self.env['kw.api.log'].search_count(
                [('name', '=', rec.url)]
            )

    def action_view_logs(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Logs',
            'res_model': 'kw.api.log',
            'domain': [('name', '=', self.url)],
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def kwapi_params(self):
        self.ensure_one()
        return {
            'token': self.is_token_required,
            'api_key': self.is_api_key_required,
            'paginate': self.is_paginated,
            'get_json': self.is_json_required,
            'cors': self.is_cors_required,
            'logging_is_required': self.logging_is_required
        }

    @api.onchange('model_id')
    def onchange_model_id(self):
        for obj in self:
            if obj.model_id:
                obj.name = obj.model_id.name
                obj.api_name = obj.model_id.model

    @api.onchange('model_id_field')
    def check_model_id_field(self):
        for rec in self:
            if rec.model_id and rec.model_id_field:
                model_id_field_rec = self.env['ir.model.fields'].search(
                    [('model', '=', rec.model_id.model),
                     ('name', '=', rec.model_id_field)], limit=1)
                if not model_id_field_rec:
                    raise UserError(_('Model ID Field not found in Model'))
                if model_id_field_rec.ttype not in ['integer', 'char']:
                    raise UserError(
                        _('Model ID Field must be integer or char'))

    def _compute_description(self):
        for obj in self:
            obj.description = ''

    def _compute_url(self):
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for obj in self:
            obj.url = f'{burl}/kw_api/custom/{obj.api_name}'

    def api_get_outbound_field_pairs(self, rec, **kw):
        return [{'field_name': f.name, 'api_name': f.outbound_api_name}
                for f in self.field_ids]

    def api_get_inbound_field_pairs(self, rec, **kw):
        return [(f.name, f.inbound_api_name or f.name)
                for f in self.field_ids.filtered_domain(
                [('is_changeable', '=', True)], )]

    def api_get_data(self, rec, **kw):
        if self.domain:
            domain = safe_eval(self.domain)
            domain.append(["id", "in", rec.ids])
            rec = rec.search(domain)
        return [self.api_get_record_value(obj, **kw) for obj in rec]

    def api_get_record_value(self, rec, **kw):
        if not rec:
            return False
        rec.ensure_one()
        rd = kw.get('relation_display', False)
        if rd == 'pure_id':
            return rec.id
        res = {'id': rec.id, }
        if rd == 'id_only':
            return res
        if rd in ['id_date', 'id_name_date', False] and \
                hasattr(rec, 'write_date'):
            if self.force_response_tz:
                tz = self.force_response_tz
            elif kw.get('tz'):
                tz = kw.get('tz')
            else:
                tz = 'UTC'
            res['write_date'] = format_datetime(
                rec.env, rec.write_date, tz=tz, dt_format=False, )
        if rd in ['id_name', 'id_name_date'] and hasattr(rec, 'name'):
            res['name'] = rec.name
        if rd not in ['data_endpoint', False]:
            return res
        for f in self.field_ids:
            res.update(f.api_get_field_value(rec, **kw))
        return res

    def api_get_field_value(self, rec, field_name, api_name='', **kw):
        field = rec._fields[field_name]
        api_name = api_name or field_name
        if field.type in ['many2one', 'many2many', 'one2many']:
            f = self.field_ids.filtered(lambda x: x.name == field_name)

            if f and f.data_endpoint_id:
                if field.type == 'many2one':
                    return {api_name: f.data_endpoint_id.api_get_record_value(
                        getattr(rec, field_name))}

                return {api_name: f.data_endpoint_id.api_get_data(
                    getattr(rec, field_name))}
        return self.env['kw.api.alien'].api_get_field_value(
            rec, field_name, api_name, **kw)

    def data_response(self, kw_api, data=False, **kw):
        self.ensure_one()
        total_elements = len(data)

        if kw_api.paginate:
            offset = kw_api.page_size * kw_api.page_index
            data = data[offset:offset + kw_api.page_size]

        if hasattr(data, 'search'):
            data = self.api_get_data(data)
            if not kw_api.paginate and len(data) == 1:
                data = data[0]

        if kw_api.paginate:
            number_of_elements = len(data)
            total_pages = math.ceil(total_elements / kw_api.page_size)
            data = {
                'content': data,
                'code': '200',
                'totalElements': total_elements,
                'totalPages': total_pages,
                'numberOfElements': number_of_elements,
                'number': kw_api.page_index,
                'last': (total_pages - kw_api.page_index) <= 0, }
        else:
            data = {'content': data, 'code': '200'}

        return kw_api.response(code=200, data=data)

    def response(self, kw_api, obj_id=False, **kw):
        self.ensure_one()
        if self.kind == 'function':
            try:
                kw_api.data = kw_api.data if kw_api.data else {}
                return self.data_response(
                    kw_api,
                    getattr(self.env[self.model_id.model].sudo(),
                            self.response_function)(
                        **dict(kw, obj_id=obj_id, param_data=kw_api.data)))
            except Exception as e:
                return kw_api.response(
                    code=400, error='Wrong Settings', data={'error': {
                        'code': '400', 'message': e}}, )
        if not obj_id:
            domain = self.get_requested_domain(kw_api, **kw)
            try:
                self_domain = safe_eval(self.domain)
            except Exception as e:
                _logger.debug(e)
                self_domain = []
            if not domain:
                domain = self_domain
            elif self_domain:
                domain = AND([domain, self_domain])

            obj_ids = self.env['kw.api.alien'].api_search(
                model_name=self.model_id.model,
                domain=domain, **kw
            )

            kw_api.paginate = self.is_paginated
            return self.data_response(kw_api, obj_ids, **kw)

        obj_id = self.env[self.model_id.model].with_user(kw.get(
            'user',
            SUPERUSER_ID
        )).search([(self.model_id_field, '=', obj_id), ], limit=1)
        if not obj_id:
            return kw_api.response(
                code=400, error='Wrong ID', data={'error': {
                    'code': '400', 'message': 'Wrong ID'}}, )

        kw_api.paginate = False
        return self.data_response(kw_api, obj_id)

    # pylint: disable=too-many-branches,too-many-statements
    def get_requested_domain(self, kw_api, **kw):
        domain = []
        searchable_fields = self.field_ids.filtered(lambda x: x.is_searchable)
        for k, v in kw.items():
            k = k.split('__')
            if not v or k[0] not in searchable_fields.mapped('outbound_name'):
                continue
            s_field = searchable_fields.filtered(
                lambda x: x.outbound_name == k[0])
            s_field_name = s_field[0].name
            if s_field.model_field_id.ttype in ['many2one', 'many2many', ]:
                if len(k) > 2:
                    s_field_name = f'{s_field[0].name}.{k[1]}'
                else:
                    try:
                        v = int(v)
                    except Exception as e:
                        _logger.debug(e)
            if s_field.model_field_id.ttype in [
                    'integer', 'many2one_reference', 'monetary', ]:
                try:
                    v = int(v)
                except Exception as e:
                    _logger.debug(e)

            if s_field.model_field_id.ttype == 'float':
                try:
                    v = float(v)
                except Exception as e:
                    _logger.debug(e)

            if len(k) > 1:
                if k[-1] == 'eq':
                    domain.append((s_field_name, '=', v))
                elif k[-1] == 'not_eq':
                    domain.append((s_field_name, '!=', v))
                elif k[-1] == 'empty':
                    domain.append((s_field_name, 'in', ['', False]))
                elif k[-1] == 'not_empty':
                    domain.append((s_field_name, 'not in', ['', False]))
                elif k[-1] == 'gt':
                    domain.append((s_field_name, '>', v))
                elif k[-1] == 'gte':
                    domain.append((s_field_name, '>=', v))
                elif k[-1] == 'lt':
                    domain.append((s_field_name, '<', v))
                elif k[-1] == 'lte':
                    domain.append((s_field_name, '<=', v))
                elif k[-1] == 'like':
                    domain.append((s_field_name, 'like', v))
                elif k[-1] == 'ilike':
                    domain.append((s_field_name, 'ilike', v))
                elif k[-1] == 'not_like':
                    domain.append((s_field_name, 'not like', v))
                elif k[-1] == 'not_ilike':
                    domain.append((s_field_name, 'not ilike', v))
                continue
            if s_field.model_field_id.ttype in \
                    ['char', 'selection', 'text', 'html']:
                domain.append((s_field_name, 'ilike', v))
            else:
                # ['float', 'integer', 'boolean']
                domain.append((s_field_name, '=', v))
        return domain

    def change(self, kw_api, obj_id=False, **kw):
        self.ensure_one()
        m = self.env[self.model_id.model].sudo()
        try:
            kw_api.data = json.loads(request.httprequest.data.decode('utf-8'))
        except Exception as e:
            kw_api.data = {}
            _logger.debug(e)
        # run function
        if self.kind == 'function':
            return self.response(kw_api, obj_id, **kw)
        data = kw_api.get_data_fields_by_name(
            self.api_get_inbound_field_pairs(m))
        data = self.env['kw.api.alien'].prepare_inbound_x2many_data(
            self.model_id.model, data)
        try:
            if obj_id:
                obj_id = m.search(
                    [(self.model_id_field, '=', obj_id)], limit=1)
                obj_id.write(data)
            else:
                obj_id = m.create(data)
        except psycopg2.IntegrityError as e:
            self._cr.rollback()
            return kw_api.response(
                code=400, error=e, data={'error': {
                    'code': '400', 'message': e}}, )
        kw_api.paginate = False
        return self.data_response(kw_api, obj_id)

    def delete(self, kw_api, obj_id=False, **kw):
        self.ensure_one()
        m = self.env[self.model_id.model].sudo()
        # run function
        if self.kind == 'function':
            return self.response(kw_api, obj_id, **kw)
        try:
            obj_id = m.search(
                [(self.model_id_field, '=', obj_id)], limit=1)
            obj_id.unlink()
        except Exception as e:
            return kw_api.response(
                code=400, error=e, data={'error': {
                    'code': '400', 'message': 'Wrong ID'}}, )
        return kw_api.response(
            data={'message': f'Object {obj_id} was deleted'})


class CustomEndpointField(models.Model):
    _name = 'kw.api.custom.endpoint.field'
    _description = 'API custom endpoint field'

    name = fields.Char(
        related='model_field_id.name', )
    outbound_api_name = fields.Char()

    outbound_name = fields.Char(
        compute='_compute_outbound_name', inverse='_inverse_outbound_name', )
    inbound_api_name = fields.Char()

    inbound_name = fields.Char(
        compute='_compute_inbound_name', inverse='_inverse_inbound_name', )
    is_changeable = fields.Boolean(
        default=True, )
    is_searchable = fields.Boolean(
        default=False, )
    endpoint_id = fields.Many2one(
        comodel_name='kw.api.custom.endpoint', )
    kind = fields.Selection(
        default='field', selection=[('field', _('Field')), ('eval', 'Eval')])
    model_id = fields.Many2one(
        comodel_name='ir.model', related='endpoint_id.model_id', )
    model_field_id = fields.Many2one(
        comodel_name='ir.model.fields',
        domain="[('model_id', '=', model_id)]", )
    ttype = fields.Selection(
        string='Field Type', related='model_field_id.ttype', )
    relation = fields.Char(
        comodel_name='ir.model', related='model_field_id.relation', )
    data_endpoint_id = fields.Many2one(
        comodel_name='kw.api.custom.endpoint',
        domain="[('model_id.model', '=', relation)]")
    eval_source = fields.Text(
        default='\n\n\n\n\n\n\n', )
    relation_display = fields.Selection(
        defalut='data_endpoint',
        selection=[('pure_id', 'Pure ID'), ('id_only', 'Only ID'),
                   ('id_name', 'ID & name'), ('id_date', 'ID & write_date'),
                   ('id_name_date', 'ID, name & write_date'),
                   ('data_endpoint', 'Data endpoint'), ], )

    def _compute_outbound_name(self):
        for obj in self:
            obj.outbound_name = \
                obj.outbound_api_name or obj.model_field_id.name

    def _inverse_outbound_name(self):
        for obj in self:
            obj.outbound_api_name = obj.outbound_name

    def _compute_inbound_name(self):
        for obj in self:
            obj.inbound_name = \
                obj.inbound_api_name or obj.model_field_id.name

    def _inverse_inbound_name(self):
        for obj in self:
            obj.inbound_api_name = obj.inbound_name

    def api_get_field_value(self, rec, **kw):
        self.ensure_one()
        api_name = self.outbound_name
        if self.endpoint_id.force_response_tz:
            tz = self.endpoint_id.force_response_tz
        elif kw.get('tz'):
            tz = kw.get('tz')
        else:
            tz = 'UTC'
        if self.kind == 'field':
            if self.ttype in ['datetime', ]:
                return {api_name: format_datetime(
                    env=self.env, value=getattr(rec, self.name),
                    tz=tz, dt_format=False, )}
            if self.ttype not in ['many2one', 'many2many', 'one2many']:
                return self.env['kw.api.alien'].api_get_field_value(
                    rec, self.name, api_name, **kw)
            if self.ttype == 'many2one':
                return {api_name: self.data_endpoint_id.api_get_record_value(
                    rec=getattr(rec, self.name), tz=tz,
                    relation_display=self.relation_display)}
            return {api_name: self.data_endpoint_id.api_get_data(
                rec=getattr(rec, self.name), tz=tz,
                relation_display=self.relation_display)}
        if self.kind == 'eval':
            return {api_name: safe_eval(
                self.eval_source, {
                    'env': self.env,
                    'model': self.env[self.endpoint_id.model_id.model],
                    'record': rec,
                    'time': safe_eval_time,
                    'datetime': safe_eval_datetime,
                    'dateutil': safe_eval_dateutil,
                    'pytz': safe_eval_pytz,
                    'json': safe_eval_json,
                    'float_compare': fields.Float.compare,
                    'round': fields.Float.round,
                    'is_zero': fields.Float.is_zero,
                    'html2text': html2text,
                })}
        return {api_name: False}
