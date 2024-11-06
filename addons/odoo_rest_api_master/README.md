# Odoo REST API
This is a module which expose Odoo as a REST API 


## Installing
* Download this module and put it to your Odoo addons directory
* Install requirements with `pip install -r requirements.txt`

## Getting Started

### Authenticating users
Before making any request make sure you are authenticated. The route which is used to authenticate users is `/auth/`. Below is an example showing how to authenticate users.
```py
import json
import requests
import sys

AUTH_URL = 'http://localhost:8069/auth/'

headers = {'Content-type': 'application/json'}


# Remember to configure default db on odoo configuration file(dbfilter = ^db_name$)
# Authentication credentials
data = {
    'params': {
         'login': 'your@email.com',
         'password': 'yor_password',
         'db': 'your_db_name'
    }
}

# Authenticate user
res = requests.post(
    AUTH_URL, 
    data=json.dumps(data), 
    headers=headers
)

# Get response cookies
# This hold information for authenticated user
cookies = res.cookies


# Example 1
# Get users
USERS_URL = 'http://localhost:8069/api/res.users/'

# This will take time since it retrives all res.users fields
# You can use query param to fetch specific fields

res = requests.get(
    USERS_URL, 
    cookies=cookies  # Here we are sending cookies which holds info for authenticated user
)

# This will be a very long response since it has many data
print(res.text)


# Example 2
# Get products(assuming you have products in you db)
# Here am using query param to fetch only product id and name(This will be faster)
USERS_URL = 'http://localhost:8069/api/product.product/'

# Use query param to fetch only id and name
params = {'query': '{id, name}'}

res = requests.get(
    USERS_URL, 
    params=params,
    cookies=cookies  # Here we are sending cookies which holds info for authenticated user
)

# This will be small since we've retrieved only id and name
print(res.text)
```


## Allowed HTTP methods 

## 1. GET

### Model records: 

`GET /api/{model}/`
#### Parameters 
* **query (optional):**

   This parameter is used to dynamically select fields to include on a response. For example if we want to select `id` and `name` fields from `res.users` model here is how we would do it.

   `GET /api/res.users/?query={id, name}`

   ```js
   {
       "count": 2, 
       "prev": null, 
       "current": 1, 
       "next": null, 
       "total_pages": 1, 
       "result": [
           {
               "id": 2, 
               "name": "Administrator"
            }, 
           {
               "id": 6, 
               "name": "Sailors Co Ltd"
            }
        ]
    }
   ```
   
   For nested records, for example if we want to select `id`, `name` and `company_id` fields from `res.users` model, but under `company_id` we want to select `name` field only. here is how we would do it.

   `GET /api/res.users/?query={id, name, company_id{name}}`

   ```js
   {
       "count": 2, 
       "prev": null, 
       "current": 1, 
       "next": null, 
       "total_pages": 1, 
       "result": [
           {
               "id": 2, 
               "name": "Administrator",
               "company_id": {
                   "name": "Singo Africa"
               }
            }, 
           {
               "id": 6, 
               "name": "Sailors Co Ltd",
               "company_id": {
                   "name": "Singo Africa"
               }
            }
        ]
    }
   ```

   For nested iterable records, for example if we want to select `id`, `name` and `related_products` fields from `product.template` model, but under `related_products` we want to select `name` field only. here is how we would do it.

   `GET /api/product.template/?query={id, name, related_products{name}}`

   ```js
   {
       "count": 2, 
       "prev": null, 
       "current": 1, 
       "next": null, 
       "total_pages": 1, 
       "result": [
           {
               "id": 16, 
               "name": "Alaf Resincot Steel Roof-16", 
               "related_products": [
                   {"name": "Alloy Steel AISI 4140 Bright Bars - All 5.8 meter longs"}, 
                   {"name": "Test product"}
                ]
            }, 
            {
                "id": 18,
                 "name": "Alaf Resincot Steel Roof-43", 
                 "related_products": [
                     {"name": "Alloy Steel AISI 4140 Bright Bars - All 5.8 meter longs"}, 
                     {"name": "Aluminium Sheets & Plates"}, 
                     {"name": "Test product"}
                 ]
            }
        ]
   }
   ```

   If you want to fetch all fields except few you can use exclude(-) operator. For example in the case above if we want to fetch all fields except `name` field, here is how we could do it   
   `GET /api/product.template/?query={-name}`
   
   ```js
   {
        "count": 3, 
        "prev": null, 
        "current": 1, 
        "next": null, 
        "total_pages": 1, 
        "result": [
            {   
                "id": 1,
                ... // All fields except name
            }, 
            {
                "id": 2
                ... // All fields except name
            }
            ...
        ]
   }
   ```

   There is also a wildcard(\*) operator which can be used to fetch all fields, Below is an example which shows how you can fetch all product's fields but under `related_products` field get all fields except `id`.

   `GET /api/product.template/?query={*, related_products{-id}}`

   ```js
   {
        "count": 3, 
        "prev": null, 
        "current": 1, 
        "next": null, 
        "total_pages": 1, 
        "result": [
            {   
                "id": 1,
                "name": "Pen",
                "related_products"{
                    "name": "Pencil",
                    ... // All fields except id
                }
                ... // All fields
            }, 
            ...
        ]
   }
   ```

   **If you don't specify query parameter all fields will be returned.**


