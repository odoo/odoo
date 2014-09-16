# ZeroClipboard.Core API

This documents details the **ZeroClipboard.Core** API, including various types of properties, methods, and events. **ZeroClipboard.Core** is primarily intended for use in wrapping ZeroClipboard in 3rd party plugins, e.g. [jquery.zeroclipboard](https://github.com/zeroclipboard/jquery.zeroclipboard).


## Static

### Static Properties

#### `ZeroClipboard.version`

_[`String`]_ The version of the ZeroClipboard library being used, e.g. `"2.0.0"`.


### Static Methods

#### `ZeroClipboard.config(...)`

```js
var config = ZeroClipboard.config();
```

_[`Object`]_ Get a copy of the active configuration for ZeroClipboard.


```js
var swfPath = ZeroClipboard.config("swfPath");
```

_[`*`]_ Get a copy of the actively configured value for this configuration property for ZeroClipboard.


```js
var config = ZeroClipboard.config({
  forceHandCursor: true
});
```

_[`Object`]_ Set the active configuration for ZeroClipboard. Returns a copy of the updated active configuration. For complete details about what can be configured, see [**Configuration Options** below](#configuration-options).


#### `ZeroClipboard.create()`
_[`undefined`]_ Create the Flash bridge SWF object.


#### `ZeroClipboard.destroy()`
_[`undefined`]_ Emit the [`"destroy"`](#destroy) event, remove all event handlers, and destroy the Flash bridge.


#### `ZeroClipboard.setData(...)`

```js
ZeroClipboard.setData("text/plain", "Blah");
```

_[`undefined`]_ Set the pending `data` of type `format` for clipboard injection.

```js
ZeroClipboard.setData({
  "text/plain": "Blah",
  "text/html": "<b>Blah</b>"
});
```

_[`undefined`]_ Set the pending `data` of various formats for clipboard injection.


#### `ZeroClipboard.clearData(...)`

```js
ZeroClipboard.clearData("text/plain");
```

_[`undefined`]_ Clear the pending data of type `format` for clipboard injection.

```js
ZeroClipboard.clearData();
```

_[`undefined`]_ Clear the pending data of ALL formats for clipboard injection.


#### `ZeroClipboard.getData(...)`

```js
var text = ZeroClipboard.getData("text/plain");
```

_[`String`]_ Get the pending data of type `format` for clipboard injection.

```js
var dataObj = ZeroClipboard.getData();
```

_[`Object`]_ Get a copy of the pending data of ALL formats for clipboard injection.


#### `ZeroClipboard.focus(...)`
#### `ZeroClipboard.activate(...)`

```js
ZeroClipboard.focus(document.getElementById("d_clip_button"));
```

_[`undefined`]_ Focus/"activate" the provided element by moving the Flash SWF object in front of it. **NOTE:** The preferred method to use is `focus` but the alias `activate` is available for backward compatibility's sake.


#### `ZeroClipboard.blur()`
#### `ZeroClipboard.deactivate()`

_[`undefined`]_ Blur/"deactivate" the currently focused/"activated" element, moving the Flash SWF object off the screen. **NOTE:** The preferred method to use is `blur` but the alias `deactivate` is available for backward compatibility's sake.


#### `ZeroClipboard.activeElement()`

```js
var el = document.getElementById("d_clip_button");
ZeroClipboard.focus(el);
var activeEl = ZeroClipboard.activeElement();  // activeEl === el
```

_[`HTMLElement` or `null`]_ Return the currently "activated" element that the Flash SWF object is in front of it.


#### `ZeroClipboard.state()`

_[`Object`]_ Diagnostic method that describes the state of the browser, Flash Player, and ZeroClipboard.


#### `ZeroClipboard.isFlashUnavailable()`

_[`Boolean`]_ Indicates if Flash Player is **definitely** unusable (disabled, outdated, unavailable, or deactivated). _**IMPORTANT:**_ This method should be considered private.


#### `ZeroClipboard.on(...)`

```js
var listenerFn = function(e) { var ZeroClipboard = this; /* ... */ };
ZeroClipboard.on("ready", listenerFn);

var listenerObj = {
  handleEvent: function(e) { var listenerObj = this; /* ... */ }
};
ZeroClipboard.on("error", listenerObj);
```

_[`undefined`]_ Add a `listener` function/object for an `eventType`.

```js
ZeroClipboard.on("ready error", function(e) { /* ... */ });
```

_[`undefined`]_ Add a `listener` function/object for multiple `eventType`s.

```js
ZeroClipboard.on({
  "ready": function(e) { /* ... */ },
  "error": function(e) { /* ... */ }
});
```

_[`undefined`]_ Add a set of `eventType` to `listener` function/object mappings.


#### `ZeroClipboard.off(...)`

```js
ZeroClipboard.off("ready", listenerFn);
ZeroClipboard.off("error", listenerObj);
```

_[`undefined`]_ Remove a `listener` function/object for an `eventType`.

```js
ZeroClipboard.off("ready error", listenerFn);
```

_[`undefined`]_ Remove a `listener` function/object for multiple `eventType`s.

```js
ZeroClipboard.off({
  "ready": readyListenerFn,
  "error": errorListenerFn
});
```

_[`undefined`]_ Remove a set of `eventType` to `listener` function/object mappings.

```js
ZeroClipboard.off("ready");
```

_[`undefined`]_ Remove ALL listener functions/objects for an `eventType`.

```js
ZeroClipboard.off();
```

_[`undefined`]_ Remove ALL listener functions/objects for ALL registered event types.


#### `ZeroClipboard.emit(...)`

```js
ZeroClipboard.emit("ready");
ZeroClipboard.emit({
  type: "error",
  name: "flash-disabled"
});

var pendingCopyData = ZeroClipboard.emit("copy");
```

_[`undefined`, or a Flash-friendly data Object for the `"copy"` event]_ Dispatch an event to all
registered listeners. The emission of some types of events will result in side effects.


#### `ZeroClipboard.handlers()`

```js
var listeners = ZeroClipboard.handlers("ready");
```

_[`Array`]_ Retrieves a copy of the registered listener functions/objects for the given `eventType`.


```js
var listeners = ZeroClipboard.handlers();
```

_[`Object`]_ Retrieves a copy of the map of registered listener functions/objects for ALL event types.



### Static Events

#### `"ready"`

The `ready` event is fired when the Flash SWF completes loading and is ready for action.  Please
note that you need to set most configuration options [with [`ZeroClipboard.config(...)`](#zeroclipboardconfig)]
before `ZeroClipboard.create()` is invoked.

```js
ZeroClipboard.on("ready", function(e) {
/*
  e = {
    type: "ready",
    message: "Flash communication is established",
    target: null,
    relatedTarget: null,
    currentTarget: flashSwfObjectRef,
    version: "11.2.202",
    timeStamp: Date.now()
  };
*/
});
```


#### `"beforecopy"`

On `click`, the Flash object will fire off a `beforecopy` event. This event is generally only
used for "UI prepartion" if you want to alter anything before the `copy` event fires.

**IMPORTANT:** Handlers of this event are expected to operate synchronously if they intend to be
finished before the "copy" event is triggered.

```js
ZeroClipboard.on("beforecopy", function(e) {
/*
  e = {
    type: "beforecopy",
    target: currentlyActivatedElementOrNull,
    relatedTarget: dataClipboardElementTargetOfCurrentlyActivatedElementOrNull,
    currentTarget: flashSwfObjectRef,
    timeStamp: Date.now()
  };
*/
});
```


#### `"copy"`

On `click` (and after the `beforecopy` event), the Flash object will fire off a `copy` event. If
the HTML object has `data-clipboard-text` or `data-clipboard-target`, then ZeroClipboard will take
care of getting an initial set of data. It will then invoke any `copy` event handlers, in which you
can call `event.clipboardData.setData` to set the text, which will complete the loop.

**IMPORTANT:** If a handler of this event intends to modify the pending data for clipboard
injection, it _MUST_ operate synchronously in order to maintain the temporarily elevated
permissions granted by the user's `click` event. The most common "gotcha" for this restriction is
if someone wants to make an asynchronous XMLHttpRequest in response to the `copy` event to get the
data to inject &mdash; this won't work; make it a _synchronous_ XMLHttpRequest instead, or do the
work in advance before the `copy` event is fired.

```js
ZeroClipboard.on("copy", function(e) {
/*
  e = {
    type: "copy",
    target: currentlyActivatedElementOrNull,
    relatedTarget: dataClipboardElementTargetOfCurrentlyActivatedElementOrNull,
    currentTarget: flashSwfObjectRef,
    timeStamp: Date.now(),
    clipboardData: {
      setData: ZeroClipboard.setData,
      clearData: ZeroClipboard.clearData
    }
  };
*/
});
```


#### `"aftercopy"`

The `aftercopy` event is fired when the text is copied [or failed to copy] to the clipboard.

```js
ZeroClipboard.on("aftercopy", function(e) {
/*
  e = {
    type: "aftercopy",
    target: currentlyActivatedElementOrNull,
    relatedTarget: dataClipboardElementTargetOfCurrentlyActivatedElementOrNull,
    currentTarget: flashSwfObjectRef,
    timeStamp: Date.now(),
    success: {
      "text/plain": true,
      "text/html": true,
      "application/rtf": false
    },
    data: {
      "text/plain": "Blah",
      "text/html": "<b>Blah</b>",
      "application/rtf": "{\\rtf1\\ansi\n{\\b Blah}}"
    }
  };
*/
});
```


#### `"destroy"`

The `destroy` event is fired when `ZeroClipboard.destroy()` is invoked.

**IMPORTANT:** Handlers of this event are expected to operate synchronously if they intend to be
finished before the destruction is complete.

```js
ZeroClipboard.on("destroy", function(e) {
/*
  e = {
    type: "destroy",
    target: null,
    relatedTarget: null,
    currentTarget: flashSwfObjectRef,
    timeStamp: Date.now(),
    success: {
      "text/plain": true,
      "text/html": true,
      "application/rtf": false
    },
    data: {
      "text/plain": "Blah",
      "text/html": "<b>Blah</b>",
      "application/rtf": "{\\rtf1\\ansi\n{\\b Blah}}"
    }
  };
*/
});
```


#### `"error"`

The `error` event is fired under a number of conditions, which will be detailed as sub-sections below.

Some consumers may not consider all `error` types to be critical, and thus ZeroClipboard does not take it upon
itself to implode by calling `ZeroClipboard.destroy()` under error conditions.  However, many consumers may
want to do just that.


##### `error[name = "flash-disabled"]`

This type of `error` event fires when Flash Player is either not installed or not enabled in the browser.

```js
ZeroClipboard.on("error", function(e) {
/*
  e = {
    type: "error",
    name: "flash-disabled",
    messsage: "Flash is disabled or not installed",
    target: null,
    relatedTarget: null,
    currentTarget: flashSwfObjectRef,
    timeStamp: Date.now(),
    minimumVersion: "11.0.0"
  };
*/
});
```


##### `error[name = "flash-outdated"]`

This type of `error` event fires when Flash Player is installed in the browser but the version is too old
for ZeroClipboard. ZeroClipboard requires Flash Player 11.0.0 or above.

```js
ZeroClipboard.on("error", function(e) {
/*
  e = {
    type: "error",
    name: "flash-outdated",
    messsage: "Flash is too outdated to support ZeroClipboard",
    target: null,
    relatedTarget: null,
    currentTarget: flashSwfObjectRef,
    timeStamp: Date.now(),
    minimumVersion: "11.0.0",
    version: "10.3.183"
  };
*/
});
```


##### `error[name = "flash-unavailable"]`

This type of `error` event fires when the browser's installation of Flash Player cannot communicate bidirectionally with JavaScript.

```js
ZeroClipboard.on("error", function(e) {
/*
  e = {
    type: "error",
    name: "flash-unavailable",
    messsage: "Flash is unable to communicate bidirectionally with JavaScript",
    target: null,
    relatedTarget: null,
    currentTarget: flashSwfObjectRef,
    timeStamp: Date.now(),
    minimumVersion: "11.0.0",
    version: "11.2.202"
  };
*/
});
```


##### `error[name = "flash-deactivated"]`

This type of `error` event fires when the browser's installation of Flash Player is either too old
for the browser [but _not_ too old for ZeroClipboard] or if Flash objects are configured as
click-to-play and the user does not authorize it within `_globalConfig.flashLoadTimeout`
milliseconds or does not authorize it at all.

```js
ZeroClipboard.on("error", function(e) {
/*
  e = {
    type: "error",
    name: "flash-deactivated",
    messsage: "Flash is too outdated for your browser and/or is configured as click-to-activate",
    target: null,
    relatedTarget: null,
    currentTarget: flashSwfObjectRef,
    timeStamp: Date.now(),
    minimumVersion: "11.0.0",
    version: "11.2.202"
  };
*/
});
```


##### `error[name = "flash-overdue"]`

This type of `error` event fires when the SWF loads successfully but takes longer than
`_globalConfig.flashLoadTimeout` milliseconds to do so. This would likely be caused by
one of the following situations:
 1. Too short of a `_globalConfig.flashLoadTimeout` duration configured
 2. Network latency
 3. The user's installation of Flash is configured as click-to-play but then authorized
    by the user too late such that the SWF does not finish loading before the timeout
    period has expired (or it may have expired before they authorized it at all).

The appropriate response to this event is left up to the consumer. For instance, if they
chose to invoke `ZeroClipboard.destroy()` in response to the earlier
`error[name = "flash-deactivated"]` event but then receive this `error[name = "flash-overdue"]`
event, they may choose to "restart" their process and construct new ZeroClipboard client instances,
or they may choose to just log the error to their server so they can consider increasing the
allowed timeout duration in the future.

This may be especially important for SPA or PJAX-based applications to consider as their users
may remain on a single page for an extended period of time during which they _possibly_ could
have enjoyed an improved experience if ZeroClipboard had been "restarted" after an initial hiccup.

```js
ZeroClipboard.on("error", function(e) {
/*
  e = {
    type: "error",
    name: "flash-overdue",
    messsage: "Flash communication was established but NOT within the acceptable time limit",
    target: null,
    relatedTarget: null,
    currentTarget: flashSwfObjectRef,
    timeStamp: Date.now(),
    minimumVersion: "11.0.0",
    version: "11.2.202"
  };
*/
});
```



## Configuration Options

These are default values for the global configurations options. You should generally update these _before_ you create your clients.

```js
var _globalConfig = {

  // SWF URL, relative to the page. Default value will be "ZeroClipboard.swf"
  // under the same path as the ZeroClipboard JS file.
  swfPath: _swfPath,

  // SWF inbound scripting policy: page domains that the SWF should trust.
  // (single string, or array of strings)
  trustedDomains: window.location.host ? [window.location.host] : [],

  // Include a "noCache" query parameter on requests for the SWF.
  cacheBust: true,

  // Enable use of the fancy "Desktop" clipboard, even on Linux where it is
  // known to suck.
  forceEnhancedClipboard: false,

  // How many milliseconds to wait for the Flash SWF to load and respond before assuming that
  // Flash is deactivated (e.g. click-to-play) in the user's browser. If you don't care about
  // how long it takes to load the SWF, you can set this to `null`.
  flashLoadTimeout: 30000,

  // Setting this to `false` would allow users to handle calling `ZeroClipboard.focus(...);`
  // themselves instead of relying on our per-element `mouseover` handler.
  autoActivate: true,

  // Bubble synthetic events in JavaScript after they are received by the Flash object.
  bubbleEvents: true,

  // Sets the ID of the `div` encapsulating the Flash object.
  // Value is validated against the [HTML4 spec for `ID` tokens][valid_ids].
  containerId: "global-zeroclipboard-html-bridge",
 
  // Sets the class of the `div` encapsulating the Flash object.
  containerClass: "global-zeroclipboard-container",
 
  // Sets the ID and name of the Flash `object` element.
  // Value is validated against the [HTML4 spec for `ID` and `Name` tokens][valid_ids].
  swfObjectId: "global-zeroclipboard-flash-bridge",

  // The class used to indicate that a clipped element is being hovered over.
  hoverClass: "zeroclipboard-is-hover",

  // The class used to indicate that a clipped element is active (is being clicked).
  activeClass: "zeroclipboard-is-active",



  // Forcibly set the hand cursor ("pointer") for all clipped elements.
  // IMPORTANT: This configuration value CAN be modified while a SWF is actively embedded.
  forceHandCursor: false,

  // Sets the title of the `div` encapsulating the Flash object.
  // IMPORTANT: This configuration value CAN be modified while a SWF is actively embedded.
  title: null,

  // The z-index used by the Flash object.
  // Max value (32-bit): 2147483647.
  // IMPORTANT: This configuration value CAN be modified while a SWF is actively embedded.
  zIndex: 999999999

};
```

You can override the defaults by making calls like `ZeroClipboard.config({ swfPath: "new/path" });`
before you create any clients.


### SWF Inbound Scripting Access: The `trustedDomains` option

This allows other SWF files and HTML pages from the allowed domains to access/call publicly
exposed ActionScript code, e.g. functions shared via `ExternalInterface.addCallback`. In other
words, it controls the SWF inbound scripting access.

If your ZeroClipboard SWF is served from a different origin/domain than your page, you need to tell
the SWF that it's OK to trust your page. The default value of `[window.location.host]` is almost
_**always**_ what you will want unless you specifically want the SWF to communicate with pages from
other domains (e.g. in `iframe`s or child windows).

For more information about trusted domains, consult the [_official Flash documentation for `flash.system.Security.allowDomain(...)`_](http://help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/flash/system/Security.html#allowDomain\(\)).


### SWF Outbound Scripting Access

The `allowScriptAccess` parameter (for Flash embedding markup) allows the SWF file to access/call
JavaScript/HTML functionality of HTML pages on allowed domains, e.g. invoking functions via
`ExternalInterface.call`. In other words, it controls the SWF outbound scripting access.

As of version `v2.0.0-alpha.2`, the `allowScriptAccess` configuration option no longer exists. The
appropriate value will be determined immediately before the Flash object is embedded on the page.
The value is based on a relationship between the current domain (`window.location.host`) and the
value of the `trustedDomains` configuration option.

For more information about `allowScriptAccess`, consult the [_official Flash documentation_](http://helpx.adobe.com/flash/kb/control-access-scripts-host-web.html).


### Cross-Protocol Limitations

ZeroClipboard was intentionally configured to _not_ allow the SWF to be served from a secure domain (HTTPS) but scripted by an insecure domain (HTTP).

If you find yourself in this situation (as in [Issue #170](https://github.com/zeroclipboard/zeroclipboard/issues/170)), please consider the following options:  
 1. Serve the SWF over HTTP instead of HTTPS. If the page's protocol can vary (e.g. authorized/unauthorized, staging/production, etc.), you should include add the SWF with a relative protocol (`//s3.amazonaws.com/blah/ZeroClipboard.swf`) instead of an absolute protocol (`https://s3.amazonaws.com/blah/ZeroClipboard.swf`).
 2. Serve the page over HTTPS instead of HTTP. If the page's protocol can vary, see the note on the previous option (1).
 3. Update ZeroClipboard's ActionScript codebase to call the [`allowInsecureDomain`](http://help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/flash/system/Security.html#allowInsecureDomain\(\)) method, then recompile the SWF with your custom changes.


### `file://` Protocol Limitations

If you want to host a page locally on the `file://` protocol, you must specifically configure
ZeroClipboard to trust ALL domains for SWF interaction via a wildcard. This configuration must be
set _before_ creating ZeroClipboard client instances as a typical consumer, or before calling
`ZeroClipboard.create()` in a 3rd party wrapper:

```js
ZeroClipboard.config({ trustedDomains: ["*"] });
```

This wildcard configuration should _**NOT**_ be used in environments hosted over HTTP/HTTPS.


## Extending `ZeroClipboard`

For developers who want to wrap ZeroClipboard into a 3rd party plugin
(e.g. [jquery.zeroclipboard](https://github.com/zeroclipboard/jquery.zeroclipboard)), here
are the important extension points:


### Constructor

Although the root `ZeroClipboard` function itself is actually a constructor, it also contains a
particular hook that checks for the existence of a `ZeroClipboard._createClient` static function
and invokes it with `this` (the freshly created `ZeroClipboard` instance) as the context and passes
along all provided arguments to the constructor function, e.g.:

```js
var counterId = 0;
ZeroClipboard._createClient = function(elements, otherStuff, etc) {
  this.id = "" + (counterId++);
  /* ... */
};

var $elementsToOperateOn = $(".clip_button");

var client = new ZeroClipboard($elementsToOperateOn);
```


### Prototype Chain

Using the `ZeroClipboard` constructor will allow you to also extend the underlying prototype with
new instance-based methods, e.g.:

```js
ZeroClipboard.prototype.clientEmitOrSomeOtherOperationToInvoke = function(e) {
  e.client = this;
};
```


### Eventing

Most clients will want to listen for some or all of the `ZeroClipboard.Core` events, and some
clients will even want to regurgitate the same events to their own client-based listeners. To
make the latter easier, `ZeroClipboard.Core` will also allow you to add a listener to an
`eventType` of `"*"`, e.g.:

```js
ZeroClipboard._createClient = function() {
  var client = this;
  ZeroClipboard.on("*", function(e) {
    client.clientEmitOrSomeOtherOperationToInvoke(e);
  });
};
```


### Static Extension

The `ZeroClipboard.Core` API is composed of static methods stored as properties of the
root `ZeroClipboard` function. As such, additional static methods can be added as desired, if there
is any actual benefit to doing so, e.g.:

```js
ZeroClipboard.log = function() {
  if (typeof console !== "undefined" && console.log) {
    console.log.apply(console, Array.prototype.slice.call(arguments, 0));
  }
};
```
