<?xml version="1.0" encoding="UTF-8"?>
<!--
	Validate UBL Invoice and UBL Credit Note(XML file) for compliance with the  national rules RO_CIUS
	Schematron version 1.0.8 - Last update: 2022-10-18:
   	- modify Syntax of Specification identifier element (BT-24)(RO-MAJOR-MINOR-PATCH-VERSION value = 1.0.1);
   	- modify allowed maximum number of characters for BT-1, BT-12, BT-13, BT-14, BT-15, BT-16, BT-17, BT-18, BT-25 and BT-122(200)
   	- replace special and romanian characters in error messages; 
   	- correction error messages for BR-RO-100, BR-RO-160, BR-RO-200; 
   	- apply BR-R0-100 to BT-52(id=BR-RO-101) and BR-RO-110 to BT-54(id=BR-RO-111); 
   	- eliminate rules BR-RO-L030 and BR-RO-A999
	RO_CIUS version 1.0.1 - Last update: 2022-10-18 
-->
<schema xmlns="http://purl.oclc.org/dsdl/schematron"
	xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
	xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
	queryBinding="xslt2"
	defaultPhase="roefactura-model">
	<title>Schematron Version 1.0.8 - CIUS-RO version 1.0.1 compatible - UBL - Invoice</title>
	<ns prefix="ext" uri="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" />
	<ns prefix="cbc" uri="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" />
	<ns prefix="cac" uri="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" />
	<ns prefix="qdt" uri="urn:oasis:names:specification:ubl:schema:xsd:QualifiedDataTypes-2" />
	<ns prefix="udt" uri="urn:oasis:names:specification:ubl:schema:xsd:UnqualifiedDataTypes-2" />
	<ns prefix="cn" uri="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2" />
	<ns prefix="ubl" uri="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" />
	<ns prefix="xs"  uri="http://www.w3.org/2001/XMLSchema" />
	
	<phase id="roefactura-model">
		<active pattern="ubl-pattern" />
	</phase>
	<!-- Validate UBL Invoice and UBL Credit Notes according to the  national rules RO_CIUS -->
	<pattern id="ubl-pattern">
