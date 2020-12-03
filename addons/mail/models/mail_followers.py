# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


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

    # Note. There is no integrity check on model names for performance reasons.
    # However, followers of unlinked models are deleted by models themselves
    # (see 'ir.model' inheritance).
    res_model = fields.Char(
        'Related Document Model Name', required=True, index=True)
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
    def _add_follower_command(self, res_model, res_ids, partner_data, channel_data, force=True):
        """ Please upate me
        :param force: if True, delete existing followers before creating new one
                      using the subtypes given in the parameters
        """
        force_mode = force or (all(partner_data.values()) and all(channel_data.values()))
        generic = []
        specific = {}
        existing = {}  # {res_id: follower_ids}
        p_exist = {}  # {partner_id: res_ids}
        c_exist = {}  # {channel_id: res_ids}

        followers = self.sudo().search([
            '&',
            '&', ('res_model', '=', res_model), ('res_id', 'in', res_ids),
            '|', ('partner_id', 'in', list(partner_data)), ('channel_id', 'in', list(channel_data))])

        if force_mode:
            followers.unlink()
        else:
            for follower in followers:
                existing.setdefault(follower.res_id, list()).append(follower)
                if follower.partner_id:
                    p_exist.setdefault(follower.partner_id.id, list()).append(follower.res_id)
                if follower.channel_id:
                    c_exist.setdefault(follower.channel_id.id, list()).append(follower.res_id)

        default_subtypes, _internal_subtypes, external_subtypes = \
            self.env['mail.message.subtype'].default_subtypes(res_model)

        if force_mode:
            employee_pids = self.env['res.users'].sudo().search([('partner_id', 'in', list(partner_data)), ('share', '=', False)]).mapped('partner_id').ids
            for pid, data in partner_data.items():
                if not data:
                    if pid not in employee_pids:
                        partner_data[pid] = external_subtypes.ids
                    else:
                        partner_data[pid] = default_subtypes.ids
            for cid, data in channel_data.items():
                if not data:
                    channel_data[cid] = default_subtypes.ids

        # create new followers, batch ok
        gen_new_pids = [pid for pid in partner_data if pid not in p_exist]
        gen_new_cids = [cid for cid in channel_data if cid not in c_exist]
        for pid in gen_new_pids:
            generic.append([0, 0, {'res_model': res_model, 'partner_id': pid, 'subtype_ids': [(6, 0, partner_data.get(pid) or default_subtypes.ids)]}])
        for cid in gen_new_cids:
            generic.append([0, 0, {'res_model': res_model, 'channel_id': cid, 'subtype_ids': [(6, 0, channel_data.get(cid) or default_subtypes.ids)]}])

        # create new followers, each document at a time because of existing followers to avoid erasing
        if not force_mode:
            for res_id in res_ids:
                command = []
                doc_followers = existing.get(res_id, list())

                new_pids = set(partner_data) - set([sub.partner_id.id for sub in doc_followers if sub.partner_id]) - set(gen_new_pids)
                new_cids = set(channel_data) - set([sub.channel_id.id for sub in doc_followers if sub.channel_id]) - set(gen_new_cids)

                # subscribe new followers
                for new_pid in new_pids:
                    command.append((0, 0, {
                        'res_model': res_model,
                        'partner_id': new_pid,
                        'subtype_ids': [(6, 0, partner_data.get(new_pid) or default_subtypes.ids)],
                    }))
                for new_cid in new_cids:
                    command.append((0, 0, {
                        'res_model': res_model,
                        'channel_id': new_cid,
                        'subtype_ids': [(6, 0, channel_data.get(new_cid) or default_subtypes.ids)],
                    }))
                if command:
                    specific[res_id] = command
        return generic, specific

    #
    # Modifying followers change access rights to individual documents. As the
    # cache may contain accessible/inaccessible data, one has to refresh it.
    #
    @api.multi
    def _invalidate_documents(self):
        """ Invalidate the cache of the documents followed by ``self``. """
        for record in self:
            if record.res_id:
                self.env[record.res_model].invalidate_cache(ids=[record.res_id])

    @api.model
    def create(self, vals):
        res = super(Followers, self).create(vals)._check_rights()
        res._invalidate_documents()
        return res

    @api.multi
    def write(self, vals):
        if 'res_model' in vals or 'res_id' in vals:
            self._invalidate_documents()
        res = super(Followers, self).write(vals)
        self._check_rights()
        self._invalidate_documents()
        return res

    @api.multi
    def unlink(self):
        self._invalidate_documents()
        return super(Followers, self).unlink()

    def _check_rights(self):
        user_partner = self.env.user.partner_id
        for record in self:
            obj = self.env[record.res_model].browse(record.res_id)
            if record.channel_id or record.partner_id != user_partner:
                obj.check_access_rights('write')
                obj.check_access_rule('write')
                subject = record.channel_id or record.partner_id
                subject.check_access_rights('read')
                subject.check_access_rule('read')
            else:
                obj.check_access_rights('read')
                obj.check_access_rule('read')
        return self

    _sql_constraints = [
        ('mail_followers_res_partner_res_model_id_uniq', 'unique(res_model,res_id,partner_id)', 'Error, a partner cannot follow twice the same object.'),
        ('mail_followers_res_channel_res_model_id_uniq', 'unique(res_model,res_id,channel_id)', 'Error, a channel cannot follow twice the same object.'),
        ('partner_xor_channel', 'CHECK((partner_id IS NULL) != (channel_id IS NULL))', 'Error: A follower must be either a partner or a channel (but not both).')
    ]
