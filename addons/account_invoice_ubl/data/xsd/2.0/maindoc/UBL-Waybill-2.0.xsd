<?xml version="1.0" encoding="UTF-8"?>
<!--
  Document Type:     Waybill
  Generated On:      Tue Oct 03 2:26:39 P3 2006

-->
<!-- ===== xsd:schema Element With Namespaces Declarations ===== -->
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    targetNamespace="urn:oasis:names:specification:ubl:schema:xsd:Waybill-2"
    xmlns="urn:oasis:names:specification:ubl:schema:xsd:Waybill-2"
    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
    xmlns:udt="urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2"
    xmlns:ccts="urn:un:unece:uncefact:documentation:2"
    xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
    xmlns:qdt="urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2"
    elementFormDefault="qualified"
    attributeFormDefault="unqualified"
    version="2.0">
<!-- ===== Imports ===== -->
  <xsd:import namespace="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" schemaLocation="../common/UBL-CommonAggregateComponents-2.0.xsd"/>
  <xsd:import namespace="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemaLocation="../common/UBL-CommonBasicComponents-2.0.xsd"/>
  <xsd:import namespace="urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2" schemaLocation="../common/UnqualifiedDataTypeSchemaModule-2.0.xsd"/>
  <xsd:import namespace="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" schemaLocation="../common/UBL-CommonExtensionComponents-2.0.xsd"/>
  <xsd:import namespace="urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2" schemaLocation="../common/UBL-QualifiedDatatypes-2.0.xsd"/>
