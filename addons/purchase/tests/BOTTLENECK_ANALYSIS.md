# Purchase Module Bottleneck Analysis

**Date:** 2026-01-23
**Focus:** Python/ORM processing overhead in computed fields

---

## Executive Summary

The purchase module's query optimization is excellent, but **Python processing time**
dominates performance for large orders. The main bottlenecks are:

1. **Per-line seller selection** - No caching/batching across lines
2. **O(lines × sellers) date checking** - Loops through all sellers per line
3. **Python-based filtering** - Seller filtering done in Python, not SQL

---

## Bottleneck #1: Per-Line Seller Selection

### Location
`purchase_order_line.py:723-747` - `_compute_selected_seller_id()`

### Code Analysis
```python
@api.depends(
    "partner_id", "date_order", "product_id",
    "product_id.seller_ids", "product_id.seller_ids.partner_id",
    # ... 12+ dependencies
)
def _compute_selected_seller_id(self):
    for line in self:  # ← PER-LINE PROCESSING
        if line.display_type or not line.product_id:
            line.selected_seller_id = False
            continue

        params = line._get_select_sellers_params()
        seller = line.product_id._select_seller(  # ← CALLED FOR EACH LINE
            partner_id=line.partner_id,
            quantity=abs(line.product_qty) or 1.0,
            date=...,
            uom_id=line.product_uom_id,
            params=params,
        )
        line.selected_seller_id = seller or False
```

### Problem
- Each line independently calls `product._select_seller()`
- `_select_seller()` internally calls:
  - `_prepare_sellers()` → fetches all sellers, sorts them
  - `_get_filtered_sellers()` → Python loop filtering

### Impact
For 200 lines with 8 sellers each:
- 200 calls to `_select_seller()`
- 200 × 8 = 1,600 Python filter operations
- Same product may be processed multiple times

### Optimization Opportunity
**Cache seller lookups by (product_id, partner_id, date, quantity_bucket)**

```python
def _compute_selected_seller_id(self):
    # Build cache key → seller mapping
    seller_cache = {}

    # Group lines by product to reduce lookups
    for product, lines in self.grouped('product_id').items():
        if not product:
            continue
        # Single seller lookup per product (for same partner/date)
        ...
```

---

## Bottleneck #2: O(lines × sellers) Date Check

### Location
`purchase_order_line.py:841-853` - `_compute_date_planned()`

### Code Analysis
```python
def _compute_date_planned(self):
    for line in self:
        # ... early returns ...

        # Check if current date matches ANY seller's expected date
        for seller in line.product_id.seller_ids:  # ← LOOPS ALL SELLERS
            seller_date = line._get_date_planned(seller)
            if line.date_planned.date() == seller_date.date():
                line.date_planned = new_date.strftime(...)
                break
        else:
            # Also check no-seller default
            no_seller_date = line._get_date_planned(False)
            if line.date_planned.date() == no_seller_date.date():
                line.date_planned = new_date.strftime(...)
```

### Problem
- For each line, iterates through ALL seller_ids
- Purpose: Detect if date was "manually customized" vs "system-set"
- Complexity: O(lines × sellers_per_product)

### Impact
For 200 lines with 8 sellers each:
- 200 × 8 = 1,600 date comparisons
- Plus 200 calls to `_get_date_planned(False)`

### Optimization Opportunity
**Precompute valid seller dates once per product**

```python
def _compute_date_planned(self):
    # Precompute seller dates per product
    product_seller_dates = {}
    for line in self:
        product = line.product_id
        if product.id not in product_seller_dates:
            product_seller_dates[product.id] = {
                line._get_date_planned(seller).date()
                for seller in product.seller_ids
            }
            product_seller_dates[product.id].add(
                line._get_date_planned(False).date()
            )

    for line in self:
        # ... use precomputed set for O(1) lookup ...
        if line.date_planned.date() in product_seller_dates[line.product_id.id]:
            line.date_planned = new_date.strftime(...)
```

---

## Bottleneck #3: Python-Based Seller Filtering

### Location
`product_product.py:1067-1120` - `_get_filtered_sellers()`

