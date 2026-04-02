# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import ValidationError
from odoo.fields import Command


class ProductCatalogMixin(models.AbstractModel):
    _inherit = 'product.catalog.mixin'

    def _has_sections(self) -> bool:
        """Determine whether this model handles (sub)sections.

        Must be overridden to enable (sub)sections update in the catalog.
        """
        return False

    def _get_action_add_from_catalog_extra_context(self) -> dict:
        res = super()._get_action_add_from_catalog_extra_context()

        if self._has_sections():
            res['show_sections'] = bool(self.id)

        return res

    def _get_product_catalog_record_lines(
        self, product_ids, child_field, *, section_id=None, **kwargs
    ):
        if not self._has_sections() or section_id is not None:
            return super()._get_product_catalog_record_lines(
                product_ids, child_field, section_id=section_id, **kwargs
            )

        # If no particular section was chosen, use the first one by default (if any).
        first_child = next(
            (line for line in self[child_field] if line.display_type == 'line_section'),
            False,
        )
        if first_child:
            section_id = first_child.id

        return super()._get_product_catalog_record_lines(
            product_ids, child_field, section_id=section_id, **kwargs
        )

    def _get_updated_order_line_info(self, catalog_line, product, uom, **kwargs) -> dict:
        vals = super()._get_updated_order_line_info(catalog_line, product, uom, **kwargs)
        if self._has_sections():
            vals["subtotal"] = sum(catalog_line.mapped("price_subtotal")) if catalog_line else 0
        return vals

    def _catalog_prepare_new_line_vals(self, child_field, *args, section_id=None, **kwargs) -> dict:
        vals = super()._catalog_prepare_new_line_vals(
            child_field, *args, section_id=section_id, **kwargs
        )

        if self._has_sections():
            # Insert on last position of (sub)section
            vals['sequence'] = self._prepare_lines_insertion(
                child_field, into_section_id=section_id
            )

        return vals

    def get_catalog_section_data(self, child_field) -> dict:
        """Return order information and sections for the product catalog.

        :param str child_field: Field name of the order's lines (e.g., 'order_line').
        :return: A dictionary containing order information and sections data.
        """
        self.ensure_one()
        self = self.with_company(self.company_id)  # noqa: PLW0642

        return {
            "order_details": {
                "amount_untaxed": self.amount_untaxed,
                "name": self.name,
            },
            "sections": self._get_sections(child_field),
        }

    def _get_sections(self, child_field) -> list[dict]:
        """Return section data for the product catalog display.

        :param str child_field: name of the one2many field holding the catalog lines.
        :return: Ordered list of section details (id, name, sequence, parent_id, subtotal)
        """
        lines = self[child_field].sorted('sequence')

        section_details = [
            {
                'id': line.id,
                'name': line.name,
                'parent_id': line.parent_id.id,
                'subtotal': sum(line._get_section_lines().mapped('price_subtotal')),
            }
            for line in lines
            if line.display_type in ('line_section', 'line_subsection')
        ]

        if section_details and (
            no_section_lines := lines.filtered(
                lambda line: (
                    line.display_type not in ('line_section', 'line_subsection')
                    and not line.parent_id
                )
            )
        ):
            section_details.insert(
                0,
                {
                    'id': False,
                    'name': self.env._("No Section"),
                    'subtotal': sum(no_section_lines.mapped('price_subtotal')),
                },
            )

        return section_details

    def create_section(self, child_field, name, parent_id=None) -> dict:
        """Create a new section in order.

        :param str child_field: Field name of the order's lines (e.g., 'order_line').
        :param str name: The name of the section to create.
        :param int parent_id: The id of the parent section.

        :return: A dictionary with newly created section's details.
        """
        self = self.with_company(self.company_id)  # noqa: PLW0642

        if not self._has_sections():
            raise ValidationError(self.env._("This model does not support (sub)sections"))

        child_model = self._fields[child_field].comodel_name
        parent_field = self._fields[child_field].inverse_name

        # Insert after last line of parent (or end of the order)
        after_section_id = parent_id
        if not after_section_id:
            after_section_id = self[child_field].sorted('sequence').filtered(
                lambda line: line.display_type == 'line_section'
            )[-1:].id

        new_section_sequence = self._prepare_lines_insertion(
            child_field, after_section_id=after_section_id
        )
        section = self.env[child_model].create({
            parent_field: self.id,
            'name': name,
            'display_type': 'line_subsection' if parent_id else 'line_section',
            'sequence': new_section_sequence,
            self.env[child_model]._get_quantity_field(): 0,
        })

        return {
            'id': section.id,
            'subtotal': 0.0,
        }

    def _prepare_lines_insertion(
        self, child_field, after_section_id=None, into_section_id=False, lines_to_insert=None
    ) -> int:
        lines = self[child_field].sorted('sequence')
        if after_section_id:
            # Insert after the last line of the (sub)section
            section_line = lines.browse(after_section_id)
            last_line_before_gap = (section_line | section_line._get_section_lines())[-1:]
        else:
            # (into_section_id = False) => Insert before the first section
            # (into_section_id) => Insert before the section subsections (if any)
            # We do not call `_get_section_lines` as we only want the direct descendents, to
            # introduce the line before the subsections
            into_section_id = into_section_id or False
            last_line_before_gap = (
                lines.browse(into_section_id)
                | lines.filtered(
                    lambda line: (
                        line.parent_id.id == into_section_id
                        and line.display_type not in ('line_section', 'line_subsection')
                    )
                )
            )[-1:]

        sequence_gap = 1
        if last_line_before_gap:
            line_before_gap_index = lines._ids.index(last_line_before_gap.id)
        else:
            line_before_gap_index = -1

        lines_to_move = lines[line_before_gap_index + 1 : len(lines)]
        if lines_to_move:
            if lines_to_insert:
                sequence_gap = len(lines_to_insert)
                lines_to_move = lines_to_move - lines_to_insert

            self[child_field] = [
                Command.update(line.id, {'sequence': line.sequence + sequence_gap + 1})
                for line in lines_to_move
            ]

        if last_line_before_gap:
            return last_line_before_gap.sequence + 1

        # Return default model sequence
        return lines.browse().default_get(['sequence']).get('sequence', 10)

    def delete_section(self, child_field, section_id):
        """Delete the given section with all its children.

        :param string child_field: The field name of the lines in the order model.
        :param int section_id: The section id.
        """
        self.ensure_one()
        self = self.with_company(self.company_id)  # noqa: PLW0642

        if section := self.env[self._fields[child_field].comodel_name].browse(section_id).exists():
            (section | section._get_section_lines()).unlink()

    def duplicate_section(self, child_field, section_id) -> dict:
        """Duplicate the given section with all its children.

        :param string child_field: The field name of the lines in the order model.
        :param int section_id: The section id.
        :return: A dictionary with the list of sections and the id of the duplicated section.
        """
        self.ensure_one()
        self = self.with_company(self.company_id)  # noqa: PLW0642
        lines = self[child_field].sorted('sequence')

        section = lines.browse(section_id)

        section_lines = (section | section._get_section_lines()).sorted("sequence")
        new_section_sequence = self._prepare_lines_insertion(
            child_field, after_section_id=section_id, lines_to_insert=section_lines
        )

        # Insert duplicated block
        self[child_field] = [
            Command.create({**line_data, "sequence": new_section_sequence + index})
            for index, line_data in enumerate(section_lines.copy_data())
        ]
        new_lines = (self[child_field] - lines).sorted("sequence")

        return {
            "sections": self._get_sections(child_field),
            "duplicated_section_id": new_lines[0].id,
        }

    def rename_section(self, child_field, section_id, new_name):
        """Rename the given section.

        :param string child_field: The field name of the lines in the order model.
        :param int section_id: The section id.
        :param string new_name: The new name for the section.
        """
        section = self.with_company(self.company_id)[child_field].browse(section_id)
        if section:
            section.name = new_name

    def resequence_sections(
        self, child_field, moved_section_id, new_parent_section_id=None, previous_section_id=None
    ):
        """Resequence the order content based on the new sequence order.

        1) move a section after a section (or no section)
        2) move a subsection after subsection (same or other parent)
        3) move a subsection into another section (without subsections, or on first place)

        :param str child_field: name of the one2many field holding the catalog lines.
        :param int moved_section_id: id of the moved section line
        :param int new_parent_section_id: id of the new parent line (for subsections)
        :param int previous_section_id: id of the previous (sub)section if any.
        """
        self.ensure_one()
        self = self.with_company(self.company_id)  # noqa: PLW0642

        lines = self[child_field].sorted('sequence')
        moved_section = lines.browse(moved_section_id)

        if not moved_section:
            return

        section_lines = moved_section | moved_section._get_section_lines()
        new_section_sequence = self._prepare_lines_insertion(
            child_field,
            after_section_id=previous_section_id,
            into_section_id=new_parent_section_id,
            lines_to_insert=section_lines,
        )

        self[child_field] = [
            Command.update(line.id, {"sequence": new_section_sequence + index})
            for index, line in enumerate(section_lines)
        ]
