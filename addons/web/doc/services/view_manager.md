# ViewManager service

| Technical name | Dependencies |
| -------------- | ------------ |
| `view_manager` | `model`      |

## Overview

The `view_manager` service is a low level service that helps with loading view
informations (such as the arch, the `id` and other view informations).

## API

The `view_manager` service provide a single method:

-   `loadView(model: string, type: ViewType, viewId?: number | false): Promise<ViewDefinition>`
    This method loads from the server the description for a view.

A `ViewDefinition` object contains the following information:

    - `arch (string)`
    - `type (ViewType)`
    - `viewId (number)`
