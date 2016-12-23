# -*- coding: utf-'8' "-*-"

from openerp import models, fields, api, exceptions


class ProviderFedex(models.Model):
    """
    """
    _inherit ='shipping.provider'

    developer_key = fields.Char(string='Developer Key')
    developer_password = fields.Char(string='Password')
    account_number = fields.Char(string='Account Number')
    meter_number = fields.Char(string='Meter Number')

    default_droppoff_type = fields.Selection(
        [('BUSINESS_SERVICE_CENTER','BUSINESS_SERVICE_CENTER'),
        ('DROP_BOX','DROP_BOX'),
        ('REGULAR_PICKUP','REGULAR_PICKUP'),
        ('REQUEST_COURIER','REQUEST_COURIER'),
        ('STATION','STATION')], default='REGULAR_PICKUP'
        )

    default_packaging_type = fields.Selection(
        [('FEDEX_BOX','FEDEX_BOX'),
        ('FEDEX_ENVELOPE','FEDEX_ENVELOPE'),
        ('FEDEX_PAK','FEDEX_PAK'),
        ('FEDEX_TUBE','FEDEX_TUBE'),
        ('YOUR_PACKAGING','YOUR_PACKAGING')], default='FEDEX_BOX'
        )

    default_service_type=fields.Selection(
        [('INTERNATIONAL_ECONOMY','INTERNATIONAL_ECONOMY'),
        ('INTERNATIONAL_PRIORITY','INTERNATIONAL_PRIORITY'),
        ('PRIORITY_OVERNIGHT','PRIORITY_OVERNIGHT'),
        ('STANDARD_OVERNIGHT','STANDARD_OVERNIGHT')],default='INTERNATIONAL_PRIORITY'
        )

    default_document_content=fields.Selection(
        [('DERIVED','DERIVED'),
        ('DOCUMENTS_ONLY','DOCUMENTS_ONLY'),
        ('NON_DOCUMENTS','NON_DOCUMENTS')],default='NON_DOCUMENTS'
        )

    default_image_type=fields.Selection(
        [('PDF','PDF'),
        ('PNG','PNG')],default='PDF'
        )

    default_label_format_type=fields.Selection(
        [('COMMON2D','COMMON2D'),
        ('FEDEX_FREIGHT_STRAIGHT_BILL_OF_LADING','FEDEX_FREIGHT_STRAIGHT_BILL_OF_LADING'),
        ('LABEL_DATA_ONLY','LABEL_DATA_ONLY'),
        ('VICS_BILL_OF_LADING','VICS_BILL_OF_LADING')], default='COMMON2D'
        )
    
    default_label_stock_type=fields.Selection(
        [('PAPER_4X6','PAPER_4X6'),
        ('PAPER_4X8','PAPER_4X8'),
        ('PAPER_4X9','PAPER_4X9'),
        ('PAPER_7X4.75','PAPER_7X4.75'),
        ('PAPER_8.5X11_BOTTOM_HALF_LABEL','PAPER_8.5X11_BOTTOM_HALF_LABEL'),
        ('PAPER_8.5X11_TOP_HALF_LABEL','PAPER_8.5X11_TOP_HALF_LABEL'),
        ('PAPER_LETTER','PAPER_LETTER')], default='PAPER_LETTER'
        )

    default_label_order=fields.Selection(
        [('SHIPPING_LABEL_FIRST','SHIPPING_LABEL_FIRST'),
        ('SHIPPING_LABEL_LAST','SHIPPING_LABEL_LAST')], default='SHIPPING_LABEL_FIRST' 
        )

    default_label_printing_orientation=fields.Selection(
        [('BOTTOM_EDGE_OF_TEXT_FIRST','BOTTOM_EDGE_OF_TEXT_FIRST'),
        ('TOP_EDGE_OF_TEXT_FIRST','TOP_EDGE_OF_TEXT_FIRST')], default='TOP_EDGE_OF_TEXT_FIRST'
        )

    default_weight_unit=fields.Selection(
        [('LB','LB'),('KG','KG')],default='KG'
        )

    default_edt_request_type = fields.Selection(
        [('ALL','ALL'),('NONE','NONE')],default='ALL'
        )

    @api.one
    @api.constrains('default_edt_request_type','default_service_type')
    def _check_international_shipping(self):
        if "INTERNATIONAL" in self.default_service_type:
            if self.default_edt_request_type =="NONE" :
                raise exceptions.ValidationError("The EDT must be ALL when INTERNATIONAL")
        else :
            if self.default_edt_request_type =="ALL":
                raise exceptions.ValidationError("The EDT must be NONE when NOT INTERNATIONAL ")

