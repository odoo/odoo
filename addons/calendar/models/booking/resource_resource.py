import logging

from odoo import api, fields, models
from odoo.tools.translate import html_translate

_logger = logging.getLogger(__name__)

# `_get_possible_capacity_combinations` doubles its result for every combinable
# resource, so an unbounded search costs 2**len(combinable_resource_ids). It is
# reachable from the public appointment page, where 20 mutually combinable
# resources measured ~45s of CPU for a single request. Stop expanding past this
# many combinations; combinable resources are walked in `booking_sequence`
# order, so the ones an administrator ranked first are kept.
MAX_CAPACITY_COMBINATIONS = 4096


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    appointment_type_ids = fields.Many2many(
        comodel_name="appointment.type",
        relation="appointment_type_resource_rel",
        column1="resource_id",
        column2="appointment_type_id",
        string="Available in",
        domain="[('schedule_based_on', '=', 'resources')]",
    )
    is_bookable = fields.Boolean(
        compute="_compute_is_bookable",
        store=True,
        help="This resource is offered by at least one appointment type.",
    )
    booking_sequence = fields.Integer(
        default=1,
        required=True,
        help="Picked first when several resources fit the asked capacity (of two tables of 4, the lowest sequence goes first).",
    )
    booking_exclusive = fields.Boolean(
        default=True,
        help="A booking takes the whole resource, whatever capacity it asked for. Clear it to let several bookings share one time slot up to the capacity, as a bar counter does.",
    )
    source_resource_ids = fields.Many2many(
        comodel_name="resource.resource",
        relation="resource_combinable_resource_rel",
        column1="resource_id",
        column2="combinable_resource_id",
        string="Source combination",
        domain="[('id', '!=', id)]",
    )
    destination_resource_ids = fields.Many2many(
        comodel_name="resource.resource",
        relation="resource_combinable_resource_rel",
        column1="combinable_resource_id",
        column2="resource_id",
        string="Destination combination",
        domain="[('id', '!=', id)]",
    )
    combinable_resource_ids = fields.Many2many(
        comodel_name="resource.resource",
        compute="_compute_combinable_resource_ids",
        inverse="_inverse_combinable_resource_ids",
        store=False,
        domain="[('id', '!=', id)]",
        help="Resources that combine with this one to serve a bigger demand.",
    )
    description = fields.Html(
        translate=html_translate,
        sanitize_attributes=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        """A resource offered for booking works round the clock unless it says
        otherwise: a court or a table is not bound to office hours, and that is
        what the appointment calendar means. A resource that names its own
        calendar, or that is not offered, keeps what it was given."""
        default_calendar = self.env.ref(
            "calendar.appointment_default_resource_calendar", raise_if_not_found=False
        )
        if default_calendar:
            for vals in vals_list:
                if vals.get("appointment_type_ids") and not vals.get("calendar_id"):
                    vals["calendar_id"] = default_calendar.id
        return super().create(vals_list)

    def _get_booking_picture(self):
        """The record whose image the public booking page shows for this resource.

        A resource is time and capacity; it holds no picture. What a visitor
        recognises belongs to the thing behind it, which `resource_asset_calendar`
        answers with the asset.
        """
        self.check_singleton()
        return self.browse()

    @api.depends("appointment_type_ids")
    def _compute_is_bookable(self):
        for resource in self:
            resource.is_bookable = bool(resource.appointment_type_ids)

    @api.depends("source_resource_ids", "destination_resource_ids")
    def _compute_combinable_resource_ids(self):
        """Compute based on two sided many2many relationships. Resources used
        as source or destination of a relationship are combinable both ways."""
        for resource in self:
            resource.combinable_resource_ids = (
                resource.source_resource_ids | resource.destination_resource_ids
            )

    def _inverse_combinable_resource_ids(self):
        """Update combination. When having new combination, consider current
        record is always the source to simplify. When having to remove links
        remove from both source and destination relationships to be sure to
        really break the link."""
        for resource in self:
            actual_resources = resource.combinable_resource_ids
            current_resources = (
                resource.source_resource_ids | resource.destination_resource_ids
            )
            new_resources = actual_resources - current_resources
            old_resources = current_resources - actual_resources
            resource.source_resource_ids = (
                resource.source_resource_ids + new_resources - old_resources
            )
            resource.destination_resource_ids -= old_resources

    def _get_filtered_possible_capacity_combinations(
        self, asked_capacity, capacity_info
    ):
        """Get combinations of resources with total capacity based on the capacity needed and the resources we want.
        :param int asked_capacity: asked capacity for the appointment
        :param dict capacity_info: available resources (main and combinable ones) mapped to their
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
        """Return the possible capacity combination for the resource with all possible combinable resources.
        :param dict capacity_info: available resources (main and combinable ones) mapped to their
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
        for combinable_resource in self.combinable_resource_ids.sorted(
            "booking_sequence"
        ):
            if len(capacities) >= MAX_CAPACITY_COMBINATIONS:
                _logger.warning(
                    "resource.resource %s: capacity combination search capped at %s; "
                    "some combinable resources were not considered. Reduce the number of "
                    "mutually combinable resources on this appointment type.",
                    self.id,
                    MAX_CAPACITY_COMBINATIONS,
                )
                break
            capacities_to_add = {}
            for resource_ids, capacity in capacities.items():
                new_resource_ids = set(resource_ids)
                new_resource_ids.add(combinable_resource.id)
                combinable_resource_capacity = capacity_info.get(
                    combinable_resource, {}
                ).get("remaining_capacity", combinable_resource.capacity)
                capacities_to_add.update(
                    {
                        tuple(sorted(new_resource_ids)): capacity
                        + combinable_resource_capacity,
                    }
                )
            capacities.update(capacities_to_add)
        return capacities