* **filter (optional):**

    This is used to filter out data returned. For example if we want to get all products with id ranging from 60 to 70, here's how we would do it.

    `GET /api/product.template/?query={id, name}&filter=[["id", ">", 60], ["id", "<", 70]]`

    ```js
    {
        "count": 3, 
        "prev": null, 
        "current": 1, 
        "next": null, 
        "total_pages": 1, 
        "result": [
            {
                "id": 67, 
                "name": "Crown Paints Economy Superplus Emulsion"
            }, 
            {
                "id": 69,
                "name": "Crown Paints Permacote"
            }
        ]
    }
    ```

* **page_size (optional) & page (optional):**

    These two allows us to do pagination. Hre page_size is used to specify number of records on a single page and page is used to specify the current page. For example if we want our page_size to be 5 records and we want to fetch data on page 3 here is how we would do it.

    `GET /api/product.template/?query={id, name}&page_size=5&page=3`

    ```js
    {
        "count": 5, 
        "prev": 2, 
        "current": 3, 
        "next": 4, 
        "total_pages": 15, 
        "result": [
            {"id": 141, "name": "Borewell Slotting Pipes"}, 
            {"id": 114, "name": "Bright Bars"}, 
            {"id": 128, "name": "Chain Link Fence"}, 
            {"id": 111, "name": "Cold Rolled Sheets - CRCA & GI Sheets"}, 
            {"id": 62, "name": "Crown Paints Acrylic Primer/Sealer Undercoat"}
        ]
    }
    ```

    Note: `prev`, `current`, `next` and `total_pages` shows the previous page, current page, next page and the total number of pages respectively.

* **limit (optional):**

    This is used to limit the number of results returned on a request regardless of pagination. For example
    
    `GET /api/product.template/?query={id, name}&limit=3`

    ```js
    {
        "count": 3, 
        "prev": null, 
        "current": 1, 
        "next": null, 
        "total_pages": 1, 
        "result": [
            {"id": 16, "name": "Alaf Resincot Steel Roof-16"}, 
            {"id": 18, "name": "Alaf Resincot Steel Roof-43"}, 
            {"id": 95, "name": "Alaf versatile steel roof"}
        ]
    }
    ```

### Model record:  

`GET /api/{model}/{id}`
#### Parameters
* **query (optional):**

    Here query parameter works exactly the same as explained before except it selects fields on a single record. For example

    `GET /api/product.template/95/?query={id, name}`

    ```js
    {
        "id": 95, 
        "name": "Alaf versatile steel roof"
    }
    ```


## 2. POST

`POST /api/{model}/`
#### Headers
* Content-Type: application/json
#### Parameters 
* **data (mandatory):**

    This is used to pass data to be posted. For example
    
    `POST /api/product.public.category/`

    Request Body

    ```js
    {
        "params": {
            "data": {
                "name": "Test category_2"
            }
        }
    }
    ```

    Response

    ```js
    {
        "jsonrpc": "2.0",
        "id": null,
        "result": 398
    }
    ```

    The number on `result` is the `id` of the newly created record.

* **context (optional):**

    This is used to pass any context if it's needed when creating new record. The format of passing it is

    Request Body

    ```js
    {
        "params": {
            "context": {
                "context_1": "context_1_value",
                "context_2": "context_2_value",
                ....
            },
            "data": {
                "field_1": "field_1_value",
                "field_2": "field_2_value",
                ....
            }
        }
    }
    ```

## 3. PUT

### Model records: 

`PUT /api/{model}/`
#### Headers
* Content-Type: application/json
#### Parameters
* **data (mandatory):**

    This is used to pass data to update, it works with filter parameter, See example below

