# Browser

## Overview

The browser object is a part of the [environment](environment.md). It contains
all `window` API that perform some kind of side effects. This is useful when we
need to disable/configure/modify/react to any call to these APIs. It is also
necessary to be able to mock them properly in a test environment.

```ts
console.log(env.browser); // display the content of browser
```

## Exported values

Here is a list of all entities available in the `browser` object:

-   `Date`
-   `XMLHTTPRequest`
-   `clearInterval`
-   `clearTimeout`
-   `console`
-   `fetch`
-   `localStorage`
-   `location`
-   `random`
-   `requestAnimationFrame`
-   `setInterval`
-   `setTimeout`
