# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Teachers(models.Model):
    _name = 'academy.teachers'
    _description = "Teachers"
    name = fields.Char()

    def create_invoices():
        print("create_invoices")

    def action_quotation_sent(self):
        self.write({'name': 'sent'})

    def do_advanced_query(self):
       pass

    def auto_create_record(self):
        pass
        #self.name_create("自动创建的记录")

    def getCities(self):
        cities = ["New York", "Los Angeles", "Chicago", "Houston", "Philadelphia", "Phoenix", "San Antonio",
                  "San Diego", "Dallas", "San Jose", "Austin", "Indianapolis", "Jacksonville", "San Francisco",
                  "Columbus", "Charlotte", "Fort Worth", "Detroit", "El Paso", "Memphis", "Seattle", "Denver",
                  "Washington", "Boston", "Nashville", "Baltimore", "Oklahoma City", "Louisville", "Portland",
                  "Las Vegas", "Milwaukee", "Albuquerque", "Tucson", "Fresno", "Sacramento", "Long Beach",
                  "Kansas City", "Mesa", "Virginia Beach", "Atlanta", "Colorado Springs", "Omaha", "Raleigh", "Miami",
                  "Oakland", "Minneapolis", "Tulsa", "Cleveland", "Wichita", "Arlington", "New Orleans", "Bakersfield",
                  "Tampa", "Honolulu", "Aurora", "Anaheim", "Santa Ana", "St. Louis", "Riverside", "Corpus Christi",
                  "Lexington", "Pittsburgh", "Anchorage", "Stockton", "Cincinnati", "Saint Paul", "Toledo",
                  "Greensboro", "Newark", "Plano", "Henderson", "Lincoln", "Buffalo", "Jersey City", "Chula Vista",
                  "Fort Wayne", "Orlando", "St. Petersburg", "Chandler", "Laredo", "Norfolk", "Durham", "Madison",
                  "Lubbock", "Irvine", "Winston–Salem", "Glendale", "Garland", "Hialeah", "Reno", "Chesapeake",
                  "Gilbert", "Baton Rouge", "Irving", "Scottsdale", "North Las Vegas", "Fremont", "Boise", "Richmond"];
        return cities

# class academy(models.Model):
#     _name = 'academy.academy'
#     _description = 'academy.academy'
#    access_academy_academy,academy.academy,model_academy_academy,base.group_user,1,1,1,1
#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
