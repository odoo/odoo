# Ajuste de cantidad antes de facturar — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dejar constancia ejecutable (tests) de que un pedido ya confirmado se puede corregir línea por línea (siguiendo la hoja de papel) y facturar exactamente esa cantidad corregida, sin depender de validar ninguna entrega.

**Architecture:** No se agrega código de producción. Se verificó en `odoo shell` que un producto tipo "Goods" (`consu`) ya obtiene `invoice_policy = 'order'` de forma nativa (cómputo `product.template._compute_invoice_policy()` en `addons/sale/models/product_template.py:163-164`), y que una orden de venta confirmada no queda bloqueada (`sale.order.locked = False` por defecto), por lo que la línea sigue siendo editable. Este plan solo agrega un archivo de tests al addon `distribuidora_ventas` que prueba ambos hechos end-to-end.

**Tech Stack:** Odoo 19 (Python 3.10-3.14), `odoo.tests.common.TransactionCase`.

## Global Constraints

- Python 3.10–3.14 (según `CLAUDE.md` del repo).
- Imports ordenados: future → stdlib → third-party → odoo → odoo.addons (lo aplica `ruff`).
- Los tests van en `addons/distribuidora_ventas/tests/`, siguiendo la convención ya establecida en ese addon: `TransactionCase`, `@tagged('post_install', '-at_install')`.
- No se agrega ningún campo, vista, ni override de modelo — el spec (`docs/superpowers/specs/2026-07-14-ajuste-cantidad-antes-de-facturar-design.md`) determinó que el comportamiento ya es 100% nativo de Odoo; solo hace falta protegerlo con un test.
- Fuera de alcance (confirmado en el spec): conservar la cantidad originalmente pedida, marca de "revisado" por línea, cualquier bloqueo de facturación.

---

## Task 1: Test de facturación por cantidad corregida

**Files:**
- Create: `addons/distribuidora_ventas/tests/test_invoice_from_order_quantity.py`
- Modify: `addons/distribuidora_ventas/tests/__init__.py`

**Interfaces:**
- Consumes: ninguno de tasks anteriores del addon — usa directamente `product.template` (campo nativo `invoice_policy`), `sale.order`, `sale.order.line` y `sale.order._create_invoices()`, todos nativos de Odoo `sale`.
- Produces: prueba de regresión que documenta y protege el comportamiento central del spec §3 — que corregir `sale.order.line.product_uom_qty` en un pedido ya confirmado y facturar produce una factura con esa cantidad corregida, no la original.

Esta task no agrega código de producción. El comportamiento ya lo resuelve Odoo nativamente: (a) un producto nuevo sin `invoice_policy` explícito obtiene `'order'` porque su `type` por defecto es `'consu'` (verificado con `odoo shell`, ver evidencia abajo), y (b) una orden confirmada no queda bloqueada, así que su línea sigue siendo editable. El test deja constancia ejecutable de ambos hechos y del flujo completo de facturación.

**Evidencia de que el default nativo ya es `'order'`** (comando ejecutado contra este mismo contenedor, para que quien implemente pueda repetirlo si quiere verificarlo de nuevo):

```bash
MSYS_NO_PATHCONV=1 docker exec -i erp-odoo-1 odoo shell -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8098 --gevent-port=8102 --no-http <<'EOF'
p = env['product.template'].create({'name': 'Test Papa Nueva'})
print("RESULT invoice_policy=", p.invoice_policy, "type=", p.type)
env.cr.rollback()
EOF
```

Salida obtenida: `RESULT invoice_policy= order type= consu`.

- [ ] **Step 1: Escribir el test**

```python
# addons/distribuidora_ventas/tests/test_invoice_from_order_quantity.py
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestInvoiceFromOrderQuantity(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product = self.env['product.product'].create({
            'name': 'Papa',
            'list_price': 500.0,
        })
        self.partner = self.env['res.partner'].create({'name': 'Cliente Test'})

    def test_new_consu_product_defaults_to_order_invoice_policy(self):
        self.assertEqual(self.product.type, 'consu')
        self.assertEqual(self.product.invoice_policy, 'order')

    def test_invoice_uses_corrected_line_quantity_not_original(self):
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'product_uom_qty': 5,
        })
        order.action_confirm()
        self.assertFalse(order.locked)

        # El colaborador corrige la cantidad siguiendo la hoja de papel:
        # se pidieron 5 kg, solo se pudieron entregar 3 kg.
        line.product_uom_qty = 3

        invoices = order._create_invoices()
        invoice_line = invoices.invoice_line_ids.filtered(lambda l: l.product_id == self.product)
        self.assertEqual(invoice_line.quantity, 3)
```

```python
# addons/distribuidora_ventas/tests/__init__.py
from . import test_partner_categories
from . import test_sale_order_delivery_day
from . import test_customer_pricelist
from . import test_invoice_from_order_quantity
```

(El archivo `tests/__init__.py` ya existe con las primeras tres líneas de import; agregar solo la última.)

- [ ] **Step 2: Correr los tests y confirmar que pasan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_ventas --test-enable --test-tags /distribuidora_ventas --stop-after-init`

Expected: `0 failed, 0 error(s) of 11 tests` (9 tests ya existentes del addon + 2 nuevos). Si `test_invoice_uses_corrected_line_quantity_not_original` falla porque no encuentra `invoice_line_ids` con ese producto, confirmar que `order.action_confirm()` corrió sin error y que `_create_invoices()` no devolvió un recordset vacío — en ese caso, detenerse y reportar en vez de forzar código de producción nuevo (esta task no debe agregar ningún override; si el comportamiento nativo no se comporta como se documentó arriba, es una señal de que hay que revisar el supuesto, no de escribir código).

- [ ] **Step 3: Commit**

```bash
git add addons/distribuidora_ventas/tests/test_invoice_from_order_quantity.py addons/distribuidora_ventas/tests/__init__.py
git commit -m "test(distribuidora_ventas): validar facturacion por cantidad corregida antes de facturar"
```

---

## Task 2: Verificación manual end-to-end

**Files:** ninguno (verificación manual, sin cambios de código).

**Interfaces:**
- Consumes: addon `distribuidora_ventas` con el test de Task 1, instalado en la base local.

- [ ] **Step 1: Actualizar el módulo en la base local**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_ventas --stop-after-init`

- [ ] **Step 2: Confirmar un pedido de prueba y corregir una cantidad**

En la UI (`http://localhost:8069`): abrir un pedido de venta ya confirmado (o confirmar uno nuevo con un producto y cantidad, ej. 5), editar la cantidad de una línea a un valor menor (ej. 3) directamente sobre el pedido confirmado — confirmar que Odoo lo permite sin pedir desbloquear nada.

- [ ] **Step 3: Facturar y confirmar la cantidad correcta**

Click en "Crear factura" desde el pedido → confirmar que la factura generada muestra la cantidad corregida (3), no la original (5), y que no pidió validar ninguna entrega antes de dejar facturar.
