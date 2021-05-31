# RPC service

| Technical name | Dependencies    |
| -------------- | --------------- |
| `rpc`          | `notifications` |

## Overview

The RPC service has a single purpose: send requests to the server. Its external
API is a single function, with the following type:

```ts
type RPC = (route: string, params?: { [key: string]: any }) => Promise<any>;
```

This makes it easy to use. For example, calling a controller `/some/route` can
be done with the following code:

```ts
class MyComponent extends Component {
    rpc = useService("rpc");

    async someMethod() {
        const result = await this.rpc("/some/route");
    }
}
```

Note that the `rpc` service is considered a low-level service. It should only be
used to interact with Odoo controllers. To work with models (which is by far the
most important usecase), one should use the [`model`](model.md) service instead.

## Calling a controller

As explained in the overview, calling a controller is very simple. The route
should be the first argument, and optionally, a `params` object can be given as
a second argument.

```ts
const result = await this.rpc("/my/route", { some: "value" });
```

## Technical notes

-   The `rpc` service communicates with the server by using a `XMLHTTPRequest` object,
    configured to work with `application/json` content type.
-   So clearly the content of the request should be JSON serializable.
-   Each request done by this service uses the `POST` http method
-   Server errors actually return the response with an http code 200. But the `rpc`
    service will treat them as error (see below)

## Error Handling

An rpc can fail for two main reasons:

-   either the odoo server returns an error (so, we call this a `server` error).
    In that case the http request will return with am http code 200 BUT with a
    response object containing an `error` key.
-   or there is some other kind of network error

When a rpc fails, then:

-   the promise representing the rpc is rejected, so the calling code will crash,
    unless it handles the situation
-   an event `RPC_ERROR` is triggered on the main application bus. The event payload
    contains a description of the cause of the error:

    If it is a server error (the server code threw an exception). In that case
    the event payload will be an object with the following keys:

    -   `type = 'server'`
    -   `message(string)`
    -   `code(number)`

    -   `name(string)` (optional, used by the crash manager to look for an appropriate
        dialog to use when handling the error)
    -   `subType(string)` (optional, often used to determine the dialog title)
    -   `data(object)` (optional object that can contain various keys among which
        `debug`: the main debug information, with the call stack)

    If it is a network error, then the error description is simply an object
    `{type: 'network'}`.
    When a network error occurs, a notification is displayed and the server is regularly
    contacted until it responds. The notification is closed as soon as the server responds.

## Specialized behaviour for components

The `rpc` service has a specific optimization to make using it with component safer. It
does two things:

-   if a component is destroyed at the moment an rpc is initiated, an error will
    be thrown. This is considered an error, a destroyed component should be inert.
-   if a component is destroyed when a rpc is completed, which is a normal situation
    in an application, then the promise is simply left pending, to prevent any
    followup code to execute.
