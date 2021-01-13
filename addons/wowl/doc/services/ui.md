# UI service

| Technical name | Dependencies |
| -------------- | ------------ |
| `ui`           |              |

## Overview

The ui service will allow the user to be able to block or unblock the UI. When the ui will be blocked, a loading screen blocking any action will cover the UI.

## API

The `ui` service provides two methods:

- `block(): void`: this method will activate the loading screen to block the ui.

- `unblock(): void`: This method will disable the loading screen in order to unblock the ui.
  if it was not already disable.

### Good to know

If the `block()` method is called several times simultaneously, the same number of times the `unblock()` function must be used to unblock the UI.

## Example

Here is how one component can block and unblock the UI:

```js
class MyComponent extends Component {
    ...
    ui = useService('ui');

    ...

    someHandlerBlock() {
        // The loading screen will be displayed and block the UI.
        this.ui.block();
    }

    someHandlerUnblock() {
        // The loading screen is no longer displayed and the UI is unblocked.
        this.ui.unblock();
    }
}
```