"""
    @api.one
    @api.constrains('company_id')
    def _check_company_address(self):
        if not self.company_id.city :
            raise exceptions.ValidationError("The City must be completed")"""



class TxFedex(models.Model):
    """
    """
    _inherit='shipping.transaction'

    droppoff_type = fields.Selection(
        [('BUSINESS_SERVICE_CENTER','BUSINESS_SERVICE_CENTER'),
        ('DROP_BOX','DROP_BOX'),
        ('REGULAR_PICKUP','REGULAR_PICKUP'),
        ('REQUEST_COURIER','REQUEST_COURIER'),
        ('STATION','STATION')]
        )
    packaging_type = fields.Selection(
        [('FEDEX_BOX','FEDEX_BOX'),
        ('FEDEX_ENVELOPE','FEDEX_ENVELOPE'),
        ('FEDEX_PAK','FEDEX_PAK'),
        ('FEDEX_TUBE','FEDEX_TUBE'),
        ('YOUR_PACKAGING','YOUR_PACKAGING')]
        )
    service_type= fields.Selection(
        [('INTERNATIONAL_ECONOMY','INTERNATIONAL_ECONOMY'),
        ('INTERNATIONAL_PRIORITY','INTERNATIONAL_PRIORITY'),
        ('PRIORITY_OVERNIGHT','PRIORITY_OVERNIGHT')]
        )
    document_content=fields.Selection(
        [('DERIVED','DERIVED'),
        ('DOCUMENTS_ONLY','DOCUMENTS_ONLY'),
        ('NON_DOCUMENTS','NON_DOCUMENTS')]
        )

    image_type=fields.Selection(
        [('PDF','PDF'),
        ('PNG','PNG')]
        )

    label_format_type=fields.Selection(
        [('COMMON2D','COMMON2D'),
        ('FEDEX_FREIGHT_STRAIGHT_BILL_OF_LADING','FEDEX_FREIGHT_STRAIGHT_BILL_OF_LADING'),
        ('LABEL_DATA_ONLY','LABEL_DATA_ONLY'),
        ('VICS_BILL_OF_LADING','VICS_BILL_OF_LADING')]
        )
    
    label_stock_type=fields.Selection(
        [('PAPER_4X6','PAPER_4X6'),
        ('PAPER_4X8','PAPER_4X8'),
        ('PAPER_4X9','PAPER_4X9'),
        ('PAPER_7X4.75','PAPER_7X4.75'),
        ('PAPER_8.5X11_BOTTOM_HALF_LABEL','PAPER_8.5X11_BOTTOM_HALF_LABEL'),
        ('PAPER_8.5X11_TOP_HALF_LABEL','PAPER_8.5X11_TOP_HALF_LABEL'),
        ('PAPER_LETTER','PAPER_LETTER')]
        )

    label_order=fields.Selection(
        [('SHIPPING_LABEL_FIRST','SHIPPING_LABEL_FIRST'),
        ('SHIPPING_LABEL_LAST','SHIPPING_LABEL_LAST')]
        )

    label_printing_orientation=fields.Selection(
        [('BOTTOM_EDGE_OF_TEXT_FIRST','BOTTOM_EDGE_OF_TEXT_FIRST'),
        ('TOP_EDGE_OF_TEXT_FIRST','TOP_EDGE_OF_TEXT_FIRST')]
        )

    weight_unit=fields.Selection(
        [('LB','LB'),('KG','KG')]
        )

    default_edt_request_type = fields.Selection(
        [('ALL','ALL'),('NONE','NONE')]
        )

    @api.one
    @api.constrains('edt_request_type','service_type')
    def _check_international_shipping(self):
        if "INTERNATIONAL" in self.service_type:
            if self.edt_request_type =="NONE" :
                raise exceptions.ValidationError("The EDT must be ALL when INTERNATIONAL")
        else :
            if self.edt_request_type =="ALL":
                raise exceptions.ValidationError("The EDT must be NONE when NOT INTERNATIONAL ")

    """
    


    edt_request_type = fields.Selection





    customs_value_currency = fields.Selection
    customs_value_amount=fields.Float()
    document_type= fields.Selection

    shipping_charges_payment_type=fields.Selection
    shipping_charges_payment_account=
    """

