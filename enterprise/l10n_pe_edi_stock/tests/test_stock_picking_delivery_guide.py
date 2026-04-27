# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta
from unittest.mock import patch

from odoo.addons.l10n_pe_edi.tests.common import TestPeEdiCommon
from odoo.addons.l10n_pe_edi_stock.models.stock_picking import Picking
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPEDeliveryGuideCommon(TestPeEdiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.new_wh = cls.env['stock.warehouse'].create({
            'name': 'New Warehouse',
            'reception_steps': 'one_step',
            'delivery_steps': 'ship_only',
            'code': 'NWH'
        })

        cls.customer_location = cls.env.ref('stock.stock_location_customers')

        cls.productA = cls.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'unspsc_code_id': cls.env.ref('product_unspsc.unspsc_code_01010101').id,
            'weight': 1,
            'barcode': '123456789',
        })

        cls.certificate.write({
            'date_start': datetime.today() - relativedelta(years=1),
            'date_end': datetime.today() + relativedelta(years=1),
        })

        cls.company_data['company'].l10n_pe_edi_stock_client_id = "Company SUNAT ID"
        cls.company_data['company'].partner_id.l10n_latam_identification_type_id = cls.env.ref('l10n_pe.it_RUC')
        cls.company_data['company'].partner_id.l10n_pe_district = cls.env.ref('l10n_pe.district_pe_030101')
        cls.company_data['company'].partner_id.street = 'Rocafort 314'

        cls.partner_a = cls.env['res.partner'].create({
            'name': 'Partner A',
            'street_number': '728',
            'street_name': 'Street Calle',
            'city': 'Arteaga',
            'country_id': cls.env.ref('base.pe').id,
            'state_id': cls.env.ref('base.state_pe_15').id,
            'l10n_pe_district': cls.env.ref('l10n_pe.district_pe_030101').id,
            'zip': '25350',
            'vat': '20100105862',
            'l10n_latam_identification_type_id': cls.env.ref('l10n_pe.it_RUC').id,
        })

        cls.operator_luigys = cls.env['res.partner'].create({
            'name': "Luigys Toro",
            'vat': "70025425",
            'l10n_latam_identification_type_id': cls.env.ref('l10n_pe.it_DNI').id,
            'street': "JESUS VALDES SANCHEZ 728",
            'city': "Chorrillos",
            'country_id': cls.env.ref('base.pe').id,
            'state_id': cls.env.ref('base.state_pe_15').id,
            'l10n_pe_district': cls.env.ref('l10n_pe.district_pe_030101').id,
            'zip': "25350",
            'phone': "+51 912 345 677",
            'l10n_pe_edi_operator_license': "Q40723053",
        })

        cls.vehicle_luigys = cls.env['l10n_pe_edi.vehicle'].create({
            'name': 'PE TRUCK',
            'license_plate': 'ABC123',
            'operator_id':  cls.operator_luigys.id,
        })

        cls.picking = cls.env['stock.picking'].create({
            'location_id': cls.new_wh.lot_stock_id.id,
            'location_dest_id': cls.customer_location.id,
            'picking_type_id': cls.new_wh.out_type_id.id,
            'partner_id': cls.partner_a.id,
            'l10n_pe_edi_transport_type': '02',
            'l10n_pe_edi_operator_id': cls.operator_luigys.id,
            'l10n_pe_edi_reason_for_transfer': '01',
            'l10n_pe_edi_departure_start_date': datetime.today(),
            'state': 'draft',
            'l10n_pe_edi_vehicle_id': cls.vehicle_luigys.id,
        })

        cls.env['stock.move'].create({
            'name': cls.productA.name,
            'product_id': cls.productA.id,
            'product_uom_qty': 10,
            'product_uom': cls.productA.uom_id.id,
            'picking_id': cls.picking.id,
            'location_id': cls.new_wh.lot_stock_id.id,
            'location_dest_id': cls.customer_location.id,
            'state': 'confirmed',
            'description_picking': cls.productA.name,
        })
        cls.env['stock.quant']._update_available_quantity(cls.productA, cls.new_wh.lot_stock_id, 10.0)
        cls.picking.action_confirm()
        cls.picking.action_assign()
        cls.picking.move_ids[0].move_line_ids[0].quantity = 10
        cls.picking.move_ids[0].picked = True
        cls.picking._action_done()

    def test_generate_delivery_guide(self):
        """ Check the XML in the test delivery is correctly generated """
        self.picking.l10n_latam_document_number = "T001-00000001"
        ubl = self.picking._l10n_pe_edi_create_delivery_guide()
        expected_document = '''
<DespatchAdvice
    xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
    xmlns="urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2"
    xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
    <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
    <cbc:CustomizationID>2.0</cbc:CustomizationID>
    <cbc:ID>___ignore___</cbc:ID>
    <cbc:IssueDate>___ignore___</cbc:IssueDate>
    <cbc:IssueTime>___ignore___</cbc:IssueTime>
    <cbc:DespatchAdviceTypeCode listAgencyName="PE:SUNAT" listName="Tipo de Documento" listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01">09</cbc:DespatchAdviceTypeCode>
    <cbc:Note>Guía</cbc:Note>
    <cac:DespatchSupplierParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID schemeName="Documento de Identidad" schemeAgencyName="PE:SUNAT" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06" schemeID="6">20557912879</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>company_1_data</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:DespatchSupplierParty>
    <cac:DeliveryCustomerParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID schemeName="Documento de Identidad" schemeAgencyName="PE:SUNAT" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06" schemeID="6">20100105862</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>Partner A</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:DeliveryCustomerParty>
    <cac:Shipment>
        <cbc:ID>SUNAT_Envio</cbc:ID>
        <cbc:HandlingCode listAgencyName="PE:SUNAT" listName="Motivo de traslado" listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo20">01</cbc:HandlingCode>
        <cbc:HandlingInstructions>Sale</cbc:HandlingInstructions>
        <cbc:GrossWeightMeasure unitCode="KGM">10.000</cbc:GrossWeightMeasure>
        <cac:ShipmentStage>
            <cbc:TransportModeCode listName="Modalidad de traslado" listAgencyName="PE:SUNAT" listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo18">02</cbc:TransportModeCode>
            <cac:TransitPeriod><cbc:StartDate>___ignore___</cbc:StartDate></cac:TransitPeriod>
            <cac:CarrierParty>
               <cac:PartyLegalEntity>
                   <cbc:CompanyID></cbc:CompanyID>
               </cac:PartyLegalEntity>
                   <cac:AgentParty>
                        <cac:PartyLegalEntity>
                            <cbc:CompanyID schemeName="Entidad Autorizadora" schemeAgencyName="PE:SUNAT" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogoD37"></cbc:CompanyID>
                        </cac:PartyLegalEntity>
                   </cac:AgentParty>
            </cac:CarrierParty>
            <cac:DriverPerson>
                <cbc:ID schemeName="Documento de Identidad" schemeAgencyName="PE:SUNAT" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06" schemeID="1">70025425</cbc:ID>
                <cbc:FirstName>Luigys Toro</cbc:FirstName>
                <cbc:FamilyName>Luigys Toro</cbc:FamilyName>
                <cbc:JobTitle>Principal</cbc:JobTitle>
                <cac:IdentityDocumentReference>
                    <cbc:ID>Q40723053</cbc:ID>
                </cac:IdentityDocumentReference>
            </cac:DriverPerson>
        </cac:ShipmentStage>
        <cac:Delivery>
            <cac:DeliveryAddress>
                <cbc:ID schemeName="Ubigeos" schemeAgencyName="PE:INEI">030101</cbc:ID>
                <cbc:AddressTypeCode listAgencyName="PE:SUNAT" listName="Establecimientos anexos" listID="20100105862">0</cbc:AddressTypeCode>
                <cac:AddressLine>
                    <cbc:Line>Street Calle 728 Abancay Arteaga Lima</cbc:Line>
                </cac:AddressLine>
            </cac:DeliveryAddress>
            <cac:Despatch>
                <cac:DespatchAddress>
                    <cbc:ID schemeName="Ubigeos" schemeAgencyName="PE:INEI">030101</cbc:ID>
                    <cbc:AddressTypeCode listAgencyName="PE:SUNAT" listName="Establecimientos anexos" listID="20557912879">0</cbc:AddressTypeCode>
                    <cac:AddressLine>
                        <cbc:Line>Rocafort 314 Abancay  </cbc:Line>
                    </cac:AddressLine>
                </cac:DespatchAddress>
            </cac:Despatch>
        </cac:Delivery>
        <cac:TransportHandlingUnit>
            <cac:TransportEquipment>
                <cbc:ID>ABC123</cbc:ID>
                <cac:ShipmentDocumentReference>
                    <cbc:ID schemeName="Entidad Autorizadora" schemeAgencyName="PE:SUNAT"></cbc:ID>
                </cac:ShipmentDocumentReference>
            </cac:TransportEquipment>
        </cac:TransportHandlingUnit>
    </cac:Shipment>
    <cac:DespatchLine>
        <cbc:ID>1</cbc:ID>
        <cbc:DeliveredQuantity unitCodeListID="UN/ECE rec 20" unitCodeListAgencyName="United Nations Economic Commission for Europe" unitCode="NIU">10.0000000000</cbc:DeliveredQuantity>
        <cac:OrderLineReference>
            <cbc:LineID>1</cbc:LineID>
        </cac:OrderLineReference>
        <cac:Item>
            <cbc:Description>Product A</cbc:Description>
            <cac:SellersItemIdentification>
                <cbc:ID>123456789</cbc:ID>
            </cac:SellersItemIdentification>
            <cac:CommodityClassification>
                <cbc:ItemClassificationCode listID="UNSPSC" listAgencyName="GS1 US" listName="Item Classification">01010101</cbc:ItemClassificationCode>
            </cac:CommodityClassification>
            <cac:AdditionalItemProperty>
                <cbc:Name>Indicador de bien regulado por SUNAT</cbc:Name>
                <cbc:NameCode listAgencyName="PE:SUNAT" listName="Propiedad del item" listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo55">123456789</cbc:NameCode>
                <cbc:Value>0</cbc:Value>
            </cac:AdditionalItemProperty>
        </cac:Item>
    </cac:DespatchLine>
</DespatchAdvice>
        '''
        current_etree = self.get_xml_tree_from_string(ubl)
        expected_etree = self.get_xml_tree_from_string(expected_document)
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_send_delivery_guide(self):
        """Ensure that delivery guide is generated and sent to the SUNAT."""

        self.picking.l10n_latam_document_number = 'T001-%s' % datetime.now().strftime('%H%M%S')
        with patch.object(Picking, '_l10n_pe_edi_sign', lambda *_args, **_kwargs: {'cdr': '1234567890'}):
            self.picking.action_send_delivery_guide()
        self.assertEqual(self.picking.l10n_pe_edi_status, 'sent', self.picking.l10n_pe_edi_error)
