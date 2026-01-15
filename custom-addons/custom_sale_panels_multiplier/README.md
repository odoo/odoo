# Custom Sale Panels Multiplier

## Description
Odoo 19.0 Community module to add "Number of Panels" field in Sales Order Lines with impact on financial calculations.

## Features
- ✅ Add "Number of Panels" field before quantity field
- ✅ Multiply number of panels × quantity in all financial calculations
- ✅ Impact on price, taxes, and total
- ✅ Impact on invoices and deliveries
- ✅ 100% safe - does not affect old data

## Installation

### 1. Copy the Module
Make sure the module is located in `custom-addons/custom_sale_panels_multiplier`

### 2. Update Apps List
```
Apps → Update Apps List
```

### 3. Install the Module
```
Apps → Search: "Custom Sale Panels Multiplier" → Install
```

### 4. Upgrade (if already installed)
```bash
python odoo-bin -u custom_sale_panels_multiplier -d your_database
```

## Usage

### Usage Steps:
1. Open a new Quotation
2. Add a product
3. Enter quantity (e.g.: 10)
4. Enter number of panels (e.g.: 2)
5. **Result**: Effective quantity = 2 × 10 = 20
6. **Result**: Total price = Price × 20

### Example:
- **Product**: Hasaa Saw
- **Quantity**: 1.0000 m²
- **Number of Panels**: 1.00
- **Unit Price**: 530.00 LE
- **Effective Quantity**: 1.00 × 1.00 = 1.00
- **Total**: 530.00 LE

If you change number of panels to 2:
- **Effective Quantity**: 2.00 × 1.00 = 2.00
- **Total**: 530.00 × 2 = 1,060.00 LE

## Important Notes

### Security
- ✅ If number of panels = 0 or empty, it will not affect calculations
- ✅ Old data will not be affected
- ✅ Module can be uninstalled without issues

### Compatibility
- ✅ Odoo 19.0 Community Edition
- ✅ Compatible with sale_stock, sale_accounting
- ✅ Does not require Enterprise Features

## Technical Structure

### Files:
```
custom_sale_panels_multiplier/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── sale_order_line.py
├── views/
│   └── sale_order_views.xml
└── security/
    └── ir.model.access.csv
```

### Added Fields:
- `number_of_panels`: Number of Panels (Float)
- `effective_quantity`: Effective Quantity (Computed Float, store=True)

### Added Methods:
- `_compute_effective_quantity`: Calculate effective quantity
- `_prepare_base_line_for_taxes_computation`: Override for financial calculations
- `_compute_amount`: Override for amount calculation
- `_prepare_invoice_line`: Override for invoices

## Support
For issues or inquiries, please contact the development team.

## License
LGPL-3
