import secrets
from lxml import etree
from flask import Flask, request, Response

app = Flask(__name__)

WS_ENDPOINT = '/seriesbo/SeriesWSService'

TNS = 'http://at.gov.pt/'


@app.route(WS_ENDPOINT, methods=['POST'])
def mock_at_webservice():
    xml_str = request.data.decode('utf-8')
    print("--- Received SOAP Request from Odoo ---")
    print(xml_str)
    print("---------------------------------------")

    # Extract serie/tipoDoc from the incoming request for a realistic echo
    root = etree.fromstring(xml_str.encode('utf-8'))
    serie = tipoDoc = ''
    for elem in root.iter():
        if elem.tag.endswith('}serie') and not serie:
            serie = elem.text or ''
        if elem.tag.endswith('}tipoDoc') and not tipoDoc:
            tipoDoc = elem.text or ''

    validation_code = secrets.token_hex(4).upper()

    mock_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:tns="{TNS}">
  <soap:Body>
    <tns:registarSerieResponse>
      <tns:registarSerieResp>
        <tns:infoSerie>
          <tns:serie>{serie}</tns:serie>
          <tns:tipoSerie>N</tns:tipoSerie>
          <tns:classeDoc>SI</tns:classeDoc>
          <tns:tipoDoc>{tipoDoc}</tns:tipoDoc>
          <tns:numInicialSeq>1</tns:numInicialSeq>
          <tns:dataInicioPrevUtiliz>2025-01-01</tns:dataInicioPrevUtiliz>
          <tns:meioProcessamento>PI</tns:meioProcessamento>
          <tns:numCertSWFatur>0</tns:numCertSWFatur>
          <tns:codValidacaoSerie>{validation_code}</tns:codValidacaoSerie>
          <tns:dataRegisto>2025-01-01</tns:dataRegisto>
          <tns:estado>V</tns:estado>
          <tns:nifComunicou>599999999</tns:nifComunicou>
        </tns:infoSerie>
        <tns:infoResultOper>
          <tns:codResultOper>2001</tns:codResultOper>
          <tns:msgResultOper>Sucesso</tns:msgResultOper>
        </tns:infoResultOper>
      </tns:registarSerieResp>
    </tns:registarSerieResponse>
  </soap:Body>
</soap:Envelope>"""

    print(f"--- Returning validation code: {validation_code} ---")
    return Response(mock_response, mimetype='text/xml')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7001)
