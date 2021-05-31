# User service

| Technical name | Dependencies |
| -------------- | ------------ |
| `user`         |              |

## Overview

The `user` service is a very simple service, that aims to just keep track of a
few important values related to the current user. It simply provides an object
with a few keys:

-   `allowed_companies ({[id: number] : {id: number, name: string} })`: the list of companies that can be
    accessed by the user. Each element is a pair `id, name`
-   `context (object)`: the user main context (see below for a description)
-   `current_company ({id: number, name: string})`: the currently active company. It is a
    pair `[id, name]`.
-   `dateFormat`: preferred format when formatting "dates"
-   `decimalPoint`: decimal separator
-   `direction`: "rtl" ("right to left") or "lrt" ("left to right")
-   `grouping`: ?
-   `isAdmin (boolean)`: if true, the user is an administrator of the current
    odoo database
-   `lang (string)`: a short description of the user language (such as `en_us`)
-   `multiLang`: if true, this means that several languages are installed on the database
-   `partnerId (number)`: the id for the partner (`res.partner` record) associated to the user
-   `thousandsSep`: thousands separator
-   `timeFormat`: preferred format when formatting "hours"
-   `tz (string)`: the user configured timezone (such as `Europe/Brussels`)
-   `userId (number)`: the user id (for the `res.user` model)
-   `userName (string)`: the user name (string that can be displayed)

## User Context

The user context is an object that tracks a few important value. This context is
mostly useful when talking to the server (it is added to every request).

Here is complete description of its content:

-   `allowed_company_ids (number[])`: the list of all ids for all available
    companies
-   `lang (string)`: a short description of the user language (same as above)
-   `tz (string)`: the user configured timezone (same as above)
-   `uid (number)`: the current user id (as a `res.partner` record). Same as the
    `userId` value above
