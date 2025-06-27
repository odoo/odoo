import csv
import io
from odoo import models, api


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


    @api.model
    def import_from_csv(self, csv_content, model):

        record = self.csv_to_json_array(csv_content)
        model = self.env[model.name]
        valid_fields = model._fields.keys()

        processed_records = []

        for row in record:
            clean_data = {
                key: value
                for key, value in row.items()
                if key in valid_fields
            }

            name = clean_data.get("name")
            if name:
                existing = model.search([("name", "=", name)], limit=1)
            if existing:
                existing.write(clean_data)
                processed_records.append(existing)
            else:
                new = model.create(clean_data)
                processed_records.append(new)
        else:
            print(f"no se encontró el valor name.")

        return processed_records

