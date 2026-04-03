from __future__ import annotations

import functools
from collections import defaultdict
from typing import TYPE_CHECKING

from odoo.tests import TransactionCase, tagged

if TYPE_CHECKING:
    from collections.abc import Iterator

    from odoo.fields import Field, Many2one

BTREE_INDEX_PY_DEFS = (True, '1', 'btree', 'btree_not_null')

# Ignore list of models and fields we don't want to index,
# usually because the table is known to always be small,
# or there is a custom index that covers this btree index
# A separate ignore list for models is provided to simplify maintenance.
BTREE_INDEX_IGNORE_MODELS = {  # model._name
    'account.account',
    'account.report',
    'account.report.async.document',
    'account.report.external.value',
    'account.tax',
    'account.tax.group',
    'base.automation',
    'card.campaign',
    'certificate.certificate',
    'clearing.label',
    'crm.lead.scoring.frequency.field',
    'crm.team',
    'data_recycle.model',
    'delivery.carrier',
    'digest.digest',
    'event.booth.category',
    'event.type',
    'event.type.mail',
    'event.type.ticket',
    'hr.departure.reason',
    'hr.employee.type',
    'hr.payroll.structure.type',
    'hr.work.entry.type',
    'iap.account',
    'ir.actions.server',
    'ir.module.module',
    'ir.module.module.dependency',
    'ir.module.module.exclusion',
    'ir.sequence',
    'ir.sequence.date_range',
    'lunch.product.category',
    'lunch.supplier',
    'lunch.topping',
    'mail.alias',
    'mail.template',
    'mailing.filter',
    'mailing.mailing',
    'mrp.unbuild',
    'mrp.workcenter.productivity',
    'mrp.workcenter.productivity.loss',
    'payment.provider',
    'pos.payment.method',
    'pos.preset',
    'pos.printer',
    'product.pricelist',
    'res.company',
    'res.partner.grade',
    'sale.order.template.line',
    'sms.template',
    'sms.twilio.number',
    'stock.package.type',
    'stock.picking.type',
    'stock.warehouse',
    'uom.uom',
    'website',
    'website.sale.extra.field',
}

# str(field): name of <SQL object (index/constraint)> that's covering
BTREE_INDEX_IGNORE_FIELDS = {
    'ir.attachment.res_id': 'ir_attachment_res_idx',  # usually accessed with `res_model` in the domain
    'mail.message.res_id': 'mail_message_model_res_id_idx',  # usually accessed with `model` in the domain
    'mail.presence.guest_id': 'mail_presence_guest_unique',
    'mail.presence.user_id': 'mail_presence_user_unique',
}


@tagged('post_install', '-at_install')
class TestIndexMeta(TransactionCase):

    def test_ignore_list(self):
        """
        Make sure the indexes/constraints in the ignore list still exist.

        Forces the updating of the ignore-list in case of removal from the code,
        where an index on the field itself might become required from the other heuristics.
        """
        missing_fields = []
        missing_table_objects = []
        for field_full_name, table_object in BTREE_INDEX_IGNORE_FIELDS.items():
            model_name, field_name = field_full_name.rsplit('.', 1)
            model_class = self.registry[model_name]
            if field_name not in model_class._fields:
                missing_fields.append(field_full_name)
                continue
            if table_object not in model_class._table_objects:
                missing_table_objects.append(table_object)

        if missing_fields or missing_table_objects:
            msg_parts = []
            if missing_fields:
                msg_parts.append(
                    "The following fields no longer exist and must be removed from `BTREE_INDEX_IGNORE_FIELDS`:\n"
                    + "\n".join(f"  - {fname}" for fname in missing_fields)
                )
            if missing_table_objects:
                msg_parts.append(
                    "The following indexes/constraints no longer exist and must be removed from `BTREE_INDEX_IGNORE_FIELDS`:\n"
                    + "\n".join(f"  - {obj}" for obj in missing_table_objects)
                )
            self.fail("\n\n".join(msg_parts))


