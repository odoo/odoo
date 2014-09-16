/**
 * Keep track of the state of the Flash object.
 * @private
 */
var _flashState = {
  // Flash object reference
  bridge: null,

  // Flash metadata
  version: "0.0.0",
  pluginType: "unknown",

  // Flash SWF state
  disabled: null,
  outdated: null,
  unavailable: null,
  deactivated: null,
  overdue: null,
  ready: null
};


/**
 * The minimum Flash Player version required to use ZeroClipboard completely.
 * @readonly
 * @private
 */
var _minimumFlashVersion = "11.0.0";


/**
 * Keep track of all event listener registrations.
 * @private
 */
var _handlers = {};


/**
 * Keep track of the currently activated element.
 * @private
 */
var _currentElement;


/**
 * Keep track of the element that was activated when a `copy` process started.
 * @private
 */
var _copyTarget;


/**
 * Keep track of data for the pending clipboard transaction.
 * @private
 */
var _clipData = {};


/**
 * Keep track of data formats for the pending clipboard transaction.
 * @private
 */
var _clipDataFormatMap = null;


/**
 * The `message` store for events
 * @private
 */
var _eventMessages = {
  "ready": "Flash communication is established",
  "error": {
    "flash-disabled": "Flash is disabled or not installed",
    "flash-outdated": "Flash is too outdated to support ZeroClipboard",
    "flash-unavailable": "Flash is unable to communicate bidirectionally with JavaScript",
    "flash-deactivated": "Flash is too outdated for your browser and/or is configured as click-to-activate",
    "flash-overdue": "Flash communication was established but NOT within the acceptable time limit"
  }
};


/**
 * ZeroClipboard configuration defaults for the Core module.
 * @private
 */
var _globalConfig = {

  // SWF URL, relative to the page. Default value will be "ZeroClipboard.swf"
  // under the same path as the ZeroClipboard JS file.
  swfPath: _getDefaultSwfPath(),

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
  // Value is validated against the HTML4 spec for `ID` tokens.
  containerId: "global-zeroclipboard-html-bridge",
 
  // Sets the class of the `div` encapsulating the Flash object.
  containerClass: "global-zeroclipboard-container",
 
  // Sets the ID and name of the Flash `object` element.
  // Value is validated against the HTML4 spec for `ID` and `Name` tokens.
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
