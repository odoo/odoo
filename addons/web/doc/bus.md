# Bus

The web client `env` contains an event bus, named `bus`. Its purpose is to allow
various parts of the system to properly coordinate themselves, without coupling
them. The `env.bus` is an owl `EventBus`, that should be used for global events
of interest.

## Message List

| Message                     | Payload                                                                                   | Triggered when:                                                     | Addon |
| --------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | ----- |
| `ACTION_MANAGER:UI-UPDATED` | a mode indicating what part of the ui has been updated ('current', 'new' or 'fullscreen') | the rendering of the action requested to the action manager is done | wowl  |
| `ACTION_MANAGER:UPDATE`     | next rendering info                                                                       | the action manager has finished computing the next interface        | wowl  |
| `MENUS:APP-CHANGED`         | none                                                                                      | the menu service's current app has changed                          | wowl  |
| `NOTIFICATIONS_CHANGE`      | list of notifications                                                                     | the list of notifications changes                                   | wowl  |
| `ROUTE_CHANGE`              | none                                                                                      | the url hash was changed                                            | wowl  |
| `RPC_ERROR`                 | error data object                                                                         | a rpc request (going through `rpc` service) fails                   | wowl  |
| `RPC:REQUEST`               | rpc id                                                                                    | a rpc request has just started                                      | wowl  |
| `RPC:RESPONSE`              | rpc id                                                                                    | a rpc request is completed                                          | wowl  |
| `WEB_CLIENT_READY`          | none                                                                                      | the web client has been mounted                                     | wowl  |
