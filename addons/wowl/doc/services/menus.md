# Menus Service

| Technical name | Dependencies               |
| -------------- | -------------------------- |
| `menus`        | `action_manager`, `router` |

## Overview

The `menus` service is an asynchronous service: once the `deploy` method is
called, it will call the server (using the `/web/load_menus/...` url) to fetch
the data. Once it is done, the service is available and can be used to query
informations on the menu items.

## API

Here is a description of all exported methods:

- `get(menuId)`
- `apps`
- `getMenusAsTree(...)`
