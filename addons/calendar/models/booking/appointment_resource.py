import logging

from odoo import api, fields, models
from odoo.tools.translate import html_translate

_logger = logging.getLogger(__name__)

# `_get_possible_capacity_combinations` doubles its result for every linked resource,
# so an unbounded search costs 2**len(linked_resource_ids). It is reachable from the
# public appointment page, where 20 mutually linked resources measured ~45s of CPU for
# a single request. Stop expanding past this many combinations; linked resources are
# walked in `sequence` order, so the ones an administrator ranked first are kept.
MAX_CAPACITY_COMBINATIONS = 4096


class AppointmentResource(models.Model):
    _name = "appointment.resource"
    _description = "Appointment Resource"
    _inherit = ["mixin.avatar", "mixin.resource"]
    _order = "sequence,id"

    name = fields.Char(
        related="resource_id.name",
        string="Name",
        store=True,
        readonly=False,
        required=True,
    )
    active = fields.Boolean(
        related="resource_id.active",
        string="Active",
        default=True,
        store=True,
        readonly=False,
    )
    sequence = fields.Integer(
        default=1,
        required=True,
        help="""The sequence dictates if the resource is going to be picked in higher priority against another resource
        (e.g. for 2 tables of 4, the lowest sequence will be picked first)""",
    )
    company_id = fields.Many2one(default=False)
    resource_id = fields.Many2one(copy=False)
    resource_calendar_id = fields.Many2one(
        default=lambda self: (
            self.env.ref(
                "calendar.appointment_default_resource_calendar",
                raise_if_not_found=False,
            )
            or self.env.company.resource_calendar_id
        ),
        help="If kept empty, the working schedule of the company set on the resource will be used",
    )
    capacity = fields.Integer(
        related="resource_id.capacity",
        string="Capacity",
        default=1,
        store=True,
        readonly=False,
        required=True,
    )
    enforce_booking_limit = fields.Boolean(
        related="resource_id.enforce_booking_limit",
        readonly=False,
    )
    booking_limit_percentage = fields.Float(
        related="resource_id.booking_limit_percentage",
        readonly=False,
    )
    shareable = fields.Boolean(
        help="""This allows to share the resource with multiple attendee for a same time slot (e.g. a bar counter)"""
    )
    source_resource_ids = fields.Many2many(
        comodel_name="appointment.resource",
        relation="appointment_resource_linked_appointment_resource",
        column1="resource_id",
        column2="linked_resource_id",
        string="Source combination",
        domain="[('id', '!=', id)]",
    )
    destination_resource_ids = fields.Many2many(
        comodel_name="appointment.resource",
        relation="appointment_resource_linked_appointment_resource",
        column1="linked_resource_id",
        column2="resource_id",
        string="Destination combination",
        domain="[('id', '!=', id)]",
    )
    linked_resource_ids = fields.Many2many(
        comodel_name="appointment.resource",
        compute="_compute_linked_resource_ids",
        inverse="_inverse_linked_resource_ids",
        store=False,
        domain="[('id', '!=', id)]",
        help="""List of resources that can be combined to handle a bigger demand.""",
    )
    description = fields.Html(
        translate=html_translate,
        sanitize_attributes=False,
    )
    appointment_type_ids = fields.Many2many(
        comodel_name="appointment.type",
        relation="appointment_type_appointment_resource_rel",
        string="Available in",
        domain="[('schedule_based_on', '=', 'resources')]",
    )

    @api.depends("source_resource_ids", "destination_resource_ids")
    def _compute_linked_resource_ids(self):
        """Compute based on two sided many2many relationships. Resources used
        as source or destination of a relationship are combinable both ways."""
        for resource in self:
            linked = resource.source_resource_ids | resource.destination_resource_ids
            resource.linked_resource_ids = linked

    def _inverse_linked_resource_ids(self):
        """Update combination. When having new combination, consider current
        record is always the source to simplify. When having to remove links
        remove from both source and destination relationships to be sure to
        really break the link."""
        for resource in self:
            actual_resources = resource.linked_resource_ids
            current_resources = (
                resource.source_resource_ids | resource.destination_resource_ids
            )
            new_resources = actual_resources - current_resources
            old_resources = current_resources - actual_resources
            resource.source_resource_ids = (
                resource.source_resource_ids + new_resources - old_resources
            )
            resource.destination_resource_ids -= old_resources

    @api.depends("capacity")
    def _compute_display_name(self):
        """Display the capacity of the resource next to its name when it is above 1."""
        for resource in self:
            resource_name_capacity = f"{resource.name} (🪑{resource.capacity})"
            display_name = (
                resource_name_capacity if resource.capacity > 1 else resource.name
            )
            resource.display_name = display_name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("resource_id"):
                resource = self.env["resource.resource"].browse(vals["resource_id"])
                vals.setdefault("capacity", resource.capacity)
                vals.setdefault("active", resource.active)
        return super().create(vals_list)

    def write(self, vals):
        events = (
            self.env["appointment.booking.line"]
            .sudo()
            .search(
                [
                    ("appointment_resource_id", "in", self.ids),
                ]
            )
            .calendar_event_id
            if {"shareable", "resource_id"} & vals.keys()
            else self.env["calendar.event"]
        )
        result = super().write(vals)
        events._sync_reservations()
        return result

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [
            dict(vals, name=self.env._("%s (copy)", resource.name))
            for resource, vals in zip(self, vals_list, strict=False)
        ]

    def _get_filtered_possible_capacity_combinations(
        self, asked_capacity, capacity_info
    ):
        """Get combinations of resources with total capacity based on the capacity needed and the resources we want.
        :param int asked_capacity: asked capacity for the appointment
        :param dict capacity_info: available resources (main and linked ones) mapped to their
            'total_remaining_capacity' and 'remaining_capacity', see
            appointment.type._slot_availability_select_best_resources
        :return list of tuple: e.g. [
            ((1, 3), 8),  # here the key: (1, 3) => combination of resource_ids; the value: 8 => remaining capacity for these resources
            ((1, 2, 3), 10),
        ]"""
        capacities = {}
        # get all capacities combination for the resources
        for resource in self:
            capacities.update(
                resource._get_possible_capacity_combinations(capacity_info)
            )
        # filter capacities combination that can fit the asked capacity for a group of resources
        possible_capacities = {
            resource_ids: remaining_capacity
            for resource_ids, remaining_capacity in capacities.items()
            if remaining_capacity >= asked_capacity
            and all(resource_id in self.ids for resource_id in resource_ids)
        }
        # Sort possible_capacities by capacity and number of resources used in the combination
        # possible_capacity[0] = resource_ids and possible_capacity[1] = capacity
        return sorted(
            possible_capacities.items(),
            key=lambda possible_capacity: (
                possible_capacity[1],
                len(possible_capacity[0]),
            ),
        )

    def _get_possible_capacity_combinations(self, capacity_info):
        """Return the possible capacity combination for the resource with all possible linked resources.
        :param dict capacity_info: available resources (main and linked ones) mapped to their
            'total_remaining_capacity' and 'remaining_capacity', see
            appointment.type._slot_availability_select_best_resources
        :return: a dict where the key is a tuple of resource ids and the value is the total remaining capacity of these resources
        e.g. {
            (1): 4,
            (1, 2): 6,
            (1, 3): 8,
            (1, 2, 3): 10,
        }
        """
        self.check_singleton()
        resource_remaining_capacity = capacity_info.get(self, {}).get(
            "remaining_capacity", self.capacity
        )
        capacities = {
            tuple(self.ids): resource_remaining_capacity,
        }
        for linked_resource in self.linked_resource_ids.sorted("sequence"):
            if len(capacities) >= MAX_CAPACITY_COMBINATIONS:
                _logger.warning(
                    "appointment.resource %s: capacity combination search capped at %s; "
                    "some linked resources were not considered. Reduce the number of "
                    "mutually linked resources on this appointment type.",
                    self.id,
                    MAX_CAPACITY_COMBINATIONS,
                )
                break
            capacities_to_add = {}
            for resource_ids, capacity in capacities.items():
                new_resource_ids = set(resource_ids)
                new_resource_ids.add(linked_resource.id)
                linked_resource_capacity = capacity_info.get(linked_resource, {}).get(
                    "remaining_capacity", linked_resource.capacity
                )
                capacities_to_add.update(
                    {
                        tuple(sorted(new_resource_ids)): capacity
                        + linked_resource_capacity,
                    }
                )
            capacities.update(capacities_to_add)
        return capacities

    def _prepare_resource_values(self, vals, tz):
        """Override of the mixin.resource model method to force "material" as resource type for
        the resources created for our appointment.resources"""
        # The backing resource is created before this model's defaults are filled.
        defaults = self.default_get(["company_id", "resource_calendar_id"])
        resource_values = super()._prepare_resource_values(defaults | vals, tz)
        resource_values["company_id"] = vals.get(
            "company_id", defaults.get("company_id")
        )
        resource_values["calendar_id"] = vals.get(
            "resource_calendar_id", defaults.get("resource_calendar_id")
        )
        resource_values["resource_type"] = "material"
        if vals.get("capacity"):
            resource_values["capacity"] = vals["capacity"]
        return resource_values
