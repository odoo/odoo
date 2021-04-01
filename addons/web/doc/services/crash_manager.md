# Crash Manager Service

| Technical name  | Dependencies                          |
| --------------- | ------------------------------------- |
| `crash_manager` | [`dialog_manager`](dialog_manager.md) |

## Overview

The `crash manager service` responsibility is to display a dialog
when an rpc error or a client error occurs. No interaction with the
crash manager is possible. If deployed, the crash manager simply listens
to some event and opens the appropriate dialogs when needed.

## API

The crash_manager service does not export anything.

## Channels

The crash manager receives errors throught two channels:

- it listens on `env.bus` the event `RPC_ERROR`;
- it listens on `window` the event `error`;

## RPC_ERROR event handling

When an event `RPC_ERROR` is triggerd on the bus, the crash manager processes the
`RPCError` in the following way:

- look if the error's `type` is `server`;

- if this is the case, the optional error's `name` indicates which [dialog class](./dialog_manager.md#api)
  (from the registry `errorDialogs`) should be used to display the error details.
  If the error is unnamed or no [dialog class]](./dialog_manager.md#api) corresponds to its name, the class
  `ErrorDialog` is used by default.

- The [dialog class](./dialog_manager.md#api) is instantiated with one prop: the error itself.

This is how a `UserError`, `AccessError`... or a custom server error is handled.

## ERROR event handlling

When an event `error` is triggered on window, the crash manager processes the `ErrorEvent`
received in the following way:

- if some information on the file name where the error occurs, the error stack... is available
  an `ErrorDialog` is displayed showing that information.

- if such information is not available, an `ErrorDialog` is also displayed but with a generic message.

This is how client errors are treated.