* **filter (mandatory):**

    This is used to filter data to update. For example

    `PUT /api/product.template/`

    Request Body

    ```js
    {
        "params": {
            "filter": [["id", "=", 95]],
            "data": {
                "name": "Test product"
            }
        }
    }
    ```

    Response

    ```js
    {
        "jsonrpc": "2.0",
        "id": null,
        "result": true
    }
    ```

    Note: If the result is true it means success and if false or otherwise it means there was an error during update.

* **context (optional):**
    Just like in GET context is used to pass any context associated with record update. The format of passing it is

    Request Body

    ```js
    {
        "params": {
            "context": {
                "context_1": "context_1_value",
                "context_2": "context_2_value",
                ....
            },
            "filter": [["id", "=", 95]],
            "data": {
                "field_1": "field_1_value",
                "field_2": "field_2_value",
                ....
            }
        }
    }
    ```

* **operation (optional)**:

    This is only applied to `one2many` and `many2many` fields. The concept is sometimes you might not want to replace all records on either `one2many` or `many2many` fields, instead you might want to add other records or remove some records, this is where put operations comes in place. Thre are basically three PUT operations which are push, pop and delete. 
    * push is used to add/append other records to existing linked records
    * pop is used to remove/unlink some records from the record being updated but it doesn't delete them on the system
    * delete is used to remove/unlink and delete records permanently on the system

    For example here is how you would update `related_product_ids` which is `many2many` field with PUT operations

    `PUT /api/product.template/`

    Request Body

    ```js
    {
        "params": {
            "filter": [["id", "=", 95]],
            "data": {
                "related_product_ids": {
                    "push": [102, 30],
                    "pop": [45],
                    "delete": [55]
                }
            }
        }
    }
    ```

    This will append product with ids 102 and 30 as related products to product with id 95 and from there unlink product with id 45 and again unlink product with id 55 and delete it from the system. So if befor this request product with id 95 had [20, 37, 45, 55] as related product ids, after this request it will be [20, 37, 102, 30].

    Note: You can use one operation or two or all three at a time depending on what you want to update on your field. If you dont use these operations on `one2many` and `many2many` fields, existing values will be replaced by new values passed, so you need to be very carefull on this part.

    Response:

    ```js
    {
        "jsonrpc": "2.0",
        "id": null,
        "result": true
    }
    ```

### Model record: 

`PUT /api/{model}/{id}`
#### Headers
* Content-Type: application/json
#### Parameters
* data (mandatory)
* context (optional)
* PUT operation(push, pop, delete) (optional)

All parameters works the same as explained on previous section, what changes is that here they apply to a single record being updated and we don't have filter parameter because `id` of record to be updated is passed on URL as `{id}`. Example to give us an idea of how this works.

`PUT /api/product.template/95/`

Request Body

```js
{
    "params": {
        "data": {
            "related_product_ids": {
                "push": [102, 30],
                "pop": [45],
                "delete": [55]
            }
        }
    }
}
```

## 4. DELETE

### Model records: 

`DELETE /api/{model}/`
#### Parameters
* **filter (mandatory):**

    This is used to filter data to delete. For example

    `DELETE /api/product.template/?filter=[["id", "=", 95]]`

    Response

    ```js
    {
        "result": true
    }
    ```
    
    Note: If the result is true it means success and if false or otherwise it means there was an error during deletion.


### Model records: 

`DELETE /api/{model}/{id}`
#### Parameters
This takes no parameter and we don't have filter parameter because `id` of record to be deleted is passed on URL as `{id}`. Example to give us an idea of how this works.

`DELETE /api/product.template/95/`

Response

```js
{
    "result": true
}
```

## Calling Model's Function

Sometimes you might need to call model's function or a function bound to a record, inorder to do so, send a `POST` request with a body containing arguments(args) and keyword arguments(kwargs) required by the function you want to call.

Below is how you can call model's function

`POST /object/{model}/{function name}`

Request Body

```js
{
    "params": {
	"args": [arg1, arg2, ..],
	"kwargs ": {
	    "key1": "value1",
	    "key2": "value2",
	    ...
	}
    }
}
```

And below is how you can call a function bound to a record

`POST /object/{model}/{record_id}/{function name}`

Request Body

```js
{
    "params": {
	"args": [arg1, arg2, ..],
	"kwargs ": {
	    "key1": "value1",
	    "key2": "value2",
	    ...
	}
    }
}
```

In both cases the response will be the result returned by the function called
