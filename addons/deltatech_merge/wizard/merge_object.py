# ©  2008-2021 Deltatech
# See README.rst file on addons root folder for license details

import datetime
import functools
import itertools
import logging
from ast import literal_eval

import psycopg2

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import mute_logger

_logger = logging.getLogger("merge.object")


class MergeDummy(models.TransientModel):
    _name = "merge.dummy"
    _description = "Merge Object Dummy"

    name = fields.Char()


class MergeObjectLine(models.TransientModel):
    _name = "merge.object.line"
    _description = "Merge Object Line"
    _order = "min_id asc"

    wizard_id = fields.Many2one("merge.object.wizard", "Wizard")
    min_id = fields.Integer("MinID")
    aggr_ids = fields.Char("Ids", required=True)


class MergeObject(models.TransientModel):
    """
    The idea behind this wizard is to create a list of potential objects to
    merge. We use two objects, the first one is the wizard for the end-user.
    And the second will contain the object list to merge.
    """

    _name = "merge.object.wizard"
    _description = "Merge Object Wizard"
    _model_merge = "merge.dummy"
    _table_merge = "merge_dummy"

    group_by_name = fields.Boolean("Name")

    state = fields.Selection(
        [("option", "Option"), ("selection", "Selection"), ("finished", "Finished")],
        readonly=True,
        required=True,
        string="State",
        default="option",
    )

    number_group = fields.Integer("Group of Objects", readonly=True)
    current_line_id = fields.Many2one("merge.object.line", string="Current Line")
    line_ids = fields.One2many("merge.object.line", "wizard_id", string="Lines")
    object_ids = fields.Many2many(_model_merge, string="Objects")
    dst_object_id = fields.Many2one(_model_merge, string="Destination Object")

    maximum_group = fields.Integer("Maximum of Group of Objects")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids")
        if self.env.context.get("active_model") == self._model_merge and active_ids:
            res["state"] = "selection"
            res["object_ids"] = [(6, 0, active_ids)]
            res["dst_object_id"] = self._get_ordered_object(active_ids)[-1].id
        return res

    # ----------------------------------------
    # Update method. Core methods to merge steps
    # ----------------------------------------

    def _get_fk_on(self, table):
        """return a list of many2one relation with the given table.
        :param table : the name of the sql table to return relations
        :returns a list of tuple 'table name', 'column name'.
        """
        query = """
            SELECT cl1.relname as table, att1.attname as column
            FROM pg_constraint as con, pg_class as cl1, pg_class as cl2,
                 pg_attribute as att1, pg_attribute as att2
            WHERE con.conrelid = cl1.oid
                AND con.confrelid = cl2.oid
                AND array_lower(con.conkey, 1) = 1
                AND con.conkey[1] = att1.attnum
                AND att1.attrelid = cl1.oid
                AND cl2.relname = %s
                AND att2.attname = 'id'
                AND array_lower(con.confkey, 1) = 1
                AND con.confkey[1] = att2.attnum
                AND att2.attrelid = cl2.oid
                AND con.contype = 'f'
        """
        self._cr.execute(query, (table,))
        return self._cr.fetchall()

    @api.model
    def _update_foreign_keys(self, src_objects, dst_object):
        """Update all foreign key from the src_object to dst_object. All many2one fields will be updated.
        :param src_objects : merge source res.object recordset (does not include destination one)
        :param dst_object : record of destination res.object
        """
        _logger.debug(
            "_update_foreign_keys for dst_object: %s for src_objects: %s", dst_object.id, str(src_objects.ids)
        )

        # find the many2one relation to a object
        Object = self.env[self._model_merge]
        relations = self._get_fk_on(self._table_merge)

        self.env.flush_all()

        for table, column in relations:
            if "merge_object_" in table:  # ignore two tables
                continue

            # get list of columns of current table (exept the current fk column)
            # pylint: disable=E8103
            query = "SELECT column_name FROM information_schema.columns WHERE table_name LIKE '%s'" % (table)
            self._cr.execute(query, ())
            columns = []
            for data in self._cr.fetchall():
                if data[0] != column:
                    columns.append(data[0])

            # do the update for the current table/column in SQL
            query_dic = {
                "table": table,
                "column": column,
                "value": columns[0],
            }
            if len(columns) <= 1:
                # unique key treated
                query = (
                    """
                    UPDATE "%(table)s" as ___tu
                    SET "%(column)s" = %%s
                    WHERE
                        "%(column)s" = %%s AND
                        NOT EXISTS (
                            SELECT 1
                            FROM "%(table)s" as ___tw
                            WHERE
                                "%(column)s" = %%s AND
                                ___tu.%(value)s = ___tw.%(value)s
                        )"""
                    % query_dic
                )
                for src_object in src_objects:
                    self._cr.execute(query, (dst_object.id, src_object.id, dst_object.id))
            else:
                try:
                    with mute_logger("odoo.sql_db"), self.env.clear_upon_failure():
                        query = 'UPDATE "%(table)s" SET "%(column)s" = %%s WHERE "%(column)s" IN %%s' % query_dic
                        self._cr.execute(
                            query,
                            (
                                dst_object.id,
                                tuple(src_objects.ids),
                            ),
                        )

                        # handle the recursivity with parent relation
                        if column == Object._parent_name and table == self._table_merge:
                            query = (
                                """
                                WITH RECURSIVE cycle(id, parent_id) AS (
                                        SELECT id, parent_id FROM %(table)s
                                    UNION
                                        SELECT  cycle.id, %(table)s.parent_id
                                        FROM    %(table)s, cycle
                                        WHERE   %(table)s.id = cycle.parent_id AND
                                                cycle.id != cycle.parent_id
                                )
                                SELECT id FROM cycle WHERE id = parent_id AND id = %%s
                            """
                                % query_dic
                            )
                            self._cr.execute(query, (dst_object.id,))

                except psycopg2.Error:
                    # updating fails, most likely due to a violated unique constraint
                    # keeping record with nonexistent object_id is useless, better delete it
                    query = 'DELETE FROM "%(table)s" WHERE "%(column)s" IN %%s' % query_dic
                    self._cr.execute(query, (tuple(src_objects.ids),))

        self.invalidate_recordset()

    @api.model
    def _update_reference_fields(self, src_objects, dst_object):
        """Update all reference fields from the src_object to dst_object.
        :param src_objects : merge source res.object recordset (does not include destination one)
        :param dst_object : record of destination res.object
        """
        _logger.debug("_update_reference_fields for dst_object: %s for src_objects: %r", dst_object.id, src_objects.ids)

        def update_records(model, src, field_model="model", field_id="res_id"):
            Model = self.env[model] if model in self.env else None
            if Model is None:
                return
            records = Model.sudo().search([(field_model, "=", self._model_merge), (field_id, "=", src.id)])
            try:
                with mute_logger("odoo.sql_db"), self.env.clear_upon_failure():
                    records.sudo().write({field_id: dst_object.id})
                    self.env.flush_all()
            except psycopg2.Error:
                # updating fails, most likely due to a violated unique constraint
                # keeping record with nonexistent object_id is useless, better delete it
                records.sudo().unlink()

        update_records = functools.partial(update_records)

        for scr_object in src_objects:
            update_records("calendar.event", src=scr_object, field_model="res_model")
            update_records("ir.attachment", src=scr_object, field_model="res_model")
            update_records("mail.followers", src=scr_object, field_model="res_model")

            update_records("portal.share", src=scr_object, field_model="res_model")
            update_records("rating.rating", src=scr_object, field_model="res_model")
            update_records("mail.activity", src=scr_object, field_model="res_model")
            update_records("mail.message", src=scr_object)
            update_records("ir.model.data", src=scr_object)

        records = self.env["ir.model.fields"].search([("ttype", "=", "reference")])
        for record in records.sudo():
            try:
                Model = self.env[record.model]
                field = Model._fields[record.name]
            except KeyError:
                # unknown model or field => skip
                continue

            if field.compute is not None:
                continue

            for src_object in src_objects:
                records_ref = Model.sudo().search([(record.name, "=", "%s,%d" % (self._model_merge, src_object.id))])
                values = {
                    record.name: "%s,%d" % (self._model_merge, dst_object.id),
                }
                records_ref.sudo().write(values)

        self.env.flush_all()

    def _get_summable_fields(self):
        """Returns the list of fields that should be summed when merging objects"""
        return []

    @api.model
    def _update_values(self, src_objects, dst_object):
        """Update values of dst_object with the ones from the src_objects.
        :param src_objects : recordset of source res.object
        :param dst_object : record of destination res.object
        """
        _logger.debug("_update_values for dst_object: %s for src_objects: %r", dst_object.id, src_objects.ids)

        model_fields = dst_object.fields_get().keys()
        summable_fields = self._get_summable_fields()

        def write_serializer(item):
            if isinstance(item, models.BaseModel):
                return item.id
            else:
                return item

        # get all fields that are not computed or x2many
        values = dict()
        for column in model_fields:
            field = dst_object._fields[column]
            if field.type not in ("many2many", "one2many") and field.compute is None:
                for item in itertools.chain(src_objects, [dst_object]):
                    if item[column]:
                        if column in summable_fields and values.get(column):
                            values[column] += write_serializer(item[column])
                        else:
                            values[column] = write_serializer(item[column])
        # remove fields that can not be updated (id and parent_id)
        values.pop("id", None)
        parent_id = values.pop("parent_id", None)
        dst_object.write(values)
        # try to update the parent_id
        if parent_id and parent_id != dst_object.id:
            try:
                dst_object.write({"parent_id": parent_id})
            except ValidationError:
                _logger.info(
                    "Skip recursive object hierarchies for parent_id %s of object: %s", parent_id, dst_object.id
                )

    def _merge(self, object_ids, dst_object=None, extra_checks=True):
        """private implementation of merge object
        :param object_ids : ids of object to merge
        :param dst_object : record of destination res.object
        :param extra_checks: pass False to bypass extra sanity check (e.g. email address)
        """

        Object = self.env[self._model_merge]
        object_ids = Object.browse(object_ids).exists()
        if len(object_ids) < 2:
            return
        params = self.env["ir.config_parameter"].sudo()
        try:
            max_no_objects = int(params.get_param("deltatech_merge.merge_objects_max_number", default=3))
        except Exception:
            raise UserError(
                _("Invalid system parameter value (deltatech_merge.merge_objects_max_number): %s")
                % params.get_param("deltatech_merge.merge_objects_max_number")
            )
        if len(object_ids) > max_no_objects:
            raise UserError(
                _(
                    "For safety reasons, you cannot merge more than %s objects together."
                    " You can re-open the wizard several times if needed."
                )
                % max_no_objects
            )

        # check if the list of objects to merge contains child/parent relation
        if "parent_id" in Object._fields:
            child_ids = self.env[self._model_merge]
            for object_id in object_ids:
                child_ids |= Object.search([("id", "child_of", [object_id.id])]) - object_id
            if object_ids & child_ids:
                raise UserError(_("You cannot merge a object with one of his parent."))

        # remove dst_object from objects to merge
        if dst_object and dst_object in object_ids:
            src_objects = object_ids - dst_object
        else:
            ordered_objects = self._get_ordered_object(object_ids.ids)
            dst_object = ordered_objects[-1]
            src_objects = ordered_objects[:-1]
        _logger.info("dst_object: %s", dst_object.id)

        # call sub methods to do the merge
        self._update_foreign_keys(src_objects, dst_object)
        self._update_reference_fields(src_objects, dst_object)
        self._update_values(src_objects, dst_object)

        self._log_merge_operation(src_objects, dst_object)

        # delete source object, since they are merged
        src_objects.unlink()

    def _log_merge_operation(self, src_objects, dst_object):
        _logger.info("(uid = %s) merged the objects %r with %s", self._uid, src_objects.ids, dst_object.id)

    # ----------------------------------------
    # Helpers
    # ----------------------------------------

    # @api.model
    # def _generate_query(self, fields, maximum_group=100):
    #     """Build the SQL query on res.object table to group them according to given criteria
    #     :param fields : list of column names to group by the objects
    #     :param maximum_group : limit of the query
    #     """
    #     # make the list of column to group by in sql query
    #     sql_fields = []
    #     for field in fields:
    #         if field in ["email", "name"]:
    #             sql_fields.append("lower(%s)" % field)
    #         elif field in ["vat"]:
    #             sql_fields.append("replace(%s, ' ', '')" % field)
    #         else:
    #             sql_fields.append(field)
    #     group_fields = ", ".join(sql_fields)
    #
    #     # where clause : for given group by columns, only keep the 'not null' record
    #     filters = []
    #     for field in fields:
    #         if field in ["email", "name", "vat"]:
    #             filters.append((field, "IS NOT", "NULL"))
    #     criteria = " AND ".join("{} {} {}".format(field, operator, value) for field, operator, value in filters)
    #
    #     # build the query
    #     text = [
    #         "SELECT min(id), array_agg(id)",
    #         "FROM %s" % self._table_merge,
    #     ]
    #
    #     if criteria:
    #         text.append("WHERE %s" % criteria)
    #
    #     text.extend(["GROUP BY %s" % group_fields, "HAVING COUNT(*) >= 2", "ORDER BY min(id)"])
    #
    #     if maximum_group:
    #         text.append(
    #             "LIMIT %s" % maximum_group,
    #         )
    #
    #     return " ".join(text)

    # @api.model
    # def _compute_selected_groupby(self):
    #     """Returns the list of field names the object can be grouped (as merge
    #     criteria) according to the option checked on the wizard
    #     """
    #     groups = []
    #     group_by_prefix = "group_by_"
    #
    #     for field_name in self._fields:
    #         if field_name.startswith(group_by_prefix):
    #             if getattr(self, field_name, False):
    #                 groups.append(field_name[len(group_by_prefix) :])
    #
    #     if not groups:
    #         raise UserError(_("You have to specify a filter for your selection."))
    #
    #     return groups

    @api.model
    def _object_use_in(self, aggr_ids, models):
        """Check if there is no occurence of this group of object in the selected model
        :param aggr_ids : stringified list of object ids separated with a comma (sql array_agg)
        :param models : dict mapping a model name with its foreign key with res_object table
        """
        return any(self.env[model].search_count([(field, "in", aggr_ids)]) for model, field in models.items())

    @api.model
    def _get_ordered_object(self, object_ids):
        """Helper : returns a `res.object` recordset ordered by create_date/active fields
        :param object_ids : list of object ids to sort
        """
        return (
            self.env[self._model_merge]
            .browse(object_ids)
            .sorted(
                key=lambda p: (p.create_date or datetime.datetime(1970, 1, 1)),
                reverse=True,
            )
        )

    def _compute_models(self):
        """Compute the different models needed by the system if you want to exclude some objects."""
        model_mapping = {}

        return model_mapping

    # ----------------------------------------
    # Actions
    # ----------------------------------------

    def action_skip(self):
        """Skip this wizard line. Don't compute any thing, and simply redirect to the new step."""
        if self.current_line_id:
            self.current_line_id.unlink()
        return self._action_next_screen()

    def _action_next_screen(self):
        """return the action of the next screen ; this means the wizard is set to treat the
        next wizard line. Each line is a subset of object that can be merged together.
        If no line left, the end screen will be displayed (but an action is still returned).
        """
        self.invalidate_recordset()  # FIXME: is this still necessary?
        values = {}
        if self.line_ids:
            # in this case, we try to find the next record.
            current_line = self.line_ids[0]
            current_object_ids = literal_eval(current_line.aggr_ids)
            values.update(
                {
                    "current_line_id": current_line.id,
                    "object_ids": [(6, 0, current_object_ids)],
                    "dst_object_id": self._get_ordered_object(current_object_ids)[-1].id,
                    "state": "selection",
                }
            )
        else:
            values.update({"current_line_id": False, "object_ids": [], "state": "finished"})

        self.write(values)

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    # def _process_query(self, query):
    #     """Execute the select request and write the result in this wizard
    #     :param query : the SQL query used to fill the wizard line
    #     """
    #     self.ensure_one()
    #     model_mapping = self._compute_models()
    #
    #     # group object query
    #     self._cr.execute(query)
    #
    #     counter = 0
    #     for min_id, aggr_ids in self._cr.fetchall():
    #         # To ensure that the used objects are accessible by the user
    #         objects = self.env[self._model_merge].search([("id", "in", aggr_ids)])
    #         if len(objects) < 2:
    #             continue
    #
    #         # exclude object according to options
    #         if model_mapping and self._object_use_in(objects.ids, model_mapping):
    #             continue
    #
    #         self.env["merge.object.line"].create({"wizard_id": self.id, "min_id": min_id, "aggr_ids": objects.ids})
    #         counter += 1
    #
    #     self.write({"state": "selection", "number_group": counter})
    #
    #     _logger.info("counter: %s", counter)

    # def action_start_manual_process(self):
    #     """Start the process 'Merge with Manual Check'. Fill the wizard according to the group_by and exclude
    #     options, and redirect to the first step (treatment of first wizard line). After, for each subset of
    #     object to merge, the wizard will be actualized.
    #         - Compute the selected groups (with duplication)
    #         - If the user has selected the 'exclude_xxx' fields, avoid the objects
    #     """
    #     self.ensure_one()
    #     groups = self._compute_selected_groupby()
    #     query = self._generate_query(groups, self.maximum_group)
    #     self._process_query(query)
    #     return self._action_next_screen()

    # def action_start_automatic_process(self):
    #     """Start the process 'Merge Automatically'. This will fill the wizard with the same mechanism as 'Merge
    #     with Manual Check', but instead of refreshing wizard with the current line, it will automatically process
    #     all lines by merging object grouped according to the checked options.
    #     """
    #     self.ensure_one()
    #     self.action_start_manual_process()  # here we don't redirect to the next screen, since it is automatic process
    #
    #     self.write({"state": "finished"})
    #     return {
    #         "type": "ir.actions.act_window",
    #         "res_model": self._name,
    #         "res_id": self.id,
    #         "view_mode": "form",
    #         "target": "new",
    #     }

    # def parent_migration_process_cb(self):
    #     self.ensure_one()
    #     return {
    #         "type": "ir.actions.act_window",
    #         "res_model": self._name,
    #         "res_id": self.id,
    #         "view_mode": "form",
    #         "target": "new",
    #     }

    # def action_update_all_process(self):
    #     self.ensure_one()
    #
    #     return self._action_next_screen()

    def action_merge(self):
        """Merge Object button. Merge the selected objects, and redirect to
        the end screen (since there is no other wizard line to process.
        """
        if not self.object_ids:
            self.write({"state": "finished"})
            return {
                "type": "ir.actions.act_window",
                "res_model": self._name,
                "res_id": self.id,
                "view_mode": "form",
                "target": "new",
            }

        self._merge(self.object_ids.ids, self.dst_object_id)

        if self.current_line_id:
            self.current_line_id.unlink()

        return self._action_next_screen()
