# Dialog Manager Service

| Technical name   | Dependencies |
| ---------------- | ------------ |
| `dialog_manager` |              |

## Overview

The `dialog manager service` offers a simple API that allows to open dialogs but with
few interactions possible: when possible, it is better to instantiate a
dialog by using a Dialog tag in a component template.

## API

The dialog_manager service exports one method:

- `open(dialogClass: Type<Component>, props?: object): void`: the `dialog class` given as
  first parameter is instantiated with the optional props given (or with `{}`).

By `dialog class`, we mean a class extending `owl.Component` and having as root node `Dialog`:

```js
class CustomDialog extends owl.Component {
    static template = owl.tags.xml`
        <Dialog title="'Custom title'" size="'modal-xl'">
            ...
        </Dialog
    `;
    ...
}
```
