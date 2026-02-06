# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
from datetime import datetime


def compute_cufe(
    num_fac,        # Invoice number
    fec_fac,        # Invoice date+time (datetime or ISO string 'YYYY-MM-DDTHH:MM:SS')
    val_fac,        # Invoice subtotal (before tax)
    cod_imp_1,      # Tax code 1 (IVA = '01')
    val_imp_1,      # Tax amount 1 (IVA amount)
    cod_imp_2,      # Tax code 2 (INC = '04')
    val_imp_2,      # Tax amount 2 (INC amount)
    cod_imp_3,      # Tax code 3 (ICA = '03')
    val_imp_3,      # Tax amount 3 (ICA amount)
    val_tot,        # Total invoice amount (subtotal + taxes)
    nit_ofe,        # NIT of the issuer (emisor)
    num_adq,        # Identification of the buyer (adquiriente)
    cl_tec,         # Technical key (clave tecnica) from DIAN numbering range
    tipo_ambiente,  # Environment: '1' = Production, '2' = Test
):
    """Compute the CUFE (Clave Unica de Facturacion Electronica) per DIAN Technical Annex v1.9.

    The CUFE is a SHA-384 hash of a concatenated string of invoice fields.
    It uniquely identifies each electronic invoice and must be included in
    the UBL XML (cbc:UUID) and the graphic representation (QR code).

    Formula:
        SHA384(NumFac + FecFac + ValFac + CodImp1 + ValImp1 + CodImp2 + ValImp2
               + CodImp3 + ValImp3 + ValTot + NitOFE + NumAdq + ClTec + TipoAmbiente)

    :param num_fac: Invoice number (string, e.g., 'SETP990000001')
    :param fec_fac: Invoice datetime (datetime object or ISO string)
    :param val_fac: Subtotal before taxes (Decimal/float, formatted to 2 decimals)
    :param cod_imp_1: DIAN tax type code for IVA ('01')
    :param val_imp_1: IVA tax amount
    :param cod_imp_2: DIAN tax type code for INC ('04')
    :param val_imp_2: INC tax amount
    :param cod_imp_3: DIAN tax type code for ICA ('03')
    :param val_imp_3: ICA tax amount
    :param val_tot: Total invoice amount including taxes
    :param nit_ofe: NIT of the issuer (without check digit or hyphens)
    :param num_adq: Identification number of the buyer
    :param cl_tec: Technical key from DIAN-authorized numbering range
    :param tipo_ambiente: '1' for production, '2' for test
    :return: CUFE as a lowercase hex string (96 characters)
    """
    if isinstance(fec_fac, datetime):
        fec_fac_str = fec_fac.strftime('%Y-%m-%dT%H:%M:%S')
    else:
        fec_fac_str = str(fec_fac)

    # Format monetary values to exactly 2 decimal places
    val_fac_str = _format_amount(val_fac)
    val_imp_1_str = _format_amount(val_imp_1)
    val_imp_2_str = _format_amount(val_imp_2)
    val_imp_3_str = _format_amount(val_imp_3)
    val_tot_str = _format_amount(val_tot)

    # Build the concatenated string per DIAN specification
    cufe_input = (
        str(num_fac)
        + fec_fac_str
        + val_fac_str
        + str(cod_imp_1)
        + val_imp_1_str
        + str(cod_imp_2)
        + val_imp_2_str
        + str(cod_imp_3)
        + val_imp_3_str
        + val_tot_str
        + str(nit_ofe)
        + str(num_adq)
        + str(cl_tec)
        + str(tipo_ambiente)
    )

    return hashlib.sha384(cufe_input.encode('utf-8')).hexdigest()


def compute_cude(
    num_doc,        # Document number (credit note, debit note, etc.)
    fec_doc,        # Document date+time
    val_doc,        # Document subtotal
    cod_imp_1,      # Tax code 1 (IVA = '01')
    val_imp_1,      # Tax amount 1
    cod_imp_2,      # Tax code 2 (INC = '04')
    val_imp_2,      # Tax amount 2
    cod_imp_3,      # Tax code 3 (ICA = '03')
    val_imp_3,      # Tax amount 3
    val_tot,        # Total amount
    nit_ofe,        # NIT of the issuer
    num_adq,        # Identification of the buyer
    pin_software,   # Software PIN (replaces cl_tec for CUDE)
    tipo_ambiente,  # Environment: '1' = Production, '2' = Test
):
    """Compute the CUDE (Codigo Unico de Documento Electronico).

    Used for credit notes, debit notes, and equivalent documents.
    Same algorithm as CUFE but uses the software PIN instead of the
    technical key (clave tecnica).

    :param num_doc: Document number
    :param fec_doc: Document datetime
    :param val_doc: Subtotal before taxes
    :param cod_imp_1: DIAN tax type code for IVA ('01')
    :param val_imp_1: IVA tax amount
    :param cod_imp_2: DIAN tax type code for INC ('04')
    :param val_imp_2: INC tax amount
    :param cod_imp_3: DIAN tax type code for ICA ('03')
    :param val_imp_3: ICA tax amount
    :param val_tot: Total amount including taxes
    :param nit_ofe: NIT of the issuer
    :param num_adq: Identification number of the buyer
    :param pin_software: DIAN software PIN (from company settings)
    :param tipo_ambiente: '1' for production, '2' for test
    :return: CUDE as a lowercase hex string (96 characters)
    """
    if isinstance(fec_doc, datetime):
        fec_doc_str = fec_doc.strftime('%Y-%m-%dT%H:%M:%S')
    else:
        fec_doc_str = str(fec_doc)

    val_doc_str = _format_amount(val_doc)
    val_imp_1_str = _format_amount(val_imp_1)
    val_imp_2_str = _format_amount(val_imp_2)
    val_imp_3_str = _format_amount(val_imp_3)
    val_tot_str = _format_amount(val_tot)

    cude_input = (
        str(num_doc)
        + fec_doc_str
        + val_doc_str
        + str(cod_imp_1)
        + val_imp_1_str
        + str(cod_imp_2)
        + val_imp_2_str
        + str(cod_imp_3)
        + val_imp_3_str
        + val_tot_str
        + str(nit_ofe)
        + str(num_adq)
        + str(pin_software)
        + str(tipo_ambiente)
    )

    return hashlib.sha384(cude_input.encode('utf-8')).hexdigest()


def _format_amount(value):
    """Format a numeric value to exactly 2 decimal places as required by DIAN.

    :param value: A numeric value (int, float, Decimal, or string)
    :return: String formatted to 2 decimal places (e.g., '1000.00')
    """
    return '%.2f' % float(value)
