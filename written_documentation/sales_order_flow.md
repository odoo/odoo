# Sales Order Confirmation Flow

## 1. Sequence Diagram
This diagram traces the execution path when a user clicks "Confirm" on a Sales Order.

```mermaid
sequenceDiagram
    actor User
    participant SO as SaleOrder (sale)
    participant SO_Website as SaleOrder (website_sale)
    participant SO_Stock as SaleOrder (sale_stock)
    participant SO_Proj as SaleOrder (sale_project)
    participant SO_Mrp as SaleOrder (sale_mrp)
    participant SO_Purch as SaleOrder (sale_purchase)
    participant Rules as ProcurementGroup

    User->>SO: action_confirm()
    Note over SO: Entry Point (RPC)
    
    SO->>SO: _confirmation_error_message()
    alt Validation Fails
        SO-->>User: Raise UserError
    end

    SO->>SO_Website: action_confirm()
    Note right of SO_Website: Assigns Salesperson (if eCommerce)
    SO_Website->>SO: super()

    SO->>SO: write(state='sale', date_order=Now)
    
    SO->>SO: _action_confirm()
    Note right of SO: Core Hook for Extensions

    rect rgb(240, 248, 255)
        note right of SO_Proj: Module: sale_project
        SO->>SO_Proj: _action_confirm()
        SO_Proj->>SO_Proj: _timesheet_service_generation()
        note right of SO_Proj: Creates Tasks/Projects
        SO_Proj-->>SO: super()
    end

    rect rgb(230, 230, 250)
        note right of SO_Purch: Module: sale_purchase
        SO->>SO_Purch: _action_confirm()
        SO_Purch->>SO_Purch: _purchase_service_generation()
        note right of SO_Purch: Creates POs for Subcontracting/Dropship
        SO_Purch-->>SO: super()
    end

    rect rgb(255, 250, 240)
        note right of SO_Stock: Module: sale_stock
        SO->>SO_Stock: _action_confirm()
        SO_Stock->>SO_Stock: _action_launch_stock_rule()
        SO_Stock->>Rules: run()
        note right of Rules: Creates Stock Moves / Pickings
        SO_Stock-->>SO: super()
    end
    
    SO->>SO: _send_order_confirmation_mail()
    SO-->>User: True (Action Completed)
```

## 2. Behind the Scenes: The "Super" Chain [📘 Ref: Inheritance](https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/12_inheritance.html)

You might wonder how Odoo calls logic from `sale_stock`, `sale_project`, and `sale_purchase` all at once without explicitly listing them.

This works through **Python's Method Resolution Order (MRO)**, essentially a "Chain of Responsibility".
1.  All these modules inherit from `sale.order`.
2.  Each module defines `def _action_confirm(self):`.
3.  Inside, they do their specific work (e.g., create a task) and then call `super()._action_confirm()`.
4.  Odoo chains them together. When `sale.order` calls `self._action_confirm()`, it triggers the first module in the chain (e.g., `sale_stock`), which calls the next (`sale_project`), and so on.

## 3. Deep Dive: What Actually Happens?

### A. Stock Logic (`sale_stock`)
**Goal**: Move physical goods.
*   **Trigger**: `_action_launch_stock_rule()`
*   **Process**:
    1.  Odoo looks at each Sales Order Line.
    2.  It checks the **Route** on the product (e.g., "Deliver from Stock", "Dropship").
    3.  It runs **Procurement Rules** associated with that route.
    4.  **Result**: If the rule is "Pull from Stock", it creates a `stock.picking` (Delivery Order). If the rule is "Buy", it might trigger a Purchase Request.

### B. Project Logic (`sale_project`)
**Goal**: Manage service delivery.
*   **Trigger**: `_timesheet_service_generation()`
*   **Process**:
    1.  Odoo filters for lines with **Service** products.
    2.  It checks the **Service Tracking** setting on the Product form:
        *   *Create a Task in an existing Project*: Adds a task to the project linked in the SO.
        *   *Create a Task in a new Project*: Creates a brand new Project and adds the task.
        *   *Create a new Project but no Task*: Pure project management.
    3.  **Result**: A link is created between the SO Line and the generated Task/Project.

### C. Purchase Logic (`sale_purchase`)
**Goal**: Outsource work or buy goods to fulfill the order.
*   **Trigger**: `_purchase_service_generation()`
*   **Process**:
    1.  Used primarily for **Subcontracting** or **Dropshipping**.
    2.  If a product is configured to be "Expensed" or "Subcontracted", this generates a Request for Quotation (RFQ) to the vendor.

## 4. Key Methods Summary [📘 Ref: Models](https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/03_basicmodel.html)

| Method | Defined In | Purpose |
| :--- | :--- | :--- |
| `action_confirm()` | [`addons/sale`](../addons/sale) | **Public Entry Point**. Validates state, locks order, sends email. |
| `_action_confirm()` | [`addons/sale`](../addons/sale) | **The Hook**. Empty in base, but extended by everyone else. |
| `_action_launch_stock_rule()` | [`addons/sale_stock`](../addons/sale_stock) | Runs procurement rules to create_Delivery Orders. |
| `_timesheet_service_generation()` | [`addons/sale_project`](../addons/sale_project) | Creates Tasks/Projects for service products. |

