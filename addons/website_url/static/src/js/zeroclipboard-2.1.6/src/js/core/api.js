/**
 * A shell constructor for `ZeroClipboard` client instances.
 *
 * @constructor
 */
var ZeroClipboard = function() {

  // Ensure the constructor is invoked with the `new` keyword.
  if (!(this instanceof ZeroClipboard)) {
    return new ZeroClipboard();
  }

  // EXTREMELY IMPORTANT!
  // Ensure the `ZeroClipboard._createClient` function is invoked if available.
  // This allows an extension point for 3rd parties to create their own
  // interpretations of what a ZeroClipboard "Client" should be like.
  if (typeof ZeroClipboard._createClient === "function") {
    ZeroClipboard._createClient.apply(this, _args(arguments));
  }

};


/**
 * The ZeroClipboard library's version number.
 *
 * @static
 * @readonly
 * @property {string}
 */
_defineProperty(ZeroClipboard, "version", {
  value: "<%= version %>",
  writable: false,
  configurable: true,
  enumerable: true
});


/**
 * Update or get a copy of the ZeroClipboard global configuration.
 * Returns a copy of the current/updated configuration.
 *
 * @returns Object
 * @static
 */
ZeroClipboard.config = function(/* options */) {
  return _config.apply(this, _args(arguments));
};


/**
 * Diagnostic method that describes the state of the browser, Flash Player, and ZeroClipboard.
 *
 * @returns Object
 * @static
 */
ZeroClipboard.state = function() {
  return _state.apply(this, _args(arguments));
};


/**
 * Check if Flash is unusable for any reason: disabled, outdated, deactivated, etc.
 *
 * @returns Boolean
 * @static
 */
ZeroClipboard.isFlashUnusable = function() {
  return _isFlashUnusable.apply(this, _args(arguments));
};


/**
 * Register an event listener.
 *
 * @returns `ZeroClipboard`
 * @static
 */
ZeroClipboard.on = function(/* eventType, listener */) {
  return _on.apply(this, _args(arguments));
};


/**
 * Unregister an event listener.
 * If no `listener` function/object is provided, it will unregister all listeners for the provided `eventType`.
 * If no `eventType` is provided, it will unregister all listeners for every event type.
 *
 * @returns `ZeroClipboard`
 * @static
 */
ZeroClipboard.off = function(/* eventType, listener */) {
  return _off.apply(this, _args(arguments));
};


/**
 * Retrieve event listeners for an `eventType`.
 * If no `eventType` is provided, it will retrieve all listeners for every event type.
 *
 * @returns array of listeners for the `eventType`; if no `eventType`, then a map/hash object of listeners for all event types; or `null`
 */
ZeroClipboard.handlers = function(/* eventType */) {
  return _listeners.apply(this, _args(arguments));
};


/**
 * Event emission receiver from the Flash object, forwarding to any registered JavaScript event listeners.
 *
 * @returns For the "copy" event, returns the Flash-friendly "clipData" object; otherwise `undefined`.
 * @static
 */
ZeroClipboard.emit = function(/* event */) {
  return _emit.apply(this, _args(arguments));
};


/**
 * Create and embed the Flash object.
 *
 * @returns The Flash object
 * @static
 */
ZeroClipboard.create = function() {
  return _create.apply(this, _args(arguments));
};


/**
 * Self-destruct and clean up everything, including the embedded Flash object.
 *
 * @returns `undefined`
 * @static
 */
ZeroClipboard.destroy = function() {
  return _destroy.apply(this, _args(arguments));
};


/**
 * Set the pending data for clipboard injection.
 *
 * @returns `undefined`
 * @static
 */
ZeroClipboard.setData = function(/* format, data */) {
  return _setData.apply(this, _args(arguments));
};


/**
 * Clear the pending data for clipboard injection.
 * If no `format` is provided, all pending data formats will be cleared.
 *
 * @returns `undefined`
 * @static
 */
ZeroClipboard.clearData = function(/* format */) {
  return _clearData.apply(this, _args(arguments));
};


/**
 * Get a copy of the pending data for clipboard injection.
 * If no `format` is provided, a copy of ALL pending data formats will be returned.
 *
 * @returns `String` or `Object`
 * @static
 */
ZeroClipboard.getData = function(/* format */) {
  return _getData.apply(this, _args(arguments));
};


/**
 * Sets the current HTML object that the Flash object should overlay. This will put the global
 * Flash object on top of the current element; depending on the setup, this may also set the
 * pending clipboard text data as well as the Flash object's wrapping element's title attribute
 * based on the underlying HTML element and ZeroClipboard configuration.
 *
 * @returns `undefined`
 * @static
 */
ZeroClipboard.focus = ZeroClipboard.activate = function(/* element */) {
  return _focus.apply(this, _args(arguments));
};


/**
 * Un-overlays the Flash object. This will put the global Flash object off-screen; depending on
 * the setup, this may also unset the Flash object's wrapping element's title attribute based on
 * the underlying HTML element and ZeroClipboard configuration.
 *
 * @returns `undefined`
 * @static
 */
ZeroClipboard.blur = ZeroClipboard.deactivate = function() {
  return _blur.apply(this, _args(arguments));
};


/**
 * Returns the currently focused/"activated" HTML element that the Flash object is wrapping.
 *
 * @returns `HTMLElement` or `null`
 * @static
 */
ZeroClipboard.activeElement = function() {
  return _activeElement.apply(this, _args(arguments));
};
