# UI service

| Technical name | Dependencies |
| -------------- | ------------ |
| `ui`           |              |

## Overview

The `ui` service offers miscellaneous UI features:

-   active element management.
    The default UI active element is the `document` element, but the `ui` service
    lets anyone become the UI active element. It is useful e.g. for dialogs.
-   block or unblock the UI.
    When the ui will be blocked, a loading screen blocking any action will cover the UI.

## API

The `ui` service provides the following API:

-   `bus: EventBus`: a bus, on which are triggered

    -   `active-element-changed (activeElement: DOMElement)` when the UI active element has changed.

-   `block(): void`: this method will activate the loading screen to block the ui.

-   `unblock(): void`: This method will disable the loading screen in order to unblock the ui.
    if it was not already disable.

-   `ìsBlocked (boolean)`: informs on the UI blocked state

-   `activateElement(activateElement: DOMElement): void`: applies an UI active element.

-   `activeElement: DOMElement`: gives the actual UI active element

-   `getVisibleElements(selector: string)`: returns all elements matching the given selector that are displayed somewhere on the active element.

In addition to that, you have access to some development helpers which are **greatly** recommended:

-   `useActiveElement(refName?:string)`: a hook that ensures the UI active element will
    take place/get released each time your component gets mounted/unmounted.
    By default, the element that will be the UI active element is the component root's.
    It can be delegated to another element through the usage of a `t-ref` directive,
    providing its value to this hook. In that case, **it is mandatory** that the referenced
    element is fixed and not dynamically attached in/detached from the DOM (e.g. with t-if directive).

### Good to know: UI blocking

If the `block()` method is called several times simultaneously, the same number of times the `unblock()` function must be used to unblock the UI.

### Good to know: UI Active Element

Due to the way components are mounted by the Owl engine (from the bottom to the top), you should be aware that if nested components try to all become the UI active element, only the topmost of them will be.

E.g.:

```js
class A extends Component {
    setup() {
        useActiveElement();
    }
}
A.components = { B };
A.template = xml`<div id="a"><B/></div>`;

class B extends Component {
    setup() {
        useActiveElement();
    }
}
B.template = xml`<div id="b"/>`;

// When A will get mounted, all its children components will get mounted first
// So B will get mounted first and div#b will become the active element.
// Finally A will get mounted and div#a will become the active element.
```

## Example: active element management

### Listen to active element changes

```js
class MyComponent extends Component {
    setup() {
        const ui = useService("ui");
        this.myActiveElement = ui.activeElement;
        useBus(ui.bus, "active-element-changed", (activeElement) => {
            if (activeElement !== this.myActiveElement) {
                // do some stuff, like changing my state or keeping myActiveElement in sync...
            }
        });
    }
}
```

### With `useActiveElement` hook

Here is how one component could change the active element of the UI

```js
class MyComponent extends Component {
    setup() {
        useActiveElement();
    }
}
```

### With `useActiveElement` hook: ref delegation

Here is how one component could change the active element of the UI

```js
class MyComponent extends Component {
    setup() {
        useActiveElement("delegatedRef");
    }
}
MyComponent.template = owl.tags.xml`
  <div>
    <h1>My Component</h1>
    <div t-ref="delegatedRef"/>
  </div>
`;
```

### Manually

Here is how one component could change the active element of the UI

```js
class MyComponent extends Component {
    setup() {
        this.uiService = useService("ui");
    }
    mounted() {
        const activateElement = this.el;
        this.uiService.activateElement(activateElement);
    }
    willUnmount() {
        this.uiService.deactivateElement(activateElement);
    }
}
```

## Example: block/unblock

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
