import csv
import io
import re
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
    def import_from_csv(self, csv_content, target_model_obj):
        """
        Importa datos de un contenido CSV a un modelo de Odoo, con lógica específica para res.partner.
        Mapea 'company' o 'individual' al campo 'name' de Odoo y establece 'is_company'.
        Asigna directamente los IDs numéricos para 'state_id' y 'country_id' del CSV.
        Limpia y asegura que los campos numéricos como 'mobile' y 'cuit' se traten como cadenas.
        Maneja errores por fila y reporta un resumen al final.

        :param csv_content: Contenido del CSV como string o bytes.
        :param target_model_obj: El objeto del modelo de Odoo (ej. env['res.partner']).
        """
        records_from_csv = self.csv_to_json_array(csv_content)
        
        valid_fields = target_model_obj._fields.keys()

        processed_records = []
        failed_imports = [] # Lista para almacenar los registros que fallaron

        for row_idx, row in enumerate(records_from_csv):
            partner_data = {}
            current_partner_name = 'N/A' # Para usar en mensajes de error si el nombre aún no se ha determinado

            try: # Bloque try-except para procesar cada fila individualmente
                for key, value in row.items():
                    cleaned_value = str(value).strip() if value is not None else ''
                    
                    # Campos que deben ser cadenas (Char) en Odoo, incluso si contienen solo dígitos
                    if key in ['mobile', 'cuit', 'zip', 'floor', 'apartment', 
                               'delivery_zip', 'delivery_floor', 'delivery_apartment']:
                        # Eliminar todos los caracteres no numéricos.
                        cleaned_value = re.sub(r'[^\d]', '', cleaned_value) 
                        
                        # Mapear 'cuit' a 'vat' si 'vat' es un campo válido en el modelo de Odoo
                        if key == 'cuit' and 'vat' in valid_fields:
                            partner_data['vat'] = cleaned_value
                        elif key in valid_fields: # Para otros campos como mobile, zip, etc.
                            partner_data[key] = cleaned_value
                    
                    # Lógica de mapeo específica para res.partner
                    elif key == 'company':
                        partner_data['name'] = cleaned_value
                        partner_data['is_company'] = True
                    elif key == 'individual':
                        if not partner_data.get('name'): # Si 'name' no ha sido establecido por 'company'
                            partner_data['name'] = cleaned_value
                            partner_data['is_company'] = False
                        if 'function' in valid_fields: # 'individual' puede ser la función si ya hay 'company'
                            partner_data['function'] = cleaned_value 
                    
                    # Campos que son Many2one y esperan un ID numérico
                    elif key in ['state_id', 'country_id']:
                        try:
                            # Intentar convertir a entero. Si es una cadena vacía, será False.
                            partner_data[key] = int(cleaned_value) if cleaned_value else False
                        except ValueError:
                            print(f"Advertencia (Fila {row_idx+1}, Campo '{key}'): El valor '{cleaned_value}' no es un ID numérico válido. Ignorando.")
                            partner_data[key] = False # Asignar False si la conversión falla
                    
                    # Otros campos que existen en el modelo de Odoo y no requieren un tratamiento especial
                    elif key in valid_fields:
                        partner_data[key] = cleaned_value

                # Ajustar 'name' e 'is_company' si solo se proporcionó 'individual' o si 'company' estaba vacío
                if not partner_data.get('name'):
                    if row.get('company'):
                        partner_data['name'] = str(row['company']).strip()
                        partner_data['is_company'] = True
                    elif row.get('individual'):
                        partner_data['name'] = str(row['individual']).strip()
                        partner_data['is_company'] = False

                current_partner_name = partner_data.get('name', 'N/A')

                # Si después de todo, el nombre principal sigue vacío, saltar la fila
                if not partner_data.get('name'):
                    raise ValueError(f"Falta el campo 'company' o 'individual' válido para el nombre. Fila: {row}")

                # Manejar campos de dirección de entrega (delivery_street, delivery_city, etc.)
                delivery_address_data = {}
                delivery_fields_mapping = {
                    'delivery_street': 'street',
                    'delivery_floor': 'floor',
                    'delivery_apartment': 'apartment',
                    'delivery_zip': 'zip',
                    'delivery_city': 'city',
                    'delivery_state_id': 'state_id',
                    'delivery_country_id': 'country_id',
                }

                has_delivery_data = False
                for csv_key, odoo_field in delivery_fields_mapping.items():
                    if row.get(csv_key) is not None: 
                        cleaned_value = str(row[csv_key]).strip()
                        if cleaned_value:
                            # Limpieza para campos numéricos en dirección de entrega (tratados como cadenas)
                            if odoo_field in ['zip', 'floor', 'apartment']:
                                cleaned_value = re.sub(r'[^\d]', '', cleaned_value)
                                delivery_address_data[odoo_field] = cleaned_value
                            
                            # Asignación directa de IDs para state_id y country_id en la dirección de entrega
                            elif odoo_field in ['state_id', 'country_id']:
                                try:
                                    delivery_address_data[odoo_field] = int(cleaned_value) if cleaned_value else False
                                except ValueError:
                                    print(f"Advertencia (Fila {row_idx+1}, Campo de entrega '{csv_key}'): El valor '{cleaned_value}' no es un ID numérico válido. Ignorando.")
                                    delivery_address_data[odoo_field] = False
                            else:
                                delivery_address_data[odoo_field] = cleaned_value
                            has_delivery_data = True

                if has_delivery_data:
                    delivery_name = f"{partner_data['name']} (Delivery)"
                    delivery_address_data['name'] = delivery_name
                    delivery_address_data['type'] = 'delivery' 
                    delivery_address_data['parent_id'] = False 

                    existing_delivery = self.env['res.partner'].search([('name', '=', delivery_name), ('type', '=', 'delivery')], limit=1)
                    if existing_delivery:
                        existing_delivery.write(delivery_address_data)
                        delivery_partner = existing_delivery
                        print(f"Dirección de entrega actualizada: {delivery_name}")
                    else:
                        delivery_partner = self.env['res.partner'].create(delivery_address_data)
                        print(f"Nueva dirección de entrega creada: {delivery_name}")
                    
                    partner_data['child_ids'] = [(4, delivery_partner.id)]


                # Buscar o crear el registro principal (company o individual)
                partner_name_for_search = partner_data['name']
                
                existing_partner = target_model_obj.search([("name", "=", partner_name_for_search)], limit=1)
                
                if existing_partner:
                    existing_partner.write(partner_data)
                    processed_records.append(existing_partner)
                    print(f"Registro principal actualizado: {partner_name_for_search}")
                else:
                    new_partner = target_model_obj.create(partner_data)
                    processed_records.append(new_partner)
                    print(f"Nuevo registro principal creado: {partner_name_for_search}")

            except Exception as e:
                # Captura cualquier error durante el procesamiento de la fila
                failed_imports.append({
                    'row_index': row_idx + 1,
                    'partner_name': current_partner_name,
                    'error': str(e),
                    'row_data': row # Incluir los datos brutos de la fila para depuración
                })
                print(f"ERROR general en la fila {row_idx+1} para '{current_partner_name}': {e}")
                print(f"Datos de la fila que causaron el fallo: {row}")
                continue # Continúa con la siguiente fila

        # Resumen final de importaciones
        if failed_imports:
            print("\n--- RESUMEN DE IMPORTACIONES FALLIDAS ---")
            for failure in failed_imports:
                print(f"Fila {failure['row_index']}: '{failure['partner_name']}' - Error: {failure['error']}")
                # print(f"  Datos de la fila: {failure['row_data']}") # Descomentar para depuración profunda
            print("----------------------------------------")
        else:
            print("\nTodos los registros se importaron/actualizaron correctamente.")

        return processed_records