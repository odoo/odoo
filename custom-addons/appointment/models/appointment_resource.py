# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.translate import html_translate


class AppointmentResource(models.Model):
    _name = "appointment.resource"
    _description = "Appointment Resource"
    _inherit = ["avatar.mixin", "resource.mixin"]
    _order = 'sequence,id'

    name = fields.Char('Appointment Resource', related="resource_id.name", store=True, required=True, readonly=False)
    active = fields.Boolean('Active', related="resource_id.active", default=True, store=True, readonly=False)
    sequence = fields.Integer("Sequence", default=1, required=True,
        help="""The sequence dictates if the resource is going to be picked in higher priority against another resource
        (e.g. for 2 tables of 4, the lowest sequence will be picked first)""")
    company_id = fields.Many2one(default=False)
    resource_id = fields.Many2one(copy=False)
    resource_calendar_id = fields.Many2one(
        default=lambda self: (
            self.env.ref('appointment.appointment_default_resource_calendar', raise_if_not_found=False) or
            self.env.company.resource_calendar_id),
        help="If kept empty, the working schedule of the company set on the resource will be used")
    capacity = fields.Integer("Capacity", default=1, required=True,
        help="""Maximum amount of people for this resource (e.g. Table for 6 persons, ...)""")
    shareable = fields.Boolean("Shareable",
        help="""This allows to share the resource with multiple attendee for a same time slot (e.g. a bar counter)""")
    source_resource_ids = fields.Many2many(
        'appointment.resource', 'appointment_resource_linked_appointment_resource',
        'resource_id', 'linked_resource_id',
        domain="[('id', '!=', id)]",
        string='Source combination',
    )
    destination_resource_ids = fields.Many2many(
        'appointment.resource', 'appointment_resource_linked_appointment_resource',
        'linked_resource_id', 'resource_id',
        domain="[('id', '!=', id)]",
        string='Destination combination',
    )
    linked_resource_ids = fields.Many2many(
        'appointment.resource',
        compute='_compute_linked_resource_ids',
        inverse='_inverse_linked_resource_ids',
        domain="[('id', '!=', id)]",
        store=False,
        help="""List of resources that can be combined to handle a bigger demand.""")
    description = fields.Html("Description", translate=html_translate, sanitize_attributes=False)
    appointment_type_ids = fields.Many2many('appointment.type', string="Available in",
        relation="appointment_type_appointment_resource_rel",
        domain="[('schedule_based_on', '=', 'resources')]")

    _sql_constraints = [
        ('check_capacity', 'check(capacity >= 1)', 'The resource should have at least one capacity.')
    ]

    @api.depends('source_resource_ids', 'destination_resource_ids')
    def _compute_linked_resource_ids(self):
        """ Compute based on two sided many2many relationships. Resources used
        as source or destination of a relationship are combinable both ways. """
        for resource in self:
            linked = resource.source_resource_ids | resource.destination_resource_ids
            resource.linked_resource_ids = linked

    def _inverse_linked_resource_ids(self):
        """ Update combination. When having new combination, consider current
        record is always the source to simplify. When having to remove links
        remove from both source and destination relationships to be sure to
        really break the link. """
        for resource in self:
            actual_resources = resource.linked_resource_ids
            current_resources = resource.source_resource_ids | resource.destination_resource_ids
            new_resources = actual_resources - current_resources
            old_resources = current_resources - actual_resources
            resource.source_resource_ids = resource.source_resource_ids + new_resources - old_resources
            resource.destination_resource_ids = resource.destination_resource_ids - old_resources

    @api.depends('capacity')
    def _compute_display_name(self):
        """ Display the capacity of the resource next to its name if resource_manage_capacity is enabled """
        for resource in self:
            resource_name_capacity = f"{resource.name} (🪑{resource.capacity})"
            display_name = resource_name_capacity if resource.capacity > 1 else resource.name
            resource.display_name = display_name

    def copy(self, default=None):
        default = dict(default or {})
        if not default.get('name'):
            default['name'] = _("%(original_name)s (copy)", original_name=self.name)
        return super().copy(default)

    def _get_filtered_possible_capacity_combinations(self, asked_capacity, capacity_info):
        """ Get combinations of resources with total capacity based on the capacity needed and the resources we want.
        :param int asked_capacity: asked capacity for the appointment
        :param dict main_resources_remaining_capacity: main resources available with the according total remaining capacity
        :param dict linked_resources_remaining_capacity: linked resources with the according remaining capacity
        :return list of tuple: e.g. [
            ((1, 3), 8),  # here the key: (1, 3) => combination of resource_ids; the value: 8 => remaining capacity for these resources
            ((1, 2, 3), 10),
        ]"""
        capacities = {}
        # get all capacities combination for the resources
        for resource in self:
            capacities.update(
                resource._get_possible_capacity_combinations(capacity_info))
        # filter capacities combination that can fit the asked capacity for a group of resources
        possible_capacities = {
            resource_ids: remaining_capacity
            for resource_ids, remaining_capacity in capacities.items()
            if remaining_capacity >= asked_capacity and all(resource_id in self.ids for resource_id in resource_ids)
        }
        # Sort possible_capacities by capacity and number of resources used in the combination
        # possible_capacity[0] = resource_ids and possible_capacity[1] = capacity
        return sorted(possible_capacities.items(), key=lambda possible_capacity: (possible_capacity[1], len(possible_capacity[0])))

    def _get_possible_capacity_combinations(self, capacity_info):
        """ Return the possible capacity combination for the resource with all possible linked resources.
        :param dict main_resources_remaining_capacity: main resources available with the according total remaining capacity
        :param dict linked_resources_remaining_capacity: linked resources with the according remaining capacity
        :return: a dict where the key is a tuple of resource ids and the value is the total remaining capacity of these resources
        e.g. {
            (1): 4,
            (1, 2): 6,
            (1, 3): 8,
            (1, 2, 3): 10,
        }
        """
        self.ensure_one()
        resource_remaining_capacity = capacity_info.get(self, {}).get('remaining_capacity', self.capacity)
        capacities = {
            tuple(self.ids): resource_remaining_capacity,
        }
        for linked_resource in self.linked_resource_ids.sorted('sequence'):
            capacities_to_add = {}
            for resource_ids, capacity in capacities.items():
                new_resource_ids = set(resource_ids)
                new_resource_ids.add(linked_resource.id)
                linked_resource_capacity = capacity_info.get(linked_resource, {}).get('remaining_capacity', linked_resource.capacity)
                capacities_to_add.update({
                    tuple(new_resource_ids): capacity + linked_resource_capacity,
                })
            capacities.update(capacities_to_add)
        return capacities

    def _prepare_resource_values(self, vals, tz):
        """ Override of the resource.mixin model method to force "material" as resource type for
        the resources created for our appointment.resources """
        resource_values = super()._prepare_resource_values(vals, tz)
        resource_values['resource_type'] = 'material'
        return resource_values
