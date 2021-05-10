# Popover Service

| Technical name | Dependencies |
| -------------- | ------------ |
| `popover`      |              |

## Overview

The `popover` service offers a simple API that allows to open popovers but with
few interactions possible: when possible, it is better to instantiate a
popover by using a Popover tag in a component template.

## API

The `popover` service exports one method:

-   `add(params: Object): string`
    Signals the manager to add a popover.

    `params` can contain any of these options:

    -   `Component: Type<Component>`: A class extending `owl.Component` and having
        as root node `Popover`.
    -   `props: Object`: The props passed to the component.
    -   `content: string`: A text which is displayed in the popover.
        Cannot be used with `Component`.
    -   `key: string`: A key to retrieve the popover and remove it later.
        If no key is given then one will be generated.
    -   `onClose: (key: string) => void`: A callback which is executed when the
        popover is closed.
    -   `keepOnClose: boolean = false`: if true then the manager will keep the
        popover when it closes otherwise the manager removes the popover.

    Returns the `key` given in `params` or the generated one.

-   `remove(key: string): void`
    Signals the manager to remove the popover with key = `key`.

## Example

```js
class CustomPopover extends owl.Component {}
CustomPopover.template = owl.tags.xml`
  <Popover target="props.target" trigger="'none'">
    <t t-set-slot="content">
      My popover
    </t>
  </Popover>
`;

...

popoverService.add({
  key: "my-popover",
  Component: CustomPopover,
  props: {
    target: "#target",
  },
  keepOnClose: true,
});

...

popoverService.remove("my-popover");
```
