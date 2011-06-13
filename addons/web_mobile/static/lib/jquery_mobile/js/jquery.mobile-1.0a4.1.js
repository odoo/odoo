/*!
 * jQuery Mobile v1.0a4.1
 * http://jquerymobile.com/
 *
 * Copyright 2010, jQuery Project
 * Dual licensed under the MIT or GPL Version 2 licenses.
 * http://jquery.org/license
 */
/*!
 * jQuery UI Widget @VERSION
 *
 * Copyright 2010, AUTHORS.txt (http://jqueryui.com/about)
 * Dual licensed under the MIT or GPL Version 2 licenses.
 * http://jquery.org/license
 *
 * http://docs.jquery.com/UI/Widget
 */
(function( $, undefined ) {

// jQuery 1.4+
if ( $.cleanData ) {
	var _cleanData = $.cleanData;
	$.cleanData = function( elems ) {
		for ( var i = 0, elem; (elem = elems[i]) != null; i++ ) {
			$( elem ).triggerHandler( "remove" );
		}
		_cleanData( elems );
	};
} else {
	var _remove = $.fn.remove;
	$.fn.remove = function( selector, keepData ) {
		return this.each(function() {
			if ( !keepData ) {
				if ( !selector || $.filter( selector, [ this ] ).length ) {
					$( "*", this ).add( [ this ] ).each(function() {
						$( this ).triggerHandler( "remove" );
					});
				}
			}
			return _remove.call( $(this), selector, keepData );
		});
	};
}

$.widget = function( name, base, prototype ) {
	var namespace = name.split( "." )[ 0 ],
		fullName;
	name = name.split( "." )[ 1 ];
	fullName = namespace + "-" + name;

	if ( !prototype ) {
		prototype = base;
		base = $.Widget;
	}

	// create selector for plugin
	$.expr[ ":" ][ fullName ] = function( elem ) {
		return !!$.data( elem, name );
	};

	$[ namespace ] = $[ namespace ] || {};
	$[ namespace ][ name ] = function( options, element ) {
		// allow instantiation without initializing for simple inheritance
		if ( arguments.length ) {
			this._createWidget( options, element );
		}
	};

	var basePrototype = new base();
	// we need to make the options hash a property directly on the new instance
	// otherwise we'll modify the options hash on the prototype that we're
	// inheriting from
//	$.each( basePrototype, function( key, val ) {
//		if ( $.isPlainObject(val) ) {
//			basePrototype[ key ] = $.extend( {}, val );
//		}
//	});
	basePrototype.options = $.extend( true, {}, basePrototype.options );
	$[ namespace ][ name ].prototype = $.extend( true, basePrototype, {
		namespace: namespace,
		widgetName: name,
		widgetEventPrefix: $[ namespace ][ name ].prototype.widgetEventPrefix || name,
		widgetBaseClass: fullName
	}, prototype );

	$.widget.bridge( name, $[ namespace ][ name ] );
};

$.widget.bridge = function( name, object ) {
	$.fn[ name ] = function( options ) {
		var isMethodCall = typeof options === "string",
			args = Array.prototype.slice.call( arguments, 1 ),
			returnValue = this;

		// allow multiple hashes to be passed on init
		options = !isMethodCall && args.length ?
			$.extend.apply( null, [ true, options ].concat(args) ) :
			options;

		// prevent calls to internal methods
		if ( isMethodCall && options.charAt( 0 ) === "_" ) {
			return returnValue;
		}

		if ( isMethodCall ) {
			this.each(function() {
				var instance = $.data( this, name );
				if ( !instance ) {
					throw "cannot call methods on " + name + " prior to initialization; " +
						"attempted to call method '" + options + "'";
				}
				if ( !$.isFunction( instance[options] ) ) {
					throw "no such method '" + options + "' for " + name + " widget instance";
				}
				var methodValue = instance[ options ].apply( instance, args );
				if ( methodValue !== instance && methodValue !== undefined ) {
					returnValue = methodValue;
					return false;
				}
			});
		} else {
			this.each(function() {
				var instance = $.data( this, name );
				if ( instance ) {
					instance.option( options || {} )._init();
				} else {
					$.data( this, name, new object( options, this ) );
				}
			});
		}

		return returnValue;
	};
};

$.Widget = function( options, element ) {
	// allow instantiation without initializing for simple inheritance
	if ( arguments.length ) {
		this._createWidget( options, element );
	}
};

$.Widget.prototype = {
	widgetName: "widget",
	widgetEventPrefix: "",
	options: {
		disabled: false
	},
	_createWidget: function( options, element ) {
		// $.widget.bridge stores the plugin instance, but we do it anyway
		// so that it's stored even before the _create function runs
		$.data( element, this.widgetName, this );
		this.element = $( element );
		this.options = $.extend( true, {},
			this.options,
			this._getCreateOptions(),
			options );

		var self = this;
		this.element.bind( "remove." + this.widgetName, function() {
			self.destroy();
		});

		this._create();
		this._trigger( "create" );
		this._init();
	},
	_getCreateOptions: function() {
		var options = {};
		if ( $.metadata ) {
			options = $.metadata.get( element )[ this.widgetName ];
		}
		return options;
	},
	_create: function() {},
	_init: function() {},

	destroy: function() {
		this.element
			.unbind( "." + this.widgetName )
			.removeData( this.widgetName );
		this.widget()
			.unbind( "." + this.widgetName )
			.removeAttr( "aria-disabled" )
			.removeClass(
				this.widgetBaseClass + "-disabled " +
				"ui-state-disabled" );
	},

	widget: function() {
		return this.element;
	},

	option: function( key, value ) {
		var options = key;

		if ( arguments.length === 0 ) {
			// don't return a reference to the internal hash
			return $.extend( {}, this.options );
		}

		if  (typeof key === "string" ) {
			if ( value === undefined ) {
				return this.options[ key ];
			}
			options = {};
			options[ key ] = value;
		}

		this._setOptions( options );

		return this;
	},
	_setOptions: function( options ) {
		var self = this;
		$.each( options, function( key, value ) {
			self._setOption( key, value );
		});

		return this;
	},
	_setOption: function( key, value ) {
		this.options[ key ] = value;

		if ( key === "disabled" ) {
			this.widget()
				[ value ? "addClass" : "removeClass"](
					this.widgetBaseClass + "-disabled" + " " +
					"ui-state-disabled" )
				.attr( "aria-disabled", value );
		}

		return this;
	},

	enable: function() {
		return this._setOption( "disabled", false );
	},
	disable: function() {
		return this._setOption( "disabled", true );
	},

	_trigger: function( type, event, data ) {
		var callback = this.options[ type ];

		event = $.Event( event );
		event.type = ( type === this.widgetEventPrefix ?
			type :
			this.widgetEventPrefix + type ).toLowerCase();
		data = data || {};

		// copy original event properties over to the new event
		// this would happen if we could call $.event.fix instead of $.Event
		// but we don't have a way to force an event to be fixed multiple times
		if ( event.originalEvent ) {
			for ( var i = $.event.props.length, prop; i; ) {
				prop = $.event.props[ --i ];
				event[ prop ] = event.originalEvent[ prop ];
			}
		}

		this.element.trigger( event, data );

		return !( $.isFunction(callback) &&
			callback.call( this.element[0], event, data ) === false ||
			event.isDefaultPrevented() );
	}
};

})( jQuery );
/*
* jQuery Mobile Framework : widget factory extentions for mobile
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/
(function($, undefined ) {

$.widget( "mobile.widget", {
	_getCreateOptions: function() {
		var elem = this.element,
			options = {};
		$.each( this.options, function( option ) {
			var value = elem.jqmData( option.replace( /[A-Z]/g, function( c ) {
				return "-" + c.toLowerCase();
			} ) );
			if ( value !== undefined ) {
				options[ option ] = value;
			}
		});
		return options;
	}
});

})( jQuery );
/*
* jQuery Mobile Framework : resolution and CSS media query related helpers and behavior
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/
(function($, undefined ) {

var $window = $(window),
	$html = $( "html" ),

	//media-query-like width breakpoints, which are translated to classes on the html element
	resolutionBreakpoints = [320,480,768,1024];


/* $.mobile.media method: pass a CSS media type or query and get a bool return
	note: this feature relies on actual media query support for media queries, though types will work most anywhere
	examples:
		$.mobile.media('screen') //>> tests for screen media type
		$.mobile.media('screen and (min-width: 480px)') //>> tests for screen media type with window width > 480px
		$.mobile.media('@media screen and (-webkit-min-device-pixel-ratio: 2)') //>> tests for webkit 2x pixel ratio (iPhone 4)
*/
$.mobile.media = (function() {
	// TODO: use window.matchMedia once at least one UA implements it
	var cache = {},
		testDiv = $( "<div id='jquery-mediatest'>" ),
		fakeBody = $( "<body>" ).append( testDiv );

	return function( query ) {
		if ( !( query in cache ) ) {
			var styleBlock = document.createElement('style'),
        		cssrule = "@media " + query + " { #jquery-mediatest { position:absolute; } }";
	        //must set type for IE!	
	        styleBlock.type = "text/css";
	        if (styleBlock.styleSheet){ 
	          styleBlock.styleSheet.cssText = cssrule;
	        } 
	        else {
	          styleBlock.appendChild(document.createTextNode(cssrule));
	        } 
				
			$html.prepend( fakeBody ).prepend( styleBlock );
			cache[ query ] = testDiv.css( "position" ) === "absolute";
			fakeBody.add( styleBlock ).remove();
		}
		return cache[ query ];
	};
})();

/*
	private function for adding/removing breakpoint classes to HTML element for faux media-query support
	It does not require media query support, instead using JS to detect screen width > cross-browser support
	This function is called on orientationchange, resize, and mobileinit, and is bound via the 'htmlclass' event namespace
*/
function detectResolutionBreakpoints(){
	var currWidth = $window.width(),
		minPrefix = "min-width-",
		maxPrefix = "max-width-",
		minBreakpoints = [],
		maxBreakpoints = [],
		unit = "px",
		breakpointClasses;

	$html.removeClass( minPrefix + resolutionBreakpoints.join(unit + " " + minPrefix) + unit + " " +
		maxPrefix + resolutionBreakpoints.join( unit + " " + maxPrefix) + unit );

	$.each(resolutionBreakpoints,function( i, breakPoint ){
		if( currWidth >= breakPoint ){
			minBreakpoints.push( minPrefix + breakPoint + unit );
		}
		if( currWidth <= breakPoint ){
			maxBreakpoints.push( maxPrefix + breakPoint + unit );
		}
	});

	if( minBreakpoints.length ){ breakpointClasses = minBreakpoints.join(" "); }
	if( maxBreakpoints.length ){ breakpointClasses += " " +  maxBreakpoints.join(" "); }

	$html.addClass( breakpointClasses );
};

/* $.mobile.addResolutionBreakpoints method:
	pass either a number or an array of numbers and they'll be added to the min/max breakpoint classes
	Examples:
		$.mobile.addResolutionBreakpoints( 500 );
		$.mobile.addResolutionBreakpoints( [500, 1200] );
*/
$.mobile.addResolutionBreakpoints = function( newbps ){
	if( $.type( newbps ) === "array" ){
		resolutionBreakpoints = resolutionBreakpoints.concat( newbps );
	}
	else {
		resolutionBreakpoints.push( newbps );
	}
	resolutionBreakpoints.sort(function(a,b){ return a-b; });
	detectResolutionBreakpoints();
};

/* 	on mobileinit, add classes to HTML element
	and set handlers to update those on orientationchange and resize*/
$(document).bind("mobileinit.htmlclass", function(){
	/* bind to orientationchange and resize
	to add classes to HTML element for min/max breakpoints and orientation */
	$window.bind("orientationchange.htmlclass resize.htmlclass", function(event){
		//add orientation class to HTML element on flip/resize.
		if(event.orientation){
			$html.removeClass( "portrait landscape" ).addClass( event.orientation );
		}
		//add classes to HTML element for min/max breakpoints
		detectResolutionBreakpoints();
	});
});

