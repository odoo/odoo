# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import pycompat
from psycopg2 import IntegrityError


class Followers(models.Model):
    """ mail_followers holds the data related to the follow mechanism inside
    Odoo. Partners can choose to follow documents (records) of any kind
    that inherits from mail.thread. Following documents allow to receive
    notifications for new messages. A subscription is characterized by:

    :param: res_model: model of the followed objects
    :param: res_id: ID of resource (may be 0 for every objects)
    """
    _name = 'mail.followers'
    _rec_name = 'partner_id'
    _log_access = False
    _description = 'Document Followers'

    res_model = fields.Char(
        'Document Model')
    res_id = fields.Integer(
        'Related Document ID', index=True, help='Id of the followed resource')
    partner_id = fields.Many2one(
        'res.partner', string='Related Partner', ondelete='cascade', index=True)
    channel_id = fields.Many2one(
        'mail.channel', string='Listener', ondelete='cascade', index=True)
    subtype_ids = fields.Many2many(
        'mail.message.subtype', string='Subtype',
        help="Message subtypes followed, meaning subtypes that will be pushed onto the user's Wall.")

    @api.model
    def _set_default_subtype(self, doc_id, model, employee=False):
        int_query = (not employee) and ' and internal=false' or ''
        self.env.cr.execute('''
            INSERT INTO
                mail_followers_mail_message_subtype_rel (mail_followers_id, mail_message_subtype_id)
            SELECT %s,id FROM
                mail_message_subtype
            WHERE
                "default"=true AND 
                ((res_model IS NULL) or (res_model=%s)) AND
                id not in (select mail_message_subtype_id from mail_followers_mail_message_subtype_rel where mail_followers_id=%s) '''+
                int_query, 
            (doc_id, model, doc_id))

    @api.model
    def _add_follower_command(self, res_model, res_ids, partner_ids=[], channel_ids=[], subtype_ids=None):
        """ Please upate me
        :param force: if True, delete existing followers before creating new one
                      using the subtypes given in the parameters
        """
        user_ids = None
        for resid in res_ids:
            for partner in partner_ids:
                doc = self.search([('res_model','=',res_model),('res_id','=',resid),('partner_id','=',partner)], limit=1)
                if not doc:
                    doc = self.create({
                        'res_model': res_model,
                        'res_id': resid,
                        'partner_id': partner,
                        'subtype_ids': subtype_ids and [(6,0, subtype_ids)] or []
                    })
                elif subtype_ids:
                    doc.write({'subtype_ids': [(6,0, subtype_ids)]})
                if not subtype_ids:
                    if user_ids is None:
                        user_ids = self.env['res.users'].sudo().search([('partner_id', 'in', partner_ids), ('share', '=', False)]).mapped('partner_id').ids
                    self._set_default_subtype(doc.id, res_model, partner in user_ids)
            for channel in channel_ids:
                doc = self.search([('res_model','=',res_model),('res_id','=',resid),('channel_id','=',channel)], limit=1)
                if not doc:
                    doc = self.create({
                        'res_model': res_model,
                        'res_id': resid,
                        'channel_id': channel,
                        'subtype_ids': subtype_ids and [(6,0, subtype_ids)] or []
                    })
                elif subtype_ids:
                    doc.write({'subtype_ids': [(6,0, subtype_ids)]})
                if not subtype_ids:
                    self._set_default_subtype(doc.id, res_model)
            self.env[res_model].invalidate_cache(ids=res_ids)

        return True

    _sql_constraints = [
        ('mail_followers_res_partner_res_model_id_uniq', 'unique(res_model,res_id,partner_id)', 'Error, a partner cannot follow twice the same object.'),
        ('mail_followers_res_channel_res_model_id_uniq', 'unique(res_model,res_id,channel_id)', 'Error, a channel cannot follow twice the same object.'),
        ('partner_xor_channel', 'CHECK((partner_id IS NULL) != (channel_id IS NULL))', 'Error: A follower must be either a partner or a channel (but not both).')
    ]
