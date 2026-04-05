# ODX UI Kit — Agent Instructions

## For Cursor, Windsurf, Copilot, and other AI coding agents

When a user asks you to build UI in Odoo 19 using OWL components, use the odx_owl library.

### Quick Reference

**Import path**: `@odx_owl/components/{component_name}/{component_name}`

**Most used components**:
| Need | Component | Import |
|------|-----------|--------|
| Text input | `Input` | `@odx_owl/components/input/input` |
| Dropdown | `Select` | `@odx_owl/components/select/select` |
| Button | `Button` | `@odx_owl/components/button/button` |
| Toggle | `Switch` | `@odx_owl/components/switch/switch` |
| Modal | `Dialog` | `@odx_owl/components/dialog/dialog` |
| Table | `DataTable` | `@odx_owl/components/data_table/data_table` |
| Tabs | `Tabs` | `@odx_owl/components/tabs/tabs` |
| Chart | `LineChart, BarChart, DonutChart` | `@odx_owl/components/chart/chart` |
| Icons | `Icon` | `@odx_owl/components/icon/icon` |
| Sidebar | `SidebarProvider, Sidebar` | `@odx_owl/components/sidebar/sidebar` |

### Rules
1. Always use `.bind` for callbacks: `onClick.bind="method"` not `onClick="() => method()"`
2. Register components in `static components = { Button, Input, ... }`
3. Props use OWL syntax: `value="state.x"` not `value={state.x}`
4. Templates use `t-att-` for dynamic attributes, `t-on-` for events
5. Wrap with `ErrorBoundary` for components that might fail (charts, external data)
6. Use `'' + value` instead of `String(value)` in templates

### File structure for new OWL components
```
my_module/
  static/src/
    js/my_component.js      # OWL component class
    xml/my_component.xml    # OWL template
  __manifest__.py           # Add to web.assets_backend
```

### Manifest asset registration
```python
"assets": {
    "web.assets_backend": [
        "my_module/static/src/js/my_component.js",
        "my_module/static/src/xml/my_component.xml",
    ],
},
```

See CLAUDE.md in this directory for the full component list with props and examples.
