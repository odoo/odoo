from odoo import _, _lt

WSFE_ERRORS = {
    '501': _lt('This is an internal error in AFIP. Please wait a couple of minutes and try again'),
    '600': _lt('"600: ValidacionDeToken: Error al verificar hash"\n    "600: VerificacionDeHash: Digital signature is not validated". It is usually an error on AFIP servers, to verify this we can go to the type of documents and do a Get Last Invoice, if we get an error then it is due to an AFIP error. It is usually solved within the day.\n * "600: ValidacionDeToken: No apareció CUIT en lista de relacione" It is likely that you has not delegated AFIP services or electronic invoice setup is not completed'),
    '602': _lt('The number or date of the document does not correspond to the next one to be authorized.\n * The invoice date not be after the last invoice validated in AFIP.\n * Verify that the next invoice number in the Journal corresponds with the next one in AFIP\n * If AFIP Concept "Services" or "Products and Services" could be due to the Invoice Date: this one could be null or need to be in the range N-10 and N+10 days being N the date of dispatch of the authorization request.\n\nYou can go to "Consult invoice in AFIP" menu and get the information about the last invoice.'),
    '1006': _lt('It solved using "round globally" method in the company'),
    '10016': _lt('The number or date of the document does not correspond to the next one to be authorized.\n * The invoice date not be after the last invoice validated in AFIP.\n * Verify that the next invoice number in the Journal corresponds with the next one in AFIP\n * If AFIP Concept "Services" or "Products and Services" could be due to the Invoice Date: this one could be null or need to be in the range N-10 and N+10 days being N the date of dispatch of the authorization request.\n\nYou can go to "Consult invoice in AFIP" menu and get the information about the last invoice.'),
    '10018': _lt('This error is usually given if the decimal precision of product prices is greater than currency precision. The alternatives are: a) use the lowest decimal precision for product price. b) raise the decimal precision of the currency in question.\n\nAfter updating the precisions you must change the quantities or prices on all invoice lines in order to recomputed the amounts, save and then reset'),
    '10040': _lt('You are trying to create a debit or credit note but the document type you selected does not match with the original one'),
    '10048': _lt('This error is usually given if the decimal precision of product prices is greater than currency precision. The alternatives are: a) use the lowest decimal precision for product price. b) raise the decimal precision of the currency in question.\n\nAfter updating the precisions you must change the quantities or prices on all invoice lines in order to recomputed the amounts, save and then reset'),
    '10015': _lt('* If you are making an invoice < 10.000 to an final consumer who has DNI as identification type you must provide the DNI number.\n * Another alternative is to set Sigd (Unidentified / daily global sale) Identification type in order to do not need to inform the Document number,\n * This also happens when you try to generate an invoice with amount greater than 1.000 to an Anonymous Final Consumer instead of one identified with DNI or CUIT.\n\nEdit the invoice and change the partner from "Final Consumer" to a customer with First and Last Name, document number with format 00xxxxxxxx0, where xxxxxxxx is a an eight-digit document number'),
    '10192': _lt('It is not a valid invoice under the Regime of Law No. 27,440, that is, you should made a FCE invoice instead of a conventional invoice. Choose a type of electronic credit invoice document (this documents containt the string MiPyME)'),
    '10154': _lt('It is possible that you are making a CN/DN but you are setting a wrong value in the "FCE: Is cancellation" field. If the AFIP message indicates:'
        '\n\t * "OK - Comprobante electrónico autorizado, NO rechazado por el Comprador" it means that the "FCE: Is cancellation" should NOT be set.'
        '\n\t * "OK - Comprobante electrónico autorizado pero fue rechazado por el comprador" it means that the "FCE: Is cancellation" should be set.'),
    '10153': _lt('If the invoice is a a FCE, Debit Note or Credit Note it is mandatory to inform related invoices. You are probably doing an CN/DN and the "Source" field (in the Other Information Tab) is not defined or has a wrong value. You must indicate in that field the original invoice number without any prefix or suffix, eg "0001-00000001"'),
    '10181': _lt('As the message mentions, if you are making an CN/DN, it must be with the same currency as the original invoice.\n\nThe only exception is the exchange rate adjustments that need to be done in ARS but taking into account that the orginal invoice must already be accepted (or rejected by the customer).\n\nWe recommend you to verify if the customer has already accepted/rejected the original invoice'),
    '10184': _lt('You are probably wanting to cancel an invoice through an CN but the invoice has already been accepted for the client. Keep in mind that acceptance may have been "express" or "tacit" (that is , automatically accepted after 30 calendar days without the client having rejected it).'),
    '10051': _lt('Could happen that the VAT is calculated without the discount, then it throws another amount.'),
    '10162': _lt('You may not have completed the Bank Account field on the invoice'),
    '10168': _lt('Please check that the company bank account is created and is filled with the CBU number (22 digits), not the account number'),
    '10180': _lt('Please check the next conditions:\n    * Review that the invoice total invoice is greater than the amount defined by AFIP for this type of document\n    * Review that the customer is a MiPYME'),
    '10216': _lt('The new RG 4919/2021 define that MiPYME document requires to inform the FCE Transmission Option. Set this one in your Accounting Settings in order to continue. Possible values are: SCA or ADC. These options means:\n * SCA - TRANSFERENCIA AL SISTEMA DE CIRCULACION ABIERTA\n * ADC - AGENTE DE DEPOSITO COLECTIVO'),
    '10164': _lt('The due date should not be earlier than the invoice date. Please verify the invoice dates and payment terms.'),
}

