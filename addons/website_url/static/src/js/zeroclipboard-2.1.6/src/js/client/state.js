/**
 * Keep track of the ZeroClipboard client instance counter.
 */
var _clientIdCounter = 0;


/**
 * Keep track of the state of the client instances.
 *
 * Entry structure:
 *   _clientMeta[client.id] = {
 *     instance: client,
 *     elements: [],
 *     handlers: {}
 *   };
 */
var _clientMeta = {};


/**
 * Keep track of the ZeroClipboard clipped elements counter.
 */
var _elementIdCounter = 0;


/**
 * Keep track of the state of the clipped element relationships to clients.
 *
 * Entry structure:
 *   _elementMeta[element.zcClippingId] = [client1.id, client2.id];
 */
var _elementMeta = {};


/**
 * Keep track of the state of the mouse event handlers for clipped elements.
 *
 * Entry structure:
 *   _mouseHandlers[element.zcClippingId] = {
 *     mouseover:  function(event) {},
 *     mouseout:   function(event) {},
 *     mouseenter: function(event) {},
 *     mouseleave: function(event) {},
 *     mousemove:  function(event) {}
 *   };
 */
var _mouseHandlers = {};


/**
 * Extending the ZeroClipboard configuration defaults for the Client module.
 */
_extend(_globalConfig, {

  // Setting this to `false` would allow users to handle calling
  // `ZeroClipboard.focus(...);` themselves instead of relying on our
  // per-element `mouseover` handler.
  autoActivate: true

});
