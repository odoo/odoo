# Redsys

## Technical details

Redirection API: https://pagosonline.redsys.es/desarrolladores-inicio/documentacion-tipos-de-integracion/desarrolladores-redireccion/

Parameters and responses: https://pagosonline.redsys.es/desarrolladores-inicio/integrate-con-nosotros/parametros-de-entrada-y-salida/
Parameters (complete list): https://docs.google.com/spreadsheets/d/1KLWzD3ZI8om9DoO7K0dYKCUo5-udJtUyyauew1zDdY0/edit?gid=1023961697#gid=1023961697

This module integrates Redsys with cards and bizum payment methods.

## Supported features

- Payment with redirection flow

## Not implemented features

- [Payment with token](https://pagosonline.redsys.es/desarrolladores-inicio/documentacion-funcionalidades-avanzadas/tokenizacion/)
- [Manual capture](https://pagosonline.redsys.es/desarrolladores-inicio/documentacion-operativa/preautorizaciones-y-confirmaciones/)
- [Refund](https://pagosonline.redsys.es/desarrolladores-inicio/documentacion-operativa/devolver-o-anular-un-pago/)

## Module history

- `18.4`
  - Integration with redirection flow. odoo/odoo#205135

## Testing instructions

### VISA

**Card Number**: `4548810000000003`
**CVV**: `123`

Additional testing cards: [Testing Cards](https://pagosonline.redsys.es/desarrolladores-inicio/integrate-con-nosotros/tarjetas-y-entornos-de-prueba/)