WSFEX_ERRORS = {
    'country_afip_code': _lt('We searched for the destination country of the invoice and had no AFIP code.\n\nPlease enter the AFIP page and look for the code in the System Tables section > Countries found in the bottom right and look for the corresponding code.\n\n Then go to Odoo to the Sales menu > Settings > Address book > Localization > Countries, activate developer mode and add the AFIP code in the corresponding field'),
    '1640': _lt('For invoices of type "(19) FACTURAS DE EXPORTACION" and AFIP Concept "Products / Definitive export of goods" it is require to sent the Incoterm infomation. Please go to Other Info Tab and select the corresponding value in the Incoterm field'),
    '1580': _lt('If the customer belongs to a Free Zone you should give the customer CUIT number in order to continue\n * If is a Foreign Customer is possible that Odoo does not have Legal VAT/Natrual VAT configured for your customer country.\n\n\t 1. Please go to AFIP page and search for the code in the section "Tablas del Sistema > Paises" that is in the bottom right of the page and get the corresponding code for the country.\n\t 2. Go back to  Odoo, in the menú Sales > Settings > Address Book > Localization > Countries, activate the developer mode and add the AFIP code in the corresponding field'),
    '1668': _lt('The registration for the online exportation invoices (invoice generate from AFIP page) is different than the registration for electronic exportation invoices. Therefore you must configure this one also because you will not be able to create invoices of this type in Odoo.\n\nWhen configuring, you must check the option "Factura Electrónica Exportación de Servicios" and then "Webservice/Facturador Plus".\n\nView image https://www.adhoc.com.ar/web/content/162597?unique=202798c78764e1c1d31b35d46556a7947ac511e8&download=true'),
    '2053': _lt('For the invoice case, if you are trying to validate an invoice "AFIP Concept: Service" and the invoice currency is not ARS then the currency rate must be the one of the previous business day of the date where the invoice was issued. If the request has a date previous that the one in the invoice then the rate should be the one of previous business day of the request.\n * For the case of the Debit or Credit Notes of type "Services" the rate should be the same as the related invoice.'),
}

WBSFE_ERRORS = {
    '501': _lt('This is an internal error in AFIP. Contact to your Odoo provider in order to let it know that is happening and to investigate what is going on with the AFIP service'),
    '1014': _lt('This error could mean any of the next options\n\n   * "Campo Tipo_doc invalido": Fiscal bond only create invoices for partners with CUIT.\n   * "Campo Cmp.Items.Pro_codigo_ncm invalido": You need to sent the NCM code of all the products in the invoice. Please verify that you provide correct NCM codes in the products of the invoice to continue.'),
}