/* Manually trigger an orientationchange event when the dom ready event fires.
   This will ensure that any viewport meta tag that may have been injected
   has taken effect already, allowing us to properly calculate the width of the
   document.
*/
$(function(){
	//trigger event manually
	$window.trigger( "orientationchange.htmlclass" );
});

})(jQuery);/*
* jQuery Mobile Framework : support tests
* Copyright (c) jQuery Project
* Dual licensed under the MIT (MIT-LICENSE.txt) and GPL (GPL-LICENSE.txt) licenses.
* Note: Code is in draft form and is subject to change 
*/
(function($, undefined ) {



var fakeBody = $( "<body>" ).prependTo( "html" ),
	fbCSS = fakeBody[0].style,
	vendors = ['webkit','moz','o'],
	webos = window.palmGetResource || window.PalmServiceBridge, //only used to rule out scrollTop 
	bb = window.blackberry; //only used to rule out box shadow, as it's filled opaque on BB

//thx Modernizr
function propExists( prop ){
	var uc_prop = prop.charAt(0).toUpperCase() + prop.substr(1),
		props   = (prop + ' ' + vendors.join(uc_prop + ' ') + uc_prop).split(' ');
	for(var v in props){
		if( fbCSS[ v ] !== undefined ){
			return true;
		}
	}
};

//test for dynamic-updating base tag support (allows us to avoid href,src attr rewriting)
function baseTagTest(){
	var fauxBase = location.protocol + '//' + location.host + location.pathname + "ui-dir/",
		base = $("head base"),
		fauxEle = null,
		href = '';
	if (!base.length) {
		base = fauxEle = $("<base>", {"href": fauxBase}).appendTo("head");
	}
	else {
		href = base.attr("href");
	}
	var link = $( "<a href='testurl'></a>" ).prependTo( fakeBody ),
		rebase = link[0].href;
	base[0].href = href ? href : location.pathname;
	if (fauxEle) {
		fauxEle.remove();
	}
	return rebase.indexOf(fauxBase) === 0;
};


//non-UA-based IE version check by James Padolsey, modified by jdalton - from http://gist.github.com/527683
//allows for inclusion of IE 6+, including Windows Mobile 7
$.mobile.browser = {};
$.mobile.browser.ie = (function() {
    var v = 3, div = document.createElement('div'), a = div.all || [];
    while (div.innerHTML = '<!--[if gt IE '+(++v)+']><br><![endif]-->', a[0]); 
    return v > 4 ? v : !v;
}());

$.extend( $.support, {
	orientation: "orientation" in window,
	touch: "ontouchend" in document,
	cssTransitions: "WebKitTransitionEvent" in window,
	pushState: !!history.pushState,
	mediaquery: $.mobile.media('only all'),
	cssPseudoElement: !!propExists('content'),
	boxShadow: !!propExists('boxShadow') && !bb,
	scrollTop: ("pageXOffset" in window || "scrollTop" in document.documentElement || "scrollTop" in fakeBody[0]) && !webos,
	dynamicBaseTag: baseTagTest(),
	eventCapture: ("addEventListener" in document) // This is a weak test. We may want to beef this up later.
});

fakeBody.remove();

//for ruling out shadows via css
if( !$.support.boxShadow ){ $('html').addClass('ui-mobile-nosupport-boxshadow'); }

})( jQuery );/*
* jQuery Mobile Framework : "mouse" plugin
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/

// This plugin is an experiment for abstracting away the touch and mouse
// events so that developers don't have to worry about which method of input
// the device their document is loaded on supports.
//
// The idea here is to allow the developer to register listeners for the
// basic mouse events, such as mousedown, mousemove, mouseup, and click,
// and the plugin will take care of registering the correct listeners
// behind the scenes to invoke the listener at the fastest possible time
// for that device, while still retaining the order of event firing in
// the traditional mouse environment, should multiple handlers be registered
// on the same element for different events.
//
// The current version exposes the following virtual events to jQuery bind methods:
// "vmouseover vmousedown vmousemove vmouseup vclick vmouseout vmousecancel"

(function($, window, document, undefined) {

var dataPropertyName = "virtualMouseBindings",
	touchTargetPropertyName = "virtualTouchID",
	virtualEventNames = "vmouseover vmousedown vmousemove vmouseup vclick vmouseout vmousecancel".split(" "),
	touchEventProps = "clientX clientY pageX pageY screenX screenY".split(" "),
	activeDocHandlers = {},
	resetTimerID = 0,
	startX = 0,
	startY = 0,
	startScrollX = 0,
	startScrollY = 0,
	didScroll = false,
	clickBlockList = [],
	blockMouseTriggers = false,
	scrollTopSupported = $.support.scrollTop,
	eventCaptureSupported = $.support.eventCapture,
	$document = $(document),
	nextTouchID = 1,
	lastTouchID = 0;

$.vmouse = {
	moveDistanceThreshold: 10,
	clickDistanceThreshold: 10,
	resetTimerDuration: 1500
};

function getNativeEvent(event)
{
	while (event && typeof event.originalEvent !== "undefined") {
		event = event.originalEvent;
	}
	return event;
}

function createVirtualEvent(event, eventType)
{
	var t = event.type;
	event = $.Event(event);
	event.type = eventType;
	
	var oe = event.originalEvent;
	var props = $.event.props;
	
	// copy original event properties over to the new event
	// this would happen if we could call $.event.fix instead of $.Event
	// but we don't have a way to force an event to be fixed multiple times
	if (oe) {
		for ( var i = props.length, prop; i; ) {
			prop = props[ --i ];
			event[prop] = oe[prop];
		}
	}
	
	if (t.search(/^touch/) !== -1){
		var ne = getNativeEvent(oe),
			t = ne.touches,
			ct = ne.changedTouches,
			touch = (t && t.length) ? t[0] : ((ct && ct.length) ? ct[0] : undefined);
		if (touch){
			for (var i = 0, len = touchEventProps.length; i < len; i++){
				var prop = touchEventProps[i];
				event[prop] = touch[prop];
			}
		}
	}

	return event;
}

function getVirtualBindingFlags(element)
{
	var flags = {};
	var $ele = $(element);
	while ($ele && $ele.length){
		var b = $ele.data(dataPropertyName);
		for (var k in b) {
			if (b[k]){
				flags[k] = flags.hasVirtualBinding = true;
			}
		}
		$ele = $ele.parent();
	}
	return flags;
}

function getClosestElementWithVirtualBinding(element, eventType)
{
	var $ele = $(element);
	while ($ele && $ele.length){
		var b = $ele.data(dataPropertyName);
		if (b && (!eventType || b[eventType])) {
			return $ele;
		}
		$ele = $ele.parent();
	}
	return null;
}

function enableTouchBindings()
{
	if (!activeDocHandlers["touchbindings"]){
		$document.bind("touchend", handleTouchEnd)
		
			// On touch platforms, touching the screen and then dragging your finger
			// causes the window content to scroll after some distance threshold is
			// exceeded. On these platforms, a scroll prevents a click event from being
			// dispatched, and on some platforms, even the touchend is suppressed. To
			// mimic the suppression of the click event, we need to watch for a scroll
			// event. Unfortunately, some platforms like iOS don't dispatch scroll
			// events until *AFTER* the user lifts their finger (touchend). This means
			// we need to watch both scroll and touchmove events to figure out whether
			// or not a scroll happenens before the touchend event is fired.
		
			.bind("touchmove", handleTouchMove)
			.bind("scroll", handleScroll);

		activeDocHandlers["touchbindings"] = 1;
	}
}

function disableTouchBindings()
{
	if (activeDocHandlers["touchbindings"]){
		$document.unbind("touchmove", handleTouchMove)
			.unbind("touchend", handleTouchEnd)
			.unbind("scroll", handleScroll);
		activeDocHandlers["touchbindings"] = 0;
	}
}

function enableMouseBindings()
{
	lastTouchID = 0;
	clickBlockList.length = 0;
	blockMouseTriggers = false;

	// When mouse bindings are enabled, our
	// touch bindings are disabled.
	disableTouchBindings();
}

function disableMouseBindings()
{
	// When mouse bindings are disabled, our
	// touch bindings are enabled.
	enableTouchBindings();
}

function startResetTimer()
{
	clearResetTimer();
	resetTimerID = setTimeout(function(){
		resetTimerID = 0;
		enableMouseBindings();
	}, $.vmouse.resetTimerDuration);
}

function clearResetTimer()
{
	if (resetTimerID){
		clearTimeout(resetTimerID);
		resetTimerID = 0;
	}
}

function triggerVirtualEvent(eventType, event, flags)
{
	var defaultPrevented = false;

	if ((flags && flags[eventType]) || (!flags && getClosestElementWithVirtualBinding(event.target, eventType))) {
		var ve = createVirtualEvent(event, eventType);
		$(event.target).trigger(ve);
		defaultPrevented = ve.isDefaultPrevented();
	}

	return defaultPrevented;
}

function mouseEventCallback(event)
{
	var touchID = $(event.target).data(touchTargetPropertyName);
	if (!blockMouseTriggers && (!lastTouchID || lastTouchID !== touchID)){
		triggerVirtualEvent("v" + event.type, event);
	}
}

function handleTouchStart(event)
{
	var touches = getNativeEvent(event).touches;
	if (touches && touches.length === 1){
		var target = event.target,
			flags = getVirtualBindingFlags(target);
	
		if (flags.hasVirtualBinding){
			lastTouchID = nextTouchID++;
			$(target).data(touchTargetPropertyName, lastTouchID);
	
			clearResetTimer();
			
			disableMouseBindings();
			didScroll = false;
			
			var t = getNativeEvent(event).touches[0];
			startX = t.pageX;
			startY = t.pageY;
		
			if (scrollTopSupported){
				startScrollX = window.pageXOffset;
				startScrollY = window.pageYOffset;
			}
		
			triggerVirtualEvent("vmouseover", event, flags);
			triggerVirtualEvent("vmousedown", event, flags);
		}
	}
}

function handleScroll(event)
{
	if (!didScroll){
		triggerVirtualEvent("vmousecancel", event, getVirtualBindingFlags(event.target));
	}

	didScroll = true;
	startResetTimer();
}

function handleTouchMove(event)
{
	var t = getNativeEvent(event).touches[0];

	var didCancel = didScroll,
		moveThreshold = $.vmouse.moveDistanceThreshold;
	didScroll = didScroll
		|| (scrollTopSupported && (startScrollX !== window.pageXOffset || startScrollY !== window.pageYOffset))
		|| (Math.abs(t.pageX - startX) > moveThreshold || Math.abs(t.pageY - startY) > moveThreshold);

	var flags = getVirtualBindingFlags(event.target);
	if (didScroll && !didCancel){
		triggerVirtualEvent("vmousecancel", event, flags);
	}
	triggerVirtualEvent("vmousemove", event, flags);
	startResetTimer();
}

function handleTouchEnd(event)
{
	disableTouchBindings();

	var flags = getVirtualBindingFlags(event.target);
	triggerVirtualEvent("vmouseup", event, flags);
	if (!didScroll){
		if (triggerVirtualEvent("vclick", event, flags)){
			// The target of the mouse events that follow the touchend
			// event don't necessarily match the target used during the
			// touch. This means we need to rely on coordinates for blocking
			// any click that is generated.
			var t = getNativeEvent(event).changedTouches[0];
			clickBlockList.push({ touchID: lastTouchID, x: t.clientX, y: t.clientY });

			// Prevent any mouse events that follow from triggering
			// virtual event notifications.
			blockMouseTriggers = true;
		}
	}
	triggerVirtualEvent("vmouseout", event, flags);
	didScroll = false;
	
	startResetTimer();
}

function hasVirtualBindings($ele)
{
	var bindings = $ele.data(dataPropertyName), k;
	if (bindings){
		for (k in bindings){
			if (bindings[k]){
				return true;
			}
		}
	}
	return false;
}

function dummyMouseHandler(){}

function getSpecialEventObject(eventType)
{
	var realType = eventType.substr(1);
	return {
		setup: function(data, namespace) {
			// If this is the first virtual mouse binding for this element,
			// add a bindings object to its data.

			var $this = $(this);

			if (!hasVirtualBindings($this)){
				$this.data(dataPropertyName, {});
			}

			// If setup is called, we know it is the first binding for this
			// eventType, so initialize the count for the eventType to zero.

			var bindings = $this.data(dataPropertyName);
			bindings[eventType] = true;

			// If this is the first virtual mouse event for this type,
			// register a global handler on the document.

			activeDocHandlers[eventType] = (activeDocHandlers[eventType] || 0) + 1;
			if (activeDocHandlers[eventType] === 1){
				$document.bind(realType, mouseEventCallback);
			}

			// Some browsers, like Opera Mini, won't dispatch mouse/click events
			// for elements unless they actually have handlers registered on them.
			// To get around this, we register dummy handlers on the elements.

			$this.bind(realType, dummyMouseHandler);

			// For now, if event capture is not supported, we rely on mouse handlers.
			if (eventCaptureSupported){
				// If this is the first virtual mouse binding for the document,
				// register our touchstart handler on the document.
	
				activeDocHandlers["touchstart"] = (activeDocHandlers["touchstart"] || 0) + 1;
				if (activeDocHandlers["touchstart"] === 1) {
					$document.bind("touchstart", handleTouchStart);
				}
			}
		},

		teardown: function(data, namespace) {
			// If this is the last virtual binding for this eventType,
			// remove its global handler from the document.

			--activeDocHandlers[eventType];
			if (!activeDocHandlers[eventType]){
				$document.unbind(realType, mouseEventCallback);
			}

			if (eventCaptureSupported){
				// If this is the last virtual mouse binding in existence,
				// remove our document touchstart listener.
	
				--activeDocHandlers["touchstart"];
				if (!activeDocHandlers["touchstart"]) {
					$document.unbind("touchstart", handleTouchStart);
				}
			}

			var $this = $(this),
				bindings = $this.data(dataPropertyName);
			bindings[eventType] = false;

			// Unregister the dummy event handler.

			$this.unbind(realType, dummyMouseHandler);

			// If this is the last virtual mouse binding on the
			// element, remove the binding data from the element.

			if (!hasVirtualBindings($this)){
				$this.removeData(dataPropertyName);
			}
		}
	};
}

// Expose our custom events to the jQuery bind/unbind mechanism.

for (var i = 0; i < virtualEventNames.length; i++){
	$.event.special[virtualEventNames[i]] = getSpecialEventObject(virtualEventNames[i]);
}

// Add a capture click handler to block clicks.
// Note that we require event capture support for this so if the device
// doesn't support it, we punt for now and rely solely on mouse events.
if (eventCaptureSupported){
	document.addEventListener("click", function(e){
		var cnt = clickBlockList.length;
		var target = e.target;
		if (cnt) {
			var x = e.clientX,
				y = e.clientY,
				threshold = $.vmouse.clickDistanceThreshold;

			// The idea here is to run through the clickBlockList to see if
			// the current click event is in the proximity of one of our
			// vclick events that had preventDefault() called on it. If we find
			// one, then we block the click.
			//
			// Why do we have to rely on proximity?
			//
			// Because the target of the touch event that triggered the vclick
			// can be different from the target of the click event synthesized
			// by the browser. The target of a mouse/click event that is syntehsized
			// from a touch event seems to be implementation specific. For example,
			// some browsers will fire mouse/click events for a link that is near
			// a touch event, even though the target of the touchstart/touchend event
			// says the user touched outside the link. Also, it seems that with most
			// browsers, the target of the mouse/click event is not calculated until the
			// time it is dispatched, so if you replace an element that you touched
			// with another element, the target of the mouse/click will be the new
			// element underneath that point.
			//
			// Aside from proximity, we also check to see if the target and any
			// of its ancestors were the ones that blocked a click. This is necessary
			// because of the strange mouse/click target calculation done in the
			// Android 2.1 browser, where if you click on an element, and there is a
			// mouse/click handler on one of its ancestors, the target will be the
			// innermost child of the touched element, even if that child is no where
			// near the point of touch.
			
			var ele = target;
			while (ele) {
				for (var i = 0; i < cnt; i++) {
					var o = clickBlockList[i],
						touchID = 0;
					if ((ele === target && Math.abs(o.x - x) < threshold && Math.abs(o.y - y) < threshold) || $(ele).data(touchTargetPropertyName) === o.touchID){
						// XXX: We may want to consider removing matches from the block list
						//      instead of waiting for the reset timer to fire.
						e.preventDefault();
						e.stopPropagation();
						return;
					}
				}
				ele = ele.parentNode;
			}
		}
	}, true);
}
})(jQuery, window, document);/*
* jQuery Mobile Framework : events
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/
(function($, undefined ) {

// add new event shortcuts
$.each( "touchstart touchmove touchend orientationchange tap taphold swipe swipeleft swiperight scrollstart scrollstop".split( " " ), function( i, name ) {
	$.fn[ name ] = function( fn ) {
		return fn ? this.bind( name, fn ) : this.trigger( name );
	};
	$.attrFn[ name ] = true;
});

var supportTouch = $.support.touch,
	scrollEvent = "touchmove scroll",
	touchStartEvent = supportTouch ? "touchstart" : "mousedown",
	touchStopEvent = supportTouch ? "touchend" : "mouseup",
	touchMoveEvent = supportTouch ? "touchmove" : "mousemove";

function triggerCustomEvent(obj, eventType, event)
{
	var originalType = event.type;
	event.type = eventType;
	$.event.handle.call( obj, event );
	event.type = originalType;
}

// also handles scrollstop
$.event.special.scrollstart = {
	enabled: true,
	
	setup: function() {
		var thisObject = this,
			$this = $( thisObject ),
			scrolling,
			timer;
		
		function trigger( event, state ) {
			scrolling = state;
			triggerCustomEvent( thisObject, scrolling ? "scrollstart" : "scrollstop", event );
		}
		
		// iPhone triggers scroll after a small delay; use touchmove instead
		$this.bind( scrollEvent, function( event ) {
			if ( !$.event.special.scrollstart.enabled ) {
				return;
			}
			
			if ( !scrolling ) {
				trigger( event, true );
			}
			
			clearTimeout( timer );
			timer = setTimeout(function() {
				trigger( event, false );
			}, 50 );
		});
	}
};

// also handles taphold
$.event.special.tap = {
	setup: function() {
		var thisObject = this,
			$this = $( thisObject );
		
		$this
			.bind("vmousedown", function( event ) {
				if ( event.which && event.which !== 1 ) {
					return false;
				}
				
				var touching = true,
					origTarget = event.target,
					origEvent = event.originalEvent,
					timer;
					
				function clearTapHandlers() {
					touching = false;
					clearTimeout(timer);
					$this.unbind("vclick", clickHandler).unbind("vmousecancel", clearTapHandlers);
				}
				
				function clickHandler(event) {
					clearTapHandlers();

					/* ONLY trigger a 'tap' event if the start target is
					 * the same as the stop target.
					 */
					if ( origTarget == event.target ) {
						triggerCustomEvent( thisObject, "tap", event );
					}
				}

				$this.bind("vmousecancel", clearTapHandlers).bind("vclick", clickHandler);

				timer = setTimeout(function() {
					if ( touching ) {
						triggerCustomEvent( thisObject, "taphold", event );
					}
				}, 750 );
			});
	}
};

// also handles swipeleft, swiperight
$.event.special.swipe = {
	setup: function() {
		var thisObject = this,
			$this = $( thisObject );
		
		$this
			.bind( touchStartEvent, function( event ) {
				var data = event.originalEvent.touches ?
						event.originalEvent.touches[ 0 ] :
						event,
					start = {
						time: (new Date).getTime(),
						coords: [ data.pageX, data.pageY ],
						origin: $( event.target )
					},
					stop;
				
				function moveHandler( event ) {
					if ( !start ) {
						return;
					}
					
					var data = event.originalEvent.touches ?
							event.originalEvent.touches[ 0 ] :
							event;
					stop = {
							time: (new Date).getTime(),
							coords: [ data.pageX, data.pageY ]
					};
					
					// prevent scrolling
					if ( Math.abs( start.coords[0] - stop.coords[0] ) > 10 ) {
						event.preventDefault();
					}
				}
				
				$this
					.bind( touchMoveEvent, moveHandler )
					.one( touchStopEvent, function( event ) {
						$this.unbind( touchMoveEvent, moveHandler );
						if ( start && stop ) {
							if ( stop.time - start.time < 1000 && 
									Math.abs( start.coords[0] - stop.coords[0]) > 30 &&
									Math.abs( start.coords[1] - stop.coords[1]) < 75 ) {
								start.origin
								.trigger( "swipe" )

								.trigger( start.coords[0] > stop.coords[0] ? "swipeleft" : "swiperight" );
							}
						}
						start = stop = undefined;
					});
			});
	}
};

(function($){
	// "Cowboy" Ben Alman
	
	var win = $(window),
		special_event,
		get_orientation,
		last_orientation;
	
	$.event.special.orientationchange = special_event = {
		setup: function(){
			// If the event is supported natively, return false so that jQuery
			// will bind to the event using DOM methods.
			if ( $.support.orientation ) { return false; }
			
			// Get the current orientation to avoid initial double-triggering.
			last_orientation = get_orientation();
			
			// Because the orientationchange event doesn't exist, simulate the
			// event by testing window dimensions on resize.
			win.bind( "resize", handler );
		},
		teardown: function(){
			// If the event is not supported natively, return false so that
			// jQuery will unbind the event using DOM methods.
			if ( $.support.orientation ) { return false; }
			
			// Because the orientationchange event doesn't exist, unbind the
			// resize event handler.
			win.unbind( "resize", handler );
		},
		add: function( handleObj ) {
			// Save a reference to the bound event handler.
			var old_handler = handleObj.handler;
			
			handleObj.handler = function( event ) {
				// Modify event object, adding the .orientation property.
				event.orientation = get_orientation();
				
				// Call the originally-bound event handler and return its result.
				return old_handler.apply( this, arguments );
			};
		}
	};
	
	// If the event is not supported natively, this handler will be bound to
	// the window resize event to simulate the orientationchange event.
	function handler() {
		// Get the current orientation.
		var orientation = get_orientation();
		
		if ( orientation !== last_orientation ) {
			// The orientation has changed, so trigger the orientationchange event.
			last_orientation = orientation;
			win.trigger( "orientationchange" );
		}
	};
	
	// Get the current page orientation. This method is exposed publicly, should it
	// be needed, as jQuery.event.special.orientationchange.orientation()
	special_event.orientation = get_orientation = function() {
		var elem = document.documentElement;
		return elem && elem.clientWidth / elem.clientHeight < 1.1 ? "portrait" : "landscape";
	};
	
})(jQuery);

$.each({
	scrollstop: "scrollstart",
	taphold: "tap",
	swipeleft: "swipe",
	swiperight: "swipe"
}, function( event, sourceEvent ) {
	$.event.special[ event ] = {
		setup: function() {
			$( this ).bind( sourceEvent, $.noop );
		}
	};
});

})( jQuery );
/*!
 * jQuery hashchange event - v1.3 - 7/21/2010
 * http://benalman.com/projects/jquery-hashchange-plugin/
 * 
 * Copyright (c) 2010 "Cowboy" Ben Alman
 * Dual licensed under the MIT and GPL licenses.
 * http://benalman.com/about/license/
 */

// Script: jQuery hashchange event
//
// *Version: 1.3, Last updated: 7/21/2010*
// 
// Project Home - http://benalman.com/projects/jquery-hashchange-plugin/
// GitHub       - http://github.com/cowboy/jquery-hashchange/
// Source       - http://github.com/cowboy/jquery-hashchange/raw/master/jquery.ba-hashchange.js
// (Minified)   - http://github.com/cowboy/jquery-hashchange/raw/master/jquery.ba-hashchange.min.js (0.8kb gzipped)
// 
// About: License
// 
// Copyright (c) 2010 "Cowboy" Ben Alman,
// Dual licensed under the MIT and GPL licenses.
// http://benalman.com/about/license/
// 
// About: Examples
// 
// These working examples, complete with fully commented code, illustrate a few
// ways in which this plugin can be used.
// 
// hashchange event - http://benalman.com/code/projects/jquery-hashchange/examples/hashchange/
// document.domain - http://benalman.com/code/projects/jquery-hashchange/examples/document_domain/
// 
// About: Support and Testing
// 
// Information about what version or versions of jQuery this plugin has been
// tested with, what browsers it has been tested in, and where the unit tests
// reside (so you can test it yourself).
// 
// jQuery Versions - 1.2.6, 1.3.2, 1.4.1, 1.4.2
// Browsers Tested - Internet Explorer 6-8, Firefox 2-4, Chrome 5-6, Safari 3.2-5,
//                   Opera 9.6-10.60, iPhone 3.1, Android 1.6-2.2, BlackBerry 4.6-5.
// Unit Tests      - http://benalman.com/code/projects/jquery-hashchange/unit/
// 
// About: Known issues
// 
// While this jQuery hashchange event implementation is quite stable and
// robust, there are a few unfortunate browser bugs surrounding expected
// hashchange event-based behaviors, independent of any JavaScript
// window.onhashchange abstraction. See the following examples for more
// information:
// 
// Chrome: Back Button - http://benalman.com/code/projects/jquery-hashchange/examples/bug-chrome-back-button/
// Firefox: Remote XMLHttpRequest - http://benalman.com/code/projects/jquery-hashchange/examples/bug-firefox-remote-xhr/
// WebKit: Back Button in an Iframe - http://benalman.com/code/projects/jquery-hashchange/examples/bug-webkit-hash-iframe/
// Safari: Back Button from a different domain - http://benalman.com/code/projects/jquery-hashchange/examples/bug-safari-back-from-diff-domain/
// 
// Also note that should a browser natively support the window.onhashchange 
// event, but not report that it does, the fallback polling loop will be used.
// 
// About: Release History
// 
// 1.3   - (7/21/2010) Reorganized IE6/7 Iframe code to make it more
//         "removable" for mobile-only development. Added IE6/7 document.title
//         support. Attempted to make Iframe as hidden as possible by using
//         techniques from http://www.paciellogroup.com/blog/?p=604. Added 
//         support for the "shortcut" format $(window).hashchange( fn ) and
//         $(window).hashchange() like jQuery provides for built-in events.
//         Renamed jQuery.hashchangeDelay to <jQuery.fn.hashchange.delay> and
//         lowered its default value to 50. Added <jQuery.fn.hashchange.domain>
//         and <jQuery.fn.hashchange.src> properties plus document-domain.html
//         file to address access denied issues when setting document.domain in
//         IE6/7.
// 1.2   - (2/11/2010) Fixed a bug where coming back to a page using this plugin
//         from a page on another domain would cause an error in Safari 4. Also,
//         IE6/7 Iframe is now inserted after the body (this actually works),
//         which prevents the page from scrolling when the event is first bound.
//         Event can also now be bound before DOM ready, but it won't be usable
//         before then in IE6/7.
// 1.1   - (1/21/2010) Incorporated document.documentMode test to fix IE8 bug
//         where browser version is incorrectly reported as 8.0, despite
//         inclusion of the X-UA-Compatible IE=EmulateIE7 meta tag.
// 1.0   - (1/9/2010) Initial Release. Broke out the jQuery BBQ event.special
//         window.onhashchange functionality into a separate plugin for users
//         who want just the basic event & back button support, without all the
//         extra awesomeness that BBQ provides. This plugin will be included as
//         part of jQuery BBQ, but also be available separately.

