# -*- coding: utf-'8' "-*-"

from openerp import models, fields 


class ProviderFedex(models.Model):
    """
    """
    _inherit ='shipping.provider'

    developer_key = fields.Char(string='Developer Key')
    developer_password = fields.Char(string='Password')
    account_number = fields.Char(string='Account Number')
    meter_number = fields.Char(string='Meter Number')

    default_droppof_type = fields.Selection(
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
 #   default_label_stock_type=fields.Selection(
  #      [('')
   #     ])

    default_label_order=fields.Selection(
        [('SHIPPING_LABEL_FIRST','SHIPPING_LABEL_FIRST'),
        ('SHIPPING_LABEL_LAST','SHIPPING_LABEL_LAST')], default='SHIPPING_LABEL_FIRST')
    default_label_printing_orientation=fields.Selection(
        [('BOTTOM_EDGE_OF_TEXT_FIRST','BOTTOM_EDGE_OF_TEXT_FIRST'),
        ('TOP_EDGE_OF_TEXT_FIRST','TOP_EDGE_OF_TEXT_FIRST')], default='TOP_EDGE_OF_TEXT_FIRST'
        )

    default_weight_unit=fields.Selection(
        [('LB','LB'),('KG','KG')],default='KG')


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

    """
    

    label_format_type = fields.Selection()
    image_type = fields.Selection
    label_stock_type= fields.Selection
    edt_request_type = fields.Selection
    label_printing_orientation=fields.Selection
    label_order = fields.Selection

    overall_weight_unit=fields.Selection

    customs_value_currency = fields.Selection
    customs_value_amount=fields.Float()
    document_type= fields.Selection

    shipping_charges_payment_type=fields.Selection
    shipping_charges_payment_account=
    """