<!-- Declaring global variables (in XSLT speak) -->
	<!-- Syntax of Specification identifier element (BT-24) according to the RO_CIUS -->
	<let name="RO-MAJOR-MINOR-PATCH-VERSION" value="'1.0.1'"/> 
	<let name="RO-CIUS-ID" value="concat('urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:', $RO-MAJOR-MINOR-PATCH-VERSION)"/>
	<!-- An email address should contain exactly one @ character, which should not be flanked by a space, a period, but at least two characters on either side. A period should not be at the beginning or at the end -->
	<let name="RO-EMAIL-REGEX"  value="'^[0-9a-zA-Z]([0-9a-zA-Z\.]*)[^\.\s@]@[^\.\s@]([0-9a-zA-Z\.]*)[0-9a-zA-Z]$'" />
	<!-- A telephone number should contain at least three digits. -->
	<let name="RO-TELEPHONE-REGEX"  value="'.*([0-9].*){3,}.*'" />
	<!-- ISO 3166-2:RO and SECTOR Codelists (applicable for countryCode = "RO") -->
	<let name="ISO-3166-RO-CODES" value="('RO-AB','RO-AG','RO-AR','RO-B','RO-BC','RO-BH','RO-BN','RO-BR','RO-BT','RO-BV','RO-BZ','RO-CJ','RO-CL','RO-CS','RO-CT', 'RO-CV', 'RO-DB', 'RO-DJ', 'RO-GJ', 'RO-GL', 'RO-GR', 'RO-HD', 'RO-HR' , 'RO-IF', 'RO-IL', 'RO-IS', 'RO-MH', 'RO-MM', 'RO-MS', 'RO-NT', 'RO-OT', 'RO-PH', 'RO-SB', 'RO-SJ', 'RO-SM', 'RO-SV', 'RO-TL', 'RO-TM', 'RO-TR', 'RO-VL', 'RO-VN', 'RO-VS')"/>
	<let name="SECTOR-RO-CODES" value="('SECTOR1', 'SECTOR2', 'SECTOR3', 'SECTOR4', 'SECTOR5', 'SECTOR6')"/>
	<!-- invoice type code constrains(BT-3) -->
	<rule flag="fatal" context="cbc:InvoiceTypeCode | cbc:CreditNoteTypeCode">
		<assert test="(self::cbc:InvoiceTypeCode and ((not(contains(normalize-space(.), ' ')) and contains(' 380 384 389 751 ', concat(' ', normalize-space(.), ' '))))) or (self::cbc:CreditNoteTypeCode and ((not(contains(normalize-space(.), ' ')) and contains(' 381 ', concat(' ', normalize-space(.), ' ')))))" 
			flag="fatal"
			id="BR-RO-020"  
			>[BR-RO-020]-Codul tipului facturii (BT-3) trebuie sa fie unul dintre urmatoarele coduri din lista de coduri UNTDID 1001: 380 (Factura), 389 (Autofactura), 384 (Factura corectata), 381 (Nota de creditare), 751 (Factura — informatii în scopuri contabile).
			#The invoice type code (BT-3) must be one of the following codes in the UNTDID 1001 code list: 380 (Invoice), 389 (Self-invoice), 384 (Corrected invoice), 381 (Credit note), 751 (Invoice - information for accounting purposes).</assert>
	</rule>
	<!-- specification identifier(BT-24) constrains -->
	<rule context="/ubl:Invoice | /cn:CreditNote">
			<assert test="cbc:CustomizationID = $RO-CIUS-ID" 
				flag="fatal"
				id="BR-RO-001"
				>[BR-RO-001]-Identificatorul specificatie (BT-24) trebuie sa corespunda sintactic cu valoarea precizata in Specificatii tehnice și de utilizare a elementelor de baza ale facturii electronice - RO_CIUS - și a regulilor operationale specifice aplicabile la nivel national.
							#The specification identifier (BT-24) must syntactically correspond to the value specified in the Technical and Usage Specifications of the basic elements of the electronic invoice - RO_CIUS - and the specific operational rules applicable at national level(<value-of select="$RO-CIUS-ID"/>).</assert>		
	<!-- occurrences constrains -->
			<assert test="count(cbc:Note) &lt;= 20"
				flag="fatal"
				id="BR-RO-A020" 
				>[BR-RO-A020]-O factura trebuie sa contina maximum 20 de aparitii ale grupului Comentariu in factura (BG-1).
							#The allowed maximum number of occurences of Invoice note (BG-1) is 20.</assert>					
	<!-- string-length constrains -->
			<assert test="string-length(normalize-space(cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:PostalZone)) &lt;=20"
				flag="fatal" 
				id="BR-RO-L0201" 
				>[BR-RO-L020]-Numarul maxim permis de caractere pentru Codul postal al Vanzatorului (BT-38) este 20.
							#The allowed maximum number of characters for the Seller post code (BT-38) is 20.</assert>
			<assert test="string-length(normalize-space(cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cbc:PostalZone)) &lt;=20"
				flag="fatal" 
				id="BR-RO-L0202" 
				>[BR-RO-L020]-Numarul maxim permis de caractere pentru Codul postal al Cumparatorului (BT-53) este 20.
							#The allowed maximum number of characters for the Buyer post code (BT-53) is 20.</assert>
			<assert test="string-length(normalize-space(cac:TaxRepresentativeParty/cac:PostalAddress/cbc:PostalZone)) &lt;= 20"
				flag="fatal" 
				id="BR-RO-L0203" 
				>[BR-RO-L020]-Numarul maxim permis de caractere pentru Codul postal al reprezentantului fiscal (BT-67) este 20.
							#The allowed maximum number of characters for the Tax representative post code (BT-67) is 20.</assert>
			<assert test="string-length(normalize-space(cac:Delivery/cac:DeliveryLocation/cac:Address/cbc:PostalZone)) &lt;= 20"
				flag="fatal" 
				id="BR-RO-L0204" 
				>[BR-RO-L020]-Numarul maxim permis de caractere pentru Codul postal de livrare (BT-78) este 20.
							#The allowed maximum number of characters for the Deliver to post code (BT-78) is 20.</assert>
		
			<assert test="string-length(normalize-space(cbc:ID)) &lt;= 200"
				flag="fatal" 
				id="BR-RO-L155" 
				>[BR-RO-L200]-Numarul maxim permis de caractere pentru Numarul facturii (BT-1) este 200.
							#The allowed maximum number of characters for the Invoice number (BT-1) is 200.</assert>
		
			<assert test="string-length(normalize-space(cac:ContractDocumentReference/cbc:ID)) &lt;= 200"
				flag="fatal" 
				id="BR-RO-L0302" 
				>[BR-RO-L200]-Numarul maxim permis de caractere pentru Referinta contractului (BT-12) este 200.
							#The allowed maximum number of characters for the Contract reference(BT-12) is 200.</assert>
			<assert test="string-length(normalize-space(cac:OrderReference/cbc:ID)) &lt;= 200"
				flag="fatal" 
				id="BR-RO-L0303" 
				>[BR-RO-L200]-Numarul maxim permis de caractere pentru Referinta comenzii (BT-13) este 200.
							#The allowed maximum number of characters for the Purchase order reference(BT-13) is 200.</assert>
			<assert test="string-length(normalize-space(cac:OrderReference/cbc:SalesOrderID)) &lt;= 200"
				flag="fatal" 
				id="BR-RO-L0304" 
				>[BR-RO-L200]-Numarul maxim permis de caractere pentru Referinta dispozitiei de vanzare (BT-14) este 200.
							#The allowed maximum number of characters for the Sales order reference (BT-14) is 200.</assert>
			<assert test="string-length(normalize-space(cac:ReceiptDocumentReference/cbc:ID)) &lt;= 200"
				flag="fatal" 
				id="BR-RO-L0305" 
				>[BR-RO-L200]-Numarul maxim permis de caractere pentru Referinta avizului de receptie (BT-15) este 200.
							#The allowed maximum number of characters for the Receiving advice reference (BT-15) is 200.</assert>
			<assert test="string-length(normalize-space(cac:DespatchDocumentReference/cbc:ID)) &lt;= 200"
				flag="fatal" 
				id="BR-RO-L0306" 
				>[BR-RO-L200]-Numarul maxim permis de caractere pentru Referinta avizului de expeditie (BT-16) este 200.
							#The allowed maximum number of characters for the Despatch advice reference (BT-16) is 200.</assert>
			<assert test="string-length(normalize-space(cac:OriginatorDocumentReference/cbc:ID)) &lt;= 200"
				flag="fatal" 
				id="BR-RO-L0307" 
				>[BR-RO-L200]-Numarul maxim permis de caractere pentru Referinta cererii de oferta sau a lotului (BT-17) este 200.
							#The allowed maximum number of characters for the Tender or lot reference (BT-17) is 200.</assert>
			<assert test="string-length(normalize-space(cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:CityName)) &lt;= 50"
				flag="fatal" 
				id="BR-RO-L0501" 
				>[BR-RO-L050]-Numarul maxim permis de caractere pentru Localitatea Vanzatorului (BT-37) este 50.
							#The allowed maximum number of characters for the Seller city (BT-37) is 50.</assert>
			<assert test="string-length(normalize-space(cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cbc:CityName)) &lt;= 50"
				flag="fatal" 
				id="BR-RO-L0502" 
				>[BR-RO-L050]-Numarul maxim permis de caractere pentru Localitatea Cumparatorului (BT-52) este 50.
							#The allowed maximum number of characters for the Buyer city (BT-52) is 50.</assert>
			<assert test="string-length(normalize-space(cac:TaxRepresentativeParty/cac:PostalAddress/cbc:CityName)) &lt;= 50"
				flag="fatal" 
				id="BR-RO-L0503" 
				>[BR-RO-L050]-Numarul maxim permis de caractere pentru Localitatea reprezentantului fiscal (BT-66) este 50.
							#The allowed maximum number of characters for the Tax representative city (BT-66) is 50.</assert>
			<assert test="string-length(normalize-space(cac:Delivery/cac:DeliveryLocation/cac:Address/cbc:CityName)) &lt;= 50"
				flag="fatal" 
				id="BR-RO-L0504" 
				>[BR-RO-L050]-Numarul maxim permis de caractere pentru Localitatea de livrare (BT-77) este 50.
							#The allowed maximum number of characters for the Deliver to city (BT-77) is 50.</assert>	
			<assert test="string-length(normalize-space(cbc:AccountingCost)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1001" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Referinta contabila a Cumparatorului (BT-19) este 100.
							#The allowed maximum number of characters for the Buyer accounting reference (BT-19) is 100.</assert>
			<assert test="string-length(normalize-space(cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:AdditionalStreetName)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1002" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Adresa Vanzatorului - Linia 2 (BT-36) este 100.
							#The allowed maximum number of characters for the Seller address line 2 (BT-36) is 100.</assert>
			<assert test="string-length(normalize-space(cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cac:AddressLine/cbc:Line)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1003" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Adresa Vanzatorului - Linia 3 (BT-162) este 100.
							#The allowed maximum number of characters for the Seller address line 3 (BT-162) is 100.</assert>
			<assert test="string-length(normalize-space(cac:AccountingSupplierParty/cac:Party/cac:Contact/cbc:Name)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1004" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Punctul de contact al Vanzatorului (BT-41) este 100.
							#The allowed maximum number of characters for the Seller contact point (BT-41) is 100.</assert>
			<assert test="string-length(normalize-space(cac:AccountingSupplierParty/cac:Party/cac:Contact/cbc:Telephone)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1005" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Numarul de telefon al contactului Vanzatorului (BT-42) este 100.
							#The allowed maximum number of characters for the Seller contact telephone number (BT-42) is 100.</assert>
			<assert test="string-length(normalize-space(cac:AccountingSupplierParty/cac:Party/cac:Contact/cbc:ElectronicMail)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1006" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Adresa de email a contactului Vanzatorului (BT-43) este 100.
							#The allowed maximum number of characters for the Seller contact email address (BT-43) is 100.</assert>
			<assert test="string-length(normalize-space(cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cbc:AdditionalStreetName)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1007" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Adresa Cumparatorului - Linia 2 (BT-51) este 100.
							#The allowed maximum number of characters for the Buyer address line 2 (BT-51) is 100.</assert>
			<assert test="string-length(normalize-space(cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cac:AddressLine/cbc:Line)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1008" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Adresa Cumparatorului - Linia 3 (BT-163) este 100.
							#The allowed maximum number of characters for the Buyer address line 3 (BT-163) is 100.</assert>
			<assert test="string-length(normalize-space(cac:AccountingCustomerParty/cac:Party/cac:Contact/cbc:Name)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1009" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Punctul de contact al Cumparatorului (BT-56) este 100.
							#The allowed maximum number of characters for the Buyer contact point (BT-56) is 100.</assert>
			<assert test="string-length(normalize-space(cac:AccountingCustomerParty/cac:Party/cac:Contact/cbc:Telephone)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1010" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Numarul de telefon al contactului Cumparatorului (BT-57) este 100.
							#The allowed maximum number of characters for the Buyer contact telephone number (BT-57) is 100.</assert>
			<assert test="string-length(normalize-space(cac:AccountingCustomerParty/cac:Party/cac:Contact/cbc:ElectronicMail)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1011" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Adresa de email a contactului Cumparatorului (BT-58) este 100.
							#The allowed maximum number of characters for the Buyer contact email address (BT-58) is 100.</assert>
			<assert test="string-length(normalize-space(cac:TaxRepresentativeParty/cac:PostalAddress/cbc:AdditionalStreetName)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1012" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Adresa reprezentantului fiscal - Linia 2 (BT-65) este 100.
							#The allowed maximum number of characters for the Tax representative address line 2 (BT-65) is 100.</assert>
			<assert test="string-length(normalize-space(cac:TaxRepresentativeParty/cac:PostalAddress/cac:AddressLine/cbc:Line)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1013" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Adresa reprezentantului fiscal - Linia 3 (BT-164) este 100.
							#The allowed maximum number of characters for the Tax representative address line 3 (BT-164) is 100.</assert>
			<assert test="string-length(normalize-space(cac:Delivery/cac:DeliveryLocation/cac:Address/cbc:AdditionalStreetName)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1014" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Adresa de livrare - Linia 2 (BT-76) este 100.
							#The allowed maximum number of characters for the Deliver to address line 2 (BT-76) is 100.</assert>
			<assert test="string-length(normalize-space(cac:Delivery/cac:DeliveryLocation/cac:Address/cac:AddressLine/cbc:Line)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1015" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Adresa de livrare - Linia 3 (BT-165) este 100.
							#The allowed maximum number of characters for the Deliver to address line 3 (BT-165) is 100.</assert>
				
			<assert test="string-length(normalize-space(cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:TaxExemptionReason)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1019" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Motivul scutirii de TVA (BT-120) este 100.
							#The allowed maximum number of characters for the VAT exemption reason text (BT-120) is 100.</assert>		
			<assert test="string-length(normalize-space(cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:StreetName)) &lt;= 150"
				flag="fatal" 
				id="BR-RO-L151" 
				>[BR-RO-L150]-Numarul maxim permis de caractere pentru Adresa Vanzatorului - Linia 1 (BT-35) este 150.
							#The allowed maximum number of characters for the Seller address line 1 (BT-35) is 150.</assert>
			<assert test="string-length(normalize-space(cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cbc:StreetName)) &lt;= 150"
				flag="fatal" 
				id="BR-RO-L152" 
				>[BR-RO-L150]-Numarul maxim permis de caractere pentru Adresa Cumparatorului - Linia 1 (BT-50) este 150.
							#The allowed maximum number of characters for the Buyer address line 1 (BT-50) is 150.</assert>
			<assert test="string-length(normalize-space(cac:TaxRepresentativeParty/cac:PostalAddress/cbc:StreetName)) &lt;= 150"
				flag="fatal" 
				id="BR-RO-L153" 
				>[BR-RO-L150]-Numarul maxim permis de caractere pentru Adresa reprezentantului fiscal - Linia 1 (BT-64) este 150.
							#The allowed maximum number of characters for the Tax representative address line 1 (BT-64) is 150.</assert>
			<assert test="string-length(normalize-space(cac:Delivery/cac:DeliveryLocation/cac:Address/cbc:StreetName)) &lt;= 150"
				flag="fatal" 
				id="BR-RO-L154" 
				>[BR-RO-L150]-Numarul maxim permis de caractere pentru Adresa de livrare - Linia(BT-75) 1 este 150.
							#The allowed maximum number of characters for the Deliver to address line 1(BT-75) is 150.</assert>
			<assert test="string-length(normalize-space(cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName)) &lt;= 200"
				flag="fatal" 
				id="BR-RO-L201" 
				>[BR-RO-L200]-Numarul maxim permis de caractere pentru Numele Vanzatorului (BT-27) este 200.
							#The allowed maximum number of characters for the Seller name (BT-27) is 200.</assert>
			<assert test="string-length(normalize-space(cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name)) &lt;= 200"
				flag="fatal" 
				id="BR-RO-L202" 
				>[BR-RO-L200]-Numarul maxim permis de caractere pentru Denumirea comerciala a Vanzatorului (BT-28), este 200.
							#The allowed maximum number of characters for the Seller trading name (BT-28) is 200.</assert>
			<assert test="string-length(normalize-space(cac:AccountingCustomerParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName)) &lt;= 200"
				flag="fatal" 
				id="BR-RO-L203" 
				>[BR-RO-L200]-Numarul maxim permis de caractere pentru Numele Cumparatorului (BT-44), este 200.
							#The allowed maximum number of characters for the Buyer name (BT-44) is 200.</assert>
			<assert test="string-length(normalize-space(cac:AccountingCustomerParty/cac:Party/cac:PartyName/cbc:Name)) &lt;= 200"
				flag="fatal" 
				id="BR-RO-L204" 
				>[BR-RO-L200]-Numarul maxim permis de caractere pentru Denumirea comerciala a Cumparatorului (BT-45), este 200.
							#The allowed maximum number of characters for the Buyer trading name (BT-45) is 200.</assert>
			<assert test="string-length(normalize-space(cac:PayeeParty/cac:PartyName/cbc:Name)) &lt;= 200"
				flag="fatal" 
				id="BR-RO-L205" 
				>[BR-RO-L200]-Numarul maxim permis de caractere pentru Numele Beneficiarului  (BT-59), este 200.
							#The allowed maximum number of characters for the Payee name (BT-59) is 200.</assert>
			<assert test="string-length(normalize-space(cac:TaxRepresentativeParty/cac:PartyName/cbc:Name)) &lt;= 200"
				flag="fatal" 
				id="BR-RO-L206" 
				>[BR-RO-L200]-Numarul maxim permis de caractere pentru Numele reprezentantului fiscal al Vanzatorului (BT-62), este 200.
				#The allowed maximum number of characters for the Seller tax representative name (BT-62) is 200.</assert>
			<assert test="string-length(normalize-space(cac:Delivery/cac:DeliveryParty/cac:PartyName/cbc:Name)) &lt;= 200"
				flag="fatal" 
				id="BR-RO-L207" 
				>[BR-RO-L200]-Numarul maxim permis de caractere pentru Numele partii catre care se face livrarea  (BT-70), este 200.
							#The allowed maximum number of characters for the Deliver to party name (BT-70) is 200.</assert>		
			<assert test="string-length(normalize-space(cac:PaymentTerms/cbc:Note)) &lt;= 300"
				flag="fatal" 
				id="BR-RO-L301" 
				>[BR-RO-L300]-Numarul maxim permis de caractere pentru Termeni de plata  (BT-20) este 300.
							#The allowed maximum number of characters for the Payment terms (BT-20) is 300.</assert>
			<assert test="string-length(normalize-space(cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:CompanyLegalForm)) &lt;= 1000"
				flag="fatal" 
				id="BR-RO-L1000" 
				>[BR-RO-L1000]-Numarul maxim permis de caractere pentru Informatii juridice suplimentare despre Vanzator (BT-33)) este 1000.
							#The allowed maximum number of characters for the Seller additional legal (BT-33) is 1000.</assert>					
	<!--  business constrains  -->
			<assert test="matches(normalize-space(cbc:ID), '([0-9])')"
				flag="fatal"
				id="BR-RO-010"
				>[BR-RO-010]-Numarul facturii (BT-1) trebuie sa includa cel putin un caracter numeric (0—9).		
							#Invoice number (BT-1) must include at least one numeric character (0-9).</assert>		
			<assert test="(normalize-space(cbc:TaxCurrencyCode) = 'RON' and normalize-space(cbc:DocumentCurrencyCode) != 'RON') or (normalize-space(cbc:TaxCurrencyCode) = 'RON' and normalize-space(cbc:DocumentCurrencyCode) = 'RON')  or (normalize-space(cbc:TaxCurrencyCode) != 'RON' and normalize-space(cbc:DocumentCurrencyCode) = 'RON') or (not(exists (cbc:TaxCurrencyCode)) and normalize-space(cbc:DocumentCurrencyCode) = 'RON')"
				flag="fatal"
				id="BR-RO-030"
				>[BR-RO-030]-Daca Codul monedei facturii (BT-5) este altul decat RON, atunci Codul monedei de contabilizare a TVA (BT-6) trebuie sa fie RON.
							#If the Invoice currency code (BT-5) is other than RON, then the VAT accounting currency code(BT-6) must be RON.</assert>		
			<assert test="not((cac:AllowanceCharge/cac:TaxCategory/cbc:ID[ancestor::cac:AllowanceCharge/cbc:ChargeIndicator = 'false' and
				following-sibling::cac:TaxScheme/cbc:ID = 'VAT'] = ('S', 'Z', 'E', 'AE', 'K', 'G', 'L', 'M')) or
				(cac:AllowanceCharge/cac:TaxCategory/cbc:ID[ancestor::cac:AllowanceCharge/cbc:ChargeIndicator = 'true'] = ('S', 'Z', 'E', 'AE', 'K', 'G', 'L', 'M')) or
				(cac:InvoiceLine/cac:Item/cac:ClassifiedTaxCategory/cbc:ID = ('S', 'Z', 'E', 'AE', 'K', 'G', 'L', 'M'))) or
				(cac:TaxRepresentativeParty/cac:PartyTaxScheme/cbc:CompanyID, cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID[boolean(normalize-space(.))])"
				flag="fatal"
				id="BR-RO-065"
				>[BR-RO-065]-Identificatorul de înregistrare fiscala a Vanzatorului (BT-32) si/sau Identificatorul de TVA al Vanzatorului (BT-31) si/sau Identificatorul de TVA al reprezentantului fiscal al Vanzatorului (BT-63) trebuie sa fie înscris.
							#The Seller tax registration identifier (BT-32) and/or the Seller VAT identifier (BT-31) and/or the Seller tax representative VAT identifier (BT-63) shall be present.</assert>
			<assert test="cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:StreetName[boolean(normalize-space(.))]"
				flag="fatal"
				id="BR-RO-081"
				>[BR-RO-080]-Adresa Vanzatorului - Linia 1 (BT-35) trebuie furnizata.
							#Seller address line 1(BT-35) must be provided.</assert>
			<assert test="cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cbc:StreetName[boolean(normalize-space(.))]"
				flag="fatal"
				id="BR-RO-082"
				>[BR-RO-080]-Adresa Cumparatorului - Linia 1 (BT-50) trebuie furnizata.
							#Buyer address line 1(BT-50) must be provided.</assert>
			<assert test="cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:CityName[boolean(normalize-space(.))]"
				flag="fatal"
				id="BR-RO-091"
				>[BR-RO-090]-Localitatea Vanzatorului (BT-37) trebuie furnizata.
							#Seller city(BT-37) must be provided.</assert>	
			<assert test="cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cbc:CityName[boolean(normalize-space(.))]"
				flag="fatal"
				id="BR-RO-092"
				>[BR-RO-090]-Localitatea Cumparatorului (BT-52) trebuie furnizata.
							#Buyer city(BT-37) must be provided.</assert>
			<report test="normalize-space(cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cac:Country/cbc:IdentificationCode) = 'RO' and normalize-space(cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:CountrySubentity) = 'RO-B' and not(normalize-space(cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:CityName) = $SECTOR-RO-CODES)"			
				flag="fatal"
				id="BR-RO-100"
				>[BR-RO-100]-Daca Codul tarii Vanzatorului (BT-40) este RO si Subdiviziunea tarii Vanzatorului (BT-39) este RO-B (corespunzator Municipiului Bucuresti), atunci Localitatea Vanzatorului (BT-37) trebuie sa fie codificata folosind lista de coduri SECTOR-RO.
				#If the Seller's country Code (BT-40) is RO and the Seller's country subdivision (BT-39) is RO-B (corresponding to Bucharest Municipality), then the Seller city (BT-37) must be coded using the code list SECTOR-RO(SECTOR1, SECTOR2, SECTOR3, SECTOR4, SECTOR5, SECTOR6).</report>		
			<report test="normalize-space(cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cac:Country/cbc:IdentificationCode) = 'RO' and not(normalize-space(cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:CountrySubentity) = $ISO-3166-RO-CODES)"			
				flag="fatal"
				id="BR-RO-110"
				>[BR-RO-110]-Daca Codul tarii Vanzatorului (BT-40) este RO, atunci Subdiviziunea tarii Vanzatorului (BT-39) trebuie sa fie codificata folosind lista de coduri ISO 3166-2:RO (ex. "RO-B" pentru Municipiul Bucuresti, "RO-AB" pentru judetul Alba...).
				#If the Seller's country Code (BT-40) is RO, then the Seller's country subdivision (BT-39) must be coded using the ISO 3166-2: RO code list (ex. "RO-B" for Bucharest, "RO-AB" for Alba County...).</report>
			<report test="normalize-space(cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cac:Country/cbc:IdentificationCode) = 'RO' and normalize-space(cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cbc:CountrySubentity) = 'RO-B' and not(normalize-space(cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cbc:CityName) = $SECTOR-RO-CODES)"			
				flag="fatal"
				id="BR-RO-101"
				>[BR-RO-100]-Daca Codul tarii Cumparatorului (BT-55) este RO si Subdiviziunea tarii Cumparatorului (BT-54) este RO-B (corespunzator Municipiului Bucuresti), atunci Localitatea Cumparatorului (BT-52) trebuie sa fie codificata folosind lista de coduri SECTOR-RO.
				#If the Buyer's country Code (BT-55) is RO and the Buyer's country subdivision (BT-54) is RO-B (corresponding to Bucharest Municipality), then the Buyer city (BT-52) must be coded using the code list SECTOR-RO(SECTOR1, SECTOR2, SECTOR3, SECTOR4, SECTOR5, SECTOR6).</report>			
			<report test="normalize-space(cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cac:Country/cbc:IdentificationCode) = 'RO' and not(normalize-space(cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cbc:CountrySubentity) = $ISO-3166-RO-CODES)"			
				flag="fatal"
				id="BR-RO-111"
				>[BR-RO-110]-Daca Codul tarii Cumparatorului (BT-55) este RO, atunci Subdiviziunea tarii Cumparatorului (BT-54) trebuie sa fie codificata folosind lista de coduri ISO 3166-2:RO (ex. "RO-B" pentru Municipiul Bucuresti, "RO-AB" pentru judetul Alba...).
				#If the Buyer's country Code (BT-55) is RO, then the Buyer's country subdivision (BT-54) must be coded using the ISO 3166-2: RO code list (ex. "RO-B" for Bucharest, "RO-AB" for Alba County...).</report>
			<assert test="not((cac:AllowanceCharge/cac:TaxCategory/cbc:ID[ancestor::cac:AllowanceCharge/cbc:ChargeIndicator = 'false' and
				following-sibling::cac:TaxScheme/cbc:ID = 'VAT'] = ('S', 'Z', 'E', 'AE', 'K', 'G', 'L', 'M')) or
				(cac:AllowanceCharge/cac:TaxCategory/cbc:ID[ancestor::cac:AllowanceCharge/cbc:ChargeIndicator = 'true'] = ('S', 'Z', 'E', 'AE', 'K', 'G', 'L', 'M')) or
				(cac:InvoiceLine/cac:Item/cac:ClassifiedTaxCategory/cbc:ID = ('S', 'Z', 'E', 'AE', 'K', 'G', 'L', 'M'))) or
				(cac:AccountingCustomerParty/cac:Party/cac:PartyLegalEntity/cbc:CompanyID, cac:AccountingCustomerParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID[boolean(normalize-space(.))])"
				flag="fatal"
				id="BR-RO-120"
				>[BR-RO-120]-Identificatorul de înregistrare legala a Cumparatorului (BT-47) si/sau Identificatorul de TVA al Cumparatorului (BT-48) trebuie sa fie înscris.
							#The Buyer legal registration identifier (BT-47) and/or the Buyer VAT identifier (BT-48) shall be present.</assert>			
	</rule>
	<rule context="/ubl:Invoice/cac:TaxRepresentativeParty/cac:PostalAddress | /ubl:CreditNote/cac:TaxRepresentativeParty/cac:PostalAddress">
			<assert test="cbc:StreetName[boolean(normalize-space(.))]"
				flag="fatal"
				id="BR-RO-140"
				>[BR-RO-140"]-Adresa poștala a reprezentantului fiscal al Vanzatorului (BG-12) trebuie sa contina Linia 1 (BT-64), daca Vanzatorul (BG-4) are un reprezentant fiscal al Vanzatorului (BG-11).
							#Tax representative address line 1 BT-64 ) must be provided, if the Seller (BG-4) has a Seller tax representative party (BG-11)</assert>
			<assert test="cbc:CityName[boolean(normalize-space(.))]"
				flag="fatal"
				id="BR-RO-150"
				>[BR-RO-150]-Adresa poștala a reprezentantului fiscal al Vanzatorului (BG-12) trebuie sa contina Localitatea reprezentantului fiscal (BT-66), daca Vanzatorul (BG-4) are un reprezentant fiscal al Vanzatorului (BG-11).
							#Tax representative city (BT-66 ) must be provided, if the Seller (BG-4) has a Seller tax representative party (BG-11),</assert>
			<report test="normalize-space(cac:Country/cbc:IdentificationCode) = 'RO' and normalize-space(cbc:CountrySubentity) = 'RO-B' and not(normalize-space(cbc:CityName) = $SECTOR-RO-CODES)"			
				flag="fatal"
				id="BR-RO-160"
				>[BR-RO-160]-Daca Codul tarii Reprezentantului fiscal al Vanzatorului (BT-69) este RO si Subdiviziunea tarii Reprezentantului fiscal al Vanzatorului (BT-68) este RO-B (corespunzator Municipiului Bucuresti), atunci Localitatea reprezentantului fiscal al Vanzatorului (BT-66) trebuie sa fie codificata folosind lista de coduri SECTOR-RO.
				#If the Tax representative country code (BT-69) is RO and the Tax representative country subdivision (BT-68) is RO-B (corresponding to Bucharest Municipality), then the Tax representative city(BT-66) must be coded using the code list SECTOR-RO(SECTOR1, SECTOR2, SECTOR3, SECTOR4, SECTOR5, SECTOR6).</report>
			<report test="normalize-space(cac:Country/cbc:IdentificationCode) = 'RO' and not(normalize-space(cbc:CountrySubentity) = $ISO-3166-RO-CODES)"			
				flag="fatal"
				id="BR-RO-170"
				>[BR-RO-170]-Daca Codul tarii Reprezentantului fiscal al Vanzatorului (BT-69) este RO, atunci Subdiviziunea tarii Reprezentantului fiscal al Vanzatorului (BT-68) trebuie sa fie codificata folosind lista de coduri ISO 3166-2:RO (ex. RO-B pentru Municipiul Bucuresti, RO-AB pentru judetul Alba...).
				#If the Seller's tax representative country code (BT-69) is RO, then the Seller's tax representative country subdivision (BT-68) must be coded using the ISO 3166-2: RO code list (ex. RO-B for Bucharest, RO-AB for Alba County...).</report>
	</rule>
	<rule context="//cac:PaymentMeans">
			<assert test="string-length(normalize-space(cac:PayeeFinancialAccount/cbc:Name)) &lt;= 200"
				flag="fatal" 
				id="BR-RO-L208" 
				>[BR-RO-L200]-Numarul maxim permis de caractere pentru Numele contului de plata  (BT-85), este 200.
				#The allowed maximum number of characters for the Payment account name (BT-85) is 200.</assert>
			<assert test="string-length(normalize-space(cac:CardAccount/cbc:HolderName)) &lt;= 200"
				flag="fatal" 
				id="BR-RO-L209" 
				>[BR-RO-L200]-Numarul maxim permis de caractere pentru Numele detinatorului cardului de plata  (BT-88), este 200.
				#The allowed maximum number of characters for the Payment card holder name(BT-88) is 200.</assert>
			<assert test="string-length(normalize-space(cbc:PaymentMeansCode/@name)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1016" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Explicatii privind instrumentul de plata (BT-82) este 100.
				#The allowed maximum number of characters for the Payment means text (BT-82) is 100.</assert>	
			<assert test="string-length(normalize-space(cbc:PaymentID)) &lt;= 140"
				flag="fatal" 
				id="BR-RO-L140" 
				>[BR-RO-L140]-Numarul maxim permis de caractere pentru Aviz de plata (BT-83) este 140.
				#The allowed maximum number of characters for the Remittance information (BT-83) is 140.</assert>
	</rule> 	
	<rule context="/ubl:Invoice/cac:Delivery/cac:DeliveryLocation/cac:Address | /ubl:CreditNote/cac:Delivery/cac:DeliveryLocation/cac:Address">
			<assert test="cbc:StreetName[boolean(normalize-space(.))]"
				flag="fatal"
				id="BR-RO-180"
				>[BR-RO-180"-Daca Adresa de livrare (BG-15) exista, trebuie furnizata Adresa de livrare — linia 1 (BT-75).
							#If the Delivery to (BG-15) exists, the Deliver to address line 1 (BT-75) must exists.</assert>
			<assert test="cbc:CityName[boolean(normalize-space(.))]"
				flag="fatal"
				id="BR-RO-201"
				>[BR-RO-200]-Daca Adresa de livrare (BG-15) exista, trebuie furnizata Localitatea de livrare (BT-77).
							#If the Delivery to (BG-15) exists, the Deliver to city (BT-77) must exists.</assert>
			<report test="normalize-space(cac:Country/cbc:IdentificationCode) = 'RO' and normalize-space(cbc:CountrySubentity) = 'RO-B' and not(normalize-space(cbc:CityName) = $SECTOR-RO-CODES)"			
				flag="fatal"
				id="BR-RO-202"
				>[BR-RO-200]-Daca Codul tarii de livrare (BT-80) este RO si Subdiviziunea tarii de livrare (BT-79) este "RO-B" (corespunzator Municipiului Bucuresti), atunci Localitatea de livrare (BT-77) trebuie sa fie codificata folosind lista de coduri SECTOR-RO.
				#If the Delivery to country code (BT-80) is RO and the Delivery to country subdivision (BT-79) is "RO-B" (corresponding to Bucharest Municipality), then the Delivery to city(BT-77) must be coded using the code list SECTOR-RO(SECTOR1, SECTOR2, SECTOR3, SECTOR4, SECTOR5, SECTOR6).</report>
			<assert test="cbc:CountrySubentity[boolean(normalize-space(.))]"
				flag="fatal"
				id="BR-RO-211"
				>[BR-RO-210"]-Daca Adresa de livrare (BG-15) exista, trebuie furnizata Subdiviziunea tarii de livrare (BT-79).
							#If the Delivery to (BG-15) exists, the Deliver to country subdivision (BT-79) must exists.</assert>
			<report test="normalize-space(cac:Country/cbc:IdentificationCode) = 'RO' and not(normalize-space(cbc:CountrySubentity) = $ISO-3166-RO-CODES)"			
				flag="fatal"
				id="BR-RO-212"
				>[BR-RO-210]-Daca Codul tarii de livrare (BT-80) este "RO", atunci Subdiviziunea tarii de livrare (BT-79) trebuie sa fie codificata folosind lista de coduri ISO 3166-2:RO (ex. "RO-B" pentru Municipiul Bucuresti, "RO-AB" pentru judetul Alba...).
				#If Delivery country code (BT-80) is "RO", then Delivery country subdivision (BT-79) must be coded using the ISO 3166-2: RO code list (ex. "RO-B" for Bucharest, "RO-AB" for Alba County...).</report>
	</rule>	
	<rule flag="fatal" context="cac:InvoicePeriod/cbc:DescriptionCode">
			<assert test="((not(contains(normalize-space(.), ' ')) and contains(' 3 35 432 ', concat(' ', normalize-space(.), ' '))))"
				flag="fatal" 
				id="BR-RO-040" 
				>[BR-RO-040]-Codul datei de exigibilitate a taxei pe valoarea adaugata (BT-8) trebuie sa fie unul dintre urmatoarele coduri din lista de coduri UNTDID 2005: 3 (Data emiterii facturii), 35 (Data reala a livrarii), 432 (Suma platita în acea zi).
							#Value added tax point date code MUST be coded using a restriction of UNTDID 2005 (only 3, 35 and 432).</assert>
	</rule>		
	<!--   line-level constrains -->
	<rule context="cac:InvoiceLine | cac:CreditNoteLine">     
			<assert test="string-length(normalize-space(cac:Item/cbc:Name)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1024" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Numele articolului (BT-153) este 100.
							#The allowed maximum number of characters for the Item name (BT-153) is 100.</assert>      
			
			<assert test="string-length(normalize-space(cbc:AccountingCost)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1021" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Referinta contabila a Cumparatorului din linia facturii (BT-133) este 100.
							#The allowed maximum number of characters for the Invoice line Buyer accounting reference (BT-133) is 100.</assert>
			
			<assert test="string-length(normalize-space(cac:Item/cbc:Description)) &lt;= 200"
				flag="fatal" 
				id="BR-RO-L212" 
				>[BR-RO-L200]-Numarul maxim permis de caractere pentru Descrierea articolului (BT-154) este 200.
							#The allowed maximum number of characters for the Item description (BT-154) is 200.</assert>
			<assert test="string-length(normalize-space(cbc:Note)) &lt;= 300"
				flag="fatal" 
				id="BR-RO-L303" 
				>[BR-RO-L300]-Numarul maxim permis de caractere pentru Nota liniei facturii (BT-127) este 300.
				#The allowed maximum number of characters for the Invoice line note (BT-127) is 300.</assert>
	</rule>	
	<rule context="//cac:Item/cac:AdditionalItemProperty"> 
		<assert test="count(.) &lt;= 50"
			flag="fatal"
			id="BR-RO-A052" 
			>[BR-RO-A050]-O factura trebuie sa contina maximum 50 de aparitii ale grupului Atributele articolului (BG-32).
			#The allowed maximum number of occurences of Item attributes (BG-32) is 50.</assert>
		<assert test="string-length(normalize-space(cbc:Name)) &lt;= 50"
			flag="fatal" 
			id="BR-RO-L0505" 
			>[BR-RO-L050]-Numarul maxim permis de caractere pentru Numele atributului articolului (BT-160) este 50.
			#The allowed maximum number of characters for the Item attribute name (BT-160) is 50.</assert>
		<assert test="string-length(normalize-space(cbc:Value)) &lt;= 100"
			flag="fatal" 
			id="BR-RO-L1025" 
			>[BR-RO-L100]-Numarul maxim permis de caractere pentru Valoarea atributului articolului (BT-161) este 100.
			#The allowed maximum number of characters for the Item attribute value (BT-161) is 100.</assert>
	</rule>
	<!--  amount number of decimals constrains  -->	
	<rule context="/ubl:Invoice/cac:AllowanceCharge[cbc:ChargeIndicator = false()] | /ubl:CreditNote/cac:AllowanceCharge[cbc:ChargeIndicator = false()]"> 
			<assert id="BR-DEC-RO-01" flag="fatal" test="string-length(substring-after(cbc:Amount,'.'))&lt;=2">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Valoarea deducerilor la nivelul documentului (BT-92) este 2.
							#The allowed maximum number of decimals for the Document level allowance amount(BT-92) is 2.</assert>
			<assert id="BR-DEC-RO-02" flag="fatal" test="string-length(substring-after(cbc:BaseAmount,'.'))&lt;=2">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Valoarea de baza a deducerii la nivelul documentului (BT-93) este 2.
							#The allowed maximum number of decimals for the Document level allowance base amount(BT-93) is 2.</assert>
			<assert test="string-length(normalize-space(cbc:AllowanceChargeReasonCode)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1017" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Motivul deducerii la nivelul documentului (BT-97) este 100.
				#The allowed maximum number of characters for the Document level allowance reason (BT-97) is 100.</assert>		
	</rule>
	<rule context="/ubl:Invoice/cac:AllowanceCharge[cbc:ChargeIndicator = true()] | /ubl:CreditNote/cac:AllowanceCharge[cbc:ChargeIndicator = true()]">
			<assert id="BR-DEC-RO-05" flag="fatal" test="string-length(substring-after(cbc:Amount,'.'))&lt;=2">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Valoarea taxelor suplimentare la nivelul documentului (BT-99) este 2.
							#The allowed maximum number of decimals for the Document level charge amount (BT-99) is 2.</assert>
			<assert id="BR-DEC-RO-06" flag="fatal" test="string-length(substring-after(cbc:BaseAmount,'.'))&lt;=2">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Valoarea de baza a taxelor suplimentare la nivelul documentului (BT-100) este 2.
							#The allowed maximum number of decimals for the Document level charge base amount (BT-100) is 2.</assert>
			<assert test="string-length(normalize-space(cbc:AllowanceChargeReasonCode)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1018" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Motivul taxei suplimentare la nivelul documentului (BT-104) este 100.
				#The allowed maximum number of characters for the Document level charge reason (BT-104) is 100.</assert>
	</rule>
	<rule context="cac:LegalMonetaryTotal">
			<assert id="BR-DEC-RO-09" flag="fatal" test="string-length(substring-after(cbc:LineExtensionAmount,'.'))&lt;=2">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Suma valorilor nete ale liniilor facturii (BT-106) este 2.
							#The allowed maximum number of decimals for the Sum of Invoice line net amount (BT-106) is 2.</assert>
			<assert id="BR-DEC-RO-10" flag="fatal" test="string-length(substring-after(cbc:AllowanceTotalAmount,'.'))&lt;=2">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Suma deducerilor la nivelul documentului (BT-107) este 2.
							#The allowed maximum number of decimals for the Sum of allowances on document level(BT-107) is 2.</assert>
			<assert id="BR-DEC-RO-11" flag="fatal" test="string-length(substring-after(cbc:ChargeTotalAmount,'.'))&lt;=2">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Suma taxelor suplimentare la nivelul documentului (BT-108) este 2.
							#The allowed maximum number of decimals for the Sum of charges on document level(BT-108) is 2.</assert>
			<assert id="BR-DEC-RO-12" flag="fatal" test="string-length(substring-after(cbc:TaxExclusiveAmount,'.'))&lt;=2">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Valoarea totala a facturii fara TVA (BT-109) este 2.
							#The allowed maximum number of decimals for the Invoice total amount without VAT (BT-109) is 2.</assert>
			<assert id="BR-DEC-RO-14" flag="fatal" test="string-length(substring-after(cbc:TaxInclusiveAmount,'.'))&lt;=2">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Valoarea totala a facturii cu TVA (BT-112) este 2.
							#The allowed maximum number of decimals for the Invoice total amount with VAT (BT-112) is 2.</assert>
			<assert id="BR-DEC-RO-16" flag="fatal" test="string-length(substring-after(cbc:PrepaidAmount,'.'))&lt;=2">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Suma platita (BT-113) este 2.
							#The allowed maximum number of decimals for the Paid amount(BT-113) is 2.</assert>
			<assert id="BR-DEC-RO-17" flag="fatal" test="string-length(substring-after(cbc:PayableRoundingAmount,'.'))&lt;=2">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Valoare de rotunjire (BT-114) este 2.
							#The allowed maximum number of decimals for the Rounding amount(BT-114) is 2.</assert>
			<assert id="BR-DEC-RO-18" flag="fatal" test="string-length(substring-after(cbc:PayableAmount,'.'))&lt;=2">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Suma de plata (BT-115) este 2.
							#The allowed maximum number of decimals for the Amount due for payment (BT-115) is 2.</assert>
	</rule>	
	<rule context="/ubl:Invoice | cac:CreditNote"> 
			<assert id="BR-DEC-RO-13" flag="fatal" test="(//cac:TaxTotal/cbc:TaxAmount[@currencyID = cbc:DocumentCurrencyCode] and (string-length(substring-after(//cac:TaxTotal/cbc:TaxAmount[@currencyID = cbc:DocumentCurrencyCode],'.'))&lt;=2)) or (not(//cac:TaxTotal/cbc:TaxAmount[@currencyID = cbc:DocumentCurrencyCode]))">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Valoarea totala a TVA a facturii (BT-110) este 2.
							#The allowed maximum number of decimals for the Invoice total VAT amount (BT-110) is 2.</assert>
			<assert id="BR-DEC-RO-15" flag="fatal" test="(//cac:TaxTotal/cbc:TaxAmount[@currencyID = cbc:TaxCurrencyCode] and (string-length(substring-after(//cac:TaxTotal/cbc:TaxAmount[@currencyID = cbc:TaxCurrencyCode],'.'))&lt;=2)) or (not(//cac:TaxTotal/cbc:TaxAmount[@currencyID = cbc:TaxCurrencyCode]))">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Valoarea TVA totala a facturii în moneda de contabilizare (BT-111) este 2.
							#The allowed maximum number of decimals for the Invoice total VAT amount in accounting currency (BT-111) is 2.</assert>
	</rule>
	<rule context="cac:TaxTotal/cac:TaxSubtotal">
			<assert id="BR-DEC-RO-1009" flag="fatal" test="string-length(substring-after(cbc:TaxableAmount,'.'))&lt;=2">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Baza de calcul pentru categoria de TVA (BT-116) este 2.
							#The allowed maximum number of decimals for the VAT category taxable amount (BT-116) is 2.</assert>
			<assert id="BR-DEC-RO-1010" flag="fatal" test="string-length(substring-after(cbc:TaxAmount,'.'))&lt;=2">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Valoarea TVA pentru fiecare categorie de TVA (BT-117) este 2.
							#The allowed maximum number of decimals for the VAT category tax amount (BT-117) is 2.</assert>		
	</rule>
	<rule context="cac:InvoiceLine | cac:CreditNoteLine">
			<assert id="BR-DEC-RO-23" flag="fatal" test="string-length(substring-after(cbc:LineExtensionAmount,'.'))&lt;=2">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Valoarea neta a liniei facturii (BT-131) este 2.
							#The allowed maximum number of decimals for the Invoice line net amount (BT-131) is 2.</assert> 
	</rule>
	<rule context="//cac:InvoiceLine/cac:AllowanceCharge[cbc:ChargeIndicator = false()] | //cac:CreditNoteLine/cac:AllowanceCharge[cbc:ChargeIndicator = false()]">
			<assert id="BR-DEC-RO-24" flag="fatal" test="string-length(substring-after(cbc:Amount,'.'))&lt;=2">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Valoarea deducerii la linia facturii (BT-136) este 2.
							#The allowed maximum number of decimals for the Invoice line allowance amount (BT-136) is 2.</assert>
			<assert id="BR-DEC-RO-25" flag="fatal" test="string-length(substring-after(cbc:BaseAmount,'.'))&lt;=2">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Valoarea de baza a deducerii la linia facturii (BT-137) este 2.
							#The allowed maximum number of decimals for the Invoice line allowance base amount (BT-137) is 2.</assert>
			<assert test="string-length(normalize-space(cbc:AllowanceChargeReason)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1022" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Motivul deducerii la linia facturii (BT-139) este 100.
				#The allowed maximum number of characters for the Invoice line allowance reason (BT-139) is 100.</assert>
	</rule>
	<rule context="//cac:InvoiceLine/cac:AllowanceCharge[cbc:ChargeIndicator = true()] | //cac:CreditNoteLine/cac:AllowanceCharge[cbc:ChargeIndicator = true()]">
			<assert id="BR-DEC-RO-27" flag="fatal" test="string-length(substring-after(cbc:Amount,'.'))&lt;=2">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Valoarea taxei suplimentare la linia facturii (BT-141) este 2.
				#The allowed maximum number of decimals for the Invoice line charge amount (BT-141) is 2.</assert>
			<assert id="BR-DEC-RO-28" flag="fatal" test="string-length(substring-after(cbc:BaseAmount,'.'))&lt;=2">
				[BR-RO-Z2]-Numarul maxim permis de zecimale pentru Valoarea de baza a taxei suplimentare la linia facturii (BT-142) este 2.
				#The allowed maximum number of decimals for the Invoice line charge base amount (BT-142) is 2.</assert>
			<assert test="string-length(normalize-space(cbc:AllowanceChargeReason)) &lt;= 100"
				flag="fatal" 
				id="BR-RO-L1023" 
				>[BR-RO-L100]-Numarul maxim permis de caractere pentru Motivul taxei suplimentare la linia facturii (BT-144) este 100.
				#The allowed maximum number of characters for the Invoice line charge reason (BT-144) is 100.</assert>
	</rule>	
	<rule context="cbc:Note">
			<assert test="string-length(normalize-space(.)) &lt;= 300"
				flag="fatal" 
				id="BR-RO-L302" 
				>[BR-RO-L300]-Numarul maxim permis de caractere pentru Comentariu în factura (BT-22) este 300.
				#The allowed maximum number of characters for the Invoice note (BT-22) is 300.</assert>
	</rule>
	<rule context="//cac:AdditionalDocumentReference">
		<assert test="count(.) &lt;= 50"
			flag="fatal"
			id="BR-RO-A051" 
			>[BR-RO-A050]-O factura trebuie sa contina maximum 50 de aparitii ale grupului Documente justificative suplimentare (BG-24).
			#The allowed maximum number of occurences of Additional supporting documents (BG-24) is 50</assert>
		<assert test="string-length(normalize-space(cbc:ID)) &lt;= 200"
			flag="fatal" 
			id="BR-RO-L0308" 
			>[BR-RO-L200]-Numarul maxim permis de caractere pentru Identificatorul obiectului facturat (BT-18) si Referinta documentului justificativ (BT-122) este 200.
			#The allowed maximum number of characters for the Invoiced object identifier (BT-18) and the Supporting document reference(BT-122)is 200.</assert>
		<assert test="string-length(normalize-space(cbc:DocumentDescription)) &lt;= 100"
			flag="fatal" 
			id="BR-RO-L1020" 
			>[BR-RO-L100]-Numarul maxim permis de caractere pentru Descrierea documentului justificativ (BT-123) este 100.
			#The allowed maximum number of characters for the Supporting document description (BT-123) is 100.</assert>
		<assert test="string-length(normalize-space(cac:Attachment/cac:ExternalReference/cbc:URI)) &lt;= 200"
			flag="fatal" 
			id="BR-RO-L210" 
			>[BR-RO-L200]-Numarul maxim permis de caractere pentru Localizarea documentului extern  (BT-124), este 200.
			#The allowed maximum number of characters for the External document location (BT-124) is 200.</assert>
		<assert test="string-length(normalize-space(cac:Attachment/cbc:EmbeddedDocumentBinaryObject/@filename)) &lt;= 200"
			flag="fatal" 
			id="BR-RO-L211" 
			>[BR-RO-L200]-Numarul maxim permis de caractere pentru Numele fisierului documentului atasat  (BT-125-2), este 200.
			#The allowed maximum number of characters for the Attached document Filename (BT-125-2) is 200.</assert>
	</rule>
	<rule context="//cac:BillingReference">
		<assert test="count(cac:InvoiceDocumentReference) &lt;= 500"
			flag="fatal"
			id="BR-RO-A500" 
			>[BR-RO-A500]-O factura trebuie sa contina maximum 500 de aparitii ale grupului Referinta la o factura anterioara (BG-3).
			#The allowed maximum number of occurences of Preceding invoice reference (BG-3) is 500.</assert>
		  
		<assert test="string-length(normalize-space(cac:InvoiceDocumentReference/cbc:ID)) &lt;= 200"
			flag="fatal" 
			id="BR-RO-L156" 
			>[BR-RO-L200]-Numarul maxim permis de caractere pentru Referinta la o factura anterioara (BT-25) este 200.
			#The allowed maximum number of characters for the Preceding Invoice number (BT-25) is 200.</assert>
		
	</rule>
</pattern>
</schema>


