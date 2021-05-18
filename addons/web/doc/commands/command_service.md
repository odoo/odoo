# Command Service

| Technical name | Dependencies             |
| -------------- | ------------------------ |
| `command`      | `dialog`, `hotkey`, `ui` |

## Overview

The `command` service offers a way to register commands.

A Command Palette could then be displayed through the hotkey `Control+K`.

This palette displays a list including :

-   the commands registered in the service
-   any visible elements in the `ui.activeElement` that are accessible through an `[data-hotkey]` attribute.

## API

The `command` service provides the following API:

-   `type Command = { name: string, action: ()=>void, category?: string, hotkey?: string, }`

-   `registerCommand(command: Command): number`

-   `unregisterCommand(token: number)`

In addition to that, you have access to some development helpers which are **greatly** recommended:

-   `useCommand(command: Command): void`:
    a hook that ensures your registration exist only when your component is mounted.

## Example

```js
class MyComponent extends Component {
    setup() {
        useCommand({
            name: "My Command 1",
            action: () => {
                // code when command 1 is executed
            }
        });
        useCommand({
            name: "My Super Command",
            hotkey: "shift-home",
            action: () => {
                // code when super command is executed
                // note that the super command can also get executed with the hotkey "shift-home"
            }
        });
    }
}
```
