<?xml version="1.0" encoding="UTF-8"?>
<xs:schema attributeFormDefault="qualified"
           elementFormDefault="qualified"
           targetNamespace="http://withholding.minfin.fgov.be/"
           xmlns="http://withholding.minfin.fgov.be/"
           xmlns:rv="http://withholding.minfin.fgov.be/"
           xmlns:xs="http://www.w3.org/2001/XMLSchema">

    <xs:element name="withholdingTaxFile" type="WithholdingTaxFile">
        <xs:unique name="uniqueReferenceForInitialDeclarations">
            <xs:selector xpath="rv:initialDeclaration"/>
            <xs:field xpath="rv:declarationUniqueReference" />
        </xs:unique>
        <xs:unique name="uniqueReferenceForModificationDeclarations">
            <xs:selector xpath="rv:modificationsDeclaration"/>
            <xs:field xpath="rv:modifiedFileId"/>
            <xs:field xpath="rv:modifiedDeclarationReference"/>
        </xs:unique>
        <xs:unique name="uniqueReferenceForCancelDeclarations">
            <xs:selector xpath="rv:cancellationDeclaration"/>
            <xs:field xpath="rv:cancelledFileId"/>
            <xs:field xpath="rv:cancelledDeclarationReference"/>
        </xs:unique>
    </xs:element>

    <xs:simpleType name="DeclarationReference">
        <xs:restriction base="xs:positiveInteger">
            <xs:maxExclusive value="100000"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:complexType name="WithholdingTaxFile">
        <xs:sequence>
            <xs:element type="TaxPayer" name="taxPayer" minOccurs="1" maxOccurs="1"/>
            <xs:element type="Contact" name="declarantContact" minOccurs="0"/>

            <xs:choice minOccurs="1" maxOccurs="1">
                <xs:element type="InitialDeclarationContent" name="initialDeclaration" maxOccurs="5000"/>
                <xs:element type="ModificationsContent" name="modificationsDeclaration" maxOccurs="5000"/>
                <xs:element type="CancelledDeclarationContent" name="cancellationDeclaration" maxOccurs="5000"/>
            </xs:choice>
        </xs:sequence>
    </xs:complexType>
    <xs:complexType name="CommonDeclarationContent">
        <xs:sequence>
            <xs:element type="DeclarationType" name="declarationType" minOccurs="1"/>
            <xs:element type="Income" name="income" minOccurs="1" maxOccurs="5000"/>
            <xs:element type="EurocentAmount" name="totalTaxAmountDue" minOccurs="1"/>
            <xs:element type="xs:date" name="attributionDate" minOccurs="1"/>
            <xs:element type="xs:date" name="genAssembDate" minOccurs="0"/>
            <xs:element type="xs:positiveInteger" name="stocksType" minOccurs="0"/>
            <xs:element type="EurocentAmountStrictlyPositive" name="totalStocksAmount" minOccurs="0"/>
            <xs:element type="xs:date" name="closureDateAccountingYear" minOccurs="0"/>
            <xs:element type="Language" name="preferredLanguage" minOccurs="0"/>
        </xs:sequence>
    </xs:complexType>
    <xs:complexType name="InitialDeclarationContent">
        <xs:complexContent>
            <xs:extension base="CommonDeclarationContent">
                <xs:sequence>
                    <xs:element type="DeclarationReference" name="declarationUniqueReference"/>
                </xs:sequence>
            </xs:extension>
        </xs:complexContent>
    </xs:complexType>
    <xs:complexType name="ModificationsContent">
        <xs:complexContent>
            <xs:extension base="CommonDeclarationContent">
                <xs:sequence>
                    <xs:element type="ReasonModification" name="reasonModification"/>
                    <xs:element type="xs:positiveInteger" name="modifiedFileId"/>
                    <xs:element type="DeclarationReference" name="modifiedDeclarationReference"/>
                </xs:sequence>
            </xs:extension>
        </xs:complexContent>
    </xs:complexType>
    <xs:simpleType name="PositiveFloat">
        <xs:restriction base="xs:float">
            <xs:minInclusive value="0.0"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="EurocentAmount">
        <xs:restriction base="xs:nonNegativeInteger">
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="EurocentAmountStrictlyPositive">
        <xs:restriction base="xs:positiveInteger">
        </xs:restriction>
    </xs:simpleType>
    <xs:complexType name="CancelledDeclarationContent">
        <xs:sequence>
            <xs:element type="ReasonCancel" name="reasonCancel"/>
            <xs:element type="xs:positiveInteger" name="cancelledFileId" />
            <xs:element type="DeclarationReference" name="cancelledDeclarationReference"/>
        </xs:sequence>
    </xs:complexType>
    <xs:simpleType name="DeclarationType">
        <xs:restriction base="xs:string">
            <xs:enumeration value="273"/>
            <xs:enumeration value="273A_Div"/>
            <xs:enumeration value="273A_Part"/>
            <xs:enumeration value="273S"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="ReasonModification">
        <xs:restriction base="xs:string">
            <xs:enumeration value="M1_WRONG_AMOUNT"/>
            <xs:enumeration value="M2_WRONG_BENEFICIARY"/>
            <xs:enumeration value="M3_WRONG_CODE"/>
            <xs:enumeration value="M4_WRONG_GENASSEMB_DATE"/>
            <xs:enumeration value="M5_WRONG_TAXRATE"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="ReasonCancel">
        <xs:restriction base="xs:string">
            <xs:enumeration value="C1_DOUBLE_DECL"/>
            <xs:enumeration value="C2_NO_DECL"/>
            <xs:enumeration value="C3_WRONG_AMOUNT"/>
            <xs:enumeration value="C4_WRONG_ATTR_DATE"/>
            <xs:enumeration value="C5_WRONG_BENEFICIARY"/>
            <xs:enumeration value="C6_WRONG_CODE"/>
            <xs:enumeration value="C7_WRONG_GENASSEMB_DATE"/>
            <xs:enumeration value="C8_WRONG_TAXPAYER"/>
            <xs:enumeration value="C9_WRONG_TAX_RATE"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:complexType name="TaxPayer">
        <xs:choice minOccurs="1" maxOccurs="1">
            <xs:element type="CitizenIdentification" name="belgianCitizen" minOccurs="1"/>
            <xs:element type="CompanyIdentification" name="belgianCompany" minOccurs="1"/>
        </xs:choice>
    </xs:complexType>
    <xs:complexType name="Contact">
        <xs:sequence>
            <xs:element type="xs:string"  name="name" minOccurs="0"/>
            <xs:element type="xs:string" name="givenName" minOccurs="0"/>
            <xs:element type="xs:string" name="phone" minOccurs="0"/>
            <xs:element type="xs:string" name="mail" minOccurs="0"/>
        </xs:sequence>
    </xs:complexType>
    <xs:complexType name="Income">
        <xs:sequence>
            <xs:element type="Integer3Digits" name="incomeCode" minOccurs="0"/>
            <xs:element type="Integer3Digits" name="situationCode" minOccurs="0"/>
            <xs:element type="xs:string" name="couponNumber" minOccurs="0"/>
            <xs:element type="xs:positiveInteger" name="numberOfStocks" minOccurs="0"/>
            <xs:element type="BooleanType" name="wtDebtor" minOccurs="0"/>
            <xs:element name="debtorPart" minOccurs="0">
                <xs:simpleType>
                    <xs:restriction base="xs:float">
                        <xs:minExclusive value="0"/>
                        <xs:maxInclusive value="100"/>
                        <xs:pattern value="100.0|[0-9]{1,2}.[0-9]{1,4}|[0-9]{1,2}"/>
                    </xs:restriction>
                </xs:simpleType>
            </xs:element>
            <xs:element type="EurocentAmount" name="grossAmount" minOccurs="0"/>
            <xs:element type="EurocentAmount" name="deductableCosts" minOccurs="0"/>
            <xs:element type="EurocentAmount" name="defTaxReserve" minOccurs="0"/>
            <xs:element type="EurocentAmount" name="reservePartners" minOccurs="0"/>
            <xs:element type="EurocentAmount" name="reserveRedCap" minOccurs="0"/>
            <xs:element type="EurocentAmount" name="taxableAmount" minOccurs="1"/>
            <xs:element name="rate" minOccurs="1" nillable="true">
                <xs:simpleType>
                    <xs:restriction base="xs:float">
                        <xs:pattern value="[0-9]{1,2}.[0-9]{1,4}|[0-9]{1,2}"/>
                        <xs:minInclusive value="0"/>
                        <xs:maxInclusive value="99.9999"/>
                    </xs:restriction>
                </xs:simpleType>
            </xs:element>
            <xs:element name="clarificationRate" minOccurs="0">
                <xs:simpleType>
                    <xs:restriction base="xs:string">
                        <xs:maxLength value="500"/>
                    </xs:restriction>
                </xs:simpleType>
            </xs:element>
            <xs:element type="EurocentAmount" name="taxAmount" minOccurs="1"/>
            <xs:element type="TaxReduction" name="taxReduction" minOccurs="0" maxOccurs="5000"/>
            <xs:element type="Beneficiary" name="beneficiary" minOccurs="0" maxOccurs="5000"/>
            <xs:element type="EurocentAmount" name="finalTaxAmount" minOccurs="1"/>
        </xs:sequence>
    </xs:complexType>
    <xs:simpleType name="BooleanType">
        <xs:restriction base="xs:boolean">
        </xs:restriction>
    </xs:simpleType>
    <xs:complexType name="TaxReduction">
        <xs:sequence>
            <xs:element type="EurocentAmountStrictlyPositive" name="taxableAmountBeforeReduction" minOccurs="1"/>
            <xs:element type="PositiveFloat" name="conventionRate" minOccurs="0"/>
            <xs:element type="xs:positiveInteger" name="numberOfStocks" minOccurs="0"/>
            <xs:element name="countryCode" minOccurs="0">
                <xs:simpleType>
                    <xs:restriction base="xs:string">
                        <xs:pattern value="[A-Z]{2}"/>
                    </xs:restriction>
                </xs:simpleType>
            </xs:element>
            <xs:element type="EurocentAmount" name="reductionAmount" minOccurs="1"/>
        </xs:sequence>
    </xs:complexType>
    <xs:complexType name="Beneficiary">
        <xs:sequence>
            <xs:element name="identification" minOccurs="1">
                <xs:complexType>
                    <xs:choice>
                        <xs:element name="belgianCitizen" type="CitizenIdentification"/>
                        <xs:element name="belgianCompany" type="CompanyIdentification"/>
                        <xs:element name="foreignPerson" type="ForeignPersonIdentification"/>
                    </xs:choice>
                </xs:complexType>
            </xs:element>
            <xs:element type="PositiveFloat" name="numberOfStocks" minOccurs="0"/>
            <xs:element type="EurocentAmount" name="taxableAmount" minOccurs="0"/>
            <xs:element type="EurocentAmount" name="taxAmount" minOccurs="0"/>
            <xs:element type="EurocentAmount" name="reductionAmount" minOccurs="0"/>
            <xs:choice minOccurs="0" maxOccurs="1">
                <xs:element type="EurocentAmount" name="actualCost"/>
                <xs:element type="EurocentAmount" name="fixedCost"/>
            </xs:choice>
            <xs:element name="fixedCostRate" minOccurs="0">
                <xs:simpleType>
                    <xs:restriction base="xs:float">
                        <xs:pattern value="[0-9]{1,2}.[0-9]{1,4}|[0-9]{1,2}"/>
                        <xs:minInclusive value="0"/>
                        <xs:maxInclusive value="99.9999"/>
                    </xs:restriction>
                </xs:simpleType>
            </xs:element>
            <xs:element type="EurocentAmount" name="amountPayed" minOccurs="0"/>
        </xs:sequence>
    </xs:complexType>
    <xs:complexType name="CitizenIdentification">
        <xs:attribute name="nationalNumber" use="required">
            <xs:simpleType>
                <xs:restriction base="xs:string">
                    <xs:pattern value="[0-9]{11}"/>
                </xs:restriction>
            </xs:simpleType>
        </xs:attribute>
    </xs:complexType>
    <xs:complexType name="CompanyIdentification">
        <xs:attribute name="companyNumber" use="required">
            <xs:simpleType>
                <xs:restriction base="xs:string">
                    <xs:pattern value="([A-Z]{2})?[0-9]{10}"/>
                </xs:restriction>
            </xs:simpleType>
        </xs:attribute>
    </xs:complexType>
    <xs:complexType name="ForeignPersonIdentification">
        <xs:sequence>
            <xs:element type="Nature" name="nature" minOccurs="0"/>
            <xs:element type="xs:string" name="foreignIdentification" minOccurs="0"/>
            <xs:element type="xs:string" name="name" minOccurs="1"/>
            <xs:element type="xs:string" name="givenName" minOccurs="0"/>
            <xs:element type="xs:date" name="birthdate" minOccurs="0"/>
            <xs:element type="xs:string" name="countryCode" minOccurs="0"/>
            <xs:element type="xs:string" name="province" minOccurs="0"/>
            <xs:element type="xs:string" name="street" minOccurs="0"/>
            <xs:element type="xs:string" name="number" minOccurs="0"/>
            <xs:element type="xs:string" name="boxNumber" minOccurs="0"/>
            <xs:element type="xs:string" name="postalCode" minOccurs="0"/>
            <xs:element type="xs:string" name="city" minOccurs="0"/>
        </xs:sequence>
    </xs:complexType>

    <xs:simpleType name="Nature">
        <xs:restriction base="xs:string">
            <xs:enumeration value="Citizen"/>
            <xs:enumeration value="Company"/>
        </xs:restriction>
    </xs:simpleType>

    <xs:simpleType name="Language">
        <xs:restriction base="xs:string">
            <xs:enumeration value="nl"/>
            <xs:enumeration value="fr"/>
            <xs:enumeration value="de"/>
        </xs:restriction>
    </xs:simpleType>

    <xs:simpleType name="Integer3Digits">
        <xs:restriction base="xs:nonNegativeInteger">
            <xs:minInclusive value="0"/>
            <xs:maxInclusive value="999"/>
        </xs:restriction>
    </xs:simpleType>
</xs:schema>