(function($,window,undefined){
  '$:nomunge'; // Used by YUI compressor.
  
  // Reused string.
  var str_hashchange = 'hashchange',
    
    // Method / object references.
    doc = document,
    fake_onhashchange,
    special = $.event.special,
    
    // Does the browser support window.onhashchange? Note that IE8 running in
    // IE7 compatibility mode reports true for 'onhashchange' in window, even
    // though the event isn't supported, so also test document.documentMode.
    doc_mode = doc.documentMode,
    supports_onhashchange = 'on' + str_hashchange in window && ( doc_mode === undefined || doc_mode > 7 );
  
  // Get location.hash (or what you'd expect location.hash to be) sans any
  // leading #. Thanks for making this necessary, Firefox!
  function get_fragment( url ) {
    url = url || location.href;
    return '#' + url.replace( /^[^#]*#?(.*)$/, '$1' );
  };
  
  // Method: jQuery.fn.hashchange
  // 
  // Bind a handler to the window.onhashchange event or trigger all bound
  // window.onhashchange event handlers. This behavior is consistent with
  // jQuery's built-in event handlers.
  // 
  // Usage:
  // 
  // > jQuery(window).hashchange( [ handler ] );
  // 
  // Arguments:
  // 
  //  handler - (Function) Optional handler to be bound to the hashchange
  //    event. This is a "shortcut" for the more verbose form:
  //    jQuery(window).bind( 'hashchange', handler ). If handler is omitted,
  //    all bound window.onhashchange event handlers will be triggered. This
  //    is a shortcut for the more verbose
  //    jQuery(window).trigger( 'hashchange' ). These forms are described in
  //    the <hashchange event> section.
  // 
  // Returns:
  // 
  //  (jQuery) The initial jQuery collection of elements.
  
  // Allow the "shortcut" format $(elem).hashchange( fn ) for binding and
  // $(elem).hashchange() for triggering, like jQuery does for built-in events.
  $.fn[ str_hashchange ] = function( fn ) {
    return fn ? this.bind( str_hashchange, fn ) : this.trigger( str_hashchange );
  };
  
  // Property: jQuery.fn.hashchange.delay
  // 
  // The numeric interval (in milliseconds) at which the <hashchange event>
  // polling loop executes. Defaults to 50.
  
  // Property: jQuery.fn.hashchange.domain
  // 
  // If you're setting document.domain in your JavaScript, and you want hash
  // history to work in IE6/7, not only must this property be set, but you must
  // also set document.domain BEFORE jQuery is loaded into the page. This
  // property is only applicable if you are supporting IE6/7 (or IE8 operating
  // in "IE7 compatibility" mode).
  // 
  // In addition, the <jQuery.fn.hashchange.src> property must be set to the
  // path of the included "document-domain.html" file, which can be renamed or
  // modified if necessary (note that the document.domain specified must be the
  // same in both your main JavaScript as well as in this file).
  // 
  // Usage:
  // 
  // jQuery.fn.hashchange.domain = document.domain;
  
  // Property: jQuery.fn.hashchange.src
  // 
  // If, for some reason, you need to specify an Iframe src file (for example,
  // when setting document.domain as in <jQuery.fn.hashchange.domain>), you can
  // do so using this property. Note that when using this property, history
  // won't be recorded in IE6/7 until the Iframe src file loads. This property
  // is only applicable if you are supporting IE6/7 (or IE8 operating in "IE7
  // compatibility" mode).
  // 
  // Usage:
  // 
  // jQuery.fn.hashchange.src = 'path/to/file.html';
  
  $.fn[ str_hashchange ].delay = 50;
  /*
  $.fn[ str_hashchange ].domain = null;
  $.fn[ str_hashchange ].src = null;
  */
  
  // Event: hashchange event
  // 
  // Fired when location.hash changes. In browsers that support it, the native
  // HTML5 window.onhashchange event is used, otherwise a polling loop is
  // initialized, running every <jQuery.fn.hashchange.delay> milliseconds to
  // see if the hash has changed. In IE6/7 (and IE8 operating in "IE7
  // compatibility" mode), a hidden Iframe is created to allow the back button
  // and hash-based history to work.
  // 
  // Usage as described in <jQuery.fn.hashchange>:
  // 
  // > // Bind an event handler.
  // > jQuery(window).hashchange( function(e) {
  // >   var hash = location.hash;
  // >   ...
  // > });
  // > 
  // > // Manually trigger the event handler.
  // > jQuery(window).hashchange();
  // 
  // A more verbose usage that allows for event namespacing:
  // 
  // > // Bind an event handler.
  // > jQuery(window).bind( 'hashchange', function(e) {
  // >   var hash = location.hash;
  // >   ...
  // > });
  // > 
  // > // Manually trigger the event handler.
  // > jQuery(window).trigger( 'hashchange' );
  // 
  // Additional Notes:
  // 
  // * The polling loop and Iframe are not created until at least one handler
  //   is actually bound to the 'hashchange' event.
  // * If you need the bound handler(s) to execute immediately, in cases where
  //   a location.hash exists on page load, via bookmark or page refresh for
  //   example, use jQuery(window).hashchange() or the more verbose 
  //   jQuery(window).trigger( 'hashchange' ).
  // * The event can be bound before DOM ready, but since it won't be usable
  //   before then in IE6/7 (due to the necessary Iframe), recommended usage is
  //   to bind it inside a DOM ready handler.
  
  // Override existing $.event.special.hashchange methods (allowing this plugin
  // to be defined after jQuery BBQ in BBQ's source code).
  special[ str_hashchange ] = $.extend( special[ str_hashchange ], {
    
    // Called only when the first 'hashchange' event is bound to window.
    setup: function() {
      // If window.onhashchange is supported natively, there's nothing to do..
      if ( supports_onhashchange ) { return false; }
      
      // Otherwise, we need to create our own. And we don't want to call this
      // until the user binds to the event, just in case they never do, since it
      // will create a polling loop and possibly even a hidden Iframe.
      $( fake_onhashchange.start );
    },
    
    // Called only when the last 'hashchange' event is unbound from window.
    teardown: function() {
      // If window.onhashchange is supported natively, there's nothing to do..
      if ( supports_onhashchange ) { return false; }
      
      // Otherwise, we need to stop ours (if possible).
      $( fake_onhashchange.stop );
    }
    
  });
  
  // fake_onhashchange does all the work of triggering the window.onhashchange
  // event for browsers that don't natively support it, including creating a
  // polling loop to watch for hash changes and in IE 6/7 creating a hidden
  // Iframe to enable back and forward.
  fake_onhashchange = (function(){
    var self = {},
      timeout_id,
      
      // Remember the initial hash so it doesn't get triggered immediately.
      last_hash = get_fragment(),
      
      fn_retval = function(val){ return val; },
      history_set = fn_retval,
      history_get = fn_retval;
    
    // Start the polling loop.
    self.start = function() {
      timeout_id || poll();
    };
    
    // Stop the polling loop.
    self.stop = function() {
      timeout_id && clearTimeout( timeout_id );
      timeout_id = undefined;
    };
    
    // This polling loop checks every $.fn.hashchange.delay milliseconds to see
    // if location.hash has changed, and triggers the 'hashchange' event on
    // window when necessary.
    function poll() {
      var hash = get_fragment(),
        history_hash = history_get( last_hash );
      
      if ( hash !== last_hash ) {
        history_set( last_hash = hash, history_hash );
        
        $(window).trigger( str_hashchange );
        
      } else if ( history_hash !== last_hash ) {
        location.href = location.href.replace( /#.*/, '' ) + history_hash;
      }
      
      timeout_id = setTimeout( poll, $.fn[ str_hashchange ].delay );
    };
    
    // vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
    // vvvvvvvvvvvvvvvvvvv REMOVE IF NOT SUPPORTING IE6/7/8 vvvvvvvvvvvvvvvvvvv
    // vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
    $.browser.msie && !supports_onhashchange && (function(){
      // Not only do IE6/7 need the "magical" Iframe treatment, but so does IE8
      // when running in "IE7 compatibility" mode.
      
      var iframe,
        iframe_src;
      
      // When the event is bound and polling starts in IE 6/7, create a hidden
      // Iframe for history handling.
      self.start = function(){
        if ( !iframe ) {
          iframe_src = $.fn[ str_hashchange ].src;
          iframe_src = iframe_src && iframe_src + get_fragment();
          
          // Create hidden Iframe. Attempt to make Iframe as hidden as possible
          // by using techniques from http://www.paciellogroup.com/blog/?p=604.
          iframe = $('<iframe tabindex="-1" title="empty"/>').hide()
            
            // When Iframe has completely loaded, initialize the history and
            // start polling.
            .one( 'load', function(){
              iframe_src || history_set( get_fragment() );
              poll();
            })
            
            // Load Iframe src if specified, otherwise nothing.
            .attr( 'src', iframe_src || 'javascript:0' )
            
            // Append Iframe after the end of the body to prevent unnecessary
            // initial page scrolling (yes, this works).
            .insertAfter( 'body' )[0].contentWindow;
          
          // Whenever `document.title` changes, update the Iframe's title to
          // prettify the back/next history menu entries. Since IE sometimes
          // errors with "Unspecified error" the very first time this is set
          // (yes, very useful) wrap this with a try/catch block.
          doc.onpropertychange = function(){
            try {
              if ( event.propertyName === 'title' ) {
                iframe.document.title = doc.title;
              }
            } catch(e) {}
          };
          
        }
      };
      
      // Override the "stop" method since an IE6/7 Iframe was created. Even
      // if there are no longer any bound event handlers, the polling loop
      // is still necessary for back/next to work at all!
      self.stop = fn_retval;
      
      // Get history by looking at the hidden Iframe's location.hash.
      history_get = function() {
        return get_fragment( iframe.location.href );
      };
      
      // Set a new history item by opening and then closing the Iframe
      // document, *then* setting its location.hash. If document.domain has
      // been set, update that as well.
      history_set = function( hash, history_hash ) {
        var iframe_doc = iframe.document,
          domain = $.fn[ str_hashchange ].domain;
        
        if ( hash !== history_hash ) {
          // Update Iframe with any initial `document.title` that might be set.
          iframe_doc.title = doc.title;
          
          // Opening the Iframe's document after it has been closed is what
          // actually adds a history entry.
          iframe_doc.open();
          
          // Set document.domain for the Iframe document as well, if necessary.
          domain && iframe_doc.write( '<script>document.domain="' + domain + '"</script>' );
          
          iframe_doc.close();
          
          // Update the Iframe's hash, for great justice.
          iframe.location.hash = hash;
        }
      };
      
    })();
    // ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    // ^^^^^^^^^^^^^^^^^^^ REMOVE IF NOT SUPPORTING IE6/7/8 ^^^^^^^^^^^^^^^^^^^
    // ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    
    return self;
  })();
  
})(jQuery,this);
/*
* jQuery Mobile Framework : "page" plugin
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/
(function($, undefined ) {

$.widget( "mobile.page", $.mobile.widget, {
	options: {
		backBtnText: "Back",
		addBackBtn: true,
		backBtnTheme: null,
		degradeInputs: {
			color: false,
			date: false,
			datetime: false,
			"datetime-local": false,
			email: false,
			month: false,
			number: false,
			range: "number",
			search: true,
			tel: false,
			time: false,
			url: false,
			week: false
		},
		keepNative: null
	},

	_create: function() {
		var $elem = this.element,
			o = this.options;

		this.keepNative = ":jqmData(role='none'), :jqmData(role='nojs')" + (o.keepNative ? ", " + o.keepNative : "");

		if ( this._trigger( "beforeCreate" ) === false ) {
			return;
		}

		//some of the form elements currently rely on the presence of ui-page and ui-content
		// classes so we'll handle page and content roles outside of the main role processing
		// loop below.
		$elem.find( ":jqmData(role='page'), :jqmData(role='content')" ).andSelf().each(function() {
			$(this).addClass( "ui-" + $(this).jqmData( "role" ) );
		});

		$elem.find( ":jqmData(role='nojs')" ).addClass( "ui-nojs" );

		// pre-find data els
		var $dataEls = $elem.find( ":jqmData(role)" ).andSelf().each(function() {
			var $this = $( this ),
				role = $this.jqmData( "role" ),
				theme = $this.jqmData( "theme" );

			//apply theming and markup modifications to page,header,content,footer
			if ( role === "header" || role === "footer" ) {
				$this.addClass( "ui-bar-" + (theme || $this.parent( ":jqmData(role='page')" ).jqmData( "theme" ) || "a") );

				// add ARIA role
				$this.attr( "role", role === "header" ? "banner" : "contentinfo" );

				//right,left buttons
				var $headeranchors = $this.children( "a" ),
					leftbtn = $headeranchors.hasClass( "ui-btn-left" ),
					rightbtn = $headeranchors.hasClass( "ui-btn-right" );

				if ( !leftbtn ) {
					leftbtn = $headeranchors.eq( 0 ).not( ".ui-btn-right" ).addClass( "ui-btn-left" ).length;
				}

				if ( !rightbtn ) {
					rightbtn = $headeranchors.eq( 1 ).addClass( "ui-btn-right" ).length;
				}

				// auto-add back btn on pages beyond first view
				if ( o.addBackBtn && role === "header" &&
						$( ".ui-page" ).length > 1 &&
						$elem.jqmData( "url" ) !== $.mobile.path.stripHash( location.hash ) &&
						!leftbtn && $this.jqmData( "backbtn" ) !== false ) {

					var backBtn = $( "<a href='#' class='ui-btn-left' data-"+ $.mobile.ns +"rel='back' data-"+ $.mobile.ns +"icon='arrow-l'>"+ o.backBtnText +"</a>" ).prependTo( $this );
					
					//if theme is provided, override default inheritance
					if( o.backBtnTheme ){
						backBtn.attr( "data-"+ $.mobile.ns +"theme", o.backBtnTheme );
					}
				}

				//page title
				$this.children( "h1, h2, h3, h4, h5, h6" )
					.addClass( "ui-title" )
					//regardless of h element number in src, it becomes h1 for the enhanced page
					.attr({ "tabindex": "0", "role": "heading", "aria-level": "1" });

			} else if ( role === "content" ) {
				if ( theme ) {
					$this.addClass( "ui-body-" + theme );
				}

				// add ARIA role
				$this.attr( "role", "main" );

			} else if ( role === "page" ) {
				$this.addClass( "ui-body-" + (theme || "c") );
			}

			switch(role) {
				case "header":
				case "footer":
				case "page":
				case "content":
					$this.addClass( "ui-" + role );
					break;
				case "collapsible":
				case "fieldcontain":
				case "navbar":
				case "listview":
				case "dialog":
					$this[ role ]();
					break;
			}
		});

		//enhance form controls
  	this._enhanceControls();

		//links in bars, or those with  data-role become buttons
		$elem.find( ":jqmData(role='button'), .ui-bar > a, .ui-header > a, .ui-footer > a" )
			.not( ".ui-btn" )
			.not(this.keepNative)
			.buttonMarkup();

		$elem
			.find(":jqmData(role='controlgroup')")
			.controlgroup();

		//links within content areas
		$elem.find( "a:not(.ui-btn):not(.ui-link-inherit)" )
			.not(this.keepNative)
			.addClass( "ui-link" );

		//fix toolbars
		$elem.fixHeaderFooter();
	},

	_typeAttributeRegex: /\s+type=["']?\w+['"]?/,

	_enhanceControls: function() {
		var o = this.options, self = this;

		// degrade inputs to avoid poorly implemented native functionality
		this.element.find( "input" ).not(this.keepNative).each(function() {
			var type = this.getAttribute( "type" ),
				optType = o.degradeInputs[ type ] || "text";

			if ( o.degradeInputs[ type ] ) {
				$( this ).replaceWith(
					$( "<div>" ).html( $(this).clone() ).html()
						.replace( self._typeAttributeRegex, " type=\""+ optType +"\" data-" + $.mobile.ns + "type=\""+type+"\" " ) );
			}
		});

		// We re-find form elements since the degredation code above
		// may have injected new elements. We cache the non-native control
		// query to reduce the number of times we search through the entire page.

		var allControls = this.element.find("input, textarea, select, button"),
			nonNativeControls = allControls.not(this.keepNative);

		// XXX: Temporary workaround for issue 785. Turn off autocorrect and
		//      autocomplete since the popup they use can't be dismissed by
		//      the user. Note that we test for the presence of the feature
		//      by looking for the autocorrect property on the input element.

		var textInputs = allControls.filter( "input[type=text]" );
		if (textInputs.length && typeof textInputs[0].autocorrect !== "undefined") {
			textInputs.each(function(){
				// Set the attribute instead of the property just in case there
				// is code that attempts to make modifications via HTML.
				this.setAttribute("autocorrect", "off");
				this.setAttribute("autocomplete", "off");
			});
		}

		// enchance form controls
		nonNativeControls
			.filter( "[type='radio'], [type='checkbox']" )
			.checkboxradio();

		nonNativeControls
			.filter( "button, [type='button'], [type='submit'], [type='reset'], [type='image']" )
			.button();

		nonNativeControls
			.filter( "input, textarea" )
			.not( "[type='radio'], [type='checkbox'], [type='button'], [type='submit'], [type='reset'], [type='image'], [type='hidden']" )
			.textinput();

		nonNativeControls
			.filter( "input, select" )
			.filter( ":jqmData(role='slider'), :jqmData(type='range')" )
			.slider();

		nonNativeControls
			.filter( "select:not(:jqmData(role='slider'))" )
			.selectmenu();
	}
});

})( jQuery );
/*!
 * jQuery Mobile v@VERSION
 * http://jquerymobile.com/
 *
 * Copyright 2010, jQuery Project
 * Dual licensed under the MIT or GPL Version 2 licenses.
 * http://jquery.org/license
 */

(function( $, window, undefined ) {

	//jQuery.mobile configurable options
	$.extend( $.mobile, {

		//namespace used framework-wide for data-attrs. Default is no namespace
		ns: "",

		//define the url parameter used for referencing widget-generated sub-pages.
		//Translates to to example.html&ui-page=subpageIdentifier
		//hash segment before &ui-page= is used to make Ajax request
		subPageUrlKey: "ui-page",

		//anchor links with a data-rel, or pages with a  data-role, that match these selectors will be untrackable in history
		//(no change in URL, not bookmarkable)
		nonHistorySelectors: "dialog",

		//class assigned to page currently in view, and during transitions
		activePageClass: "ui-page-active",

		//class used for "active" button state, from CSS framework
		activeBtnClass: "ui-btn-active",

		//automatically handle clicks and form submissions through Ajax, when same-domain
		ajaxEnabled: true,

		//automatically load and show pages based on location.hash
		hashListeningEnabled: true,

		// TODO: deprecated - remove at 1.0
		//automatically handle link clicks through Ajax, when possible
		ajaxLinksEnabled: true,

		// TODO: deprecated - remove at 1.0
		//automatically handle form submissions through Ajax, when possible
		ajaxFormsEnabled: true,

		//set default transition - 'none' for no transitions
		defaultTransition: "slide",

		//show loading message during Ajax requests
		//if false, message will not appear, but loading classes will still be toggled on html el
		loadingMessage: "loading",

		//error response message - appears when an Ajax page request fails
		pageLoadErrorMessage: "Error Loading Page",

		//configure meta viewport tag's content attr:
		//note: this feature is deprecated in A4 in favor of adding
		//the meta viewport element directly in the markup
		metaViewportContent: "width=device-width, minimum-scale=1, maximum-scale=1",

		//support conditions that must be met in order to proceed
		//default enhanced qualifications are media query support OR IE 7+
		gradeA: function(){
			return $.support.mediaquery || $.mobile.browser.ie && $.mobile.browser.ie >= 7;
		},

		//TODO might be useful upstream in jquery itself ?
		keyCode: {
			ALT: 18,
			BACKSPACE: 8,
			CAPS_LOCK: 20,
			COMMA: 188,
			COMMAND: 91,
			COMMAND_LEFT: 91, // COMMAND
			COMMAND_RIGHT: 93,
			CONTROL: 17,
			DELETE: 46,
			DOWN: 40,
			END: 35,
			ENTER: 13,
			ESCAPE: 27,
			HOME: 36,
			INSERT: 45,
			LEFT: 37,
			MENU: 93, // COMMAND_RIGHT
			NUMPAD_ADD: 107,
			NUMPAD_DECIMAL: 110,
			NUMPAD_DIVIDE: 111,
			NUMPAD_ENTER: 108,
			NUMPAD_MULTIPLY: 106,
			NUMPAD_SUBTRACT: 109,
			PAGE_DOWN: 34,
			PAGE_UP: 33,
			PERIOD: 190,
			RIGHT: 39,
			SHIFT: 16,
			SPACE: 32,
			TAB: 9,
			UP: 38,
			WINDOWS: 91 // COMMAND
		},

		//scroll page vertically: scroll to 0 to hide iOS address bar, or pass a Y value
		silentScroll: function( ypos ) {
			ypos = ypos || 0;
			// prevent scrollstart and scrollstop events
			$.event.special.scrollstart.enabled = false;

			setTimeout(function() {
				window.scrollTo( 0, ypos );
				$(document).trigger( "silentscroll", { x: 0, y: ypos });
			},20);

			setTimeout(function() {
				$.event.special.scrollstart.enabled = true;
			}, 150 );
		}
	});

	//mobile version of data and removeData and hasData methods
	//ensures all data is set and retrieved using jQuery Mobile's data namespace
  $.fn.jqmData = function( prop, value ){
    return this.data( prop ? $.mobile.ns + prop : prop, value );
  };

  $.jqmData = function( elem, prop, value ){
    return $.data( elem, prop && $.mobile.ns + prop, value );
  };

  $.fn.jqmRemoveData = function( prop ){
    return this.removeData( $.mobile.ns + prop );
  };

  $.jqmRemoveData = function( elem, prop ){
    return $.removeData( elem, prop && $.mobile.ns + prop );
  };

  $.jqmHasData = function( elem, prop ){
    return $.hasData( elem, prop && $.mobile.ns + prop );
  };


	// Monkey-patching Sizzle to filter the :jqmData selector
	var oldFind = $.find;

	$.find = function( selector, context, ret, extra ) {
		selector = selector.replace(/:jqmData\(([^)]*)\)/g, "[data-" + ($.mobile.ns || "") + "$1]");

		return oldFind.call( this, selector, context, ret, extra );
	};

	$.extend( $.find, oldFind );

	$.find.matches = function( expr, set ) {
		return $.find( expr, null, null, set );
	};

	$.find.matchesSelector = function( node, expr ) {
		return $.find( expr, null, null, [node] ).length > 0;
	};
})( jQuery, this );
/*
* jQuery Mobile Framework : core utilities for auto ajax navigation, base tag mgmt,
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/
(function($, undefined ) {

	//define vars for interal use
	var $window = $(window),
		$html = $('html'),
		$head = $('head'),

		//url path helpers for use in relative url management
		path = {

			//get path from current hash, or from a file path
			get: function( newPath ){
				if( newPath === undefined ){
					newPath = location.hash;
				}
				return path.stripHash( newPath ).replace(/[^\/]*\.[^\/*]+$/, '');
			},

			//return the substring of a filepath before the sub-page key, for making a server request
			getFilePath: function( path ){
				var splitkey = '&' + $.mobile.subPageUrlKey;
				return path && path.split( splitkey )[0].split( dialogHashKey )[0];
			},

			//set location hash to path
			set: function( path ){
				location.hash = path;
			},

			//location pathname from intial directory request
			origin: '',

			setOrigin: function(){
				path.origin = path.get( location.protocol + '//' + location.host + location.pathname );
			},

			//prefix a relative url with the current path
			// TODO rename to reflect conditional functionality
			makeAbsolute: function( url ){
				// only create an absolute path when the hash can be used as one
				return path.isPath(window.location.hash) ? path.get() + url : url;
			},

			// test if a given url (string) is a path
			// NOTE might be exceptionally naive
			isPath: function( url ){
				return /\//.test(url);
			},

			//return a url path with the window's location protocol/hostname/pathname removed
			clean: function( url ){
				// Replace the protocol, host, and pathname only once at the beginning of the url to avoid
				// problems when it's included as a part of a param
				// Also, since all urls are absolute in IE, we need to remove the pathname as well.
				var leadingUrlRootRegex = new RegExp("^" + location.protocol + "//" + location.host + location.pathname);
				return url.replace(leadingUrlRootRegex, "");
			},

			//just return the url without an initial #
			stripHash: function( url ){
				return url.replace( /^#/, "" );
			},

			//check whether a url is referencing the same domain, or an external domain or different protocol
			//could be mailto, etc
			isExternal: function( url ){
				return path.hasProtocol( path.clean( url ) );
			},

			hasProtocol: function( url ){
				return (/^(:?\w+:)/).test( url );
			},

			//check if the url is relative
			isRelative: function( url ){
				return  (/^[^\/|#]/).test( url ) && !path.hasProtocol( url );
			},

			isEmbeddedPage: function( url ){
				return (/^#/).test( url );
			}
		},

		//will be defined when a link is clicked and given an active class
		$activeClickedLink = null,

		//urlHistory is purely here to make guesses at whether the back or forward button was clicked
		//and provide an appropriate transition
		urlHistory = {
			//array of pages that are visited during a single page load. each has a url and optional transition
			stack: [],

			//maintain an index number for the active page in the stack
			activeIndex: 0,

			//get active
			getActive: function(){
				return urlHistory.stack[ urlHistory.activeIndex ];
			},

			getPrev: function(){
				return urlHistory.stack[ urlHistory.activeIndex - 1 ];
			},

			getNext: function(){
				return urlHistory.stack[ urlHistory.activeIndex + 1 ];
			},

			// addNew is used whenever a new page is added
			addNew: function( url, transition, title, storedTo ){
				//if there's forward history, wipe it
				if( urlHistory.getNext() ){
					urlHistory.clearForward();
				}

				urlHistory.stack.push( {url : url, transition: transition, title: title, page: storedTo } );

				urlHistory.activeIndex = urlHistory.stack.length - 1;
			},

			//wipe urls ahead of active index
			clearForward: function(){
				urlHistory.stack = urlHistory.stack.slice( 0, urlHistory.activeIndex + 1 );
			},

			directHashChange: function(opts){
				var back , forward, newActiveIndex;

				// check if url isp in history and if it's ahead or behind current page
				$.each( urlHistory.stack, function( i, historyEntry ){

					//if the url is in the stack, it's a forward or a back
					if( opts.currentUrl === historyEntry.url ){
						//define back and forward by whether url is older or newer than current page
						back = i < urlHistory.activeIndex;
						forward = !back;
						newActiveIndex = i;
					}
				});

				// save new page index, null check to prevent falsey 0 result
				this.activeIndex = newActiveIndex !== undefined ? newActiveIndex : this.activeIndex;

				if( back ){
					opts.isBack();
				} else if( forward ){
					opts.isForward();
				}
			},

			//disable hashchange event listener internally to ignore one change
			//toggled internally when location.hash is updated to match the url of a successful page load
			ignoreNextHashChange: true
		},

		//define first selector to receive focus when a page is shown
		focusable = "[tabindex],a,button:visible,select:visible,input",

		//contains role for next page, if defined on clicked link via data-rel
		nextPageRole = null,

		//queue to hold simultanious page transitions
		pageTransitionQueue = [],

		// indicates whether or not page is in process of transitioning
		isPageTransitioning = false,

		//nonsense hash change key for dialogs, so they create a history entry
		dialogHashKey = "&ui-state=dialog",

		//existing base tag?
		$base = $head.children("base"),
		hostURL = location.protocol + '//' + location.host,
		docLocation = path.get( hostURL + location.pathname ),
		docBase = docLocation;

		if ($base.length){
			var href = $base.attr("href");
			if (href){
				if (href.search(/^[^:\/]+:\/\/[^\/]+\/?/) === -1){
					//the href is not absolute, we need to turn it into one
					//so that we can turn paths stored in our location hash into
					//relative paths.
					if (href.charAt(0) === '/'){
						//site relative url
						docBase = hostURL + href;
					}
					else {
						//the href is a document relative url
						docBase = docLocation + href;
						//XXX: we need some code here to calculate the final path
						// just in case the docBase contains up-level (../) references.
					}
				}
				else {
					//the href is an absolute url
					docBase = href;
				}
			}
			//make sure docBase ends with a slash
			docBase = docBase  + (docBase.charAt(docBase.length - 1) === '/' ? ' ' : '/');
		}

		//base element management, defined depending on dynamic base tag support
		var base = $.support.dynamicBaseTag ? {

			//define base element, for use in routing asset urls that are referenced in Ajax-requested markup
			element: ($base.length ? $base : $("<base>", { href: docBase }).prependTo( $head )),

			//set the generated BASE element's href attribute to a new page's base path
			set: function( href ){
				base.element.attr('href', docBase + path.get( href ));
			},

			//set the generated BASE element's href attribute to a new page's base path
			reset: function(){
				base.element.attr('href', docBase );
			}

		} : undefined;



		//set location pathname from intial directory request
		path.setOrigin();

/*
	internal utility functions
--------------------------------------*/


	//direct focus to the page title, or otherwise first focusable element
	function reFocus( page ){
		var lastClicked = page.jqmData( "lastClicked" );
			
		if( lastClicked && lastClicked.length ){
			lastClicked.focus();
		}
		else {
			var pageTitle = page.find( ".ui-title:eq(0)" );
			
			if( pageTitle.length ){
				pageTitle.focus();
			}
			else{
				page.find( focusable ).eq(0).focus();
			}
		}
	}

	//remove active classes after page transition or error
	function removeActiveLinkClass( forceRemoval ){
		if( !!$activeClickedLink && (!$activeClickedLink.closest( '.ui-page-active' ).length || forceRemoval )){
			$activeClickedLink.removeClass( $.mobile.activeBtnClass );
		}
		$activeClickedLink = null;
	}

	//animation complete callback
	$.fn.animationComplete = function( callback ){
		if($.support.cssTransitions){
			return $(this).one('webkitAnimationEnd', callback);
		}
		else{
			// defer execution for consistency between webkit/non webkit
			setTimeout(callback, 0);
			return $(this);
		}
	};



/* exposed $.mobile methods	 */

	//update location.hash, with or without triggering hashchange event
	//TODO - deprecate this one at 1.0
	$.mobile.updateHash = path.set;

	//expose path object on $.mobile
	$.mobile.path = path;

	//expose base object on $.mobile
	$.mobile.base = base;

	//url stack, useful when plugins need to be aware of previous pages viewed
	//TODO: deprecate this one at 1.0
	$.mobile.urlstack = urlHistory.stack;

	//history stack
	$.mobile.urlHistory = urlHistory;

	//enable cross-domain page support
	$.mobile.allowCrossDomainPages = false;

	// changepage function
	$.mobile.changePage = function( to, transition, reverse, changeHash, fromHashChange ){
		//from is always the currently viewed page
		var toIsArray = $.type(to) === "array",
			toIsObject = $.type(to) === "object",
			from = toIsArray ? to[0] : $.mobile.activePage;

			to = toIsArray ? to[1] : to;

		var url = $.type(to) === "string" ? path.stripHash( to ) : "",
			fileUrl = url,
			data,
			type = 'get',
			isFormRequest = false,
			duplicateCachedPage = null,
			currPage = urlHistory.getActive(),
			back = false,
			forward = false,
			pageTitle = document.title;


		// If we are trying to transition to the same page that we are currently on ignore the request.
		// an illegal same page request is defined by the current page being the same as the url, as long as there's history
		// and to is not an array or object (those are allowed to be "same")
		if( currPage && urlHistory.stack.length > 1 && currPage.url === url && !toIsArray && !toIsObject ) {
			return;
		}
		else if(isPageTransitioning) {
			pageTransitionQueue.unshift(arguments);
			return;
		}

		isPageTransitioning = true;

		// if the changePage was sent from a hashChange event guess if it came from the history menu
		// and match the transition accordingly
		if( fromHashChange ){
			urlHistory.directHashChange({
				currentUrl: url,
				isBack: function(){
					forward = !(back = true);
					reverse = true;
					transition = transition || currPage.transition;
				},
				isForward: function(){
					forward = !(back = false);
					transition = transition || urlHistory.getActive().transition;
				}
			});

			//TODO forward = !back was breaking for some reason
		}

		if( toIsObject && to.url ){
			url = to.url;
			data = to.data;
			type = to.type;
			isFormRequest = true;
			//make get requests bookmarkable
			if( data && type === 'get' ){
				if($.type( data ) === "object" ){
					data = $.param(data);
				}

				url += "?" + data;
				data = undefined;
			}
		}

		//reset base to pathname for new request
		if(base){ base.reset(); }

		//kill the keyboard
		if( window.document.activeElement ){
			$( window.document.activeElement || "" ).add( "input:focus, textarea:focus, select:focus" ).blur();
		}

		function defaultTransition(){
			if(transition === undefined){
				transition = ( nextPageRole && nextPageRole === 'dialog' ) ? 'pop' : $.mobile.defaultTransition;
			}
		}

		function releasePageTransitionLock(){
			isPageTransitioning = false;
			if(pageTransitionQueue.length>0) {
				$.mobile.changePage.apply($.mobile, pageTransitionQueue.pop());
			}
		}

		//function for transitioning between two existing pages
		function transitionPages() {
		    $.mobile.silentScroll();

			//get current scroll distance
			var currScroll = $window.scrollTop(),
					perspectiveTransitions = [ "flip" ],
					pageContainerClasses = [];

			//support deep-links to generated sub-pages
			if( url.indexOf( "&" + $.mobile.subPageUrlKey ) > -1 ){
				to = $( ":jqmData(url='" + url + "')" );
			}

			if( from ){
				//set as data for returning to that spot
				from
					.jqmData( "lastScroll", currScroll)
					.jqmData( "lastClicked", $activeClickedLink);
				//trigger before show/hide events
				from.data( "page" )._trigger( "beforehide", null, { nextPage: to } );
			}
			to.data( "page" )._trigger( "beforeshow", null, { prevPage: from || $("") } );

			function pageChangeComplete(){

				if( changeHash !== false && url ){
					//disable hash listening temporarily
					urlHistory.ignoreNextHashChange = false;
					//update hash and history
					path.set( url );
				}

				//if title element wasn't found, try the page div data attr too
				var newPageTitle = to.jqmData("title") || to.find(".ui-header .ui-title" ).text();
				if( !!newPageTitle && pageTitle == document.title ){
					pageTitle = newPageTitle;
				}

				//add page to history stack if it's not back or forward
				if( !back && !forward ){
					urlHistory.addNew( url, transition, pageTitle, to );
				}

				//set page title
				document.title = urlHistory.getActive().title;

				removeActiveLinkClass();

				//jump to top or prev scroll, sometimes on iOS the page has not rendered yet.  I could only get by this with a setTimeout, but would like to avoid that.
				$.mobile.silentScroll( to.jqmData( "lastScroll" ) );

				reFocus( to );

				//trigger show/hide events
				if( from ){
					from.data( "page" )._trigger( "hide", null, { nextPage: to } );
				}
				//trigger pageshow, define prevPage as either from or empty jQuery obj
				to.data( "page" )._trigger( "show", null, { prevPage: from || $("") } );

				//set "to" as activePage
				$.mobile.activePage = to;

				//if there's a duplicateCachedPage, remove it from the DOM now that it's hidden
				if (duplicateCachedPage !== null) {
				    duplicateCachedPage.remove();
				}

				//remove initial build class (only present on first pageshow)
				$html.removeClass( "ui-mobile-rendering" );

				releasePageTransitionLock();
			}

			function addContainerClass(className){
				$.mobile.pageContainer.addClass(className);
				pageContainerClasses.push(className);
			}

			function removeContainerClasses(){
				$.mobile
					.pageContainer
					.removeClass(pageContainerClasses.join(" "));

				pageContainerClasses = [];
			}

			if(transition && (transition !== 'none')){
			    $.mobile.pageLoading( true );
				if( $.inArray(transition, perspectiveTransitions) >= 0 ){
					addContainerClass('ui-mobile-viewport-perspective');
				}

				addContainerClass('ui-mobile-viewport-transitioning');

				if( from ){
					from.addClass( transition + " out " + ( reverse ? "reverse" : "" ) );
				}
				to.addClass( $.mobile.activePageClass + " " + transition +
					" in " + ( reverse ? "reverse" : "" ) );

				// callback - remove classes, etc
				to.animationComplete(function() {
					to.add(from).removeClass("out in reverse " + transition );
					if( from ){
						from.removeClass( $.mobile.activePageClass );
					}
					pageChangeComplete();
					removeContainerClasses();
				});
			}
			else{
			    $.mobile.pageLoading( true );
			    if( from ){
					from.removeClass( $.mobile.activePageClass );
				}
				to.addClass( $.mobile.activePageClass );
				pageChangeComplete();
			}
		}

		//shared page enhancements
		function enhancePage(){

			//set next page role, if defined
			if ( nextPageRole || to.jqmData('role') === 'dialog' ) {
				url = urlHistory.getActive().url + dialogHashKey;
				if(nextPageRole){
					to.attr( "data-" + $.mobile.ns + "role", nextPageRole );
					nextPageRole = null;
				}
			}

			//run page plugin
			to.page();
		}

		//if url is a string
		if( url ){
			to = $( ":jqmData(url='" + url + "')" );
			fileUrl = path.getFilePath(url);
		}
		else{ //find base url of element, if avail
			var toID = to.attr( "data-" + $.mobile.ns + "url" ),
				toIDfileurl = path.getFilePath(toID);

			if(toID !== toIDfileurl){
				fileUrl = toIDfileurl;
			}
		}

		// ensure a transition has been set where pop is undefined
		defaultTransition();

		// find the "to" page, either locally existing in the dom or by creating it through ajax
		if ( to.length && !isFormRequest ) {
			if( fileUrl && base ){
				base.set( fileUrl );
			}
			enhancePage();
			transitionPages();
		} else {

			//if to exists in DOM, save a reference to it in duplicateCachedPage for removal after page change
			if( to.length ){
				duplicateCachedPage = to;
			}

			$.mobile.pageLoading();

			$.ajax({
				url: fileUrl,
				type: type,
				data: data,
				dataType: "html",
				success: function( html ) {
					//pre-parse html to check for a data-url,
					//use it as the new fileUrl, base path, etc
					var all = $("<div></div>"),
							redirectLoc,

							//page title regexp
							newPageTitle = html.match( /<title[^>]*>([^<]*)/ ) && RegExp.$1,

							// TODO handle dialogs again
							pageElemRegex = new RegExp(".*(<[^>]+\\bdata-" + $.mobile.ns + "role=[\"']?page[\"']?[^>]*>).*"),
							dataUrlRegex = new RegExp("\\bdata-" + $.mobile.ns + "url=[\"']?([^\"'>]*)[\"']?");


					// data-url must be provided for the base tag so resource requests can be directed to the
					// correct url. loading into a temprorary element makes these requests immediately
					if(pageElemRegex.test(html) && RegExp.$1 && dataUrlRegex.test(RegExp.$1) && RegExp.$1) {
						redirectLoc = RegExp.$1;
					}

					if( redirectLoc ){
						if(base){
							base.set( redirectLoc );
						}
						url = fileUrl = path.getFilePath( redirectLoc );
					}
					else {
						if(base){
							base.set(fileUrl);
						}
					}

					//workaround to allow scripts to execute when included in page divs
					all.get(0).innerHTML = html;
					to = all.find( ":jqmData(role='page'), :jqmData(role='dialog')" ).first();

					//finally, if it's defined now, set the page title for storage in urlHistory
					if( newPageTitle ){
						pageTitle = newPageTitle;
					}

					//rewrite src and href attrs to use a base url
					if( !$.support.dynamicBaseTag ){
						var newPath = path.get( fileUrl );
						to.find( "[src], link[href], a[rel='external'], :jqmData(ajax='false'), a[target]" ).each(function(){
							var thisAttr = $(this).is('[href]') ? 'href' : 'src',
								thisUrl = $(this).attr(thisAttr);


							//if full path exists and is same, chop it - helps IE out
							thisUrl = thisUrl.replace( location.protocol + '//' + location.host + location.pathname, '' );

							if( !/^(\w+:|#|\/)/.test(thisUrl) ){
								$(this).attr(thisAttr, newPath + thisUrl);
							}
						});
					}

					//append to page and enhance
					to
						.attr( "data-" + $.mobile.ns + "url", fileUrl )
						.appendTo( $.mobile.pageContainer );

					enhancePage();
					setTimeout(function() { transitionPages(); }, 0);
				},
				error: function() {

					//remove loading message
					$.mobile.pageLoading( true );

					//clear out the active button state
					removeActiveLinkClass(true);

					//set base back to current path
					if( base ){
						base.set( path.get() );
					}

					//release transition lock so navigation is free again
					releasePageTransitionLock();

					//show error message
					$("<div class='ui-loader ui-overlay-shadow ui-body-e ui-corner-all'><h1>"+ $.mobile.pageLoadErrorMessage +"</h1></div>")
						.css({ "display": "block", "opacity": 0.96, "top": $(window).scrollTop() + 100 })
						.appendTo( $.mobile.pageContainer )
						.delay( 800 )
						.fadeOut( 400, function(){
							$(this).remove();
						});
				}
			});
		}

	};


/* Event Bindings - hashchange, submit, and click */

	//bind to form submit events, handle with Ajax
	$( "form" ).live('submit', function(event){
		if( !$.mobile.ajaxEnabled ||
			//TODO: deprecated - remove at 1.0
			!$.mobile.ajaxFormsEnabled ||
			$(this).is( ":jqmData(ajax='false')" ) ){ return; }

		var type = $(this).attr("method"),
			url = path.clean( $(this).attr( "action" ) ),
			target = $(this).attr("target");

		//external submits use regular HTTP
		if( path.isExternal( url ) || target ){
			return;
		}

		//if it's a relative href, prefix href with base url
		if( path.isRelative( url ) ){
			url = path.makeAbsolute( url );
		}

		$.mobile.changePage({
				url: url.length && url || path.get(),
				type: type.length && type.toLowerCase() || "get",
				data: $(this).serialize()
			},
			$(this).jqmData("transition"),
			$(this).jqmData("direction"),
			true
		);
		event.preventDefault();
	});
	
	//add active state on vclick
	$( "a" ).live( "vclick", function(){
		$(this).closest( ".ui-btn" ).not( ".ui-disabled" ).addClass( $.mobile.activeBtnClass );
	});


	//click routing - direct to HTTP or Ajax, accordingly
	$( "a" ).live( "click", function(event) {

		var $this = $(this),

			//get href, if defined, otherwise fall to null #
			href = $this.attr( "href" ) || "#",

			//cache a check for whether the link had a protocol
			//if this is true and the link was same domain, we won't want
			//to prefix the url with a base (esp helpful in IE, where every
			//url is absolute
			hadProtocol = path.hasProtocol( href ),

			//get href, remove same-domain protocol and host
			url = path.clean( href ),

			//rel set to external
			isRelExternal = $this.is( "[rel='external']" ),

			//rel set to external
			isEmbeddedPage = path.isEmbeddedPage( url ),

			// Some embedded browsers, like the web view in Phone Gap, allow cross-domain XHR
			// requests if the document doing the request was loaded via the file:// protocol.
			// This is usually to allow the application to "phone home" and fetch app specific
			// data. We normally let the browser handle external/cross-domain urls, but if the
			// allowCrossDomainPages option is true, we will allow cross-domain http/https
			// requests to go through our page loading logic.
			isCrossDomainPageLoad = ($.mobile.allowCrossDomainPages && location.protocol === "file:" && url.search(/^https?:/) != -1),

			//check for protocol or rel and its not an embedded page
			//TODO overlap in logic from isExternal, rel=external check should be
			//     moved into more comprehensive isExternalLink
			isExternal = (path.isExternal(url) && !isCrossDomainPageLoad) || (isRelExternal && !isEmbeddedPage),

			//if target attr is specified we mimic _blank... for now
			hasTarget = $this.is( "[target]" ),

			//if data-ajax attr is set to false, use the default behavior of a link
			hasAjaxDisabled = $this.is( ":jqmData(ajax='false')" ),

			//if the url matches the active page's url
			isCurrentPage = path.stripHash(url) == $.mobile.activePage.jqmData("url");

		//if there's a data-rel=back attr, go back in history
		if( $this.is( ":jqmData(rel='back')" ) ){
			window.history.back();
			return false;
		}

		//prevent # urls from bubbling
		//path.get() is replaced to combat abs url prefixing in IE
		//or if the link is to the current page
		if( url.replace(path.get(), "") == "#" || isCurrentPage ){
			//for links created purely for interaction - ignore
			event.preventDefault();
			return;
		}

		$activeClickedLink = $this.closest( ".ui-btn" );

		if( isExternal || hasAjaxDisabled || hasTarget || !$.mobile.ajaxEnabled ||
			// TODO: deprecated - remove at 1.0
			!$.mobile.ajaxLinksEnabled ){
			//remove active link class if external (then it won't be there if you come back)
			window.setTimeout(function() {removeActiveLinkClass(true);}, 200);

			//use default click handling
			return;
		}

		//use ajax
		var transition = $this.jqmData( "transition" ),
			direction = $this.jqmData("direction"),
			reverse = (direction && direction === "reverse") ||
			// deprecated - remove by 1.0
			$this.jqmData( "back" );

		//this may need to be more specific as we use data-rel more
		nextPageRole = $this.attr( "data-" + $.mobile.ns + "rel" );

		//if it's a relative href, prefix href with base url
		if( path.isRelative( url ) && !hadProtocol ){
			url = path.makeAbsolute( url );
		}

		url = path.stripHash( url );

		$.mobile.changePage( url, transition, reverse);
		event.preventDefault();
	});

	//hashchange event handler
	$window.bind( "hashchange", function( e, triggered ) {
		//find first page via hash
		var to = path.stripHash( location.hash ),
			//transition is false if it's the first page, undefined otherwise (and may be overridden by default)
			transition = $.mobile.urlHistory.stack.length === 0 ? false : undefined;

		//if listening is disabled (either globally or temporarily), or it's a dialog hash
		if( !$.mobile.hashListeningEnabled || !urlHistory.ignoreNextHashChange ){
			if( !urlHistory.ignoreNextHashChange ){
				urlHistory.ignoreNextHashChange = true;
			}

			return;
		}

		// special case for dialogs
		if( urlHistory.stack.length > 1 &&
				to.indexOf( dialogHashKey ) > -1 ){

			// If current active page is not a dialog skip the dialog and continue
			// in the same direction
			if(!$.mobile.activePage.is( ".ui-dialog" )) {
				//determine if we're heading forward or backward and continue accordingly past
				//the current dialog
				urlHistory.directHashChange({
					currentUrl: to,
					isBack: function(){ window.history.back(); },
					isForward: function(){ window.history.forward(); }
				});

				// prevent changepage
				return;
			} else {
				var setTo = function(){ to = $.mobile.urlHistory.getActive().page; };
				// if the current active page is a dialog and we're navigating
				// to a dialog use the dialog objected saved in the stack
				urlHistory.directHashChange({	currentUrl: to, isBack: setTo, isForward: setTo	});
			}
		}

		//if to is defined, load it
		if ( to ){
			$.mobile.changePage( to, transition, undefined, false, true );
		}
		//there's no hash, go to the first page in the dom
		else {
			$.mobile.changePage( $.mobile.firstPage, transition, true, false, true );
		}
		});

})( jQuery );
/*
* jQuery Mobile Framework : "fixHeaderFooter" plugin - on-demand positioning for headers,footers
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/
(function($, undefined ) {
$.fn.fixHeaderFooter = function(options){
	if( !$.support.scrollTop ){ return this; }
	
	return this.each(function(){
		var $this = $(this);
		
		if( $this.jqmData('fullscreen') ){ $this.addClass('ui-page-fullscreen'); }
		$this.find( ".ui-header:jqmData(position='fixed')" ).addClass('ui-header-fixed ui-fixed-inline fade'); //should be slidedown
		$this.find( ".ui-footer:jqmData(position='fixed')" ).addClass('ui-footer-fixed ui-fixed-inline fade'); //should be slideup		
	});
};

//single controller for all showing,hiding,toggling		
$.fixedToolbars = (function(){
	if( !$.support.scrollTop ){ return; }
	var currentstate = 'inline',
		autoHideMode = false,
		showDelay = 100,
		delayTimer,
		ignoreTargets = 'a,input,textarea,select,button,label,.ui-header-fixed,.ui-footer-fixed',
		toolbarSelector = '.ui-header-fixed:first, .ui-footer-fixed:not(.ui-footer-duplicate):last',
		stickyFooter, //for storing quick references to duplicate footers
		supportTouch = $.support.touch,
		touchStartEvent = supportTouch ? "touchstart" : "mousedown",
		touchStopEvent = supportTouch ? "touchend" : "mouseup",
		stateBefore = null,
		scrollTriggered = false,
        touchToggleEnabled = true;

	function showEventCallback(event)
	{
		// An event that affects the dimensions of the visual viewport has
		// been triggered. If the header and/or footer for the current page are in overlay
		// mode, we want to hide them, and then fire off a timer to show them at a later
		// point. Events like a resize can be triggered continuously during a scroll, on
		// some platforms, so the timer is used to delay the actual positioning until the
		// flood of events have subsided.
		//
		// If we are in autoHideMode, we don't do anything because we know the scroll
		// callbacks for the plugin will fire off a show when the scrolling has stopped.
		if (!autoHideMode && currentstate == 'overlay') {
			if (!delayTimer)
				$.fixedToolbars.hide(true);
			$.fixedToolbars.startShowTimer();
		}
	}

	$(function() {
		$(document)
			.bind( "vmousedown",function(event){
				if( touchToggleEnabled ) {
					stateBefore = currentstate;
				}
			})
			.bind( "vclick",function(event){
				if( touchToggleEnabled ) {
					if( $(event.target).closest(ignoreTargets).length ){ return; }
					if( !scrollTriggered ){
						$.fixedToolbars.toggle(stateBefore);
						stateBefore = null;
					}
				}
			})
			.bind('scrollstart',function(event){
				scrollTriggered = true;
				if(stateBefore == null){ stateBefore = currentstate; }

				// We only enter autoHideMode if the headers/footers are in
				// an overlay state or the show timer was started. If the
				// show timer is set, clear it so the headers/footers don't
				// show up until after we're done scrolling.
				var isOverlayState = stateBefore == 'overlay';
				autoHideMode = isOverlayState || !!delayTimer;
				if (autoHideMode){
					$.fixedToolbars.clearShowTimer();
					if (isOverlayState) {
						$.fixedToolbars.hide(true);
					}
				}
			})
			.bind('scrollstop',function(event){
				if( $(event.target).closest(ignoreTargets).length ){ return; }
				scrollTriggered = false;
				if (autoHideMode) {
					autoHideMode = false;
					$.fixedToolbars.startShowTimer();
				}
				stateBefore = null;
			})
			.bind('silentscroll', showEventCallback);

			$(window).bind('resize', showEventCallback);
	});
		
	//before page is shown, check for duplicate footer
	$('.ui-page').live('pagebeforeshow', function(event, ui){
		var page = $(event.target),
			footer = page.find( ":jqmData(role='footer')" ),
			id = footer.data('id'),
			prevPage = ui.prevPage;
		
		prevFooter = prevPage && prevPage.find( ":jqmData(role='footer')" );
		var prevFooterMatches = prevFooter.jqmData( "id" ) === id;
		
		if( id && prevFooterMatches ){
			stickyFooter = footer;
			setTop( stickyFooter.removeClass( "fade in out" ).appendTo( $.mobile.pageContainer ) );
		}
	});

	//after page is shown, append footer to new page
	$('.ui-page').live('pageshow', function(event, ui){
		var $this = $(this);
		
		if( stickyFooter && stickyFooter.length ){	
			
			setTimeout(function(){
				setTop( stickyFooter.appendTo( $this ).addClass("fade") );
				stickyFooter = null;
			}, 500);	
		}
		
		$.fixedToolbars.show(true, this);	
	});

	
	// element.getBoundingClientRect() is broken in iOS 3.2.1 on the iPad. The
	// coordinates inside of the rect it returns don't have the page scroll position
	// factored out of it like the other platforms do. To get around this,
	// we'll just calculate the top offset the old fashioned way until core has
	// a chance to figure out how to handle this situation.
	//
	// TODO: We'll need to get rid of getOffsetTop() once a fix gets folded into core.

	function getOffsetTop(ele)
	{
		var top = 0;
		if (ele)
		{
			var op = ele.offsetParent, body = document.body;
			top = ele.offsetTop;
			while (ele && ele != body)
			{
				top += ele.scrollTop || 0;
				if (ele == op)
				{
					top += op.offsetTop;
					op = ele.offsetParent;
				}
				ele = ele.parentNode;
			}
		}
		return top;
	}

	function setTop(el){
		var fromTop = $(window).scrollTop(),
			thisTop = getOffsetTop(el[0]), // el.offset().top returns the wrong value on iPad iOS 3.2.1, call our workaround instead.
			thisCSStop = el.css('top') == 'auto' ? 0 : parseFloat(el.css('top')),
			screenHeight = window.innerHeight,
			thisHeight = el.outerHeight(),
			useRelative = el.parents('.ui-page:not(.ui-page-fullscreen)').length,
			relval;
		if( el.is('.ui-header-fixed') ){
			relval = fromTop - thisTop + thisCSStop;
			if( relval < thisTop){ relval = 0; }
			return el.css('top', ( useRelative ) ? relval : fromTop);
		}
		else{
			//relval = -1 * (thisTop - (fromTop + screenHeight) + thisCSStop + thisHeight);
			//if( relval > thisTop ){ relval = 0; }
			relval = fromTop + screenHeight - thisHeight - (thisTop - thisCSStop);
			return el.css('top', ( useRelative ) ? relval : fromTop + screenHeight - thisHeight );
		}
	}

	//exposed methods
	return {
		show: function(immediately, page){
			$.fixedToolbars.clearShowTimer();
			currentstate = 'overlay';
			var $ap = page ? $(page) : ($.mobile.activePage ? $.mobile.activePage : $(".ui-page-active"));
			return $ap.children( toolbarSelector ).each(function(){
				var el = $(this),
					fromTop = $(window).scrollTop(),
					thisTop = getOffsetTop(el[0]), // el.offset().top returns the wrong value on iPad iOS 3.2.1, call our workaround instead.
					screenHeight = window.innerHeight,
					thisHeight = el.outerHeight(),
					alreadyVisible = (el.is('.ui-header-fixed') && fromTop <= thisTop + thisHeight) || (el.is('.ui-footer-fixed') && thisTop <= fromTop + screenHeight);	
				
				//add state class
				el.addClass('ui-fixed-overlay').removeClass('ui-fixed-inline');	
					
				if( !alreadyVisible && !immediately ){
					el.animationComplete(function(){
						el.removeClass('in');
					}).addClass('in');
				}
				setTop(el);
			});	
		},
		hide: function(immediately){
			currentstate = 'inline';
			var $ap = $.mobile.activePage ? $.mobile.activePage : $(".ui-page-active");
			return $ap.children( toolbarSelector ).each(function(){
				var el = $(this);

				var thisCSStop = el.css('top'); thisCSStop = thisCSStop == 'auto' ? 0 : parseFloat(thisCSStop);
				
				//add state class
				el.addClass('ui-fixed-inline').removeClass('ui-fixed-overlay');
				
				if (thisCSStop < 0 || (el.is('.ui-header-fixed') && thisCSStop != 0))
				{
					if(immediately){
						el.css('top',0);
					}
					else{
						if( el.css('top') !== 'auto' && parseFloat(el.css('top')) !== 0 ){
							var classes = 'out reverse';
							el.animationComplete(function(){
								el.removeClass(classes);
								el.css('top',0);
							}).addClass(classes);	
						}
					}
				}
			});
		},
		startShowTimer: function(){
			$.fixedToolbars.clearShowTimer();
			var args = $.makeArray(arguments);
			delayTimer = setTimeout(function(){
				delayTimer = undefined;
				$.fixedToolbars.show.apply(null, args);
			}, showDelay);
		},
		clearShowTimer: function() {
			if (delayTimer) {
				clearTimeout(delayTimer);
			}
			delayTimer = undefined;
		},
		toggle: function(from){
			if(from){ currentstate = from; }
			return (currentstate == 'overlay') ? $.fixedToolbars.hide() : $.fixedToolbars.show();
		},
        setTouchToggleEnabled: function(enabled) {
            touchToggleEnabled = enabled;
        }
	};
})();

})(jQuery);
/*
* jQuery Mobile Framework : "checkboxradio" plugin
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/
(function($, undefined ) {
$.widget( "mobile.checkboxradio", $.mobile.widget, {
	options: {
		theme: null
	},
	_create: function(){
		var self = this,
			input = this.element,
			//NOTE: Windows Phone could not find the label through a selector
			//filter works though.
			label = input.closest("form,fieldset,:jqmData(role='page')").find("label").filter("[for=" + input[0].id + "]"),
			inputtype = input.attr( "type" ),
			checkedicon = "ui-icon-" + inputtype + "-on",
			uncheckedicon = "ui-icon-" + inputtype + "-off";

		if ( inputtype != "checkbox" && inputtype != "radio" ) { return; }

		//expose for other methods
		$.extend( this,{
			label			: label,
			inputtype		: inputtype,
			checkedicon		: checkedicon,
			uncheckedicon	: uncheckedicon
		});

		// If there's no selected theme...
		if( !this.options.theme ) {
			this.options.theme = this.element.jqmData( "theme" );
		}

		label
			.buttonMarkup({
				theme: this.options.theme,
				icon: this.element.parents( ":jqmData(type='horizontal')" ).length ? undefined : uncheckedicon,
				shadow: false
			});

		// wrap the input + label in a div
		input
			.add( label )
			.wrapAll( "<div class='ui-" + inputtype +"'></div>" );

		label.bind({
			vmouseover: function() {
				if( $(this).parent().is('.ui-disabled') ){ return false; }
			},

			vclick: function( event ){
				if ( input.is( ":disabled" ) ){
					event.preventDefault();
					return;
				}

				self._cacheVals();
				input.attr( "checked", inputtype === "radio" && true || !input.is( ":checked" ) );
				self._updateAll();
				return false;
			}

		});

		input
			.bind({
				vmousedown: function(){
					this._cacheVals();
				},

				vclick: function(){
					self._updateAll();
				},

				focus: function() {
					label.addClass( "ui-focus" );
				},

				blur: function() {
					label.removeClass( "ui-focus" );
				}
			});

		this.refresh();

	},

	_cacheVals: function(){
		this._getInputSet().each(function(){
			$(this).jqmData("cacheVal", $(this).is(":checked") );
		});
	},

	//returns either a set of radios with the same name attribute, or a single checkbox
	_getInputSet: function(){
		return this.element.closest( "form,fieldset,:jqmData(role='page')" )
				.find( "input[name='"+ this.element.attr( "name" ) +"'][type='"+ this.inputtype +"']" );
	},

	_updateAll: function(){
		var self = this;

		this._getInputSet().each(function(){
			if( $(this).is(":checked") || self.inputtype === "checkbox" ){
				$(this).trigger("change");
			}
		})
		.checkboxradio( "refresh" );
	},

	refresh: function( ){
		var input = this.element,
			label = this.label,
			icon = label.find( ".ui-icon" );

		if ( input[0].checked ) {
			label.addClass( $.mobile.activeBtnClass );
			icon.addClass( this.checkedicon ).removeClass( this.uncheckedicon );

		} else {
			label.removeClass( $.mobile.activeBtnClass );
			icon.removeClass( this.checkedicon ).addClass( this.uncheckedicon );
		}

		if( input.is( ":disabled" ) ){
			this.disable();
		}
		else {
			this.enable();
		}
	},

	disable: function(){
		this.element.attr("disabled",true).parent().addClass("ui-disabled");
	},

	enable: function(){
		this.element.attr("disabled",false).parent().removeClass("ui-disabled");
	}
});
})( jQuery );
/*
* jQuery Mobile Framework : "textinput" plugin for text inputs, textareas
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/
(function($, undefined ) {
$.widget( "mobile.textinput", $.mobile.widget, {
	options: {
		theme: null
	},
	_create: function(){
		var input = this.element,
			o = this.options,
			theme = o.theme,
			themeclass;
			
		if ( !theme ) {
			var themedParent = this.element.closest("[class*='ui-bar-'],[class*='ui-body-']"); 
				theme = themedParent.length ?
					/ui-(bar|body)-([a-z])/.exec( themedParent.attr("class") )[2] :
					"c";
		}	
		
		themeclass = " ui-body-" + theme;
		
		$('label[for='+input.attr('id')+']').addClass('ui-input-text');
		
		input.addClass('ui-input-text ui-body-'+ o.theme);
		
		var focusedEl = input;
		
		//"search" input widget
		if( input.is( "[type='search'],:jqmData(type='search')" ) ){
			focusedEl = input.wrap('<div class="ui-input-search ui-shadow-inset ui-btn-corner-all ui-btn-shadow ui-icon-searchfield'+ themeclass +'"></div>').parent();
			var clearbtn = $('<a href="#" class="ui-input-clear" title="clear text">clear text</a>')
				.tap(function( e ){
					input.val('').focus();
					input.trigger('change'); 
					clearbtn.addClass('ui-input-clear-hidden');
					e.preventDefault();
				})
				.appendTo(focusedEl)
				.buttonMarkup({icon: 'delete', iconpos: 'notext', corners:true, shadow:true});
			
			function toggleClear(){
				if(input.val() == ''){
					clearbtn.addClass('ui-input-clear-hidden');
				}
				else{
					clearbtn.removeClass('ui-input-clear-hidden');
				}
			}
			
			toggleClear();
			input.keyup(toggleClear);	
		}
		else{
			input.addClass('ui-corner-all ui-shadow-inset' + themeclass);
		}
				
		input
			.focus(function(){
				focusedEl.addClass('ui-focus');
			})
			.blur(function(){
				focusedEl.removeClass('ui-focus');
			});	
			
		//autogrow
		if ( input.is('textarea') ) {
			var extraLineHeight = 15,
				keyupTimeoutBuffer = 100,
				keyup = function() {
					var scrollHeight = input[0].scrollHeight,
						clientHeight = input[0].clientHeight;
					if ( clientHeight < scrollHeight ) {
						input.css({ height: (scrollHeight + extraLineHeight) });
					}
				},
				keyupTimeout;
			input.keyup(function() {
				clearTimeout( keyupTimeout );
				keyupTimeout = setTimeout( keyup, keyupTimeoutBuffer );
			});
		}
	},
	
	disable: function(){
		( this.element.attr("disabled",true).is( "[type='search'],:jqmData(type='search')" ) ? this.element.parent() : this.element ).addClass("ui-disabled");
	},
	
	enable: function(){
		( this.element.attr("disabled", false).is( "[type='search'],:jqmData(type='search')" ) ? this.element.parent() : this.element ).removeClass("ui-disabled");
	}
});
})( jQuery );
/*
* jQuery Mobile Framework : "selectmenu" plugin
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/
(function($, undefined ) {
$.widget( "mobile.selectmenu", $.mobile.widget, {
	options: {
		theme: null,
		disabled: false,
		icon: 'arrow-d',
		iconpos: 'right',
		inline: null,
		corners: true,
		shadow: true,
		iconshadow: true,
		menuPageTheme: 'b',
		overlayTheme: 'a',
		hidePlaceholderMenuItems: true,
		closeText: 'Close',
		nativeMenu: true
	},
	_create: function(){
		
		var self = this,

			o = this.options,

			select = this.element
						.wrap( "<div class='ui-select'>" ),

			selectID = select.attr( "id" ),

			label = $( "label[for="+ selectID +"]" ).addClass( "ui-select" ),
			
			//IE throws an exception at options.item() function when
			//there is no selected item
			//select first in this case 
			selectedIndex = select[0].selectedIndex == -1 ? 0 : select[0].selectedIndex,
			
			button = ( self.options.nativeMenu ? $( "<div/>" ) : $( "<a>", {
					"href": "#",
					"role": "button",
					"id": buttonId,
					"aria-haspopup": "true",
					"aria-owns": menuId
				}) )
				.text( $( select[0].options.item( selectedIndex ) ).text() )
				.insertBefore( select )
				.buttonMarkup({
					theme: o.theme,
					icon: o.icon,
					iconpos: o.iconpos,
					inline: o.inline,
					corners: o.corners,
					shadow: o.shadow,
					iconshadow: o.iconshadow
				}),

			//multi select or not
			isMultiple = self.isMultiple = select[0].multiple;

		//Opera does not properly support opacity on select elements
		//In Mini, it hides the element, but not its text
		//On the desktop,it seems to do the opposite
		//for these reasons, using the nativeMenu option results in a full native select in Opera
		if( o.nativeMenu && window.opera && window.opera.version ){
			select.addClass( "ui-select-nativeonly" );
		}

		//vars for non-native menus
		if( !o.nativeMenu ){
			var options = select.find("option"),

				buttonId = selectID + "-button",

				menuId = selectID + "-menu",

				thisPage = select.closest( ".ui-page" ),

				//button theme
				theme = /ui-btn-up-([a-z])/.exec( button.attr("class") )[1],

				menuPage = $( "<div data-" + $.mobile.ns + "role='dialog' data-" +$.mobile.ns + "theme='"+ o.menuPageTheme +"'>" +
							"<div data-" + $.mobile.ns + "role='header'>" +
								"<div class='ui-title'>" + label.text() + "</div>"+
							"</div>"+
							"<div data-" + $.mobile.ns + "role='content'></div>"+
						"</div>" )
						.appendTo( $.mobile.pageContainer )
						.page(),

				menuPageContent = menuPage.find( ".ui-content" ),

				menuPageClose = menuPage.find( ".ui-header a" ),

				screen = $( "<div>", {"class": "ui-selectmenu-screen ui-screen-hidden"})
							.appendTo( thisPage ),

				listbox = $( "<div>", { "class": "ui-selectmenu ui-selectmenu-hidden ui-overlay-shadow ui-corner-all pop ui-body-" + o.overlayTheme } )
						.insertAfter(screen),

				list = $( "<ul>", {
						"class": "ui-selectmenu-list",
						"id": menuId,
						"role": "listbox",
						"aria-labelledby": buttonId
					})
					.attr( "data-" + $.mobile.ns + "theme", theme )
					.appendTo( listbox ),

				header = $( "<div>", {
						"class": "ui-header ui-bar-" + theme
					})
					.prependTo( listbox ),

				headerTitle = $( "<h1>", {
						"class": "ui-title"
					})
					.appendTo( header ),

				headerClose = $( "<a>", {
						"text": o.closeText,
						"href": "#",
						"class": "ui-btn-left"
					})
					.attr( "data-" + $.mobile.ns + "iconpos", "notext" )
					.attr( "data-" + $.mobile.ns + "icon", "delete" )
					.appendTo( header )
					.buttonMarkup(),

				menuType;
		} //end non native vars

		// add counter for multi selects
		if( isMultiple ){
			self.buttonCount = $('<span>')
				.addClass( 'ui-li-count ui-btn-up-c ui-btn-corner-all' )
				.hide()
				.appendTo( button );
		}

		//disable if specified
		if( o.disabled ){ this.disable(); }

		//events on native select
		select
			.change(function(){
				self.refresh();
			});

		//expose to other methods
		$.extend(self, {
			select: select,
			optionElems: options,
			selectID: selectID,
			label: label,
			buttonId:buttonId,
			menuId:menuId,
			thisPage:thisPage,
			button:button,
			menuPage:menuPage,
			menuPageContent:menuPageContent,
			screen:screen,
			listbox:listbox,
			list:list,
			menuType:menuType,
			header:header,
			headerClose:headerClose,
			headerTitle:headerTitle,
			placeholder: ''
		});

		//support for using the native select menu with a custom button
		if( o.nativeMenu ){

			select
				.appendTo(button)
				.bind( "vmousedown", function( e ){
					//add active class to button
					button.addClass( $.mobile.activeBtnClass );
				})
				.bind( "focus vmouseover", function(){
					button.trigger( "vmouseover" );
				})
				.bind( "vmousemove", function(){
					//remove active class on scroll/touchmove
					button.removeClass( $.mobile.activeBtnClass );
				})
				.bind( "change blur vmouseout", function(){
					button
						.trigger( "vmouseout" )
						.removeClass( $.mobile.activeBtnClass );
				});


		} else {

			//create list from select, update state
			self.refresh();

			select
				.attr( "tabindex", "-1" )
				.focus(function(){
					$(this).blur();
					button.focus();
				});	

			//button events
			button
				.bind( "vclick keydown" , function( event ){
					if( event.type == "vclick" || 
						event.keyCode && ( event.keyCode === $.mobile.keyCode.ENTER || event.keyCode === $.mobile.keyCode.SPACE ) ){
						self.open();
						event.preventDefault();
					}
				});

			//events for list items
			list
			.attr( "role", "listbox" )
			.delegate( ".ui-li>a", "focusin", function() {
				$( this ).attr( "tabindex", "0" );
			})
			.delegate( ".ui-li>a", "focusout", function() {
				$( this ).attr( "tabindex", "-1" );
			})
			.delegate("li:not(.ui-disabled, .ui-li-divider)", "vclick", function(event){

				// index of option tag to be selected
				var oldIndex = select[0].selectedIndex,
					newIndex = list.find( "li:not(.ui-li-divider)" ).index( this ),
					option = self.optionElems.eq( newIndex )[0];

				// toggle selected status on the tag for multi selects
				option.selected = isMultiple ? !option.selected : true;

				// toggle checkbox class for multiple selects
				if( isMultiple ){
					$(this)
						.find('.ui-icon')
						.toggleClass('ui-icon-checkbox-on', option.selected)
						.toggleClass('ui-icon-checkbox-off', !option.selected);
				}

				// trigger change if value changed
				if( oldIndex !== newIndex ){
					select.trigger( "change" );
				}

				//hide custom select for single selects only
				if( !isMultiple ){
					self.close();
				}

				event.preventDefault();
			})
			//keyboard events for menu items
			.keydown(function( e ) {
				var target = $( e.target ),
					li = target.closest( "li" );
	
				// switch logic based on which key was pressed
				switch ( e.keyCode ) {
					// up or left arrow keys
					case 38:
						var prev = li.prev();
	
						// if there's a previous option, focus it
						if ( prev.length ) {
							target
								.blur()
								.attr( "tabindex", "-1" );
	
							prev.find( "a" ).first().focus();
						}	
	
						return false;
					break;
	
					// down or right arrow keys
					case 40:
						var next = li.next();
					
						// if there's a next option, focus it
						if ( next.length ) {
							target
								.blur()
								.attr( "tabindex", "-1" );
							
							next.find( "a" ).first().focus();
						}	
	
						return false;
					break;
	
					// if enter or space is pressed, trigger click
					case 13:
					case 32:
						 target.trigger( "vclick" );
	
						 return false;
					break;	
				}
			});	

			//events on "screen" overlay
			screen.bind("vclick", function( event ){
				self.close();
			});
			
			//close button on small overlays
			self.headerClose.click(function(){
				if( self.menuType == "overlay" ){
					self.close();
					return false;
				}
			})
		}
	},

	_buildList: function(){
		var self = this,
			o = this.options,
			placeholder = this.placeholder,
			optgroups = [],
			lis = [],
			dataIcon = self.isMultiple ? "checkbox-off" : "false";

		self.list.empty().filter('.ui-listview').listview('destroy');

		//populate menu with options from select element
		self.select.find( "option" ).each(function( i ){
			var $this = $(this),
				$parent = $this.parent(),
				text = $this.text(),
				anchor = "<a href='#'>"+ text +"</a>",
				classes = [],
				extraAttrs = [];

			// are we inside an optgroup?
			if( $parent.is("optgroup") ){
				var optLabel = $parent.attr("label");

				// has this optgroup already been built yet?
				if( $.inArray(optLabel, optgroups) === -1 ){
					lis.push( "<li data-" + $.mobile.ns + "role='list-divider'>"+ optLabel +"</li>" );
					optgroups.push( optLabel );
				}
			}

			//find placeholder text
			if( !this.getAttribute('value') || text.length == 0 || $this.jqmData('placeholder') ){
				if( o.hidePlaceholderMenuItems ){
					classes.push( "ui-selectmenu-placeholder" );
				}
				placeholder = self.placeholder = text;
			}

			// support disabled option tags
			if( this.disabled ){
				classes.push( "ui-disabled" );
				extraAttrs.push( "aria-disabled='true'" );
			}

			lis.push( "<li data-" + $.mobile.ns + "icon='"+ dataIcon +"' class='"+ classes.join(" ") + "' " + extraAttrs.join(" ") +">"+ anchor +"</li>" )
		});

		self.list.html( lis.join(" ") );
		
		self.list.find( "li" )
			.attr({ "role": "option", "tabindex": "-1" })
			.first().attr( "tabindex", "0" );

		// hide header close link for single selects
		if( !this.isMultiple ){
			this.headerClose.hide();
		}

		// hide header if it's not a multiselect and there's no placeholder
		if( !this.isMultiple && !placeholder.length ){
			this.header.hide();
		} else {
			this.headerTitle.text( this.placeholder );
		}

		//now populated, create listview
		self.list.listview();
	},

	refresh: function( forceRebuild ){
		var self = this,
			select = this.element,
			isMultiple = this.isMultiple,
			options = this.optionElems = select.find("option"),
			selected = options.filter(":selected"),

			// return an array of all selected index's
			indicies = selected.map(function(){
				return options.index( this );
			}).get();

		if( !self.options.nativeMenu && ( forceRebuild || select[0].options.length != self.list.find('li').length )){
			self._buildList();
		}

		self.button
			.find( ".ui-btn-text" )
			.text(function(){
				if( !isMultiple ){
					return selected.text();
				}

				return selected.length ?
					selected.map(function(){ return $(this).text(); }).get().join(', ') :
					self.placeholder;
			});

		// multiple count inside button
		if( isMultiple ){
			self.buttonCount[ selected.length > 1 ? 'show' : 'hide' ]().text( selected.length );
		}

		if( !self.options.nativeMenu ){
			self.list
				.find( 'li:not(.ui-li-divider)' )
				.removeClass( $.mobile.activeBtnClass )
				.attr( 'aria-selected', false )
				.each(function( i ){
					if( $.inArray(i, indicies) > -1 ){
						var item = $(this).addClass( $.mobile.activeBtnClass );

						// aria selected attr
						item.find( 'a' ).attr( 'aria-selected', true );

						// multiple selects: add the "on" checkbox state to the icon
						if( isMultiple ){
							item.find('.ui-icon').removeClass('ui-icon-checkbox-off').addClass('ui-icon-checkbox-on');
						}
					}
				});
		}
	},

	open: function(){
		if( this.options.disabled || this.options.nativeMenu ){ return; }

		var self = this,
			menuHeight = self.list.parent().outerHeight(),
			menuWidth = self.list.parent().outerWidth(),
			scrollTop = $(window).scrollTop(),
			btnOffset = self.button.offset().top,
			screenHeight = window.innerHeight,
			screenWidth = window.innerWidth;

		//add active class to button
		self.button.addClass( $.mobile.activeBtnClass );

		//remove after delay
		setTimeout(function(){
			self.button.removeClass( $.mobile.activeBtnClass );
		}, 300);

		function focusMenuItem(){
			self.list.find( ".ui-btn-active" ).focus();
		}

		if( menuHeight > screenHeight - 80 || !$.support.scrollTop ){

			//for webos (set lastscroll using button offset)
			if( scrollTop == 0 && btnOffset > screenHeight ){
				self.thisPage.one('pagehide',function(){
					$(this).jqmData('lastScroll', btnOffset);
				});
			}

			self.menuPage.one('pageshow', function() {
				// silentScroll() is called whenever a page is shown to restore
				// any previous scroll position the page may have had. We need to
				// wait for the "silentscroll" event before setting focus to avoid
				// the browser's "feature" which offsets rendering to make sure
				// whatever has focus is in view.
				$(window).one("silentscroll", function(){ focusMenuItem(); });
			});

			self.menuType = "page";
			self.menuPageContent.append( self.list );
			$.mobile.changePage(self.menuPage, 'pop', false, true);
		}
		else {
			self.menuType = "overlay";

			self.screen
				.height( $(document).height() )
				.removeClass('ui-screen-hidden');

			//try and center the overlay over the button
			var roomtop = btnOffset - scrollTop,
				roombot = scrollTop + screenHeight - btnOffset,
				halfheight = menuHeight / 2,
				maxwidth = parseFloat(self.list.parent().css('max-width')),
				newtop, newleft;

			if( roomtop > menuHeight / 2 && roombot > menuHeight / 2 ){
				newtop = btnOffset + ( self.button.outerHeight() / 2 ) - halfheight;
			}
			else{
				//30px tolerance off the edges
				newtop = roomtop > roombot ? scrollTop + screenHeight - menuHeight - 30 : scrollTop + 30;
			}

			// if the menuwidth is smaller than the screen center is
			if (menuWidth < maxwidth) {
				newleft = (screenWidth - menuWidth) / 2;
			} else { //otherwise insure a >= 30px offset from the left
				newleft = self.button.offset().left + self.button.outerWidth() / 2 - menuWidth / 2;
				// 30px tolerance off the edges
				if (newleft < 30) {
					newleft = 30;
				} else if ((newleft + menuWidth) > screenWidth) {
					newleft = screenWidth - menuWidth - 30;
				}
			}

			self.listbox
				.append( self.list )
				.removeClass( "ui-selectmenu-hidden" )
				.css({
					top: newtop,
					left: newleft
				})
				.addClass("in");

			focusMenuItem();
		}

		// wait before the dialog can be closed
		setTimeout(function(){
		 	self.isOpen = true;
		}, 400);
	},

	close: function(){
		if( this.options.disabled || !this.isOpen || this.options.nativeMenu ){ return; }
		var self = this;

		function focusButton(){
			setTimeout(function(){
				self.button.focus();
			}, 40);

			self.listbox.removeAttr('style').append( self.list );
		}

		if(self.menuType == "page"){
			$.mobile.changePage([self.menuPage,self.thisPage], 'pop', true, false);
			self.menuPage.one("pagehide", focusButton);
		}
		else{
			self.screen.addClass( "ui-screen-hidden" );
			self.listbox.addClass( "ui-selectmenu-hidden" ).removeAttr( "style" ).removeClass("in");
			focusButton();
		}

		// allow the dialog to be closed again
		this.isOpen = false;
	},

	disable: function(){
		this.element.attr("disabled",true);
		this.button.addClass('ui-disabled').attr("aria-disabled", true);
		return this._setOption( "disabled", true );
	},

	enable: function(){
		this.element.attr("disabled",false);
		this.button.removeClass('ui-disabled').attr("aria-disabled", false);
		return this._setOption( "disabled", false );
	}
});
})( jQuery );

/*
* jQuery Mobile Framework : plugin for making button-like links
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/
(function($, undefined ) {

$.fn.buttonMarkup = function( options ){
	return this.each( function() {
		var el = $( this ),
		    o = $.extend( {}, $.fn.buttonMarkup.defaults, el.jqmData(), options),

			// Classes Defined
			buttonClass,
			innerClass = "ui-btn-inner",
			iconClass;

		if ( attachEvents ) {
			attachEvents();
		}

		// if not, try to find closest theme container
		if ( !o.theme ) {
			var themedParent = el.closest("[class*='ui-bar-'],[class*='ui-body-']");
			o.theme = themedParent.length ?
				/ui-(bar|body)-([a-z])/.exec( themedParent.attr("class") )[2] :
				"c";
		}

		buttonClass = "ui-btn ui-btn-up-" + o.theme;

		if ( o.inline ) {
			buttonClass += " ui-btn-inline";
		}

		if ( o.icon ) {
			o.icon = "ui-icon-" + o.icon;
			o.iconpos = o.iconpos || "left";

			iconClass = "ui-icon " + o.icon;

			if ( o.shadow ) {
				iconClass += " ui-icon-shadow";
			}
		}

		if ( o.iconpos ) {
			buttonClass += " ui-btn-icon-" + o.iconpos;

			if ( o.iconpos == "notext" && !el.attr("title") ) {
				el.attr( "title", el.text() );
			}
		}

		if ( o.corners ) {
			buttonClass += " ui-btn-corner-all";
			innerClass += " ui-btn-corner-all";
		}

		if ( o.shadow ) {
			buttonClass += " ui-shadow";
		}

		el
			.attr( "data-" + $.mobile.ns + "theme", o.theme )
			.addClass( buttonClass );

		var wrap = ("<D class='" + innerClass + "'><D class='ui-btn-text'></D>" +
			( o.icon ? "<span class='" + iconClass + "'></span>" : "" ) +
			"</D>").replace(/D/g, o.wrapperEls);

		el.wrapInner( wrap );
	});
};

$.fn.buttonMarkup.defaults = {
	corners: true,
	shadow: true,
	iconshadow: true,
	wrapperEls: "span"
};

var attachEvents = function() {
	$(".ui-btn:not(.ui-disabled)").live({
		"vmousedown": function() {
			var theme = $(this).attr( "data-" + $.mobile.ns + "theme" );
			$(this).removeClass( "ui-btn-up-" + theme ).addClass( "ui-btn-down-" + theme );
		},
		"vmousecancel vmouseup": function() {
			var theme = $(this).attr( "data-" + $.mobile.ns + "theme" );
			$(this).removeClass( "ui-btn-down-" + theme ).addClass( "ui-btn-up-" + theme );
		},
		"vmouseover focus": function() {
			var theme = $(this).attr( "data-" + $.mobile.ns + "theme" );
			$(this).removeClass( "ui-btn-up-" + theme ).addClass( "ui-btn-hover-" + theme );
		},
		"vmouseout blur": function() {
			var theme = $(this).attr( "data-" + $.mobile.ns + "theme" );
			$(this).removeClass( "ui-btn-hover-" + theme ).addClass( "ui-btn-up-" + theme );
		}
	});

	attachEvents = null;
};

})(jQuery);
/*
* jQuery Mobile Framework : "button" plugin - links that proxy to native input/buttons
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/ 
(function($, undefined ) {
$.widget( "mobile.button", $.mobile.widget, {
	options: {
		theme: null, 
		icon: null,
		iconpos: null,
		inline: null,
		corners: true,
		shadow: true,
		iconshadow: true
	},
	_create: function(){
		var $el = this.element,
			o = this.options;
		
		//add ARIA role
		this.button = $( "<div></div>" )
			.text( $el.text() || $el.val() )
			.buttonMarkup({
				theme: o.theme, 
				icon: o.icon,
				iconpos: o.iconpos,
				inline: o.inline,
				corners: o.corners,
				shadow: o.shadow,
				iconshadow: o.iconshadow
			})
			.insertBefore( $el )
			.append( $el.addClass('ui-btn-hidden') );
		
		//add hidden input during submit
		var type = $el.attr('type');
		if( type !== 'button' && type !== 'reset' ){
			$el.bind("vclick", function(){
				var $buttonPlaceholder = $("<input>", 
						{type: "hidden", name: $el.attr("name"), value: $el.attr("value")})
						.insertBefore($el);
						
				//bind to doc to remove after submit handling	
				$(document).submit(function(){
					 $buttonPlaceholder.remove();
				});
			});
		}
		this.refresh();
			
	},

	enable: function(){
		this.element.attr("disabled", false);
		this.button.removeClass("ui-disabled").attr("aria-disabled", false);
		return this._setOption("disabled", false);
	},

	disable: function(){
		this.element.attr("disabled", true);
		this.button.addClass("ui-disabled").attr("aria-disabled", true);
		return this._setOption("disabled", true);
	},

	refresh: function(){
		if( this.element.attr('disabled') ){
			this.disable();
		}
		else{
			this.enable();
		}
	}
});
})( jQuery );/*
* jQuery Mobile Framework : "slider" plugin
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/
(function($, undefined ) {
$.widget( "mobile.slider", $.mobile.widget, {
	options: {
		theme: null,
		trackTheme: null,
		disabled: false
	},
	_create: function(){
		var self = this,

			control = this.element,

			parentTheme = control.parents('[class*=ui-bar-],[class*=ui-body-]').eq(0),

			parentTheme = parentTheme.length ? parentTheme.attr('class').match(/ui-(bar|body)-([a-z])/)[2] : 'c',

			theme = this.options.theme ? this.options.theme : parentTheme,

			trackTheme = this.options.trackTheme ? this.options.trackTheme : parentTheme,

			cType = control[0].nodeName.toLowerCase(),
			selectClass = (cType == 'select') ? 'ui-slider-switch' : '',
			controlID = control.attr('id'),
			labelID = controlID + '-label',
			label = $('[for='+ controlID +']').attr('id',labelID),
			val = function(){
				return (cType == 'input') ? parseFloat(control.val()) : control[0].selectedIndex;
			},
			min = (cType == 'input') ? parseFloat(control.attr('min')) : 0,
			max = (cType == 'input') ? parseFloat(control.attr('max')) : control.find('option').length-1,
			step = window.parseFloat(control.attr('step') || 1),
			slider = $('<div class="ui-slider '+ selectClass +' ui-btn-down-'+ trackTheme+' ui-btn-corner-all" role="application"></div>'),
			handle = $('<a href="#" class="ui-slider-handle"></a>')
				.appendTo(slider)
				.buttonMarkup({corners: true, theme: theme, shadow: true})
				.attr({
					'role': 'slider',
					'aria-valuemin': min,
					'aria-valuemax': max,
					'aria-valuenow': val(),
					'aria-valuetext': val(),
					'title': val(),
					'aria-labelledby': labelID
				});

		$.extend(this, {
			slider: slider,
			handle: handle,
			dragging: false,
			beforeStart: null
		});

		if(cType == 'select'){
			slider.wrapInner('<div class="ui-slider-inneroffset"></div>');
			var options = control.find('option');

			control.find('option').each(function(i){
				var side = (i==0) ?'b':'a',
					corners = (i==0) ? 'right' :'left',
					theme = (i==0) ? ' ui-btn-down-' + trackTheme :' ui-btn-active';
				$('<div class="ui-slider-labelbg ui-slider-labelbg-'+ side + theme +' ui-btn-corner-'+ corners+'"></div>').prependTo(slider);
				$('<span class="ui-slider-label ui-slider-label-'+ side + theme +' ui-btn-corner-'+ corners+'" role="img">'+$(this).text()+'</span>').prependTo(handle);
			});

		}

		label.addClass('ui-slider');

		// monitor the input for updated values
		control
			.addClass((cType == 'input') ? 'ui-slider-input' : 'ui-slider-switch')
			.change(function(){
				self.refresh( val(), true );
			})
			.keyup(function(){ // necessary?
				self.refresh( val(), true, true );
			})
			.blur(function(){
				self.refresh( val(), true );
			});

		// prevent screen drag when slider activated
		$(document).bind( "vmousemove", function(event){
			if ( self.dragging ) {
				self.refresh( event );
				return false;
			}
		});

		slider
			.bind( "vmousedown", function(event){
				self.dragging = true;
				if ( cType === "select" ) {
					self.beforeStart = control[0].selectedIndex;
				}
				self.refresh( event );
				return false;
			});

		slider
			.add(document)
			.bind( "vmouseup", function(){
				if ( self.dragging ) {
					self.dragging = false;
					if ( cType === "select" ) {
						if ( self.beforeStart === control[0].selectedIndex ) {
							//tap occurred, but value didn't change. flip it!
							self.refresh( self.beforeStart === 0 ? 1 : 0 );
						}
						var curval = val();
						var snapped = Math.round( curval / (max - min) * 100 );
						handle
							.addClass("ui-slider-handle-snapping")
							.css("left", snapped + "%")
							.animationComplete(function(){
								handle.removeClass("ui-slider-handle-snapping");
							});
					}
					return false;
				}
			});

		slider.insertAfter(control);

		// NOTE force focus on handle
		this.handle
			.bind( "vmousedown", function(){
				$(this).focus();
			})
			.bind( "vclick", false );

		this.handle
			.bind( "keydown", function( event ) {
				var index = val();

				if ( self.options.disabled ) {
					return;
				}

				// In all cases prevent the default and mark the handle as active
				switch ( event.keyCode ) {
				 case $.mobile.keyCode.HOME:
				 case $.mobile.keyCode.END:
				 case $.mobile.keyCode.PAGE_UP:
				 case $.mobile.keyCode.PAGE_DOWN:
				 case $.mobile.keyCode.UP:
				 case $.mobile.keyCode.RIGHT:
				 case $.mobile.keyCode.DOWN:
				 case $.mobile.keyCode.LEFT:
					event.preventDefault();

					if ( !self._keySliding ) {
						self._keySliding = true;
						$( this ).addClass( "ui-state-active" );
					}
					break;
				}

				// move the slider according to the keypress
				switch ( event.keyCode ) {
				 case $.mobile.keyCode.HOME:
					self.refresh(min);
					break;
				 case $.mobile.keyCode.END:
					self.refresh(max);
					break;
				 case $.mobile.keyCode.PAGE_UP:
				 case $.mobile.keyCode.UP:
				 case $.mobile.keyCode.RIGHT:
					self.refresh(index + step);
					break;
				 case $.mobile.keyCode.PAGE_DOWN:
				 case $.mobile.keyCode.DOWN:
				 case $.mobile.keyCode.LEFT:
					self.refresh(index - step);
					break;
				}
			}) // remove active mark
			.keyup(function( event ) {
				if ( self._keySliding ) {
					self._keySliding = false;
					$( this ).removeClass( "ui-state-active" );
				}
			});

		this.refresh();
	},

	refresh: function(val, isfromControl, preventInputUpdate){
		if ( this.options.disabled ) { return; }

		var control = this.element, percent,
			cType = control[0].nodeName.toLowerCase(),
			min = (cType === "input") ? parseFloat(control.attr("min")) : 0,
			max = (cType === "input") ? parseFloat(control.attr("max")) : control.find("option").length - 1;

		if ( typeof val === "object" ) {
			var data = val,
				// a slight tolerance helped get to the ends of the slider
				tol = 8;
			if ( !this.dragging
					|| data.pageX < this.slider.offset().left - tol
					|| data.pageX > this.slider.offset().left + this.slider.width() + tol ) {
				return;
			}
			percent = Math.round( ((data.pageX - this.slider.offset().left) / this.slider.width() ) * 100 );
		} else {
			if ( val == null ) {
				val = (cType === "input") ? parseFloat(control.val()) : control[0].selectedIndex;
			}
			percent = (parseFloat(val) - min) / (max - min) * 100;
		}

		if ( isNaN(percent) ) { return; }
		if ( percent < 0 ) { percent = 0; }
		if ( percent > 100 ) { percent = 100; }

		var newval = Math.round( (percent / 100) * (max - min) ) + min;
		if ( newval < min ) { newval = min; }
		if ( newval > max ) { newval = max; }

		//flip the stack of the bg colors
		if ( percent > 60 && cType === "select" ) {

		}
		this.handle.css("left", percent + "%");
		this.handle.attr({
				"aria-valuenow": (cType === "input") ? newval : control.find("option").eq(newval).attr("value"),
				"aria-valuetext": (cType === "input") ? newval : control.find("option").eq(newval).text(),
				title: newval
			});

		// add/remove classes for flip toggle switch
		if ( cType === "select" ) {
			if ( newval === 0 ) {
				this.slider.addClass("ui-slider-switch-a")
					.removeClass("ui-slider-switch-b");
			} else {
				this.slider.addClass("ui-slider-switch-b")
					.removeClass("ui-slider-switch-a");
			}
		}

		if(!preventInputUpdate){
			// update control's value
			if ( cType === "input" ) {
				control.val(newval);
			} else {
				control[ 0 ].selectedIndex = newval;
			}
			if (!isfromControl) { control.trigger("change"); }
		}
	},

	enable: function(){
		this.element.attr("disabled", false);
		this.slider.removeClass("ui-disabled").attr("aria-disabled", false);
		return this._setOption("disabled", false);
	},

	disable: function(){
		this.element.attr("disabled", true);
		this.slider.addClass("ui-disabled").attr("aria-disabled", true);
		return this._setOption("disabled", true);
	}

});
})( jQuery );

/*
* jQuery Mobile Framework : "collapsible" plugin
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/ 
(function($, undefined ) {
$.widget( "mobile.collapsible", $.mobile.widget, {
	options: {
		expandCueText: ' click to expand contents',
		collapseCueText: ' click to collapse contents',
		collapsed: false,
		heading: '>:header,>legend',
		theme: null,
		iconTheme: 'd'
	},
	_create: function(){

		var $el = this.element,
			o = this.options,
			collapsibleContain = $el.addClass('ui-collapsible-contain'),
			collapsibleHeading = $el.find(o.heading).eq(0),
			collapsibleContent = collapsibleContain.wrapInner('<div class="ui-collapsible-content"></div>').find('.ui-collapsible-content'),
			collapsibleParent = $el.closest( ":jqmData(role='collapsible-set')" ).addClass('ui-collapsible-set');				
		
		//replace collapsibleHeading if it's a legend	
		if(collapsibleHeading.is('legend')){
			collapsibleHeading = $('<div role="heading">'+ collapsibleHeading.html() +'</div>').insertBefore(collapsibleHeading);
			collapsibleHeading.next().remove();
		}	
		
		//drop heading in before content
		collapsibleHeading.insertBefore(collapsibleContent);
		
		//modify markup & attributes
		collapsibleHeading.addClass('ui-collapsible-heading')
			.append('<span class="ui-collapsible-heading-status"></span>')
			.wrapInner('<a href="#" class="ui-collapsible-heading-toggle"></a>')
			.find('a:eq(0)')
			.buttonMarkup({
				shadow: !!!collapsibleParent.length,
				corners:false,
				iconPos: 'left',
				icon: 'plus',
				theme: o.theme
			})
			.find('.ui-icon')
			.removeAttr('class')
			.buttonMarkup({
				shadow: true,
				corners:true,
				iconPos: 'notext',
				icon: 'plus',
				theme: o.iconTheme
			});
			
			if( !collapsibleParent.length ){
				collapsibleHeading
					.find('a:eq(0)')	
					.addClass('ui-corner-all')
						.find('.ui-btn-inner')
						.addClass('ui-corner-all');
			}
			else {
				if( collapsibleContain.jqmData('collapsible-last') ){
					collapsibleHeading
						.find('a:eq(0), .ui-btn-inner')	
							.addClass('ui-corner-bottom');
				}					
			}
			
		
		//events
		collapsibleContain	
			.bind('collapse', function(event){
				if( !event.isDefaultPrevented() ){
					event.preventDefault();
					collapsibleHeading
						.addClass('ui-collapsible-heading-collapsed')
						.find('.ui-collapsible-heading-status').text(o.expandCueText);
					
					collapsibleHeading.find('.ui-icon').removeClass('ui-icon-minus').addClass('ui-icon-plus');	
					collapsibleContent.addClass('ui-collapsible-content-collapsed').attr('aria-hidden',true);
					
					if( collapsibleContain.jqmData('collapsible-last') ){
						collapsibleHeading
							.find('a:eq(0), .ui-btn-inner')
							.addClass('ui-corner-bottom');
					}
				}						
				
			})
			.bind('expand', function(event){
				if( !event.isDefaultPrevented() ){
					event.preventDefault();
					collapsibleHeading
						.removeClass('ui-collapsible-heading-collapsed')
						.find('.ui-collapsible-heading-status').text(o.collapseCueText);
					
					collapsibleHeading.find('.ui-icon').removeClass('ui-icon-plus').addClass('ui-icon-minus');	
					collapsibleContent.removeClass('ui-collapsible-content-collapsed').attr('aria-hidden',false);
					
					if( collapsibleContain.jqmData('collapsible-last') ){
						collapsibleHeading
							.find('a:eq(0), .ui-btn-inner')
							.removeClass('ui-corner-bottom');
					}
					
				}
			})
			.trigger(o.collapsed ? 'collapse' : 'expand');
			
		
		//close others in a set
		if( collapsibleParent.length && !collapsibleParent.jqmData("collapsiblebound") ){
			collapsibleParent
				.jqmData("collapsiblebound", true)
				.bind("expand", function( event ){
					$(this).find( ".ui-collapsible-contain" )
						.not( $(event.target).closest( ".ui-collapsible-contain" ) )
						.not( "> .ui-collapsible-contain .ui-collapsible-contain" )
						.trigger( "collapse" );
				});
			var set = collapsibleParent.find( ":jqmData(role=collapsible)" )
					
			set.first()
				.find('a:eq(0)')	
				.addClass('ui-corner-top')
					.find('.ui-btn-inner')
					.addClass('ui-corner-top');
					
			set.last().jqmData('collapsible-last', true)	
		}
					
		collapsibleHeading
			.bind("vmouseup", function(e){ 
				if( collapsibleHeading.is('.ui-collapsible-heading-collapsed') ){
					collapsibleContain.trigger('expand'); 
				}	
				else {
					collapsibleContain.trigger('collapse'); 
				}
				e.preventDefault();
			})
			.bind("vclick",false );
	}
});
})( jQuery );/*
* jQuery Mobile Framework: "controlgroup" plugin - corner-rounding for groups of buttons, checks, radios, etc
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/
(function($, undefined ) {
$.fn.controlgroup = function(options){
		
	return this.each(function(){
		var o = $.extend({
			direction: $( this ).jqmData( "type" ) || "vertical",
			shadow: false
		},options);
		var groupheading = $(this).find('>legend'),
			flCorners = o.direction == 'horizontal' ? ['ui-corner-left', 'ui-corner-right'] : ['ui-corner-top', 'ui-corner-bottom'],
			type = $(this).find('input:eq(0)').attr('type');
		
		//replace legend with more stylable replacement div	
		if( groupheading.length ){
			$(this).wrapInner('<div class="ui-controlgroup-controls"></div>');	
			$('<div role="heading" class="ui-controlgroup-label">'+ groupheading.html() +'</div>').insertBefore( $(this).children(0) );	
			groupheading.remove();	
		}

		$(this).addClass('ui-corner-all ui-controlgroup ui-controlgroup-'+o.direction);
		
		function flipClasses(els){
			els
				.removeClass('ui-btn-corner-all ui-shadow')
				.eq(0).addClass(flCorners[0])
				.end()
				.filter(':last').addClass(flCorners[1]).addClass('ui-controlgroup-last');
		}
		flipClasses($(this).find('.ui-btn'));
		flipClasses($(this).find('.ui-btn-inner'));
		if(o.shadow){
			$(this).addClass('ui-shadow');
		}
	});	
};
})(jQuery);/*
* jQuery Mobile Framework : "fieldcontain" plugin - simple class additions to make form row separators
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/
(function($, undefined ) {
$.fn.fieldcontain = function(options){
	return this.addClass('ui-field-contain ui-body ui-br');
};
})(jQuery);/*
* jQuery Mobile Framework : "listview" plugin
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/
(function($, undefined ) {

$.widget( "mobile.listview", $.mobile.widget, {
	options: {
		theme: "c",
		countTheme: "c",
		headerTheme: "b",
		dividerTheme: "b",
		splitIcon: "arrow-r",
		splitTheme: "b",
		inset: false
	},
	
	_create: function() {
		var $list = this.element,
			o = this.options;

		// create listview markup 
		$list
			.addClass( "ui-listview" );
		
		if ( o.inset ) {
			$list.addClass( "ui-listview-inset ui-corner-all ui-shadow" );
		}

		this._itemApply( $list, $list );
		
		this.refresh( true );

	},

	_itemApply: function( $list, item ) {
		// TODO class has to be defined in markup
		item.find( ".ui-li-count" )
			.addClass( "ui-btn-up-" + ($list.jqmData( "counttheme" ) || this.options.countTheme) + " ui-btn-corner-all" );

		item.find( "h1, h2, h3, h4, h5, h6" ).addClass( "ui-li-heading" );

		item.find( "p, dl" ).addClass( "ui-li-desc" );

		$list.find( "li" ).find( ">img:eq(0), >:first>img:eq(0)" ).addClass( "ui-li-thumb" ).each(function() {
			$( this ).closest( "li" ).addClass( $(this).is( ".ui-li-icon" ) ? "ui-li-has-icon" : "ui-li-has-thumb" );
		});

		var aside = item.find( ".ui-li-aside" );

		if ( aside.length ) {
            aside.each(function(i, el) {
			    $(el).prependTo( $(el).parent() ); //shift aside to front for css float
            });
		}

		if ( $.support.cssPseudoElement || !$.nodeName( item[0], "ol" ) ) {
			return;
		}
	},
	
	_removeCorners: function(li){
		li
			.add( li.find(".ui-btn-inner, .ui-li-link-alt, .ui-li-thumb") )
			.removeClass( "ui-corner-top ui-corner-bottom ui-corner-br ui-corner-bl ui-corner-tr ui-corner-tl" );
	},
	
	refresh: function( create ) {
		this._createSubPages();
		
		var o = this.options,
			$list = this.element,
			self = this,
			dividertheme = $list.jqmData( "dividertheme" ) || o.dividerTheme,
			li = $list.children( "li" ),
			counter = $.support.cssPseudoElement || !$.nodeName( $list[0], "ol" ) ? 0 : 1;

		if ( counter ) {
			$list.find( ".ui-li-dec" ).remove();
		}

		li.each(function( pos ) {
			var item = $( this ),
				itemClass = "ui-li";

			// If we're creating the element, we update it regardless
			if ( !create && item.hasClass( "ui-li" ) ) {
				return;
			}

			var itemTheme = item.jqmData("theme") || o.theme;

			var a = item.find( ">a" );
				
			if ( a.length ) {	
				var icon = item.jqmData("icon");
				
				item
					.buttonMarkup({
						wrapperEls: "div",
						shadow: false,
						corners: false,
						iconpos: "right",
						icon: a.length > 1 || icon === false ? false : icon || "arrow-r",
						theme: itemTheme
					});

				a.first().addClass( "ui-link-inherit" );

				if ( a.length > 1 ) {
					itemClass += " ui-li-has-alt";

					var last = a.last(),
						splittheme = $list.jqmData( "splittheme" ) || last.jqmData( "theme" ) || o.splitTheme;
					
					last
						.appendTo(item)
						.attr( "title", last.text() )
						.addClass( "ui-li-link-alt" )
						.empty()
						.buttonMarkup({
							shadow: false,
							corners: false,
							theme: itemTheme,
							icon: false,
							iconpos: false
						})
						.find( ".ui-btn-inner" )
							.append( $( "<span>" ).buttonMarkup({
								shadow: true,
								corners: true,
								theme: splittheme,
								iconpos: "notext",
								icon: $list.jqmData( "spliticon" ) || last.jqmData( "icon" ) ||  o.splitIcon
							} ) );
				}

			} else if ( item.jqmData( "role" ) === "list-divider" ) {
				itemClass += " ui-li-divider ui-btn ui-bar-" + dividertheme;
				item.attr( "role", "heading" );

				//reset counter when a divider heading is encountered
				if ( counter ) {
					counter = 1;
				}

			} else {
				itemClass += " ui-li-static ui-body-" + itemTheme;
			}
			
			
			if( o.inset ){	
				if ( pos === 0 ) {
						itemClass += " ui-corner-top";
	
						item
							.add( item.find( ".ui-btn-inner" ) )
							.find( ".ui-li-link-alt" )
								.addClass( "ui-corner-tr" )
							.end()
							.find( ".ui-li-thumb" )
								.addClass( "ui-corner-tl" );
						if(item.next().next().length){
							self._removeCorners( item.next() );		
						}
	
				}
				if ( pos === li.length - 1 ) {
						itemClass += " ui-corner-bottom";
	
						item
							.add( item.find( ".ui-btn-inner" ) )
							.find( ".ui-li-link-alt" )
								.addClass( "ui-corner-br" )
							.end()
							.find( ".ui-li-thumb" )
								.addClass( "ui-corner-bl" );
						
						if(item.prev().prev().length){
							self._removeCorners( item.prev() );		
						}	
				}
			}


			if ( counter && itemClass.indexOf( "ui-li-divider" ) < 0 ) {
			
				var countParent = item.is(".ui-li-static:first") ? item : item.find( ".ui-link-inherit" );
				
				countParent
					.addClass( "ui-li-jsnumbering" )
					.prepend( "<span class='ui-li-dec'>" + (counter++) + ". </span>" );
			}

			item.add( item.find( ".ui-btn-inner" ) ).addClass( itemClass );

			if ( !create ) {
				self._itemApply( $list, item );
			}
		});
	},
	
	//create a string for ID/subpage url creation
	_idStringEscape: function( str ){
		return str.replace(/[^a-zA-Z0-9]/g, '-');
	},
	
	_createSubPages: function() {
		var parentList = this.element,
			parentPage = parentList.closest( ".ui-page" ),
			parentId = parentPage.jqmData( "url" ),
			o = this.options,
			self = this,
			persistentFooterID = parentPage.find( ":jqmData(role='footer')" ).jqmData( "id" );

		$( parentList.find( "li>ul, li>ol" ).toArray().reverse() ).each(function( i ) {
			var list = $( this ),
				parent = list.parent(),
				nodeEls = $( list.prevAll().toArray().reverse() ),
				nodeEls = nodeEls.length ? nodeEls : $( "<span>" + $.trim(parent.contents()[ 0 ].nodeValue) + "</span>" ),
				title = nodeEls.first().text(),//url limits to first 30 chars of text
				id = parentId + "&" + $.mobile.subPageUrlKey + "=" + self._idStringEscape(title + " " + i),
				theme = list.jqmData( "theme" ) || o.theme,
				countTheme = list.jqmData( "counttheme" ) || parentList.jqmData( "counttheme" ) || o.countTheme,
				newPage = list.wrap( "<div data-" + $.mobile.ns + "role='page'><div data-" + $.mobile.ns + "role='content'></div></div>" )
							.parent()
								.before( "<div data-" + $.mobile.ns + "role='header' data-" + $.mobile.ns + "theme='" + o.headerTheme + "'><div class='ui-title'>" + title + "</div></div>" )
								.after( persistentFooterID ? $( "<div data-" + $.mobile.ns + "role='footer'  data-" + $.mobile.ns + "id='"+ persistentFooterID +"'>") : "" )
								.parent()
									.attr( "data-" + $.mobile.ns + "url", id )
									.attr( "data-" + $.mobile.ns + "theme", theme )
									.attr( "data-" + $.mobile.ns + "count-theme", countTheme )
									.appendTo( $.mobile.pageContainer );

				newPage.page();		
			var anchor = parent.find('a:first');
			if (!anchor.length) {
				anchor = $("<a></a>").html( nodeEls || title ).prependTo(parent.empty());
			}
			anchor.attr('href','#' + id);
		}).listview();
	}
});

})( jQuery );
/*
* jQuery Mobile Framework : "listview" filter extension
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/
(function($, undefined ) {

$.mobile.listview.prototype.options.filter = false;
$.mobile.listview.prototype.options.filterPlaceholder = "Filter items...";

$( ":jqmData(role='listview')" ).live( "listviewcreate", function() {
	var list = $( this ),
		listview = list.data( "listview" );

	if ( !listview.options.filter ) {
		return;
	}

	var wrapper = $( "<form>", { "class": "ui-listview-filter ui-bar-c", "role": "search" } ),

		search = $( "<input>", {
				placeholder: listview.options.filterPlaceholder
			})
			.attr( "data-" + $.mobile.ns + "type", "search" )
			.bind( "keyup change", function() {
				var val = this.value.toLowerCase(),
						listItems = list.children();
				listItems.show();
				if ( val ) {
					// This handles hiding regular rows without the text we search for
					// and any list dividers without regular rows shown under it
					var childItems = false,
							item;

					for (var i = listItems.length; i >= 0; i--) {
						item = $(listItems[i]);
						if (item.is("li:jqmData(role=list-divider)")) {
							if (!childItems) {
								item.hide();
							}
							// New bucket!
							childItems = false;
						} else if (item.text().toLowerCase().indexOf( val ) === -1) {
							item.hide();
						} else {
							// There's a shown item in the bucket
							childItems = true;
						}
					}
				}
			})
			.appendTo( wrapper )
			.textinput();

	if ($( this ).jqmData( "inset" ) ) {
		wrapper.addClass( "ui-listview-filter-inset" );
	}

	wrapper.insertBefore( list );
});

})( jQuery );
/*
* jQuery Mobile Framework : "dialog" plugin.
* Copyright (c) jQuery Project
* Dual licensed under the MIT (MIT-LICENSE.txt) and GPL (GPL-LICENSE.txt) licenses.
* Note: Code is in draft form and is subject to change
*/
(function($, undefined ) {
$.widget( "mobile.dialog", $.mobile.widget, {
	options: {
		closeBtnText: "Close"
	},
	_create: function(){
		var self = this,
			$el = self.element;
		
		/* class the markup for dialog styling */	
		this.element			
			//add ARIA role
			.attr("role","dialog")
			.addClass('ui-page ui-dialog ui-body-a')
			.find( ":jqmData(role=header)" )
			.addClass('ui-corner-top ui-overlay-shadow')
				.prepend( "<a href='#' data-" + $.mobile.ns + "icon='delete' data-" + $.mobile.ns + "rel='back' data-" + $.mobile.ns + "iconpos='notext'>"+ this.options.closeBtnText +"</a>" )
			.end()
			.find('.ui-content:not([class*="ui-body-"])')
				.addClass('ui-body-c')
			.end()
			.find( ".ui-content,:jqmData(role='footer')" )
				.last()
				.addClass('ui-corner-bottom ui-overlay-shadow');
		
		/* bind events 
			- clicks and submits should use the closing transition that the dialog opened with
			  unless a data-transition is specified on the link/form
			- if the click was on the close button, or the link has a data-rel="back" it'll go back in history naturally
		*/
		this.element		
			.bind( "vclick submit", function(e){
				var $targetel;
				if( e.type == "vclick" ){
					$targetel = $(e.target).closest("a");
				}
				else{
					$targetel = $(e.target).closest("form");
				}
				
				if( $targetel.length && !$targetel.jqmData("transition") ){
					$targetel
						.attr("data-" + $.mobile.ns + "transition", $.mobile.urlHistory.getActive().transition )
						.attr("data-" + $.mobile.ns + "direction", "reverse");
				}
			});

	},
	
	//close method goes back in history
	close: function(){
		window.history.back();
	}
});
})( jQuery );/*
* jQuery Mobile Framework : "navbar" plugin
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/
(function($, undefined ) {
$.widget( "mobile.navbar", $.mobile.widget, {
	options: {
		iconpos: 'top',
		grid: null
	},
	_create: function(){
		var $navbar = this.element,
			$navbtns = $navbar.find("a"),
			iconpos = $navbtns.filter( ":jqmData(icon)").length ? this.options.iconpos : undefined;
		
		$navbar
			.addClass('ui-navbar')
			.attr("role","navigation")
			.find("ul")
				.grid({grid: this.options.grid });		
		
		if( !iconpos ){ 
			$navbar.addClass("ui-navbar-noicons");
		}
		
		$navbtns
			.buttonMarkup({
				corners:	false, 
				shadow:		false, 
				iconpos:	iconpos
			});
		
		$navbar.delegate("a", "vclick",function(event){
			$navbtns.not( ".ui-state-persist" ).removeClass( $.mobile.activeBtnClass );
			$( this ).addClass( $.mobile.activeBtnClass );
		});	
	}
});
})( jQuery );
/*
* jQuery Mobile Framework : plugin for creating CSS grids
* Copyright (c) jQuery Project
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*/ 
(function($, undefined ) {
$.fn.grid = function(options){
	return this.each(function(){
		var o = $.extend({
			grid: null
		},options);
	
			
		var $kids = $(this).children(),
			gridCols = {solo:1, a:2, b:3, c:4, d:5},
			grid = o.grid,
			iterator;
			
			if( !grid ){
				if( $kids.length <= 5 ){
					for(var letter in gridCols){
						if(gridCols[letter] == $kids.length){ grid = letter; }
					}
				}
				else{
					grid = 'a';
				}
			}
			iterator = gridCols[grid];
			
		$(this).addClass('ui-grid-' + grid);
	
		$kids.filter(':nth-child(' + iterator + 'n+1)').addClass('ui-block-a');
		if(iterator > 1){	
			$kids.filter(':nth-child(' + iterator + 'n+2)').addClass('ui-block-b');
		}	
		if(iterator > 2){	
			$kids.filter(':nth-child(3n+3)').addClass('ui-block-c');
		}	
		if(iterator > 3){	
			$kids.filter(':nth-child(4n+4)').addClass('ui-block-d');
		}	
		if(iterator > 4){	
			$kids.filter(':nth-child(5n+5)').addClass('ui-block-e');
		}
				
	});	
};
})(jQuery);/*!
 * jQuery Mobile v@VERSION
 * http://jquerymobile.com/
 *
 * Copyright 2010, jQuery Project
 * Dual licensed under the MIT or GPL Version 2 licenses.
 * http://jquery.org/license
 */

(function( $, window, undefined ) {
	var	$html = $( "html" ),
			$head = $( "head" ),
			$window = $( window );

 	//trigger mobileinit event - useful hook for configuring $.mobile settings before they're used
	$( window.document ).trigger( "mobileinit" );

	//support conditions
	//if device support condition(s) aren't met, leave things as they are -> a basic, usable experience,
	//otherwise, proceed with the enhancements
	if ( !$.mobile.gradeA() ) {
		return;
	}

	//add mobile, initial load "rendering" classes to docEl
	$html.addClass( "ui-mobile ui-mobile-rendering" );

	//define & prepend meta viewport tag, if content is defined
	//NOTE: this is now deprecated. We recommend placing the meta viewport element in
	//the markup from the start.
	$.mobile.metaViewportContent && !$head.find( "meta[name='viewport']" ).length ? $( "<meta>", { name: "viewport", content: $.mobile.metaViewportContent}).prependTo( $head ) : undefined;

	//loading div which appears during Ajax requests
	//will not appear if $.mobile.loadingMessage is false
	var $loader = $.mobile.loadingMessage ?		$( "<div class='ui-loader ui-body-a ui-corner-all'>" + "<span class='ui-icon ui-icon-loading spin'></span>" + "<h1>" + $.mobile.loadingMessage + "</h1>" + "</div>" )	: undefined;

	if(typeof $loader === "undefined"){
		alert($.mobile.loadingMessage);
	}

	$.extend($.mobile, {
		// turn on/off page loading message.
		pageLoading: function ( done ) {
			if ( done ) {
				$html.removeClass( "ui-loading" );
			} else {
				if( $.mobile.loadingMessage ){
					var activeBtn = $( "." + $.mobile.activeBtnClass ).first();


					if(typeof $loader === "undefined"){
						 alert($.mobile.loadingMessage);
					}

					$loader
						.appendTo( $.mobile.pageContainer )
						//position at y center (if scrollTop supported), above the activeBtn (if defined), or just 100px from top
						.css( {
							top: $.support.scrollTop && $(window).scrollTop() + $(window).height() / 2 ||
							activeBtn.length && activeBtn.offset().top || 100
						} );
				}

				$html.addClass( "ui-loading" );
			}
		},

		// find and enhance the pages in the dom and transition to the first page.
		initializePage: function(){
			//find present pages
			var $pages = $( ":jqmData(role='page')" );

			//add dialogs, set data-url attrs
			$pages.add( ":jqmData(role='dialog')" ).each(function(){
				var $this = $(this);

				// unless the data url is already set set it to the id
				if( !$this.jqmData('url') ){
					$this.attr( "data-" + $.mobile.ns + "url", $this.attr( "id" ) );
				}
			});

			//define first page in dom case one backs out to the directory root (not always the first page visited, but defined as fallback)
			$.mobile.firstPage = $pages.first();

			//define page container
			$.mobile.pageContainer = $pages.first().parent().addClass( "ui-mobile-viewport" );

			//cue page loading message
			$.mobile.pageLoading();

			// if hashchange listening is disabled or there's no hash deeplink, change to the first page in the DOM
			if( !$.mobile.hashListeningEnabled || !$.mobile.path.stripHash( location.hash ) ){
				$.mobile.changePage( $.mobile.firstPage, false, true, false, true );
			}
			// otherwise, trigger a hashchange to load a deeplink
			else {
				$window.trigger( "hashchange", [ true ] );
			}
		}
	});

	//dom-ready inits
	$( $.mobile.initializePage );

	//window load event
	//hide iOS browser chrome on load
	$window.load( $.mobile.silentScroll );
})( jQuery, this );
