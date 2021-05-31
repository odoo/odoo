# Global odoo object

## Overview

Whenever the odoo web client is loaded on a page, a special global variable `odoo`
will be set in the page. This object contains a few useful methods/entities.
These values are there for information, integration or debugging purposes, and
are not to be used by business code.

```js
// in browser console (opened with F12)
console.log(odoo);
// will display an object looking like this:
// {
//   info: {...},
//   __DEBUG__: {...}
// }
```

## Exported Values

Here is an explanation of what each exported values are:

-   `info`: this is an object which contains a few informations about the odoo
    server that we are connected to.

    -   `db (string)`: the technical name of the current postgres database
    -   `server_version (string)`: a short string describing the version of the odoo
        code currently running. It may look like this: `14.1alpha1`.
    -   `server_version_info ((string|number)[])`: the `server_version` string is not
        easy to parse/consume, so the `server_version_info` key is exported as well.
        It is an array looking like this: `[14, 1, 0, "alpha", 1, ""]`

-   `__DEBUG__`: this object contains values that are useful to debug/play with the
    odoo application, but that should not be accessed in real code

    -   `root (Component)`: this is the main web client instance
