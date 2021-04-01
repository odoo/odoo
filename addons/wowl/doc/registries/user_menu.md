# userMenu registry

## Overview

The registry `userMenu` gathers the `user menu` dropdown elements.

## Value type

```ts
(env: OdooEnv) => UserMenuItem;
```

where

```ts
interface UserMenuItem {
  description: string;
  callback: () => void | Promise<any>;
  hide?: boolean;
  href?: string;
  sequence?: number;
}
```

Thus each value of the registy is a function taking the [environment](../environment.md) in entry
and returning a plain object with some keys:

- `description`: the item text,
- `href`: (optional) if given (and truthy), the item text is put in a `a` tag with given attribute href,
- `callback`: callback to call when the item is clicked on,
- `hide`: (optional) indicates if the item should be hidden (default: false),
- `sequence`: (optional) determines the rank of the item among the other dropwdown items (default: 100).

Example:

```js
env.registry.userMenu.add("key", (env) => {
  return {
    description: env._t("Technical Settings"),
    callback: () => { env.services.action_manager.doAction(3); };
    hide: (env.browser.random() < 0.5),
  }
}
```
