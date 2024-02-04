When searching for records on same field Odoo joins multiple queries with OR.
For example:

* Perform a search for customer "John" on field Name
* Odoo displays customers containing "John"
* Search for "Smith" on same field Name
* Odoo displays customers containing "John" OR "Smith"

With this module installed you can press Shift key before searching for "Smith"
and Odoo finds customers containing "John" AND "Smith"
