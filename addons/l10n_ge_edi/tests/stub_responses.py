"""Builders for the SOAP replies RS.ge sends, one per `ntosservice.asmx` operation.

Element names and their order come from `test_files/ntosservice.wsdl`, which `zeep` validates the
reply against, so a renamed, reordered or missing mandatory field fails the test instead of
passing silently. Every field is a parameter, so one builder covers both the happy answer and the
rejection RS.ge sends through the same shape.
"""

_INVOICE_DESC_SCHEMA = """        <xsd:schema xmlns="" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:msdata="urn:schemas-microsoft-com:xml-msdata" xmlns:msprop="urn:schemas-microsoft-com:xml-msprop" id="NewDataSet">
          <xsd:element name="NewDataSet" msdata:IsDataSet="true" msdata:MainDataTable="invoices_descs" msdata:UseCurrentLocale="true">
            <xsd:complexType>
              <xsd:choice minOccurs="0" maxOccurs="unbounded">
                <xsd:element name="invoices_descs" msprop:REFCursorName="REFCursor">
                  <xsd:complexType>
                    <xsd:sequence>
                      <xsd:element name="ID" type="xsd:decimal" minOccurs="0"/>
                      <xsd:element name="INV_ID" type="xsd:decimal" minOccurs="0"/>
                      <xsd:element name="GOODS" type="xsd:string" minOccurs="0"/>
                      <xsd:element name="G_UNIT" type="xsd:string" minOccurs="0"/>
                      <xsd:element name="G_NUMBER" type="xsd:decimal" minOccurs="0"/>
                      <xsd:element name="FULL_AMOUNT" type="xsd:decimal" minOccurs="0"/>
                      <xsd:element name="DRG_AMOUNT" type="xsd:decimal" minOccurs="0"/>
                      <xsd:element name="VAT_TYPE" type="xsd:decimal" minOccurs="0"/>
                    </xsd:sequence>
                  </xsd:complexType>
                </xsd:element>
              </xsd:choice>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
"""

RSGE_NAMESPACE = "http://tempuri.org/"
SOAP_NAMESPACE = "http://schemas.xmlsoap.org/soap/envelope/"


def chek(result=True, user_id=783, sua=0):
    return _envelope("chek", chekResult=result, user_id=user_id, sua=sua)


def get_un_id_from_tin(un_id=1149251, name="GE Customer"):
    return _envelope("get_un_id_from_tin", get_un_id_from_tinResult=un_id, name=name)


def save_invoice(invois_id=700123, result=True):
    return _envelope("save_invoice", save_invoiceResult=result, invois_id=invois_id)


def save_invoice_desc(id=800001, result=True):
    return _envelope("save_invoice_desc", save_invoice_descResult=result, id=id)


def k_invoice(k_id=700900, result=True):
    return _envelope("k_invoice", k_invoiceResult=result, k_id=k_id)


def delete_invoice_desc(result=True):
    return _envelope("delete_invoice_desc", delete_invoice_descResult=result)


def change_invoice_status(result=True):
    return _envelope("change_invoice_status", change_invoice_statusResult=result)


def get_invoice(status=2, f_series="AA", f_number="12345", reg_dt="2026-01-15T10:30:00", k_id=-1, k_type=-1, result=True):
    return _envelope(
        "get_invoice",
        get_invoiceResult=result,
        f_series=f_series,
        f_number=f_number,
        operation_dt="2026-01-15T00:00:00",
        reg_dt=reg_dt,
        seller_un_id=731937,
        buyer_un_id=1149251,
        overhead_no="",
        overhead_dt="0001-01-01T00:00:00",
        status=status,
        seq_num_s="",
        seq_num_b="",
        k_id=k_id,
        r_un_id=0,
        k_type=k_type,
        b_s_user_id=0,
        dec_status=0,
    )


def get_invoice_desc(*rows):
    """The ADO.NET diffgram RS.ge answers its list calls with, one dict of wire columns per row.

    `zeep` cannot deserialise this shape, which is the normal outcome the client relies on: it
    parses the rows out of the raw envelope instead. An empty result carries no diffgram at all.
    """
    body = "".join(
        f'            <invoices_descs diffgr:id="invoices_descs{index}" msdata:rowOrder="{index - 1}">\n'
        + "".join(
            f"              <{name}>{value}</{name}>\n" for name, value in row.items()
        )
        + "            </invoices_descs>\n"
        for index, row in enumerate(rows, start=1)
    )
    diffgram = (
        (
            '        <diffgr:diffgram xmlns:msdata="urn:schemas-microsoft-com:xml-msdata"'
            ' xmlns:diffgr="urn:schemas-microsoft-com:xml-diffgram-v1">\n'
            '          <DocumentElement xmlns="">\n'
            f"{body}"
            "          </DocumentElement>\n"
            "        </diffgr:diffgram>\n"
        )
        if rows
        else ""
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<soap:Envelope xmlns:soap="{SOAP_NAMESPACE}">\n'
        "  <soap:Body>\n"
        f'    <get_invoice_descResponse xmlns="{RSGE_NAMESPACE}">\n'
        "      <get_invoice_descResult>\n"
        f"{_INVOICE_DESC_SCHEMA}"
        f"{diffgram}"
        "      </get_invoice_descResult>\n"
        "    </get_invoice_descResponse>\n"
        "  </soap:Body>\n"
        "</soap:Envelope>"
    )


def fault(code="soap:Server", string="Server was unable to process request."):
    """The SOAP fault RS.ge returns for a server-side error, which `zeep` raises as a `Fault`."""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<soap:Envelope xmlns:soap="{SOAP_NAMESPACE}">\n'
        "  <soap:Body>\n"
        "    <soap:Fault>\n"
        f"      <faultcode>{code}</faultcode>\n"
        f"      <faultstring>{string}</faultstring>\n"
        "      <detail/>\n"
        "    </soap:Fault>\n"
        "  </soap:Body>\n"
        "</soap:Envelope>"
    )


def _envelope(operation, **fields):
    """Wrap `fields`, in declaration order, in the envelope RS.ge answers `operation` with."""
    body = "".join(f"      <{name}>{_xml_value(value)}</{name}>\n" for name, value in fields.items() if value is not None)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<soap:Envelope xmlns:soap="{SOAP_NAMESPACE}">\n'
        "  <soap:Body>\n"
        f'    <{operation}Response xmlns="{RSGE_NAMESPACE}">\n'
        f"{body}"
        f"    </{operation}Response>\n"
        "  </soap:Body>\n"
        "</soap:Envelope>"
    )


def _xml_value(value):
    return str(value).lower() if isinstance(value, bool) else str(value)
