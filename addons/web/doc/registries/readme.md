# Registries

## Overview

The Odoo web client provides many registries, which allow developers to extend
the web client in a safe and structured way.

Here is a list of all registries:

| Name                                           | Description                                                                        |
| ---------------------------------------------- | ---------------------------------------------------------------------------------- |
| `actions`                                      | definition of all available client actions                                         |
| `Components`                                   | components (class) that will be instantiated at root of web client                 |
| `errorDialogs`                                 | dialogs (class) that will be instantiated by the crash manager to handle errors    |
| `services`                                     | definition of all services that will be deployed                                   |
| [systray](../systray.md#adding-a-systray-item) | components (class) that will be display in the systray menu (a part of the navbar) |
| `views`                                        | definition of all available views                                                  |
| [userMenu](user_menu.md)                       | definition of all user menu items                                                  |

## Usage

A registry is an owl [EventBus](https://github.com/odoo/owl/blob/master/doc/reference/event_bus.md#-event-bus-) with some additional methods (below `T` is the type of values to be found in the registry):

- `add: (key: string, value: T, force: boolean = false) => Registry<T>`: add an entry `(key, value)` to the registry. By default, add
  a key already used results in an error. This can be prevented by using the parameter `force`, leading to the replacement of the old entry.
  The `add` method returns the registry itself to allow chaining.
- `get: (key: string) => T`: returns a value from the registry. An error is thrown in case the key cannot be found in the registry.
- `contains: (key: string) => boolean`: allow to check the presence of a key in the registry.
- `getAll: () => T[]`: returns the registry values.
- `getEntries: () => [string, T][] `: returns the registry entries.
- `remove: (key: string)`: remove an entry from the registry.

Each time an item is added (deleted) via `add` (resp. `delete`), an event "UPDATE" is triggered with a payload of type

```ts
interface Payload {
  operation: "add" | "delete";
  key: string;
  value: T;
}
```
