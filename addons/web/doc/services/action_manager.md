# Action Manager Service

| Technical name   | Dependencies                             |
| ---------------- | ---------------------------------------- |
| `action_manager` | `notifications`, `rpc`, `router`, `user` |

## Overview

The action manager handles every [`ir.actions.actions`](https://www.odoo.com/documentation/14.0/reference/actions.html) triggered by user interaction.
Clicking on a menu item, on a button, or changing of view type are all examples of
interactions handled by the action manager.

The action manager gives priority to the most recent user request, and will drop
a request if another one comes after. The second request obviously takes the state
of the action manager as it was before the first request. When possible, unnecessary RPC
and rendering must be canceled if another request is made by the user.

## API

The action_manager service exports some methods, which are not all meant to be used by everyone:

- `doAction(action: ActionRequest, options: ActionOptions): Promise<void>;`: probably the one thing to remember and use. It executes the action represented by the ActionRequest descriptor. An `ActionRequest` can be either its full XML id, its postgres id, the tag of the client action, or an object fully describing the action. `ActionOptions` is ....... . The moment when the Promise is resolved is guaranteed only in the following crucial cases:

  - `ir.actions.report`: when the report is downloaded, or when the report is displayed in the DOM.
  - `ir.actions.act_window`: when the action is visible in the DOM.
  - `ir.actions.act_window_close`: when the dialog has been closed. If there was no dialog, the Promise resolves immediately.
    For all other actions types, there are no guarantee of that precise moment.

- `switchView(viewType: viewType): void`: only applicable when the current visible action is an `ir.actions.act_window`. It switches the view to the target viewType. In principle, it shouldn't be used outside of frameworky developments.

- `restore(jsId: string): void;`: restores the controller with `jsId` from the breadcrumbs stack back in the DOM. It shouldn't be used outside of frameworky developments.

- `loadState(state: Route["hash"], options: ActionOptions): Promise<boolean>;`: an algorithm that decides what the action manager should do with the data present in the URL's hash. It returns a `boolean` wrapped in a Promise. The boolean indicates whether the action manager did handle the URL's state. This method must not be used.

## Technical notes

The action manager service tells the world that a rendering is necessary by triggering the
event `ACTION_MANAGER:UPDATE` on the [main bus](./../bus.md).
