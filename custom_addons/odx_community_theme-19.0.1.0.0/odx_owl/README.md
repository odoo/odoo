# ODX OWL

`odx_owl` is an Odoo 19 addon that provides an OWL-native design system inspired by shadcn/ui.

## Included foundations

- CSS-token-based light, dark, and system theming via the `odx_theme` service
- Global toast service via `useService("odx_toast")`
- Reusable primitives:
  - `Button`
  - `Input`
  - `Textarea`
  - `Badge`
  - `Card`
  - `Dialog`
  - `DropdownMenu`
  - `Tabs`

## Import surface

Other addons can import directly from the component files or from the shared index:

```js
import { Button, Dialog, Tabs } from "@odx_owl/index";
import { useService } from "@web/core/utils/hooks";

const toast = useService("odx_toast");
toast.add({ title: "Saved", description: "Changes have been stored." });
```

## Demo entry points

- Backend client action: `ODX OWL / Component Gallery`
- Public preview route: `/odx_owl/preview`

## Asset bundles

- `odx_owl.assets_backend`
- `odx_owl.assets_frontend`
