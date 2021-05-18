# Hotkey Service

| Technical name | Dependencies |
| -------------- | ------------ |
| `hotkey`       | `ui`         |

## Overview

The `hotkey` service offers an easy way to react to a
fine bounded subset of keyboard inputs: [hotkeys](#hotkey-definition).

It provides some very special features:

-   awareness of the UI active element: no need to worry about that from your side.

-   a clean subset of listenable hotkeys:
    it ensures a consistent experience through different OSes or browsers.

-   a `useHotkey` hook: it ensures your JS code executes only
    when your component is alive and present in the DOM.

-   a `[data-hotkey]` attribute: it gives a JS-free way to make
    any HTML element "clickable" through an hotkey press.

-   a single key to display overlays over all HTML elements having `[data-hotkey]` attributes.

### Good To Know - ALT is required

By default, to trigger an hotkey, it is required to also press the `ALT` key:

> _e.g._ **ALT+_C_** would trigger the **_C_** hotkey.

An option is available to make it optional in some cases. See the [API](#api) section.

### Good To Know - MAC users

To ensure a similar experience to Mac users some keys had to get swapped :

| Standard Key is... | MacOS Corresponding Key is...            |
| ------------------ | ---------------------------------------- |
| `alt`              | `control`                                |
| `control`          | `meta` (known as _Command_ by mac users) |

### Hotkey Definition

An **hotkey** represents as a string a single keyboard
input from a _single key_ combined or not with _modifiers_.

| Authorized Single Keys                                       |
| ------------------------------------------------------------ |
| **a-z**                                                      |
| **0-9**                                                      |
| **ArrowUp**, **ArrowLeft**, **ArrowDown** and **ArrowRight** |
| **PageUp**, **PageDown**, **Home** and **End**               |
| **Backspace**, **Enter** and **Escape**                      |

| Authorized Modifiers |
| -------------------- |
| **Control**          |
| **Shift**            |

Hotkeys **must be** written following these rules:

-   they are not case sensitive.
-   the composition character is the plus sign: "**+**".
-   each hotkey can have none or any modifier in the authorized subset.
-   order of their parts is important:
    -   modifiers must come first
    -   modifiers must get alphabetically sorted (**Control** is always before **Shift**)
    -   single key part must come last

E.g. following hotkeys are valid:

-   `Control+Shift+5`
-   `g`
-   `Control+g` (same as `Control+G`)

E.g. following hotkeys are **NOT** valid:

-   `Alt+o`: **alt** is neither a valid modifier nor a valid single key
-   `o+d`: combining two or more single keys is not valid
-   `Shift-p`: the composition character must be "+" and not "-"
-   `Tab`: it is not part of the list of valid single keys, nor modifiers

### Hotkey Activation

Hotkeys are activated through keyboard inputs.

By default, to activate an hotkey, `ALT` key should get pressed simultaneously.
It is also possible to register an hotkey that will be fireable, even without pressing ALT key.

When the service detects an hotkey activation, it will:

-   execute **all matching registrations callbacks**.
-   click on **all visible elements having a matching `[data-hotkey]` attribute**.

The `hotkey` service will also **make sure that those
registrations and elements belong to the correct UI active element** (see [`ui` service](ui.md)).

## API

The `hotkey` service provides the following API:

-   `registerHotkey(hotkey: string, callback: ()=>void, options: { altIsOptional?: boolean, allowRepeat?: boolean }): number`

    it asks the service to call the given callback when a matching hotkey is pressed.

    `options.altIsOptional`: default is false.

    `options.allowRepeat`: default is false.

    This method returns a token you can use to unsubscribe later on.

-   `unregisterHotkey(token: number): void`

    it asks the service to forget about the token matching registration.

In addition to that, you have access to some development helpers which are **greatly** recommended:

-   `useHotkey(hotkey: string, callback: ()=>void, options: { altIsOptional?: boolean, allowRepeat?: boolean }): void`

    a hook that ensures your registration exists only when your component is mounted.

-   `[data-hotkey]`

    an HTML attribute taking an hotkey definition.

    When the defined hotkey is pressed, the element gets clicked.

## Examples

### `useHotkey` hook

```js
class MyComponent extends Component {
  setup() {
    useHotkey("a", this.onAHotkey.bind(this));
    useHotkey("Home", () => this.onHomeHotkey());
  }
  onAHotkey() { ... }
  onHomeHotkey() { ... }
}
```

### `[data-hotkey]` attribute

```js
class MyComponent extends Component {
    setup() {
        this.variableHotkey = "control+j";
    }
    onButton1Clicked() {
        console.log("clicked either with the mouse or with hotkey 'Shift+o'");
    }
    onButton2Clicked() {
        console.log(`clicked either with the mouse or with hotkey '${this.variableHotkey}'`);
    }
}
MyComponent.template = xml`
  <div>

    <button t-on-click="onButton1Clicked" data-hotkey="Shift+o">
      One!
    </button>

    <button t-on-click="onButton2Clicked" t-att-data-hotkey="variableHotkey">
      Two!
    </button>

  </div>
`;
```

### manual usage of the service

```js
class MyComponent extends Component {
    setup() {
        this.hotkey = useService("hotkey");
    }
    mounted() {
        this.hotkeyToken1 = this.hotkey.registerHotkey("backspace", () =>
            console.log("backspace has been pressed")
        );
        this.hotkeyToken2 = this.hotkey.registerHotkey("Shift+P", () =>
            console.log('Someone pressed on "shift+p"!')
        );
    }
    willUnmount() {
        // You need to manually unregister your registrations when needed!
        this.hotkey.unregisterHotkey(this.hotkeyToken1);
        this.hotkey.unregisterHotkey(this.hotkeyToken2);
    }
}
```
