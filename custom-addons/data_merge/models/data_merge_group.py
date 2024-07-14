# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _
from odoo.models import MAGIC_COLUMNS
from odoo.osv import expression
from odoo.tools import split_every

import logging
_logger = logging.getLogger(__name__)

IGNORED_FIELDS = MAGIC_COLUMNS
DM_CRON_BATCH_SIZE = 100


class DataMergeGroup(models.Model):
    _name = 'data_merge.group'
    _description = 'Deduplication Group'
    _order = 'similarity desc'

    active = fields.Boolean(default=True)
    model_id = fields.Many2one('data_merge.model', string='Deduplication Model', ondelete='cascade', required=True)
    res_model_id = fields.Many2one(related='model_id.res_model_id', store=True, readonly=True)
    res_model_name = fields.Char(related='model_id.res_model_name', store=True, readonly=True)
    similarity = fields.Float(
        string='Similarity %', readonly=True, store=True, compute='_compute_similarity',
        help='Similarity coefficient based on the amount of text fields exactly in common.')
    divergent_fields = fields.Char(
        compute='_compute_similarity', store=True)
    record_ids = fields.One2many('data_merge.record', 'group_id')

    @api.depends('model_id', 'similarity')
    def _compute_display_name(self):
        for group in self:
            group.display_name = _('%s - Similarity: %s%%', group.model_id.name, int(group.similarity * 100))

    def _get_similarity_fields(self):
        self.ensure_one()
        group_fields = self.env[self.res_model_name]._fields.items()
        return [name for name, field in group_fields if field.type == 'char']

    @api.depends('record_ids')
    def _compute_similarity(self):
        for group in self:
            if not group.record_ids:
                group.divergent_fields = ''
                group.similarity = 1
                continue

            read_fields = group._get_similarity_fields()

            record_ids = group.record_ids.mapped('res_id')
            records = self.env[group.res_model_name].browse(record_ids).read(read_fields)
            # YTI What about unaccent ? Should be taken into account IMO if the
            # rule was computed from that.
            data = set(records[0].items())
            data = data.intersection(*[set(record.items()) for record in records[1:]])

            diff_fields = set(read_fields) - {k for k, v in data}  # fields of the model minus the identical fields
            group.divergent_fields = ','.join(diff_fields)
            group.similarity = min(1, len(data) / len(read_fields))

    def discard_records(self, records=None):
        domain = [('group_id', '=', self.id)]

        if records is not None:
            domain = expression.AND([domain, [('id', 'in', records)]])
        self.env['data_merge.record'].search(domain).write({'is_discarded': True, 'is_master': False})
        if all(not record.active for record in self.record_ids):
            self.active = False
        self._elect_master_record()

    ###################
    ### Master Record
    ###################
    def _elect_master_record(self):
        """
        Elect the "master" record.

        This method will look for a `_elect_method()` on the model.
        If it exists, this method is responsible to return the master record, otherwise, a generic method is used.
        """
        for group in self:
            if hasattr(self.env[group.res_model_name], '_elect_method'):
                elect_master = getattr(self.env[group.res_model_name], '_elect_method')
            else:
                elect_master = group._elect_method

            records = group.record_ids._original_records()
            if not records:
                return

            master = elect_master(records)
            if master:
                master_record = group.record_ids.filtered(lambda r: r.res_id == master.id)
                master_record.is_master = True

    ## Generic master
    def _elect_method(self, records):
        """
        Generic master election method.

        :param records: all the records of the duplicate group
        :return the oldest record as master
        """
        records_sorted = records.sorted('create_date')
        return records_sorted[0] if records_sorted else None

    ###########
    ### Merge
    ###########
    @api.model
    def merge_multiple_records(self, group_records):
        group_ids = self.browse([int(group_id) for group_id in group_records.keys()])

        for group in group_ids:
            group.merge_records(group_records[str(group.id)])

    def merge_records(self, records=None):
        """
        Merge the selected records.

        This method will look for a `_merge_method()` on the model.
        If it exists, this method is responsible to merge the records, otherwise, the generic method is used.

        :param records: Group records to be merged, or None if all records should be merged
        """
        self.ensure_one()
        if records is None:
            records = []

        domain = [('group_id', '=', self.id)]
        if records:
            domain += [('id', 'in', records)]

        to_merge = self.env['data_merge.record'].with_context(active_test=False).search(domain, order='id')
        to_merge_count = len(to_merge)
        if to_merge_count <= 1:
            return
        master_record = to_merge.filtered('is_master') or to_merge[0]
        to_merge = to_merge - master_record

        if not master_record._original_records():
            _logger.warning('The master record does not exist')
            return

        _logger.info('Merging %s records %s into %s' % (self.res_model_name, to_merge.mapped('res_id'), master_record.res_id))

        model = self.env[self.res_model_name]
        if hasattr(model, '_merge_method'):
            merge = getattr(model, '_merge_method')
        else:
            merge = self._merge_method

        # Create a dict with chatter data, in case the merged records are deleted during the merge procedure
        chatter_data = {rec.res_id:dict(res_id=rec.res_id, merged_record=str(rec.name), changes=rec._record_snapshot()) for rec in to_merge}
        res = merge(master_record._original_records(), to_merge._original_records())
        if res.get('log_chatter'):
            self._log_merge(master_record, to_merge, chatter_data)

        if res.get('post_merge'):
            self._post_merge(master_record, to_merge)

        is_merge_action = master_record.model_id.is_contextual_merge_action
        (master_record + to_merge).unlink()

        return {
            'records_merged': res['records_merged'] if res.get('records_merged') else to_merge_count,
            # Used to get back to the functional model if deduplicate was
            # called from contextual action menu - instead of staying on
            # the deduplicate view.
            'back_to_model': is_merge_action
        }

    def _log_merge(self, master_record, merged_records, chatter_data):
        """
        Post a snapshot of each merged records on the master record
        """
        if not isinstance(self.env[self.res_model_name], self.env.registry['mail.thread']):
           return

        values = {
            'res_model_label': self.res_model_id.name,
            'res_model_name': self.res_model_name,
            'res_id': master_record.res_id,
            'master_record': master_record.name,
        }
        for rec in merged_records:
            master_values = chatter_data.get(rec.res_id, {})
            master_values.update({
                'res_model_label': self.res_model_id.name,
                'res_model_name': self.res_model_name,
                'archived': rec._original_records().exists(),
            })
            if self.model_id.removal_mode == 'archive':
                rec._original_records()._message_log_with_view('data_merge.data_merge_merged', render_values=values)
            master_record._original_records()._message_log_with_view('data_merge.data_merge_main', render_values=master_values)


    ## Generic Merge
    def _merge_method(self, master, records):
        """
        Generic merge method, will "only" update the foreign keys from the source records to the master record

        :param master: original record considered as the destination
        :param records: source records to be merged with the master
        :return dict
        """
        self.env['data_merge.record']._update_foreign_keys(destination=master, source=records)

        return {
            'post_merge': True, # Perform post merge activities
            'log_chatter': True # Log merge notes in the chatter
        }

    def _post_merge(self, master, records):
        """
        Perform the post merge activities such as archiving or deleting the original record
        """
        origins = records._original_records()
        if self.model_id.removal_mode == 'delete' or not origins._active_name:
            origins.unlink()
        else:
            origins.write({origins._active_name: False})

    ##########
    ### Cron
    ##########
    def _cron_cleanup(self, auto_commit=True):
        """ Perform cleanup activities for each data_merge.group. """
        groups = self.with_context(active_test=False).env['data_merge.group'].search([])

        for batched_groups in split_every(DM_CRON_BATCH_SIZE, groups.ids, self.with_context(active_test=False).browse):
            batched_groups._cleanup()

            if auto_commit:
                self.env.cr.commit()

    def _cleanup(self):
        """
        Do the cleanup, it will delete:
            - merged data_merge.record
            - data_merge.record with archived or deleted original record
            - data_merge.group with 0 or 1 data_merge.record
        """
        records_to_delete = self.env['data_merge.record']
        groups_to_delete = self.env['data_merge.group']

        for group in self:
            # Count the records kept per group and if there are discarded records
            records_discarded = False
            records_kept = 0

            # Delete records no longer existing
            original_records = {r.id: r for r in group.record_ids._original_records()} if group.record_ids else {}
            # Delete group if all original records in a group have been deleted
            if not original_records:
                groups_to_delete += group
                continue

            for rec in group.record_ids:
                original_record = original_records.get(rec.res_id)
                if not original_record:
                    records_to_delete += rec
                    continue

                origin_inactive = (original_record._active_name and not original_record[original_record._active_name])
                if origin_inactive:
                    records_to_delete += rec
                    continue

                records_discarded = records_discarded or rec.is_discarded
                if not rec.is_discarded:
                    records_kept += 1

            # Delete groups with at most 1 record and no discarded records
            if not records_discarded and records_kept <= 1:
                groups_to_delete += group

            # Delete single non-discarded record in groups with discarded record(s)
            if records_discarded and records_kept == 1:
                records_to_delete += group.record_ids.filtered(lambda r: not r.is_discarded)

        records_to_delete.unlink()
        groups_to_delete.unlink()