@tagged('post_install', '-at_install')
class TestIndex(TransactionCase):

    @functools.cached_property
    def _leading_index_columns(self) -> dict[str, set[str]]:
        """
        Map table -> columns, for those columns which are covered by
        a non-partial index or unique constraint as the first (leading) or only index key.
        """
        self.addCleanup(
            self.__dict__.pop,
            '_leading_index_columns',
            None,
        )
        self.env.cr.execute("""
            SELECT c.relname AS table_name,
                   ARRAY_AGG(DISTINCT a.attname) AS column_names
              FROM pg_index i
              JOIN pg_class c ON c.oid = i.indrelid
              JOIN pg_attribute a
                   ON a.attrelid = c.oid
                   AND a.attnum = i.indkey[0]        -- first key
             WHERE i.indisvalid
               AND NOT i.indisprimary                -- not the pkey
               AND c.relnamespace = current_schema::regnamespace
               AND i.indpred IS NULL                 -- not partial
             GROUP BY c.relname
        """)
        return {
            table_name: set(column_names)
            for table_name, column_names in self.env.cr.fetchall()
        }

    def should_ignore(self, field: Many2one) -> bool:
        model = self.registry[field.model_name]
        return (
            # ignore models without a table
            model._abstract
            # ignore SQL views
            or not model._auto
            # ignore transient models (because small tables)
            or model._transient
            # ignore non-column fields
            or not (field.store and field.column_type)
            # ignore "small" models
            or field.model_name in BTREE_INDEX_IGNORE_MODELS
            # ignore already indexed
            or field.index in BTREE_INDEX_PY_DEFS
            # ignore special cases
            or str(field) in BTREE_INDEX_IGNORE_FIELDS
            # ignore indirectly indexed columns
            or field.name in self._leading_index_columns.get(model._table, set())
            # ignore fields from test modules
            or (field._modules and all('test' in module for module in field._modules))
        )

    def test_index_on_one2many_inverse(self):
        """Ensure btree indexes are enforced on the stored inverse fields of One2many relations."""
        fields_to_index = set()
        for model in self.registry.values():
            for field in model._fields.values():
                if field.type == 'one2many' and field.inverse_name:
                    comodel = self.registry[field.comodel_name]
                    inverse_field = comodel._fields[field.inverse_name].base_field
                    if not self.should_ignore(inverse_field):
                        fields_to_index.add(f"{inverse_field} (inverse of {field})")
        if fields_to_index:
            msg = ("The following fields should be indexed with a btree index,\n"
                   "as they are inverse of an One2many field:\n"
                   "- if the field is sparse -> 'btree_not_null'\n"
                   "- if the field is Required or low fraction of False/NULL values -> True or 'btree'\n"
                   "- if not sure -> 'btree_not_null': \n%s" % "\n".join(sorted(fields_to_index)))
            self.fail(msg)

    def test_index_on_related_field_path(self):
        """
        Ensure btree indexes are enforced on the fields
        that serve as a 'path' for the value of a related field.
        """

        def get_traversed_fields(
            field: Field,
            visited: set[Field] | None = None,
            full: bool = False,
        ) -> Iterator[Field]:
            assert field.related is not None

            if visited is None:
                visited: set = set()

            model_name = field.model_name

            related_segments = field.related.split('.')
            if not full:
                related_segments = related_segments[:-1]

            for segment_name in related_segments:
                segment_field = self.registry[model_name]._fields[segment_name].base_field
                if segment_field in visited:
                    continue
                visited.add(segment_field)

                yield segment_field

                if segment_field.related and not segment_field.store:
                    # For non-stored related fields, the entire related path needs to be indexed,
                    # including the last segment.
                    yield from get_traversed_fields(segment_field, visited, full=True)

                model_name = segment_field.comodel_name

        fields_to_index: dict[str, set[str]] = defaultdict(set)

        for model in self.registry.values():
            for field in model._fields.values():
                if not field.related:
                    continue

                for segment_field in get_traversed_fields(field):
                    # If the segment_field.type is:
                    # - 'one2many' -> covered by `test_enforce_index_on_one2many_inverse`
                    # - 'many2many' -> already indexed with a compositive index by default
                    if (
                        segment_field.type == 'many2one'
                        and not self.should_ignore(segment_field)
                    ):
                        fields_to_index[str(segment_field)].add(str(field))

        if fields_to_index:
            field_lines = [
                f'{segment} (used by: {", ".join(sorted(sources))})'
                for segment, sources in sorted(fields_to_index.items())
            ]
            msg = (
                "The following fields should be indexed with a btree index,\n"
                "as they are used as a path segment for a related field:\n"
                "- if the field is sparse -> 'btree_not_null'\n"
                "- if the field is Required or low fraction of False/NULL values -> True or 'btree'\n"
                "- if not sure -> 'btree_not_null':\n%s" % "\n".join(field_lines)
            )
            self.fail(msg)
