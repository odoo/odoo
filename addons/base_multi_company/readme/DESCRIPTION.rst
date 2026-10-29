This module will provide a way to change the way Odoo manages a 'multi-company'
implementation.

Abstract
--------

Odoo traditional implementation of multi-company:

- Some models contain a field named Company (company_id) that allows to set one company or None
  in order to:
  - Limit access to that company if set.
  - not limiting access to any company if not set.

This module changes that in order to introduce a finer company access.
e.g.: If you want to give record access to company A and B but not for C.

This module is not doing anything by its own but provide a transversal implementation
for further ones.
e.g.: If you want to implement OCA multi-company behaviour for products, install
also the 'product_multi_company' or 'partner_multi_company' modules.
