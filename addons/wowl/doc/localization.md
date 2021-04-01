# Localization

## Overview

Each internal user has a specified language (default `en_US`) according to which various parts
of the interface can depend on: terms are translated, numbers are formated,... with respect to
that language.

The localization module defines two functions `_t` and `_lt` used to translate terms
and various other preference parameters.

## \_t

Eager translation function, performs translation immediately at call (this requires the translations
to be available). Used by owl to translate automatically text nodes.
It is also available in the [environment](environment.md) so that,
for example, the components can use it to translate various terms:

```ts
this.env._t("Hello");
```

## \_lt

Lazy translation function, only performs the translation when actually
printed (e.g. inserted into a template).
Useful when defining translatable strings in code evaluated before the
translations are loaded, as class attributes or at the top-level of
an Odoo Web module, for example:

```ts
import { _lt } from ./services/localization.ts
const greeting = _lt("Hello");
```

The value returned by `_lt` is an object with a single property `toString`.
If the current user language is `fr_FR` and `Hello` has translation `Bonjour`,
`greeting` takes the value

```ts
{
  toString: () => "Bonjour";
}
```

## Other localization parameters

The following localization parameters can be accessed via the [User Service](services/user.md):

`dateFormat`, `decimalPoint`, `direction`, `grouping`, `multiLang`, `thousandsSep`, `timeFormat`.

## Terms to translate

Every string literal on which `_t` or `_lt` is applied to is automatically added to the list of
terms to translate (if not already added).
For more information on translations see [Translating Modules](../../../doc/reference/translations.rst)
