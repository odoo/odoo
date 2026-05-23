# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.fields import Command


class ProductCatalogMixin(models.AbstractModel):
    _inherit = 'product.catalog.mixin'

    def create_section(self, child_field, name, *, parent_id=None):
        """Create a new section in order.

        :param str child_field: Field name of the order's lines (e.g., 'order_line').
        :param str name: The name of the section to create.
        :param int parent_id: The id of the parent section.

        :return: A dictionary with values of the created section.
        :rtype: dict
        """
        order = self.with_company(self.company_id)
        parent_field = order._get_parent_field_on_child_model()

        if not parent_field:
            return {}

        lines = order[child_field].sorted('sequence')
        line_model = lines._name
        sequence = lines[-1].sequence + 1 if lines else 10
        if parent_id:
            # Insert after the last line of the parent section
            section_found = False
            for line in lines:
                if line.display_type != 'line_section':
                    continue
                if section_found:
                    sequence = line.sequence
                    break
                if line.id == parent_id:
                    section_found = True

        order[child_field] = [
            Command.update(line.id, {'sequence': line.sequence + 1})
            for line in lines.filtered_domain([('sequence', '>=', sequence)])
        ]

        section = order.env[line_model].create({
            parent_field: order.id,
            'name': name,
            'display_type': 'line_subsection' if parent_id else 'line_section',
            'sequence': sequence,
            **order._get_default_create_section_values(),
        })

        return {
            'id': section.id,
            'sequence': section.sequence,
            'display_type': section.display_type,
            'subtotal': 0.0,
        }

    def _get_new_line_sequence(self, child_field, section_id):
        """Compute the sequence number for inserting a new line into the order.

        :param str child_field: Field name of the order's lines (e.g., 'order_line').
        :param int section_id: ID of the section line to insert after.
        :rtype: int
        :return: Computed sequence number.
        """
        lines = self[child_field].sorted('sequence')

        # Default case : insert at the end
        sequence = (lines and lines[-1].sequence + 1) or 10
        if section_id:
            # Insert after the last product of the selected section
            section_found = False
            for line in lines:
                if line.display_type not in ('line_section', 'line_subsection'):
                    continue
                if section_found:
                    sequence = line.sequence
                    break
                if line.id == section_id:
                    section_found = True
        elif (
            section_lines := lines.filtered_domain([
                ('display_type', '=', 'line_section'),
            ])
        ):
            # Insert before the first section (top of the order)
            sequence = section_lines[0].sequence

        self[child_field] = [
            Command.update(line.id, {'sequence': line.sequence + 1})
            for line in lines.filtered_domain([('sequence', '>=', sequence)])
        ]

        return sequence

    def get_sections(self, child_field):
        """Return section data for the product catalog display.

        :param str child_field: Field name of the order's lines (e.g., 'order_line').
        :rtype: list
        :return: List of section dicts with 'id', 'name', 'sequence', 'parent_id', 'display_type'
                 and 'subtotal'
        """
        sections = {}
        lines = self.with_company(self.company_id)[child_field]
        for line in lines.sorted('sequence'):
            if line.display_type in ('line_section', 'line_subsection'):
                sections[line.id] = {
                    'id': line.id,
                    'name': line.name,
                    'sequence': line.sequence,
                    'parent_id': line.parent_id.id if line.parent_id else False,
                    'display_type': line.display_type,
                    'subtotal': line.get_section_subtotal(),
                }

        return sorted(sections.values(), key=lambda x: x['sequence'])

    def _get_default_create_section_values(self):
        """Return default values for creating a new section in order through catalog.

        :return: A dictionary with default values for creating a new section.
        :rtype: dict
        """
        return {}

    def _get_parent_field_on_child_model(self):
        """Return the parent field for the order lines.

        :return: parent field
        :rtype: str
        """
        return ''

    def resequence_sections(
        self,
        child_field,
        moved_section_id,
        new_parent_section_id,
        insert_before_section_sequence,
    ):
        """Reorder the sections.

        :param str child_field: Field name of the order's lines (e.g., 'order_line').
        :param int moved_section_id: ID of the section to move.
        :param int new_parent_section_id: ID of the new parent section.
        :param int insert_before_section_sequence: Sequence of the section to insert before.
        :rtype: list
        :return: List of sections
        """
        order = self.with_company(self.company_id)
        lines = order[child_field].sorted('sequence')
        moved_section = lines.browse(moved_section_id)

        if not moved_section:
            return []

        moved_block = lines.filtered(
            lambda line: (
                moved_section.id in {line.id, line.parent_id.id, line.parent_id.parent_id.id}
            )
        )

        old_start = moved_block[0].sequence
        old_end = moved_block[-1].sequence
        block_size = len(moved_block)

        # Target position
        if insert_before_section_sequence is not None:
            target_sequence = insert_before_section_sequence
        elif new_parent_section_id:
            siblings = (
                lines.filtered(
                    lambda line:
                        line.parent_id.id == new_parent_section_id
                )
                - moved_block
            )
            if siblings:
                target_sequence = siblings[-1].sequence + 1
            else:
                target_sequence = lines.browse(new_parent_section_id).sequence + 1
        else:
            target_sequence = lines[-1].sequence + 1

        # Moving upward
        if target_sequence < old_start:
            affected_lines = lines.filtered(
                lambda line:
                    target_sequence <= line.sequence < old_start
                    and line not in moved_block
            )
            shift = block_size
            new_start = target_sequence

        else:  # Moving downward
            affected_lines = lines.filtered(
                lambda line:
                    old_end < line.sequence < target_sequence
                    and line not in moved_block
            )
            shift = -block_size
            new_start = target_sequence - block_size

        commands = [
            Command.update(line.id, {"sequence": line.sequence + shift}) for line in affected_lines
        ]
        # Place moved block in new position
        commands.extend(
            Command.update(line.id, {"sequence": new_start + index})
            for index, line in enumerate(moved_block)
        )
        self[child_field] = commands

        order[child_field].invalidate_recordset(['parent_id'])

        return order.get_sections(child_field)

    def duplicate_section(self, child_field, section_id, *, parent_id=None):
        """Duplicate the given section with all its children.

        :param string child_field: The field name of the lines in the order model.
        :param int section_id: The section id.
        :param int parent_id: The id of the parent section for the duplicated section.
        :rtype: dict
        :return: A dictionary with the list of sections and the id of the duplicated section.
        """
        order = self.with_company(self.company_id)
        lines = order[child_field]
        section = lines.browse(section_id)

        section_children = (
            lines.filtered(lambda line: line.parent_id.id == section_id)
            if parent_id
            else section._get_section_lines()
        )

        section_lines = (section | section_children).sorted("sequence")

        # If duplicating a section with children, insert the duplicated block after the last child
        # to keep them together.
        anchor = section_lines[-1]

        ordered_lines = lines.sorted(lambda l: (l.sequence, l.id))

        anchor_index = ordered_lines.ids.index(anchor.id)

        # Lines after anchor (including same sequence ones)
        lines_to_shift = ordered_lines[anchor_index + 1:]

        shift_by = len(section_lines) + 1

        # Shift existing lines
        commands = [
            Command.update(line.id, {"sequence": line.sequence + shift_by})
            for line in lines_to_shift
        ]

        # Insert duplicated block
        base_sequence = anchor.sequence + 1
        commands.extend(
            Command.create({
                **line.copy_data()[0],
                "sequence": base_sequence + i,
            })
            for i, line in enumerate(section_lines)
        )

        order[child_field] = commands
        new_lines = (order[child_field] - lines).sorted("sequence")

        return {
            "sections": order.get_sections(child_field),
            "duplicated_section_id": new_lines[0].id,
        }

    def delete_section(self, child_field, section_id):
        """Delete the given section with all its children.

        :param string child_field: The field name of the lines in the order model.
        :param int section_id: The section id.
        """
        lines = self.with_company(self.company_id)[child_field]
        section = lines.browse(section_id)

        if not section:
            return

        section_children = (
            section._get_section_lines()
            if section.display_type == "line_section"
            else lines.filtered(lambda line: line.parent_id == section)
        )

        (section | section_children).unlink()

    def rename_section(self, child_field, section_id, new_name):
        """Rename the given section.

        :param string child_field: The field name of the lines in the order model.
        :param int section_id: The section id.
        :param string new_name: The new name for the section.
        """
        section = self.with_company(self.company_id)[child_field].browse(section_id)
        if section:
            section.name = new_name