<!-- ===== Root Element ===== -->
  <xsd:element name="Waybill" type="WaybillType">
    <xsd:annotation>
      <xsd:documentation>This element MUST be conveyed as the root element in any instance document based on this Schema expression</xsd:documentation>
    </xsd:annotation>
  </xsd:element>
  <xsd:complexType name="WaybillType">
    <xsd:annotation>
      <xsd:documentation>
        <ccts:Component>
          <ccts:ComponentType>ABIE</ccts:ComponentType>
          <ccts:DictionaryEntryName>Waybill. Details</ccts:DictionaryEntryName>
          <ccts:Definition>The Waybill is issued by the party who acts as an agent for the carrier or other agents, to the party who gives instructions for the transportation services (shipper, consignor, etc.) stating the details of the transportation, charges, and terms and conditions under which the transportation service is provided. The party issuing this document could be a party other than that providing the physical transportation. It corresponds to the information on the Forwarding Instruction. It is used for all modes of transport. It can serve as a contractual document between the parties for the transportation service. The document made out by the carrier or on behalf of the carrier evidencing the contract for the transport of cargo.</ccts:Definition>
          <ccts:ObjectClass>Waybill</ccts:ObjectClass>
          <ccts:AlternativeBusinessTerms>Consignment Note</ccts:AlternativeBusinessTerms>
        </ccts:Component>
      </xsd:documentation>
    </xsd:annotation>
    <xsd:sequence>
      <xsd:element ref="ext:UBLExtensions" minOccurs="0" maxOccurs="1">
        <xsd:annotation>
          <xsd:documentation>A container for all extensions present in the document.</xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cbc:UBLVersionID" minOccurs="0" maxOccurs="1">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>BBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. UBL Version Identifier. Identifier</ccts:DictionaryEntryName>
              <ccts:Definition>The earliest version of the UBL 2 schema for this document type that defines all of the elements that might be encountered in the current instance.</ccts:Definition>
              <ccts:Cardinality>0..1</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTerm>UBL Version Identifier</ccts:PropertyTerm>
              <ccts:RepresentationTerm>Identifier</ccts:RepresentationTerm>
              <ccts:DataType>Identifier. Type</ccts:DataType>
              <ccts:Examples>2.0.5</ccts:Examples>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cbc:CustomizationID" minOccurs="0" maxOccurs="1">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>BBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Customization Identifier. Identifier</ccts:DictionaryEntryName>
              <ccts:Definition>Identifies a user-defined customization of UBL for a specific use.</ccts:Definition>
              <ccts:Cardinality>0..1</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTerm>Customization Identifier</ccts:PropertyTerm>
              <ccts:RepresentationTerm>Identifier</ccts:RepresentationTerm>
              <ccts:DataType>Identifier. Type</ccts:DataType>
              <ccts:Examples>NES</ccts:Examples>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cbc:ProfileID" minOccurs="0" maxOccurs="1">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>BBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Profile Identifier. Identifier</ccts:DictionaryEntryName>
              <ccts:Definition>Identifies a user-defined profile of the customization of UBL being used.</ccts:Definition>
              <ccts:Cardinality>0..1</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTerm>Profile Identifier</ccts:PropertyTerm>
              <ccts:RepresentationTerm>Identifier</ccts:RepresentationTerm>
              <ccts:DataType>Identifier. Type</ccts:DataType>
              <ccts:Examples>BasicProcurementProcess</ccts:Examples>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cbc:ID" minOccurs="1" maxOccurs="1">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>BBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Identifier</ccts:DictionaryEntryName>
              <ccts:Definition>Unique identifier of the Waybill. Reference number to identify a document evidencing a transport contract.</ccts:Definition>
              <ccts:Cardinality>1</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTerm>Identifier</ccts:PropertyTerm>
              <ccts:RepresentationTerm>Identifier</ccts:RepresentationTerm>
              <ccts:DataType>Identifier. Type</ccts:DataType>
              <ccts:AlternativeBusinessTerms>Master Waybill Number</ccts:AlternativeBusinessTerms>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cbc:CarrierAssignedID" minOccurs="0" maxOccurs="1">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>BBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Carrier Assigned_ Identifier. Identifier</ccts:DictionaryEntryName>
              <ccts:Definition>Reference number assigned by a carrier or its agent to identify a specific shipment.</ccts:Definition>
              <ccts:Cardinality>0..1</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTermQualifier>Carrier Assigned</ccts:PropertyTermQualifier>
              <ccts:PropertyTerm>Identifier</ccts:PropertyTerm>
              <ccts:RepresentationTerm>Identifier</ccts:RepresentationTerm>
              <ccts:DataType>Identifier. Type</ccts:DataType>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cbc:UUID" minOccurs="0" maxOccurs="1">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>BBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. UUID. Identifier</ccts:DictionaryEntryName>
              <ccts:Definition>A universally unique identifier for an instance of this ABIE.</ccts:Definition>
              <ccts:Cardinality>0..1</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTerm>UUID</ccts:PropertyTerm>
              <ccts:RepresentationTerm>Identifier</ccts:RepresentationTerm>
              <ccts:DataType>Identifier. Type</ccts:DataType>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cbc:IssueDate" minOccurs="0" maxOccurs="1">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>BBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Issue Date. Date</ccts:DictionaryEntryName>
              <ccts:Definition>Date on which the Waybill was issued.</ccts:Definition>
              <ccts:Cardinality>0..1</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTerm>Issue Date</ccts:PropertyTerm>
              <ccts:RepresentationTerm>Date</ccts:RepresentationTerm>
              <ccts:DataType>Date. Type</ccts:DataType>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cbc:IssueTime" minOccurs="0" maxOccurs="1">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>BBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Issue Time. Time</ccts:DictionaryEntryName>
              <ccts:Definition>Time at which the Waybill was issued.</ccts:Definition>
              <ccts:Cardinality>0..1</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTerm>Issue Time</ccts:PropertyTerm>
              <ccts:RepresentationTerm>Time</ccts:RepresentationTerm>
              <ccts:DataType>Time. Type</ccts:DataType>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cbc:Name" minOccurs="0" maxOccurs="1">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>BBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Name</ccts:DictionaryEntryName>
              <ccts:Definition>Name of a Waybill.</ccts:Definition>
              <ccts:Cardinality>0..1</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTerm>Name</ccts:PropertyTerm>
              <ccts:RepresentationTerm>Name</ccts:RepresentationTerm>
              <ccts:DataType>Name. Type</ccts:DataType>
              <ccts:Examples>"Air Waybill", "House Waybill"</ccts:Examples>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cbc:Description" minOccurs="0" maxOccurs="unbounded">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>BBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Description. Text</ccts:DictionaryEntryName>
              <ccts:Definition>Textual description of a Waybill.</ccts:Definition>
              <ccts:Cardinality>0..n</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTerm>Description</ccts:PropertyTerm>
              <ccts:RepresentationTerm>Text</ccts:RepresentationTerm>
              <ccts:DataType>Text. Type</ccts:DataType>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cbc:Note" minOccurs="0" maxOccurs="unbounded">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>BBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Note. Text</ccts:DictionaryEntryName>
              <ccts:Definition>Textual note associated with a Waybill.</ccts:Definition>
              <ccts:Cardinality>0..n</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTerm>Note</ccts:PropertyTerm>
              <ccts:RepresentationTerm>Text</ccts:RepresentationTerm>
              <ccts:DataType>Text. Type</ccts:DataType>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cbc:ShippingOrderID" minOccurs="0" maxOccurs="1">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>BBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Shipping Order Identifier. Identifier</ccts:DictionaryEntryName>
              <ccts:Definition>Reference number to identify a Shipping Order or Forwarding Instruction.</ccts:Definition>
              <ccts:Cardinality>0..1</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTerm>Shipping Order Identifier</ccts:PropertyTerm>
              <ccts:RepresentationTerm>Identifier</ccts:RepresentationTerm>
              <ccts:DataType>Identifier. Type</ccts:DataType>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cbc:AdValoremIndicator" minOccurs="0" maxOccurs="1">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>BBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Ad Valorem_ Indicator. Indicator</ccts:DictionaryEntryName>
              <ccts:Definition>A term used in commerce in reference to certain duties, called ad valorem duties, which are levied on commodities at certain rates per centum on their value.</ccts:Definition>
              <ccts:Cardinality>0..1</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTermQualifier>Ad Valorem</ccts:PropertyTermQualifier>
              <ccts:PropertyTerm>Indicator</ccts:PropertyTerm>
              <ccts:RepresentationTerm>Indicator</ccts:RepresentationTerm>
              <ccts:DataType>Indicator. Type</ccts:DataType>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cbc:DeclaredCarriageValueAmount" minOccurs="0" maxOccurs="1">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>BBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Declared Carriage_ Value. Amount</ccts:DictionaryEntryName>
              <ccts:Definition>Value, declared by the shipper or his agent solely for the purpose of varying the carrier's level of liability from that provided in the contract of carriage, in case of loss or damage to goods or delayed delivery.</ccts:Definition>
              <ccts:Cardinality>0..1</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTermQualifier>Declared Carriage</ccts:PropertyTermQualifier>
              <ccts:PropertyTerm>Value</ccts:PropertyTerm>
              <ccts:RepresentationTerm>Amount</ccts:RepresentationTerm>
              <ccts:DataType>Amount. Type</ccts:DataType>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cbc:OtherInstruction" minOccurs="0" maxOccurs="unbounded">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>BBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Other_ Instruction. Text</ccts:DictionaryEntryName>
              <ccts:Definition>Contains other free-text based instructions related to the shipment to the forwarders or carriers. This should only be used where such information cannot be represented in other structured information entities within the document.</ccts:Definition>
              <ccts:Cardinality>0..n</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTermQualifier>Other</ccts:PropertyTermQualifier>
              <ccts:PropertyTerm>Instruction</ccts:PropertyTerm>
              <ccts:RepresentationTerm>Text</ccts:RepresentationTerm>
              <ccts:DataType>Text. Type</ccts:DataType>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cac:ConsignorParty" minOccurs="0" maxOccurs="1">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>ASBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Consignor_ Party. Party</ccts:DictionaryEntryName>
              <ccts:Definition>The party consigning goods as stipulated in the transport contract by the party ordering transport.</ccts:Definition>
              <ccts:Cardinality>0..1</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTermQualifier>Consignor</ccts:PropertyTermQualifier>
              <ccts:PropertyTerm>Party</ccts:PropertyTerm>
              <ccts:AssociatedObjectClass>Party</ccts:AssociatedObjectClass>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cac:CarrierParty" minOccurs="0" maxOccurs="1">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>ASBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Carrier_ Party. Party</ccts:DictionaryEntryName>
              <ccts:Definition>The party providing the transport of goods between named points.</ccts:Definition>
              <ccts:Cardinality>0..1</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTermQualifier>Carrier</ccts:PropertyTermQualifier>
              <ccts:PropertyTerm>Party</ccts:PropertyTerm>
              <ccts:AssociatedObjectClass>Party</ccts:AssociatedObjectClass>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cac:FreightForwarderParty" minOccurs="0" maxOccurs="1">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>ASBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Freight Forwarder_ Party. Party</ccts:DictionaryEntryName>
              <ccts:Definition>The party combining individual smaller consignments into a single larger shipment (so-called consolidated consignment ) that is sent to a counterpart who mirrors the consolidator's activity by dividing the consolidated consignment into its original components.</ccts:Definition>
              <ccts:Cardinality>0..1</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTermQualifier>Freight Forwarder</ccts:PropertyTermQualifier>
              <ccts:PropertyTerm>Party</ccts:PropertyTerm>
              <ccts:AssociatedObjectClass>Party</ccts:AssociatedObjectClass>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cac:Shipment" minOccurs="1" maxOccurs="1">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>ASBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Shipment</ccts:DictionaryEntryName>
              <ccts:Definition>A separately identifiable collection of goods items (available to be) transported from one consignor to one consignee via one or more modes of transport.</ccts:Definition>
              <ccts:Cardinality>1</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTerm>Shipment</ccts:PropertyTerm>
              <ccts:AssociatedObjectClass>Shipment</ccts:AssociatedObjectClass>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cac:DocumentReference" minOccurs="0" maxOccurs="unbounded">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>ASBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Document Reference</ccts:DictionaryEntryName>
              <ccts:Definition>An association to Document Reference.</ccts:Definition>
              <ccts:Cardinality>0..n</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTerm>Document Reference</ccts:PropertyTerm>
              <ccts:AssociatedObjectClass>Document Reference</ccts:AssociatedObjectClass>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cac:ExchangeRate" minOccurs="0" maxOccurs="unbounded">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>ASBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Exchange Rate</ccts:DictionaryEntryName>
              <ccts:Definition>Information that directly relates to the rate of exchange (conversion) between two currencies.</ccts:Definition>
              <ccts:Cardinality>0..n</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTerm>Exchange Rate</ccts:PropertyTerm>
              <ccts:AssociatedObjectClass>Exchange Rate</ccts:AssociatedObjectClass>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cac:DocumentDistribution" minOccurs="0" maxOccurs="unbounded">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>ASBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Document Distribution</ccts:DictionaryEntryName>
              <ccts:Definition>The distribution of the Waybill to interested parties.</ccts:Definition>
              <ccts:Cardinality>0..n</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTerm>Document Distribution</ccts:PropertyTerm>
              <ccts:AssociatedObjectClass>Document Distribution</ccts:AssociatedObjectClass>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
      <xsd:element ref="cac:Signature" minOccurs="0" maxOccurs="unbounded">
        <xsd:annotation>
          <xsd:documentation>
            <ccts:Component>
              <ccts:ComponentType>ASBIE</ccts:ComponentType>
              <ccts:DictionaryEntryName>Waybill. Signature</ccts:DictionaryEntryName>
              <ccts:Definition>An association to Signature.</ccts:Definition>
              <ccts:Cardinality>0..n</ccts:Cardinality>
              <ccts:ObjectClass>Waybill</ccts:ObjectClass>
              <ccts:PropertyTerm>Signature</ccts:PropertyTerm>
              <ccts:AssociatedObjectClass>Signature</ccts:AssociatedObjectClass>
            </ccts:Component>
          </xsd:documentation>
        </xsd:annotation>
      </xsd:element>
    </xsd:sequence>
  </xsd:complexType>
