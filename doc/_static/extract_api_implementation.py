import base64
import time
import sys
import json
import requests

account_token = "integration_token"  # Use your token
domain_name = "https://iap-extract.odoo.com"
path_to_pdf = "/path/to/invoice_file"

API_VERSION = 120  # Do not change
SUCCESS = 0
NOT_READY = 1

def jsonrpc(path, params):
    payload = {
        'jsonrpc': '2.0',
        'method': 'call',
        'params': params,
        'id': 0,
    }
    req = requests.post(domain_name+path, json=payload, timeout=10)
    req.raise_for_status()
    resp = req.json()
    return resp


with open(path_to_pdf, "rb") as file:
    params = {
        'account_token': account_token,
        'version': API_VERSION,
        'documents': [base64.b64encode(file.read()).decode('ascii')],
    }

response = jsonrpc("/iap/invoice_extract/parse", params)
print("/parse call status: ", response['result']['status_msg'])

if response['result']['status_code'] != SUCCESS:
    sys.exit(1)

# You received an id that you can use to poll the server to get the result of the ocr when it will be ready
document_id = response['result']['document_id']
params = {
    'version': API_VERSION,
    'document_ids': [document_id],  # you can request the results of multiple documents at once if wanted
}

response = jsonrpc("/iap/invoice_extract/get_results", params)
document_id = str(document_id) # /get_results expects a string despite the fact that the returned document_id is a int

while response['result'][document_id]['status_code'] == NOT_READY:  # 1 is the status code indicating that the server is still processing the document
    print("Still processing... Retrying in 5 seconds")
    time.sleep(5)
    response = jsonrpc("/iap/invoice_extract/get_results", params)

with open('results.txt', 'w') as outfile:
    json.dump(response, outfile, indent=2)
print("\nResult saved in results.txt")

if response['result'][document_id]['status_code'] != SUCCESS:
    print(response['result'][document_id]['status_msg'])  # if it isn't a success, print the error message
    sys.exit(1)

document_results = response['result'][document_id]['results'][0]
print("\nTotal:", document_results['total']['selected_value']['content'])
print("Subtotal:", document_results['subtotal']['selected_value']['content'])
print("Invoice id:", document_results['invoice_id']['selected_value']['content'])
print("Date:", document_results['date']['selected_value']['content'])
print("...\n")

params = {
    'document_id': document_id,
    'values': {
        'total': {'content': 100.0},
        'subtotal': {'content': 100.0},
        'global_taxes': {'content': []},
        'global_taxes_amount': {'content': 0.0},
        'date': {'content': '2020-09-25'},
        'due_date': {'content': '2020-09-25'},
        'invoice_id': {'content': document_results['invoice_id']['selected_value']['content']},
        'partner': {'content': 'twinnta'},
        'VAT_Number': {'content': 'BE23252248420'},
        'currency': {'content': 'USD'},
        'merged_lines': False,
        'invoice_lines': {'lines': [{'description': 'Total TVA ',
                                        'quantity': 1.0,
                                        'unit_price': 100.0,
                                        'product': False,
                                        'taxes_amount': 0.0,
                                        'taxes': [],
                                        'subtotal': 100.0,
                                        'total': 100.0}]
                            }
    }
}
response = jsonrpc("/iap/invoice_extract/validate", params)
if response['result']['status_code'] == SUCCESS:
    print("/validate call status: Success")
else:
    print("/validate call status: wrong format")
