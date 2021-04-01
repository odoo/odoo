# Popover

## Props

| Name           | Type                                   | Default  | Description                                                                                         |
| -------------- | -------------------------------------- | -------- | --------------------------------------------------------------------------------------------------- |
| `popoverClass` | string                                 |          | the classes contained in `popoverClass` are added on the element "div.o_popover"                    |
| `position`     | "bottom" \| "top" \| "left" \| "right" | "bottom" | determine the position of the popover                                                               |
| `target`       | string                                 |          | if provided then the popover will be placed around this target. Selector can match multiple element |
| `trigger`      | "manual" \| "click" \| "hover"         | "click"  | determine how the popover is triggered                                                              |

## Slots

Popovers can be configured with slot

The `default` slot can be used to define the popover's content

```xml
<Popover>
  Content
</Popover>
```

Popover's target can be defined with props but there is also a slot to define it.

With props

```xml
<Popover target="'.popover-target'">
  Content
</Popover>
```

With slot

```xml
<Popover>
  Content
  <t t-set-slot="target">
    <button>Click me to open the popover</button>
  </t>
</Popover>
```

## Events

Popover can trigger a `popover-closed` event when it wants to close.
This event is usually triggered by clicking outside the popover and the target
but can be triggered manually inside the popover too.

```xml
<Popover>
  <header>
    <t t-esc="title" />
    <button t-on-click="trigger('popover-closed')">x</button>
  </header>
  <div>
    Popover's content
  </div>
  <t t-set-slot="target">
    <button>Click me to open the popover</button>
  </t>
</Popover>
```

Popover also listens on the `popover-compute` event to re-compute it's
position or size when children need to.

## Location in the dom

The Popover class uses a portal to locate itself in a div with class
`o_popover_container` but the communication with the parent goes as
usual: via props or custom/dom events.
