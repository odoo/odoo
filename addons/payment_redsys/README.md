# Redsys

## Technical details

API: [Redirection API](https://pagosonline.redsys.es/desarrolladores-inicio/documentacion-tipos-de-integracion/desarrolladores-redireccion/)

This module integrates Redsys using the generic payment with redirection flow based on form
submission provided by the `payment` module.

## Supported features

- Payment with redirection flow
- Webhook notifications
- [Tokenization](https://pagosonline.redsys.es/desarrolladores-inicio/documentacion-funcionalidades-avanzadas/tokenizacion/)

## Not implemented features

- [Manual capture](https://pagosonline.redsys.es/desarrolladores-inicio/documentacion-operativa/preautorizaciones-y-confirmaciones/)
- [Refunds](https://pagosonline.redsys.es/desarrolladores-inicio/documentacion-operativa/devolver-o-anular-un-pago/)

## Module history

- `saas-19.3`
  - Support for tokenization is added. odoo/odoo#253606.
- `19.0`
  - Integration with the Redirection API. odoo/odoo#205135.

## Testing instructions

[All testing cards](https://pagosonline.redsys.es/desarrolladores-inicio/integrate-con-nosotros/tarjetas-y-entornos-de-prueba/)

### VISA

**Card Number**: `4548810000000003`
**Expiry Date**: any future date
**CVV**: `123`
