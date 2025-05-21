import csv
import io
from odoo import models


class CSVtoJsonHelper(models.AbstractModel):
    _name = "csv.to.json"
    _description = "transforms csv to jsons array"

    # le pasas un csv y te da una lista de jsons. La primera fila son las keys

    def csv_to_json_array(self, csv_content):
        if isinstance(csv_content, bytes):
            csv_content = csv_content.decode('utf-8')
        f = io.StringIO(csv_content)
        reader = csv.DictReader(f)
        return list(reader)
    
    # var = csv_to_json_array('a,b\n1,2\n3,4')
    # print(var)
    # [{'a': '1', 'b': '2'}, {'a': '3', 'b': '4'}]
    # for item on var:
    #   loquehagasparasubirloaladb/actualizarla(item)