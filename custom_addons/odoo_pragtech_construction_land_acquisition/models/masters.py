# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Who(models.Model):
    _name = 'who'
    _description = "Who"

    name = fields.Char('WHO Name', required=True)


class Style(models.Model):
    _name = 'style'
    _description = "Style"

    name = fields.Char('Style Name', required=True)


class Locations(models.Model):
    _name = 'locations'
    _description = "Locations"

    name = fields.Char('Location Name', required=True)


class Areas(models.Model):
    _name = 'areas'
    _description = "Areas"

    name = fields.Char('Area Name', required=True)
    location_id = fields.Many2one('locations', 'Location', required=True)


class DocumentType(models.Model):
    _name = 'document.type'
    _description = "DocumentType"

    name = fields.Char('Document Name', required=True)


class PropertyType(models.Model):
    _name = "property.type"
    _description = "Property Type"

    name = fields.Char('Name', required=True)


class PlaceType(models.Model):
    _name = 'place.type'
    _description = "Place Type"

    name = fields.Char('Place Type', required=True)


class ViewType(models.Model):
    _name = 'view.type'
    _description = "View Type"

    name = fields.Char('View Type', required=True)


class NearbyProperty(models.Model):
    _name = 'nearby.property'
    _description = "Nearby Property"

    distance = fields.Float('Distance (Km)')
    name = fields.Char('Name')
    type = fields.Many2one('place.type', 'Type')
    acquisition_id = fields.Many2one('land.acquisition', 'Acquisition')


class PropertyPhase(models.Model):
    _name = "property.phase"
    _description = "Property Phase"

    end_date = fields.Date('End Date')
    start_date = fields.Date('Beginning Date')
    commercial_tax = fields.Float('Commercial Tax (in %)')
    occupancy_rate = fields.Float('Occupancy Rate (in %)')
    lease_price = fields.Float('Sales/lease Price Per Month')
    phase_id = fields.Many2one('land.acquisition', 'Acquisition')
    operational_budget = fields.Float('Operational Budget (in %)')
    company_income = fields.Float('Company Income Tax CIT (in %)')


class PropertyPhoto(models.Model):
    _name = "property.photo"
    _description = "Property Photo"

    photos = fields.Binary('Photos', required=True)
    doc_name = fields.Char('Filename', required=True)
    photos_description = fields.Char('Description')
    photo_id = fields.Many2one('land.acquisition', 'Acquisition')
    select_row = fields.Boolean("Select To Delete")


class PropertyAttachment(models.Model):
    _name = 'property.attachment'
    _description = "Property Attachment"


    name = fields.Many2one('document.type', 'Document')
    docmment_attachment = fields.Binary('Attachment')
    photos = fields.Binary('Attachment', required=True)
    doc_name = fields.Char('Filename', required=True)
    photos_description = fields.Char('Description')
    photo_id = fields.Many2one('land.acquisition', 'Acquisition')
    property_id = fields.Many2one('land.acquisition', 'Acquisition')



class PartnerOwners(models.Model):
    _name = "res.partner.owners"
    _description = "Partner Owners"

    owner_id = fields.Many2one('land.acquisition', 'Owner')
    partner_id = fields.Many2one('res.partner', 'Owners')
    partnership = fields.Float('Partnership(%)')

    @api.onchange('partner_id')
    def onchange_owner_ids(self):
        global_list = []
        if self.owner_id:
            if self.owner_id.owner_ids:
                for owner in self.owner_id.owner_ids:
                    if owner.partner_id and owner.partner_id.is_owner == True:
                        global_list.append(owner.partner_id.id)

                if global_list:
                    domain = [('id', 'not in', global_list), ('is_owner', '=', True)]
                    return {
                        'domain': {
                            'partner_id': domain
                        }
                    }