ERRORS = {
    key: _lt('This is the description of the observation code: "%s"', val)
    for key, val in {
        '01': 'LA  CUIT INFORMADA NO CORRESPONDE A UN RESPONSABLE INSCRIPTO EN EL IVA ACTIVO',
        '02': 'LA CUIT INFORMADA NO SE ENCUENTRA AUTORIZADA A EMITIR COMPROBANTES ELECTRONICOS ORIGINALES O EL PERIODO DE INICIO AUTORIZADO ES POSTERIOR AL DE LA GENERACION DE LA SOLICITUD',
        '03': 'LA CUIT INFORMADA REGISTRA INCONVENIENTES CON EL DOMICILIO FISCAL',
        '04': 'EL PUNTO DE VENTA INFORMADO NO SE ENCUENTRA DECLARADO PARA SER UTILIZADO EN EL PRESENTE RÉGIMEN',
        '05': 'LA FECHA DEL COMPROBANTE INDICADA NO PUEDE SER ANTERIOR EN MAS DE CINCO DIAS, SI SE TRATA DE UNA VENTA, O ANTERIOR O POSTERIOR EN MAS DE DIEZ DIAS, SI SE TRATA DE UNA PRESTACION DE SERVICIOS, CONSECUTIVOS DE LA FECHA DE REMISION DEL ARCHIVO    Art. 22 de la RG N° 2177-',
        '06': 'LA CUIT INFORMADA NO SE ENCUENTRA AUTORIZADA A EMITIR COMPROBANTES CLASE "A"',
        '07': 'PARA LA CLASE DE COMPROBANTE SOLICITADO -COMPROBANTE CLASE A- DEBERA CONSIGNAR EN EL CAMPO CODIGO DE DOCUMENTO IDENTIFICATORIO DEL COMPRADOR EL CODIGO "80"',
        '08': 'LA CUIT INDICADA EN EL CAMPO N° DE IDENTIFICACION DEL COMPRADOR ES INVALIDA',
        '09': 'LA CUIT INDICADA EN EL CAMPO N° DE IDENTIFICACION DEL COMPRADOR NO EXISTE EN EL PADRON UNICO DE CONTRIBUYENTES',
        '10': 'LA CUIT INDICADA EN EL CAMPO N° DE IDENTIFICACION DEL COMPRADOR NO CORRESPONDE A UN RESPONSABLE INSCRIPTO EN EL IVA ACTIVO',
        '11': 'EL N° DE COMPROBANTE DESDE INFORMADO NO ES CORRELATIVO AL ULTIMO N° DE COMPROBANTE REGISTRADO/HASTA SOLICITADO PARA ESE TIPO DE COMPROBANTE Y PUNTO DE VENTA',
        '12': 'EL RANGO INFORMADO SE ENCUENTRA AUTORIZADO CON ANTERIORIDAD PARA LA MISMA CUIT, TIPO DE COMPROBANTE Y PUNTO DE VENTA',
        '13': 'LA CUIT INDICADA SE ENCUENTRA COMPRENDIDA EN EL REGIMEN ESTABLECIDO POR LA RESOLUCION GENERAL N° 2177 Y/O EN EL TITULO I DE LA RESOLUCION GENERAL N° 1361 ART. 24 DE LA RG N° 2177-',
        '15': 'LA CUIT INFORMADA DEL EMISOR NO CUMPLE LAS CONDICIONES SEGÚN EL RÉGIMEN FCE',
        '16': 'LA CUIT INFORMADA DEL EMISOR NO TIENE ACTIVO EL DOMICILIO FISCAL ELECTRONICO',
        '17': 'SI EL TIPO DE COMPROBANTE QUE ESTÁ AUTORIZANDO ES MIPYMES (FCE), EL RECEPTOR DEL COMPROBANTE INFORMADO EN DOCTIPO Y DOCNRO DEBE CORRESPONDER A UN CONTRIBUYENTE CARACTERIZADO COMO GRANDE O PYME QUE OPTÓ',
        '18': 'SI EL TIPO DE COMPROBANTE QUE ESTÁ AUTORIZANDO ES MIPYMES (FCE), EL RECEPTOR DEL COMPROBANTE DEBE TENER HABILITADO EL DOMICILIO FISCAL ELECTRONCO',
    }
}

def _hint_msg(error_code, afipws):
    """Get explanation and/or hints on errors returned by wsfe webservice.

    :param str error_code:
    :param str afipws: webservice (wsfe|wsfex|wbsfe)
    :rtype: str
    """
    if afipws == 'wsfe' and error_code in WSFE_ERRORS:
        return str(WSFE_ERRORS.get(error_code))

    elif afipws == 'wsfex' and error_code in WSFEX_ERRORS:
        return str(WSFEX_ERRORS.get(error_code))

    elif afipws == 'wsbfe' and error_code in WBSFE_ERRORS:
        return str(WBSFE_ERRORS.get(error_code))

    elif error_code in ERRORS:
        return str(ERRORS.get(error_code))

    elif error_code == 'reprocess':
        return _('The invoice is trying to be reprocessed')

    elif error_code == 'rejected':
        return _('The invoice has not been accepted by AFIP, please fix the errors and try again')

    # Observations codes
    elif error_code == "17;;":
        return str(ERRORS["17"])

    res = []
    # Observations can separate using ; multiple values can came at the same time, so we split the codes
    # in order to show all the related help
    for item in error_code.split(';'):
        code = item.strip()
        if ERRORS.get(code):
            res.append(code + ' - ' + ERRORS.get(code))

    return '\n* '.join(res)
