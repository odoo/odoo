# ODX UI Kit — OWL Component Library for Odoo 19

## What This Is

A library of 60+ reusable OWL 2 components for Odoo 19 backend, portal, and website development. Inspired by shadcn/ui and Radix patterns, adapted for Odoo's framework.

## How to Import Components

```javascript
// From index.js (recommended)
import { Button } from "@odx_owl/components/button/button";
import { Input } from "@odx_owl/components/input/input";
import { Select } from "@odx_owl/components/select/select";

// Or import directly
import { DataTable } from "@odx_owl/components/data_table/data_table";
```

All components are available in the `web.assets_backend` bundle via `odx_owl.assets_backend`.

## Component List

### Form Controls
- **Input** — Text input with type, placeholder, onChange, onInput
- **Textarea** — Multi-line text with auto-resize
- **Select** — Dropdown with items array, value, onValueChange
- **Checkbox** — Boolean with checked, onCheckedChange
- **Switch** — Toggle switch with checked, onCheckedChange
- **RadioGroup** — Radio buttons with items, value, onValueChange
- **Slider** — Range slider with min, max, step, value
- **DatePicker** — Date selector with value, onSelect
- **DateRangePicker** — Date range with value (from/to), onSelect
- **InputOtp** — OTP/PIN input with length, onComplete
- **NativeSelect** — Browser-native select element
- **Combobox** — Searchable select with filtering
- **Form** — Form wrapper with validation, onSubmit

### Layout
- **Card** — Container with header, content, footer slots
- **Separator** — Horizontal/vertical divider
- **AspectRatio** — Fixed aspect ratio container
- **Collapsible** — Expandable/collapsible content
- **Resizable** — Resizable panel layout
- **ScrollArea** — Custom scrollbar container
- **Sidebar** — Collapsible sidebar with SidebarProvider, SidebarMenu, SidebarMenuItem, SidebarTrigger, SidebarInset
- **Sheet** — Slide-out panel (top/bottom/left/right)
- **Skeleton** — Loading placeholder

### Feedback
- **Alert** — Info/warning/error/success alerts
- **AlertDialog** — Confirmation dialog with actions
- **Badge** — Status badge with variants
- **Progress** — Progress bar with value
- **Spinner** — Loading spinner
- **Toast** — Toast notifications (useToast hook)
- **Tooltip** — Hover tooltip

### Navigation
- **Tabs** — Tab panel with TabsList, TabsTrigger, TabsContent
- **Accordion** — Expandable sections
- **Breadcrumb** — Breadcrumb trail
- **NavigationMenu** — Horizontal navigation
- **Menubar** — Menu bar with submenus
- **DropdownMenu** — Context/dropdown menus
- **ContextMenu** — Right-click context menu
- **Command** — Command palette (Cmd+K)

### Overlay
- **Dialog** — Modal dialog
- **Drawer** — Bottom/side drawer
- **Popover** — Floating popover
- **HoverCard** — Hover-triggered card

### Data Display
- **DataTable** — Sortable, searchable, paginated table
- **Table** — Styled HTML table
- **Calendar** — Month calendar with date selection
- **Chart** — Charts (LineChart, BarChart, DonutChart) with ChartContainer, ChartTooltip, ChartLegend
- **Avatar** — User avatar with fallback
- **Carousel** — Horizontal carousel
- **Empty** — Empty state placeholder

### Utility
- **Button** — Button with variants (default, outline, ghost, destructive) and sizes
- **ButtonGroup** — Grouped buttons
- **Toggle** — Toggle button
- **ToggleGroup** — Multi-toggle group
- **Icon** — Lucide icon wrapper
- **Kbd** — Keyboard shortcut badge
- **Label** — Form label
- **ErrorBoundary** — Error catch with retry

## Common Patterns

### Basic form with inputs
```xml
<div>
    <Input value="state.name" placeholder="'Enter name'" onChange.bind="onNameChange"/>
    <Select items="options" value="state.selected" onValueChange.bind="onSelect"/>
    <Button onClick.bind="onSubmit">Save</Button>
</div>
```

### Data table
```xml
<DataTable
    columns="columns"
    data="rows"
    showSearch="true"
    showPagination="true"
    pageSize="10"
/>
```

### Dialog
```xml
<Dialog open="state.showDialog" onOpenChange.bind="setDialogOpen">
    <t t-set-slot="trigger"><Button>Open</Button></t>
    <t t-set-slot="content">
        <p>Are you sure?</p>
        <Button onClick.bind="confirm">Yes</Button>
    </t>
</Dialog>
```

### Chart
```xml
<ChartContainer config="chartConfig">
    <LineChart data="chartData" xKey="'date'" height="200" showDots="true" showGrid="true"/>
    <ChartTooltip/>
    <ChartLegend/>
</ChartContainer>
```

### Sidebar layout
```xml
<SidebarProvider defaultOpen="true" collapsible="'icon'">
    <Sidebar>
        <SidebarHeader>...</SidebarHeader>
        <SidebarContent>
            <SidebarMenu>
                <SidebarMenuItem>
                    <SidebarMenuButton label="'Dashboard'" onClick="..."/>
                </SidebarMenuItem>
            </SidebarMenu>
        </SidebarContent>
    </Sidebar>
    <SidebarInset>
        <!-- Main content -->
    </SidebarInset>
</SidebarProvider>
```

## CSS Tokens

The library uses CSS custom properties prefixed with `--odx-`:

```css
--odx-background    /* Page background */
--odx-foreground    /* Text color */
--odx-primary       /* Primary accent */
--odx-muted         /* Muted backgrounds */
--odx-border        /* Border color */
--odx-radius        /* Border radius base */
--odx-font-sans     /* Font family */
```

Dark mode: set `html[data-odx-theme="dark"]` to activate dark token values.

## OWL Pitfalls

- Use `onXxx.bind="method"` for event callbacks, not `onXxx="(val) => method(val)"` (loses `this` context)
- `String()` doesn't work in OWL templates — use `'' + value` instead
- `t-ref` cannot be placed on OWL components — use a wrapper `<div>` element
- Sass intercepts `hsl()` — use `unquote("hsl(var(...))")` to emit raw CSS