<!-- ===== Element Declarations ===== -->
<!-- ===== Type Definitions ===== -->
<!-- ===== Basic Business Information Entity Type Definitions ===== -->
</xsd:schema>
<!-- ===== Copyright Notice ===== -->
<!--
  OASIS takes no position regarding the validity or scope of any 
  intellectual property or other rights that might be claimed to pertain 
  to the implementation or use of the technology described in this 
  document or the extent to which any license under such rights 
  might or might not be available; neither does it represent that it has 
  made any effort to identify any such rights. Information on OASIS's 
  procedures with respect to rights in OASIS specifications can be 
  found at the OASIS website. Copies of claims of rights made 
  available for publication and any assurances of licenses to be made 
  available, or the result of an attempt made to obtain a general 
  license or permission for the use of such proprietary rights by 
  implementors or users of this specification, can be obtained from 
  the OASIS Executive Director.

  OASIS invites any interested party to bring to its attention any 
  copyrights, patents or patent applications, or other proprietary 
  rights which may cover technology that may be required to 
  implement this specification. Please address the information to the 
  OASIS Executive Director.
  
  Copyright (C) OASIS Open 2001-2006. All Rights Reserved.

  This document and translations of it may be copied and furnished to 
  others, and derivative works that comment on or otherwise explain 
  it or assist in its implementation may be prepared, copied, 
  published and distributed, in whole or in part, without restriction of 
  any kind, provided that the above copyright notice and this 
  paragraph are included on all such copies and derivative works. 
  However, this document itself may not be modified in any way, 
  such as by removing the copyright notice or references to OASIS, 
  except as needed for the purpose of developing OASIS 
  specifications, in which case the procedures for copyrights defined 
  in the OASIS Intellectual Property Rights document must be 
  followed, or as required to translate it into languages other than 
  English. 

  The limited permissions granted above are perpetual and will not be 
  revoked by OASIS or its successors or assigns. 

  This document and the information contained herein is provided on 
  an "AS IS" basis and OASIS DISCLAIMS ALL WARRANTIES, 
  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY 
  WARRANTY THAT THE USE OF THE INFORMATION HEREIN 
  WILL NOT INFRINGE ANY RIGHTS OR ANY IMPLIED 
  WARRANTIES OF MERCHANTABILITY OR FITNESS FOR A 
  PARTICULAR PURPOSE.
-->
