# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools

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
        res = super(Followers, self).create(vals)
        res._invalidate_documents()
        return res

    @api.multi
    def write(self, vals):
        if 'res_model' in vals or 'res_id' in vals:
            self._invalidate_documents()
        res = super(Followers, self).write(vals)
        if any(x in vals for x in ['res_model', 'res_id', 'partner_id']):
            self._invalidate_documents()
        return res

    @api.multi
    def unlink(self):
        self._invalidate_documents()
        return super(Followers, self).unlink()

    _sql_constraints = [
        ('mail_followers_res_partner_res_model_id_uniq', 'unique(res_model,res_id,partner_id)', 'Error, a partner cannot follow twice the same object.'),
        ('mail_followers_res_channel_res_model_id_uniq', 'unique(res_model,res_id,channel_id)', 'Error, a channel cannot follow twice the same object.'),
        ('partner_xor_channel', 'CHECK((partner_id IS NULL) != (channel_id IS NULL))', 'Error: A follower must be either a partner or a channel (but not both).')
    ]

    # --------------------------------------------------
    # Private tools methods to fetch followers data
    # --------------------------------------------------

    def _get_subscription_data(self, doc_data, pids, cids, include_pshare=False):
        """ Private method allowing to fetch follower data from several documents of a given model.
        Followers can be filtered given partner IDs and channel IDs.

        :param doc_data: list of pair (res_model, res_ids) that are the documents from which we
          want to have subscription data;
        :param pids: optional partner to filter; if None take all, otherwise limitate to pids
        :param cids: optional channel to filter; if None take all, otherwise limitate to cids
        :param include_pshare: optional join in partner to fetch their share status

        :return: list of followers data which is a list of tuples containing
          follower ID,
          document ID,
          partner ID (void if channel_id),
          channel ID (void if partner_id),
          followed subtype IDs,
          share status of partner (void id channel_id, returned only if include_pshare is True)
        """
        # base query: fetch followers of given documents
        where_clause = ' OR '.join(['fol.res_model = %s AND fol.res_id IN %s'] * len(doc_data))
        where_params = list(itertools.chain.from_iterable((rm, tuple(rids)) for rm, rids in doc_data))

        # additional: filter on optional pids / cids
        sub_where = []
        if pids:
            sub_where += ["fol.partner_id IN %s"]
            where_params.append(tuple(pids))
        elif pids is not None:
            sub_where += ["fol.partner_id IS NULL"]
        if cids:
            sub_where += ["fol.channel_id IN %s"]
            where_params.append(tuple(cids))
        elif cids is not None:
            sub_where += ["fol.channel_id IS NULL"]
        if sub_where:
            where_clause += "AND (%s)" % " OR ".join(sub_where)

        query = """
SELECT fol.id, fol.res_id, fol.partner_id, fol.channel_id, array_agg(subtype.id)%s
FROM mail_followers fol
%s
LEFT JOIN mail_followers_mail_message_subtype_rel fol_rel ON fol_rel.mail_followers_id = fol.id
LEFT JOIN mail_message_subtype subtype ON subtype.id = fol_rel.mail_message_subtype_id
WHERE %s
GROUP BY fol.id%s""" % (
            ', partner.partner_share' if include_pshare else '',
            'LEFT JOIN res_partner partner ON partner.id = fol.partner_id' if include_pshare else '',
            where_clause,
            ', partner.partner_share' if include_pshare else '')
        self.env.cr.execute(query, tuple(where_params))
        return self.env.cr.fetchall()

    # --------------------------------------------------
    # Private tools methods to generate new subscription
    # --------------------------------------------------

    def _insert_followers(self, res_model, res_ids, partner_ids, partner_subtypes, channel_ids, channel_subtypes,
                          customer_ids=None, check_existing=False, existing_policy='skip'):
        """ Main internal method allowing to create or update followers for documents, given a
        res_model and the document res_ids. This method does not handle access rights. This is the
        role of the caller to ensure there is no security breach.

        :param partner_subtypes: optional subtypes for new partner followers. If not given, default
         ones are computed;
        :param channel_subtypes: optional subtypes for new channel followers. If not given, default
         ones are computed;
        :param customer_ids: see ``_add_default_followers``
        :param check_existing: see ``_add_followers``;
        :param existing_policy: see ``_add_followers``;
        """
        sudo_self = self.sudo()
        if not partner_subtypes and not channel_subtypes:  # no subtypes -> default computation, no force, skip existing
            new, upd = self._add_default_followers(res_model, res_ids, partner_ids, channel_ids, customer_ids=customer_ids)
        else:
            new, upd = self._add_followers(res_model, res_ids, partner_ids, partner_subtypes, channel_ids, channel_subtypes, check_existing=check_existing, existing_policy=existing_policy)
        for res_id, values_list in new.items():
            for values in values_list:
                sudo_self.create(dict(values, res_id=res_id)).id
        for fol_id, values in upd.items():
            sudo_self.browse(fol_id).write(values)

    def _add_default_followers(self, res_model, res_ids, partner_ids, channel_ids=None, customer_ids=None):
        """ Shortcut to ``_add_followers`` that computes default subtypes. Existing
        followers are skipped as their subscription is considered as more important
        compared to new default subscription.

        :param customer_ids: optional list of partner ids that are customers. It is used if computing
         default subtype is necessary and allow to avoid the check of partners being customers (no
         user or share user). It is just a matter of saving queries if the info is already known;

        :return: see ``_add_followers``
        """
        if not partner_ids and not channel_ids:
            return dict(), dict()

        default, _, external = self.env['mail.message.subtype'].default_subtypes(res_model)
        if partner_ids and customer_ids is None:
            customer_ids = self.env['res.partner'].sudo().search([('id', 'in', partner_ids), ('partner_share', '=', True)]).ids

        c_stypes = dict.fromkeys(channel_ids or [], default.ids)
        p_stypes = dict((pid, external.ids if pid in customer_ids else default.ids) for pid in partner_ids)

        return self._add_followers(res_model, res_ids, partner_ids, p_stypes, channel_ids, c_stypes, check_existing=True, existing_policy='skip')

    def _add_followers(self, res_model, res_ids, partner_ids, partner_subtypes, channel_ids, channel_subtypes,
                       check_existing=False, existing_policy='skip'):
        """ Internal method that generates values to insert or update followers. Callers have to
        handle the result, for example by making a valid ORM command, inserting or updating directly
        follower records, ... This method returns two main data

         * first one is a dict which keys are res_ids. Value is a list of dict of values valid for
           creating new followers for the related res_id;
         * second one is a dict which keys are follower ids. Value is a dict of values valid for
           updating the related follower record;

        :param check_existing: if True, check for existing followers for given documents and handle
        them according to existing_policy parameter. Setting to False allows to save some computation
        if caller is sure there are no conflict for followers;
        :param existing policy: if check_existing, tells what to do with already-existing followers:

          * skip: simply skip existing followers, do not touch them;
          * force: update existing with given subtypes only;
          * replace: replace existing with nex subtypes (like force without old / new follower);
          * update: gives an update dict allowing to add missing subtypes (no subtype removal);
        """
        _res_ids = res_ids or [0]
        data_fols, doc_pids, doc_cids = dict(), dict((i, set()) for i in _res_ids), dict((i, set()) for i in _res_ids)

        if check_existing and res_ids:
            for fid, rid, pid, cid, sids in self._get_subscription_data([(res_model, res_ids)], partner_ids or None, channel_ids or None):
                if existing_policy != 'force':
                    if pid:
                        doc_pids[rid].add(pid)
                    elif cid:
                        doc_cids[rid].add(cid)
                data_fols[fid] = (rid, pid, cid, sids)

            if existing_policy == 'force':
                self.sudo().browse(data_fols.keys()).unlink()

        new, update = dict(), dict()
        for res_id in _res_ids:
            for partner_id in set(partner_ids or []):
                if partner_id not in doc_pids[res_id]:
                    new.setdefault(res_id, list()).append({
                        'res_model': res_model,
                        'partner_id': partner_id,
                        'subtype_ids': [(6, 0, partner_subtypes[partner_id])],
                    })
                elif existing_policy in ('replace', 'update'):
                    fol_id, sids = next(((key, val[3]) for key, val in data_fols.items() if val[0] == res_id and val[1] == partner_id), (False, []))
                    new_sids = set(partner_subtypes[partner_id]) - set(sids)
                    old_sids = set(sids) - set(partner_subtypes[partner_id])
                    if fol_id and new_sids:
                        update[fol_id] = {'subtype_ids': [(4, sid) for sid in new_sids]}
                    if fol_id and old_sids and existing_policy == 'replace':
                        update[fol_id] = {'subtype_ids': [(3, sid) for sid in old_sids]}
            for channel_id in set(channel_ids or []):
                if channel_id not in doc_cids[res_id]:
                    new.setdefault(res_id, list()).append({
                        'res_model': res_model,
                        'channel_id': channel_id,
                        'subtype_ids': [(6, 0, channel_subtypes[channel_id])],
                    })
                elif existing_policy in ('replace', 'update'):
                    fol_id, sids = next(((key, val[3]) for key, val in data_fols.items() if val[0] == res_id and val[2] == channel_id), (False, []))
                    new_sids = set(channel_subtypes[channel_id]) - set(sids)
                    old_sids = set(sids) - set(channel_subtypes[channel_id])
                    if fol_id and new_sids:
                        update[fol_id] = {'subtype_ids': [(4, sid) for sid in new_sids]}
                    if fol_id and old_sids and existing_policy == 'replace':
                        update[fol_id] = {'subtype_ids': [(3, sid) for sid in old_sids]}

        return new, update
