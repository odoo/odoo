# Crash Manager and Errors

## Overview

Odoo comes with a crash manager. It is a system that catch all errors that have bubbled up uncaught and show a special dialog with information to help debug the problem. It's the first and simplest way for clients to report a problem and provide useful information on the crash.

As a developer, there's very few chances you will have to touch to the crash manager code. Especially if you're a backend developer. However, a good understanding of it's inner workings and how to throw errors will help you right better code.

Note: if you're a backend dev just willing to display a different dialog from an RPC error, make sure to read the `RPC Errors` section.

## The net and the dispatcher

Any error that is not caugh (meaning that is is not handled by a try / catch block for example) will eventually bubble up all the way until it reaches what we call the net. The net is made of event listeners on the global window object, listening for errors and rejected promises. The net is an analogy to a safety net that would catch things at the last moment. Once caught, the error is cast if needed to an instance of OdooError and send with the bus to the error dispatcher.

```js
// this is pseudo code
window.addEventListener((bubbledUpErrorEvent) => {
    const error: OdooError = someCodeThatCastTheError(bubbledUpErrorEvent.error);
    bus.trigger("ERROR_DISPATCH", error);
});
```

The dispatcher will then use the error type to take action. Most of the time, it is just showing a different dialog.

```js
// this is pseudo code
bus.on(ERROR_DISPATCH, (error) => {
    switch (error.type) {
        case "SERVER_ERROR":
            dialog_service.open(ServerErrorDialog, {
                // props ...
            });
            break;
        case "CORS_ERROR":
            dialog_service.open(ClientErrorDialog, {
                // props ...
            });
            break;
        default:
            dialog_service.open(ErrorDialog, {
                // props ...
            });
            break;
    }
});
```

## OdooError

A new error class is introduced, the `OdooError`. This class inherits `Error`, and add a few properties that let one customize what will be shown in an error dialog. Note that throwing an instance of the class `Error` in your javascript code is still valid and its message and stack argument will be correctly used. The name of the error will simply fallback to `DEFAULT_ERROR`, which is less explicit than another name.

An `OdooError` expects a name as constructor argument. The name should shortly and explicitly define the kind of error that is thrown.

```js
const error = new OdooError("XHR_NETWORK_ERROR");
```

Then, you can (and should!) add some more metadata:

```js
error.message = _lt("The server couldn't be reached, you may want to check your connection...");
error.traceback = "Custom traceback";
```

Important note: you may not want to have a custom traceback. Javascript `Error` have a `stack` property that gets automatically populate. So unless you have a good reason to add a custom tracaback, simply let it empty, so the crash manager falls back to the special `stack` property.

With all that, your error will be shown in a dailog component. Which one ? It depends. By default, the `ErrorDialog` component is used. However, if the dispatcher has a case for this error name, it may be shown in a different dialog, like in this case, a `ServerDialogError` perhaps.

```js
// this is pseudo code
bus.on(ERROR_DISPATCH, error => {
    // ...
    case 'XHR_NETWORK_ERROR':
        dialog_service.open(ServerErrorDialog, {
            // props ...
        })
        break;
    // ...
})
```

What if you want a dialog that is not the simple `ErrorDialog` component but your error name is not part of the switch ? Let's say `UNIQUE_JS_ERROR_THAT_ONLY_OCCURS_AT_ONE_PLACE`. Do not jump in the switch and add a case for this error. The switch should be kept for the most common errors.
There's an alternative to map an OdooError to anoter dialog:

```js
error.component = SomeOtherDialogComponentClass;
```

With this, you instruct the crash manager to use this component that you may even have created yourself.
So, the rule is:

1. Any error: you don't mind it used the `ErrorDialog` ? Let it be, you're done.
2. Common error: there should be a error name that fits your need, like `SERVER_ERROR`, `CORS_ERROR`, etc.
3. New common error: it does not have a case in the switch yet. We should add it.
4. Uncommon error: we shouldn't add it to the switch, use the `component` on the `OdooError` class.

## RPC Errors

In odoo, most of the interactions client <=> server are made using the RPC service. The RPC service is taylored to accept and parse error from the python code. All the errors coming from the RPCs will be instances of `RPCError` that inherits directly from `OdooError`. You will never have to instanciate an `RPCError`. Just know it contains all the server metadata about an error.
What is interesting to know is how can you, as a backend dev, show a custom dialog depending on python error that occured during the RPC.
Most of the other sections of this doc are irrelevent to your case. Indeed, the dispatcher is already ready to get an `RPCError` error name, and will display correctly the `RPCErrorDialog` component.

However, the `RPCError` has a property called `exception_class`. This would contain the full python exception class name. By example, `odoo.exceptions.AccessError`. And there is a regestry mapping python error name to a dialog object.

```js
export const errorDialogRegistry: Registry<Type<Component>> = new Registry();
errorDialogRegistry
    // ...
    .add("odoo.exceptions.AccessDenied", WarningDialog)
    .add("odoo.exceptions.AccessError", WarningDialog)
    .add("odoo.exceptions.RedirectWarning", RedirectWarningDialog)
    .add("odoo.http.SessionExpiredException", SessionExpiredDialog)
    .add("werkzeug.exceptions.Forbidden", SessionExpiredDialog)
    .add("504", Error504Dialog);
// ...
```

You can therefore add to this registry a new mapping.

Little recap: you want to add a custom dialog from a python error happening during an RPC ?

```js
errorDialogRegistry.add("odoo.exceptions.SomeServerError", SomeDialogError);
```

That's it. It should work.

## Advanced case: what are \_t or \_lt is not easily available for the error message ?

In those cases, maybe it's best to have a dialog specificely for your error (or category of error). Because components have an env and have the method `_t`.
