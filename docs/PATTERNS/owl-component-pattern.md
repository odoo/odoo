# OWL Component Pattern

**Purpose:** Build interactive frontend UI elements using Odoo Web Library (OWL) — a reactive component framework similar to React/Vue. OWL components compose the entire Odoo web client: views, widgets, dialogs, and custom dashboard elements.

**Source:** `addons/board/static/src/board_controller.js`, `addons/mrp_subcontracting/static/src/components/subcontracting_production_list_controller.js`, `addons/web/static/lib/owl/owl.js`

---

## When to Use

- Creating a custom field widget for a specific data type
- Extending an existing view controller (list, form, kanban) with extra behavior
- Building a standalone UI element (dashboard panel, dialog, sidebar widget)
- Adding client-side interactivity that cannot be expressed in XML view attributes

---

## Basic Component Structure

```javascript
// addons/my_addon/static/src/components/my_component.js
import { Component, useState, onMounted, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class MyComponent extends Component {
    // 1. Template reference (matches t-name in XML template file)
    static template = "my_addon.MyComponent";

    // 2. Sub-components used in the template
    static components = { /* ChildComponent */ };

    // 3. Props declaration (validated at runtime in dev mode)
    static props = {
        title: { type: String },
        recordId: { type: Number, optional: true },
        onSave: { type: Function, optional: true },
    };

    // 4. setup() replaces constructor — all hooks called here
    setup() {
        // Reactive state: UI re-renders when these change
        this.state = useState({
            isLoading: false,
            items: [],
        });

        // Services injected via hooks
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.dialogService = useService("dialog");

        // DOM ref
        this.containerRef = useRef("container");

        // Lifecycle hook
        onMounted(() => {
            this._loadData();
        });
    }

    // 5. Methods (called from template or other methods)
    async _loadData() {
        this.state.isLoading = true;
        const result = await this.rpc("/my_addon/data", {
            record_id: this.props.recordId,
        });
        this.state.items = result;
        this.state.isLoading = false;
    }

    onItemClick(item) {
        this.notification.add(_t("Selected: %s", item.name), { type: "info" });
        this.props.onSave?.(item);
    }
}
```

---

## XML Template (QWeb)

```xml
<!-- addons/my_addon/static/src/components/my_component.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">
    <t t-name="my_addon.MyComponent">
        <div class="o_my_component" t-ref="container">
            <h3><t t-esc="props.title"/></h3>

            <t t-if="state.isLoading">
                <div class="o_loading_indicator">Loading...</div>
            </t>
            <t t-else="">
                <ul>
                    <t t-foreach="state.items" t-as="item" t-key="item.id">
                        <li t-on-click="() => onItemClick(item)">
                            <t t-esc="item.name"/>
                        </li>
                    </t>
                </ul>
            </t>
        </div>
    </t>
</templates>
```

---

## Extending an Existing View Controller

```javascript
// addons/mrp_subcontracting/static/src/components/subcontracting_production_list_controller.js
import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

class SubcontractingProductionListController extends ListController {
    // Override a getter to modify action menu items
    get actionMenuItems() {
        let items = super.actionMenuItems;
        items.action = [];   // remove all action menu entries
        return items;
    }
}

// Register as a named view variant in the views registry
registry.category("views").add("subcontracting_production_list", {
    ...listView,                                    // spread parent view definition
    Controller: SubcontractingProductionListController,  // swap only the controller
});
```

Reference it from a view XML using `js_class`:
```xml
<list js_class="subcontracting_production_list">
    ...
</list>
```

---

## Full Board Controller Example

```javascript
// addons/board/static/src/board_controller.js (full file, lines 1–133)
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useService } from "@web/core/utils/hooks";
import { standardViewProps } from "@web/views/standard_view_props";
import { Component, useState, useRef } from "@odoo/owl";

export class BoardController extends Component {
    static template = "board.BoardView";
    static components = { Dropdown };
    static props = {
        ...standardViewProps,   // inherit standard view prop shapes
        board: Object,
    };

    setup() {
        this.board = useState(this.props.board);  // make props reactive
        this.dialogService = useService("dialog");
    }

    closeAction(column, action) {
        // Show confirmation dialog before destructive action
        this.dialogService.add(ConfirmationDialog, {
            body: _t("Are you sure that you want to remove this item?"),
            confirm: () => {
                const index = column.actions.indexOf(action);
                column.actions.splice(index, 1);
                this.saveBoard();
            },
            cancel: () => {},
        });
    }
}
```

---

## OWL Hooks Reference

| Hook | Import | Purpose |
|------|--------|---------|
| `useState(obj)` | `@odoo/owl` | Reactive state object; mutations trigger re-render |
| `useRef(name)` | `@odoo/owl` | Access a DOM element via `t-ref="name"` |
| `onMounted(fn)` | `@odoo/owl` | Run after first render (component is in DOM) |
| `onWillUnmount(fn)` | `@odoo/owl` | Cleanup before component is destroyed |
| `onPatched(fn)` | `@odoo/owl` | Run after every re-render |
| `useService(name)` | `@web/core/utils/hooks` | Inject an Odoo service |
| `useEnv()` | `@odoo/owl` | Access the shared environment object |

---

## Registering a Field Widget

```javascript
// Register a custom widget for use in views via widget="my_widget"
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class MyFieldWidget extends Component {
    static template = "my_addon.MyFieldWidget";
    static props = { ...standardFieldProps };

    setup() {
        this.value = this.props.record.data[this.props.name];
    }
}

registry.category("fields").add("my_widget", {
    component: MyFieldWidget,
    supportedTypes: ["char", "text"],
});
```

---

## Asset Registration in Manifest

```python
# addons/my_addon/__manifest__.py
{
    'assets': {
        'web.assets_backend': [
            # Glob pattern — loads both .js and .xml files
            'my_addon/static/src/components/**/*',
            'my_addon/static/src/scss/my_addon.scss',
        ],
        'web.assets_tests': [
            'my_addon/static/tests/tours/**/*',
        ],
    },
}
```

---

## Common Pitfalls

- **`useState` must wrap a plain object, not a primitive.** `useState(0)` does not work; use `useState({ count: 0 })`.
- **Mutating `useState` arrays requires in-place methods** (`push`, `splice`, direct index assignment). Replacing the array reference (`this.state.items = newArray`) also works but triggers a full re-render.
- **`setup()` is the only place to call hooks.** Calling `useState` or `useService` outside `setup()` throws at runtime.
- **Template `t-name` must exactly match `static template`** string in the class. A mismatch causes a silent "template not found" error.
- **Assets are not hot-reloaded in production mode.** Run the dev server with `--dev=assets` to enable live asset reloading during development.
- **`this.env` vs `useEnv()`:** Inside `setup()`, use `useEnv()`. Outside (in methods), `this.env` is available after mounting. Never call hooks in methods.
- **Props are immutable from inside the component.** To communicate upward, call a callback prop (`this.props.onSave(value)`) or emit a custom event.

---

## Related Patterns

- [module-addon-structure-pattern.md](./module-addon-structure-pattern.md) — `static/src/` layout and asset bundle registration
- [http-controller-pattern.md](./http-controller-pattern.md) — `type='jsonrpc'` routes called via `useService("rpc")`
- [view-definition-pattern.md](./view-definition-pattern.md) — `js_class=` attribute linking XML views to OWL controllers
