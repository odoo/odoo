# Router service

| Technical name | Dependencies |
| -------------- | ------------ |
| `router`       |              |

## Overview

The `router` service provides three features:

-   information about the current route
-   provides a way for the application to update the url, depending on its state
-   listens to every hash change, and notifies the rest of the application

## Current route

The current route can be accessed with the `current` key. It contains the following
information:

-   `pathname (string)`: the path for the current location (most likely `/web`)
-   `search (object)`: a dictionary mapping each search keyword from the url to
    its value. An empty string is the value if no value was explicitely given
-   `hash (object)`: same as above, but for values described in the hash.

For example:

```js
// url = /web?debug=assets#action=123&owl&menu_id=174

const { pathname, search, hash } = env.services.router.current;
console.log(pathname); //   /web
console.log(search); //   { debug="assets" }
console.log(hash); //   { action:123, owl: "", menu_id: 174 }
```

## Updating the URL

URL updates need to use the `pushState` method:

```js
pushState(hash: object, replace?: boolean)
```

The `hash` argument is an object containing a mapping from some key to some values.
If a value is set to an empty string, the key will be simply added to the url
without any value at all.

If true, the `replace` argument tells the router that the url hash should be
completely replaced. Otherwise, the new values will be added to the current url.

For example:

```ts
// url = /web#action_id=123

env.services.router.pushState({ menu_id: 321 });
// url is now /web#action_id=123&menu_id=321

env.services.router.pushState({ yipyip: "" }, replace: true);
// url is now /web#yipyip
```

Note that using `pushState` does not trigger a `hashchange` event, nor a
`ROUTE_CHANGE` in the main bus. This is because this method is intended to be
used "from the inside", to update the url so that it matches the actual current
displayed state.

## Reacting to hash changes

This is mostly useful for the action manager, which needs to act when something
in the url changed.

When created, the router listens to every (external) hash changes, and trigger a
`ROUTE_CHANGE` event on the main bus,

## Redirect URL

The `redirect` method will redirect the browser to `url`. If `wait` is true, sleep 1s and wait for the server (e.g. after a restart).

```js
redirect(url: string, wait?: boolean)
```

For example:

```ts
// The complete url is "www.localhost/wowl"
env.services.router.redirect("/wowl/tests");

// The complete url is "www.localhost/wowl/tests"
```
