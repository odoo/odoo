# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import api, fields, models
from openerp.exceptions import RedirectWarning, Warning
from openerp.tools.translate import _
from ssl import SSLError
import base64
import json
import re
import urllib2

# URLs for requests
_account_url = 'https://www.docsaway.com/app/api/rest/account.json'
_station_finder_url = 'https://www.docsaway.com/app/api/rest/station_finder.json'
_pricing_url = 'https://www.docsaway.com/app/api/rest/pricing.json'
_mail_url = 'https://www.docsaway.com/app/api/rest/mail.json'

# Pattern to count the number of pages in a PDF file
_pattern = re.compile(r"/Count\s+(\d+)")


class mail_docsaway(models.Model):
    _name = 'mail_docsaway.api'
    
    price = fields.Float("Cost to Deliver", digits=(16,2))
    balance = fields.Float("Current DocsAway Balance", digits=(16,2))
    remaining = fields.Float("Remaining DocsAway Balance", digits=(16,2))
    station = fields.Char("Station ID")
    courier = fields.Char("Courier ID")
    nb_pages = fields.Integer("Number of Pages")
    partner_id = fields.Many2one('res.partner', string='Customer')
    pdf = fields.Binary("Report PDF")
    ink = fields.Selection([('BW', 'Black & White'),('CL', 'Colour')], "Ink")
    already_sent = fields.Boolean('Already Sent', default=False)
    sent_date = fields.Datetime('Sent Date', default=False)
    src_id = fields.Integer('Source ID')
    model_name = fields.Char('Model Name')
    currency_id = fields.Many2one('res.currency', string='Currency',
        required=True, readonly=True, track_visibility='always')
    paper = fields.Integer("Paper Weight", default=80)
    free_count = fields.Integer("Remaining Free Letters", default=0)
    attachment_ids = fields.Many2many('ir.attachment', 'message_attachment_rel',
        'message_id', 'attachment_id', 'Attachments', default=None)
    address_valid = fields.Boolean('Valid Address')

    
    @api.multi
    def _compute_price(self, balance):
        """ Find the best station to send the mail and gives the price
            Because it can send two JSON requests to the web service, it
            should be called as less as possible
        """
        for rec in self:
            if rec.ink and rec.address_valid:
                station, price = rec._fetch_price_info()
                rec.price = float(price['price'])
                rec.balance = balance
                rec.remaining = rec.balance - rec.price
                rec.station = station['stationAuto']['stationID']
                rec.courier = station['stationAuto']['courierID']
            else:
                rec.balance = balance
                rec.price = 0.00
                rec.remaining = rec.balance
                rec.station = ""
                rec.courier = ""
    
    
    @api.model
    def _get_currency(self):
        """ Return the currency for DocsAway (i.e., AUD) """
        return self.env['res.currency'].search([('name','=','AUD')])
    

    @api.model
    def _count_pages_pdf(self, pdf):
        """ Count the number of pages in the pdf file pdf """
        pages = 0
        for match in _pattern.finditer(pdf):
            pages = int(match.group(1))
        return pages


    @api.model
    def _check_address_errors(self, partner_id):
        """ Return an non-empty list if any piece of address information is missing """
        errors = []
        if not partner_id.street:
            errors.append(_('street'))
        if not partner_id.city:
            errors.append(_('city'))
        if not partner_id.zip:
            errors.append(_('ZIP code'))
        if not partner_id.country_id:
            errors.append(_('country'))
        return errors


    @api.model
    def _check_address(self, partner_id):
        """ If any piece of address information is missing, raise an error """
        errors = self._check_address_errors(partner_id)
        if errors:
            formated = errors.pop(0)
            for err in errors:
                formated += ', ' + err
            formated += '.'
            raise Warning(
                str(partner_id.name) + ': ' + _('to send a letter, partner address needs ') + formated)
                
                
    @api.model
    def _check_address_soft(self, partner_id):
        """ If any piece of address information is missing, return False """
        errors = self._check_address_errors(partner_id)
        if errors:
            return False
        return True


    @api.model
    def _get_report(self, ids, report_model):
        """ Generate the report for ids with report_model (in base64 encoding)
            and count the number of pages it contains
        """
        recs = self.browse(ids)
        report, format = self.env['report'].get_pdf(recs, report_model), 'pdf'
        numPages = self._count_pages_pdf(report)
        report64 = base64.b64encode(report)
        return report64, numPages


    @api.model
    def _call_single_wizard(self):
        """ Call the single wizard """
        res = {
            'name': 'Confirm Delivery',
            'view_mode': 'form',
            'res_model': 'mail_docsaway.single_wizard',
            'src_model': 'mail_docsaway.api',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self._context,
        }
        return res


    @api.model
    def _get_account_credentials(self):
        """Return a tuple (email, installation_key)"""
        email = self.env["ir.config_parameter"].get_param("mail.docsaway.email") or ""
        installation_key = self.env["ir.config_parameter"].get_param("mail.docsaway.installation_key") or ""
        return email, installation_key
        
        
    @api.model
    def _get_credentials(self):
        """ Return a tuple (email, installation_key, is_sass_account), either of
            Odoo (if sass and still free mails, sass_account = True) or the
            account credentials of the user/company (sass_account = False)
        """
        # If there is one, return user credentials
        email, installation_key = self._get_account_credentials()
        if email and installation_key:
            return email, installation_key, False
        # If no account, return sass account
        company_id = self.env.user.company_id
        return company_id._get_credentials_docsaway_try()
        
        
    @api.model
    def _get_ink(self):
        """Return the ink wanted """
        return self.env["ir.config_parameter"].get_param("mail.docsaway.ink") or 'BW'

        
    @api.model
    def _get_api_mode(self):
        """ Return the API mode used (TEST or LIVE) """
        return self.env["ir.config_parameter"].get_param("mail.docsaway.mode") or 'TEST'


    @api.model
    def _check_error(self, json_response):
        """ Check if json_response['APIErrorNumber'] == 0, otherwise raise an
            error (log in console if not related to user)
        """
        APIErrorNumber = int(json_response['APIErrorNumber'])
        if not APIErrorNumber == 0:
            if APIErrorNumber == 2:
                raise Warning(
                    _('Your DocsAway account information is incorrect.') + ' ' +
                    _('Please check your email and installation key in \
                    General Settings -> DocsAway.') + ' ' + \
                    _('Please contact your administrator.'))
            elif APIErrorNumber == 3:
                raise Warning(
                    _('This DocsAway account has been desactivated.') + ' ' +
                    _('Please contact your administrator.'))
            elif APIErrorNumber == 32:
                raise Warning(
                    _('Your DocsAway account has insufficient funds.'))
            else:
                print(json_response)
                raise Warning(
                    _('Technical error with DocsAway.') + ' ' +
                    _('Please contact your administrator.'))


    @api.model
    def _connect_to_server(self, url, json_dict):
        """ Connect to the server, do a POST request to url with parameter
            json_dict and return the JSON response
        """
        email, installation_key, is_sass_account = self._get_credentials()
        if email is False or installation_key is False:
            action = self.env.ref('base_setup.action_general_configuration')
            msg = _("You have no more free mails to send.") + "\n" + \
                _("Please open a new DocsAway account (follow instructions in General Settings -> Send Documents).")
            raise RedirectWarning(msg, action.id, _('Configure Account Now'))
        mode = self._get_api_mode()
        json_dict.update({
            'APIConnection': {
                'email': email,
                'key': installation_key,
            },
            'APIReport': mode,
        })
        # Convert dictionary to JSON format
        json_data = json.dumps(json_dict)
        # Post JSON object to the Docsaway server
        req = urllib2.Request(url, json_data, {'Content-Type': 'application/json'})
        try:
            f = urllib2.urlopen(req, timeout=15)
        except SSLError:
            raise Warning(
                _('Host unreachable.') + ' ' + _('Please try again later.'))

        if f.getcode() != 200:
            raise Warning(
                _('Failed request.') + ' ' + _('Please try again later.'))

        response = f.read()
        f.close()
        return json.loads(response)


    @api.multi
    def _connect_account(self, reference=None):
        """ Allow to access remotely to the Docsaway account and fetch information about
            If reference is set, then the Response JSON will add information
            about the document with the given reference
            Return a Response JSON object (explained below) if connection to the
            server succeeds, otherwise None

            Explaination of the Request JSON Object :
                - APIConnection: info about connection. It has 2 subfields:
                    - Email: login email
                    - Key: Docsaway installation key
                - APIReport: show more visual view for debugging
                - balance: True if want to have the balance in the JSON object
                - reference:  True if want to have the account reference in JSON
                - company: True if want to have the account company name in JSON
                - name: True if want to have the account name in JSON
                - audit: refenrence code of the document you want to retrieve

             Explaination of the Response JSON Object :
                - APIErrorNumber: if not 0, indicate error
                - APIReport: this JSON object in textual form (except APIReport)
                - audit: detailed informations if required
                - balance: decimal value which represent the current balance
                - company: account company name
                - name: account holders full name
                - reference: account holders account reference
                - volume: return the total number of documents sent
        """
        json_dict = {
            'balance': True,
            'volume': True,
            'reference': True,
            'company': True,
            'name': True,
        }
        if reference is not None:
            json_dict.update({
                'audit': reference,
            })
        return self._connect_to_server(_account_url, json_dict)


    @api.multi
    def _get_station_auto(self):
        """ Return the "best" station to print a document given a destination
            dest under a JSON format

            Explaination of the Request JSON Object :
                - APIConnection: info about connection. It has 2 subfields:
                    - Email: login email
                    - Key: Docsaway installation key
                - APIReport: show more visual view for debugging
                - action: function desired (here, getStationAuto)
                - ink: BW (Black & White) or CL (color)
                - paper: value in gram per square meter (default is 80 gsm)
                - destination: ISO 3166-1 (2 or 3 letter country codes)
                - StationID: AUTO (to find automatically)

             Explaination of the Response JSON Object :
                - APIErrorNumber: if not 0, indicate error
                - APIReport: this JSON object in textual form (except APIReport)
                - stationAuto: contains 3 subfields:
                    - stationID: the ID of the station
                    - courierID: the ID of the courier
                    - zone: integer (used for pricing)
        """
        for rec in self:
            json_dict = {
                'action': "getStationAuto",
                'ink': rec.ink,
                'paper': rec.paper,
                'destination': rec.partner_id.country_id.code,
                'StationID': "AUTO",
            }
            return self._connect_to_server(_station_finder_url, json_dict)


    @api.multi
    def _get_pricing(self, station, courier, zone):
        """ Return the price of sending a document with station, courier in zone
            that makes pageCount pages, if it's in color, and depending of the
            paper used

            Explaination of the Request JSON Object :
                - APIConnection: info about connection. It has 2 subfields:
                    - Email: login email
                    - Key: Docsaway installation key
                - APIReport: show more visual view for debugging
                - stationID: station id code of the station used
                - courierID: courier id code of the station used
                - paper: value in gram per square meter (default is 80 gsm)
                - ink: BW (Black & White) or CL (color)
                - zone: zone number given by _get_station_auto
                    (1=local, 2=national, 3=international)
                - pageCount: number of pages of the PDF to be sent (1-40)
                - currency: in which currency the price will be displayed.
                            By default, in AUD

            Explaination of the Response JSON Object :
                - APIErrorNumber: if not 0, indicate error
                - APIReport: this JSON object in textual form (except APIReport)
                - price: the price with two decimals
        """
        for rec in self:
            json_dict = {
                'stationID': station,
                'courierID': courier,
                'zone': zone,
                # A coversheet is added, which add a page (according to Docsaway)
                'pageCount': rec.nb_pages + 1,
                'paper': rec.paper,
                'ink': rec.ink,
                'currency': rec.currency_id.name,
            }
            return self._connect_to_server(_pricing_url, json_dict)


    @api.multi
    def _send_mail(self):
        """ Ask Docsaway to send the report at the address of the partner
        
        Explaination of the Request JSON Object :
            - APIConnection: info about connection. It has 2 subfields:
            - Email: login email
            - Key: Docsaway installation key
            - APIReport: show more visual view for debugging
            - APIMode: LIVE in production, TEST for debug
            - Recipient: information about recipient, 8 subfields:
                - name
                - company (not mandatory)
                - address1
                - address2 (not mandatory)
                - city
                - state (not mandatory)
                - zip
                - country (in ISO 3166-1, alpha 2, 3 or numeric)
            - PrintingStation: specify the printing station used, 4 subfields:
                - id (of station, or AUTO for automatic choice)
                - courierID (or False for automatic choice)
                - ink (CL for colour, BW for Black & White)
                - paper (paper weight (in gsm), 80 by default)
            - PDFFile: the PDF file to print (in base64 encoding, max 2MB)
            - Reseller: requires the value of the Docsaway account reference,
            used for service where customers are using their login
            details via the module. Not mandatory
        
        Explaination of the Response JSON Object:
            - APIErrorNumber: if not 0, indicate error
            - APIReport: this JSON object in textual form (except APIReport)
            - document: properties about the document sent, 4 subfields:
                - Envelope: id of envelope used (DL, C4, ...)
                - Ink: id of ink used (CL or BW)
                - Paper: paper weight used for the document in GSM
                - Size: total number of pages in the document send
            - station: properties about the station used, 7 subfields:
                - ID: id of station used
                - ISO2: ISO country code of the station in ISO 3166-1 Alpha 2
                - Country: country name of the station
                - City: city name of the station
                - Courier ID: courier id used by the station
                - Courier Name: name of the courier used
                - Zone: (1=local, 2=national, 3=international)
            - transaction: propoerties of the transaction, 5 subfields:
                - Approved: y (successful transaction) or n (failed one)
                - Price: price (in AUD)
                - Reference: unique string to refer this transaction
                - Date: date and time of transaction according to Docsaway
                - Balance: return the remaining account balance after
                    transaction (in AUD)
        """
        APIMode = self._get_api_mode()
        for rec in self:
            json_dict = {
                'APIMode': APIMode,
                'Recipient': {
                    'name': rec.partner_id.name,
                    'address1': rec.partner_id.street,
                    'city': rec.partner_id.city,
                    'zip': rec.partner_id.zip,
                    'country': rec.partner_id.country_id.code,
                },
                'PrintingStation': {
                    'id': rec.station,
                    'courierID': rec.courier,
                    'ink': rec.ink,
                    'paper': rec.paper,
                },
                'PDFFile': rec.pdf,
            }
            if rec.partner_id.street2:
                json_dict['Recipient'].update({
                    'address2': rec.partner_id.street2,
                })
            if rec.partner_id.state_id:
                json_dict['Recipient'].update({
                    'state': rec.partner_id.state_id.name,
                })
            if rec.partner_id.parent_id and not rec.partner_id.is_company:
                json_dict['Recipient'].update({
                    'company': rec.partner_id.parent_id.name,
                })

            response = self._connect_to_server(_mail_url, json_dict)
            self._check_error(response)
            dummy1, dummy2, is_sass_account = self._get_credentials()
            if is_sass_account:
                company_id = self.env.user.company_id
                company_id._send_free_docsaway(1)


    @api.multi
    def _fetch_price_info(self):
        """ Get all information about the pricing of a mail to Docsaway
            Because it send two JSON requests to the web service, it
            should be called as less as possible
        """
        for rec in self:
            station = rec._get_station_auto()
            self._check_error(station)
            price = rec._get_pricing(station['stationAuto']['stationID'],\
                station['stationAuto']['courierID'], station['stationAuto']['zone'])
            self._check_error(price)
            return station, price
        
        
    @api.model
    def _get_free_count(self):
        """ If the current company has still free mails, return the number of
            remaining free mails, otherwise 0
        """
        dum1, dum2, sass_account = self._get_credentials()
        free_count = 0
        if sass_account:
            company_id = self.env.user.company_id
            free_count = company_id._check_docsaway_try()
        return free_count
        
    
    @api.model
    def _get_balance(self):
        """ Return the current DocsAway balance of the DocsAway account used
            Because it send one JSON requests to the web service, it
            should be called with care
        """
        account = self._connect_account()
        self._check_error(account)
        return float(account['balance'])


    @api.model
    def _prepare_delivery(self, ids, model_name, report_model, partner_id):
        """ Create the report and prepare the wizard to ask confirmation for
            delivery
        """
        ctx = {}
        if self._context is not None:
            ctx.update(self._context)

        self._check_address(partner_id)
        report64, numPages = self._get_report(ids, report_model)
            
        balance = self._get_balance()
        currency_id = self._get_currency()
        ink = self._get_ink()
        elem = self.env[model_name].browse(ids)
        free_count = self._get_free_count()
            
        values = {
            'nb_pages': numPages,
            'partner_id': partner_id.id,
            'pdf': report64,
            'currency_id': currency_id.id,
            'ink': ink,
            'already_sent': elem.sent_docsaway,
            'sent_date': elem.date_sent_docsaway,
            'model_name': model_name,
            'src_id': elem.id,
            'free_count': free_count,
            'address_valid': True,
        }
        
        mail_id = self.create(values)
        # Enforce computation of price before lauching the wizard
        mail_id._compute_price(balance)
        
        ctx.update({
            'docsaway_mail_id': mail_id.id,
        })
        recs = self.with_context(ctx)
        return recs._call_single_wizard()


    @api.multi
    def _send_mail_multiple(self):
        """ The sending method for multiple delivery
            Return True if the mail was sent, otherwise False (when invalid address)
        """
        for rec in self:
            # If no report, don't send anything
            if not self.pdf:
                return False
            self._send_mail()
            return True
        

    @api.model
    def _compute_multiple_price(self, mail_ids, balance):
        """ Intended to decrease the number of requests made with multiple
            delivery
            Find the best station to print mails and compute its price
            mail_ids is the list of mails to compute price, and balance is the
            value of the balance of the account
        """
        known = {}
        for mail_id in mail_ids:
            # If address valid and already shown
            if (mail_id.partner_id.country_id, mail_id.ink, mail_id.nb_pages) in known and \
                mail_id.ink and mail_id.address_valid:
                data = known[mail_id.partner_id.country_id, mail_id.ink, mail_id.nb_pages]
                mail_id.price = data['price']
                mail_id.balance = balance
                mail_id.remaining = mail_id.balance - mail_id.price
                mail_id.station = data['station']
                mail_id.courier = data['courier']
            else:
                mail_id._compute_price(balance)
                # Store only if valid address and ink
                if mail_id.ink and mail_id.address_valid:
                    known[mail_id.partner_id.country_id, mail_id.ink, mail_id.nb_pages] = {
                        'price': mail_id.price,
                        'station': mail_id.station,
                        'courier': mail_id.courier,
                    }
                    
    
    @api.multi
    def _compute_price_with_attachment(self, page_lengths, balance):
        """ Compute the price of sending len(page_lengths) mails to each
            selected customer, and mail i has page_lengths[i] pages
        """
        known = {}
        for rec in self:
            if not rec.address_valid or len(page_lengths) == 0:
                rec.balance = balance
                rec.price = 0.00
                rec.remaining = rec.balance
                rec.station = ""
                rec.courier = ""
            else:
                # Accumulator for the price on all documents
                rec.price = 0.00
                for length in page_lengths:
                    if length in known:
                        rec.balance = balance
                        data = known[length]
                        rec.price += data['price']
                        rec.remaining = rec.balance - rec.price
                        rec.station = data['station']
                        rec.courier = data['courier']
                    else:
                        rec.nb_pages = length
                        station, price = rec._fetch_price_info()
                        rec.price += float(price['price'])
                        rec.balance = balance
                        rec.remaining = rec.balance - rec.price
                        rec.station = station['stationAuto']['stationID']
                        rec.courier = station['stationAuto']['courierID']
                        known[length] = {
                            'price': rec.price,
                            'station': rec.station,
                            'courier': rec.courier,
                        }
    
    
    @api.model                
    def _compute_multiple_price_with_attachments(self, mail_ids, page_lengths, balance):
        """ Intended to decrease the number of requests made with multiple
            delivery
            Find the best station to print mails and compute its price
            mail_ids is the list of mails to compute price, and balance is the
            value of the balance of the account
            Price is computed based on its balance
        """
        known = {}
        for mail_id in mail_ids:
            # If address valid and already shown
            if (mail_id.partner_id.country_id, mail_id.ink, mail_id.attachment_ids) in known and \
                mail_id.ink and mail_id.address_valid:
                data = known[mail_id.partner_id.country_id, mail_id.ink, mail_id.attachment_ids]
                mail_id.price = data['price']
                mail_id.balance = balance
                mail_id.remaining = mail_id.balance - mail_id.price
                mail_id.station = data['station']
                mail_id.courier = data['courier']
            else:
                mail_id._compute_price_with_attachment(page_lengths, balance)
                # Store only if valid address and ink
                if mail_id.ink and mail_id.address_valid:
                    known[mail_id.partner_id.country_id, mail_id.ink, mail_id.attachment_ids] = {
                        'price': mail_id.price,
                        'station': mail_id.station,
                        'courier': mail_id.courier,
                    }


    @api.model
    def _prepare_multiple_deliveries(self, ids, model_name, report_model, wiz_id, ink='BW'):
        """ For multiple wizard, create the wiz_ids attribute and compute the
            best station and price for mails
        """
        elements = self.env[model_name].browse(ids)
        res = []
        mail_ids = []
        currency_id = self._get_currency()
        balance = self._get_balance()
        
        # Generate reports and initialize the records
        for element in elements:
            # If address is not valid, don't generate the report
            address_valid = self._check_address_soft(element.partner_id)
            report64, numPages = "", 0
            if address_valid:
                report64, numPages = self._get_report([element.id], report_model)
                
            values = {
                'nb_pages': numPages,
                'partner_id': element.partner_id.id,
                'pdf': report64,
                'currency_id': currency_id.id,
                'already_sent': element.sent_docsaway,
                'sent_date': element.date_sent_docsaway,
                'model_name': model_name,
                'ink': ink,
                'src_id': element.id,
                'address_valid': address_valid,
            }
            
            mail_id = self.create(values)
            
            mail_ids.append(mail_id)
            res.append((0, 0, {
                'mail_id': mail_id.id,
                'wizard_id': wiz_id,
                'first_call': True,
            }))
        # Compute now the price in order to benefit of information other mails
        # can bring without calling the web service
        self._compute_multiple_price(mail_ids, balance)
        return res
        
    @api.model
    def _prepare_document_deliveries(self, ids, wiz_id, ink='BW'):
        """ To deliver to partners with active_ids some documents defined after """
        partners = self.env['res.partner'].browse(ids)
        res = []
        mail_ids = []
        currency_id = self._get_currency()
        balance = self._get_balance()
        
        for partner in partners:
            address_valid = self._check_address_soft(partner)
            values = {
                'nb_pages': 0,
                'partner_id': partner.id,
                'pdf': "",
                'currency_id': currency_id.id,
                'already_sent': False,
                'sent_date': False,
                'model_name': "",
                'ink': ink,
                'src_id': partner.id,
                'address_valid': address_valid,
            }
            mail_id = self.create(values)
            
            mail_ids.append(mail_id)
            res.append((0, 0, {
                'mail_id': mail_id.id,
                'wizard_customer_id': wiz_id,
                'first_call': True,
            }))
        # The compute will just gives default values for the elements
        self._compute_multiple_price_with_attachments(mail_ids, [], balance)
        return res
