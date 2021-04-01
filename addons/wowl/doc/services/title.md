# Title service

| Technical name | Dependencies |
| -------------- | ------------ |
| `title`        |              |

## Overview

The `title service` offers a simple API that allows to read/modify the document title.

## API

The `title service` exports two methods and a value:

- `current (string)`,
- `getParts(): Parts`,
- `setParts(parts: Parts): void`,

where the type `Parts` is:

```ts
interface Parts {
  [key: string]: string | null;
}
```

The `getParts` method returns a copy of an object `titleParts` maintained by the tilte service.

The value `current` is structured in the following way: `value_1 - ... - value_n` where
`value_1,...,value_n` are the values (all not null) found in the object `titleParts`.

The `setParts` method allow to add/replace/delete several parts of the title. Delete a part (a value) is done
by setting the associated key value to null;

Example:

If the title is composed of the following parts:

```ts
{
    odoo: "Odoo",
    action: "Import",
}
```

with `current` value being `Odoo - Import`,

```ts
setParts({
  odoo: "Open ERP",
  action: null,
  chat: "Sauron",
});
```

will give the title `Open ERP - Sauron` and `getParts` will return

```ts
{
    odoo: "Open ERP",
    chat: "Sauron",
}
```