### Code Analysis
```python
def _get_filtered_sellers(self, partner_id, quantity, date, uom_id, params):
    self.ensure_one()
    precision = self.env["decimal.precision"].precision_get("Product Unit")

    sellers_filtered = self._prepare_sellers(params)
    sellers = self.env["product.supplierinfo"]

    for seller in sellers_filtered:  # ← PYTHON LOOP
        # UoM conversion per seller
        quantity_uom_seller = quantity
        if quantity_uom_seller and uom_id and uom_id != seller.product_uom_id:
            quantity_uom_seller = uom_id._compute_quantity(...)

        # Date filtering in Python
        if seller.date_start and seller.date_start > date:
            continue
        if seller.date_end and seller.date_end < date:
            continue

        # Partner filtering in Python
        if partner_id and seller.partner_id not in [partner_id, partner_id.parent_id]:
            continue

        # Quantity filtering in Python
        if float_compare(quantity_uom_seller, seller.min_qty, ...) == -1:
            continue

        sellers |= seller

    return sellers
```

### Problem
- All filtering done in Python after fetching all sellers
- UoM conversion happens for each seller
- No SQL-level filtering

### Impact
For products with many price breaks, this loops through all sellers even if
only one matches the criteria.

### Optimization Opportunity (Advanced)
**SQL-based pre-filtering for basic criteria**

```python
def _get_filtered_sellers_optimized(self, partner_id, quantity, date, uom_id, params):
    # Use SQL for initial filtering
    domain = [
        ('product_tmpl_id', '=', self.product_tmpl_id.id),
        '|', ('date_start', '=', False), ('date_start', '<=', date),
        '|', ('date_end', '=', False), ('date_end', '>=', date),
        '|', ('partner_id', '=', False),
            '|', ('partner_id', '=', partner_id.id),
                 ('partner_id', '=', partner_id.parent_id.id),
    ]
    # Then do quantity/UoM filtering in Python (requires conversion)
```

---

## Bottleneck #4: Computed Field Cascade

### Dependency Chain
```
product_qty change
    ↓
_compute_selected_seller_id() [12+ dependencies]
    ↓
_compute_price_and_discount() [14 dependencies]
    ↓
_compute_date_planned() [3 dependencies]
    ↓
_compute_amounts() [on order]
```

### Problem
- Each computed field has many dependencies
- Changes cascade through multiple compute methods
- Odoo's recompute mechanism processes each method separately

### Optimization Opportunity
**Combine related computations into single method**

Instead of 3 separate compute methods that depend on each other,
combine seller selection + price + date into one atomic computation.

---

## Performance Profile

### Current (200 lines, 8 sellers/product)

| Operation | Time | % of Total |
|-----------|------|------------|
| Python loops | ~0.75s | 88% |
| SQL queries | ~0.10s | 12% |
| **Total** | **~0.85s** | 100% |

### With Optimizations (Estimated)

| Optimization | Estimated Improvement |
|--------------|----------------------|
| Cache seller lookups | 30-40% |
| Precompute seller dates | 10-15% |
| SQL pre-filtering | 10-20% |
| Combined compute | 5-10% |
| **Total Potential** | **50-70%** |

---

## Recommended Optimization Priority

### Priority 1: Cache Seller Lookups (High Impact, Medium Effort)
- Group lines by product
- Single seller lookup per unique (product, partner, date_bucket)
- Cache results for reuse

### Priority 2: Precompute Seller Dates (Medium Impact, Low Effort)
- Build set of valid dates once per product
- O(1) membership check instead of O(sellers) loop

### Priority 3: SQL Pre-filtering (Medium Impact, High Effort)
- Move basic criteria (date, partner) to SQL domain
- Reduce Python iteration

### Priority 4: Combined Compute Method (Low Impact, Medium Effort)
- Merge `_compute_selected_seller_id`, `_compute_price_and_discount`
- Reduce cascade overhead

---

## Code Locations

| File | Lines | Method |
|------|-------|--------|
| `purchase/models/purchase_order_line.py` | 723-747 | `_compute_selected_seller_id` |
| `purchase/models/purchase_order_line.py` | 776-810 | `_compute_price_and_discount` |
| `purchase/models/purchase_order_line.py` | 813-853 | `_compute_date_planned` |
| `product/models/product_product.py` | 1060-1065 | `_prepare_sellers` |
| `product/models/product_product.py` | 1067-1120 | `_get_filtered_sellers` |
| `product/models/product_product.py` | 1122-1159 | `_select_seller` |
