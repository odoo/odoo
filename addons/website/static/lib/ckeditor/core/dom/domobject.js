/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the {@link CKEDITOR.editor} class, which is the base
 *		for other classes representing DOM objects.
 */

/**
 * Represents a DOM object. This class is not intended to be used directly. It
 * serves as the base class for other classes representing specific DOM
 * objects.
 *
 * @class
 * @mixins CKEDITOR.event
 * @constructor Creates a domObject class instance.
 * @param {Object} nativeDomObject A native DOM object.
 */
CKEDITOR.dom.domObject = function( nativeDomObject ) {
	if ( nativeDomObject ) {
		/**
		 * The native DOM object represented by this class instance.
		 *
		 *		var element = new CKEDITOR.dom.element( 'span' );
		 *		alert( element.$.nodeType ); // '1'
		 *
		 * @readonly
		 * @property {Object}
		 */
		this.$ = nativeDomObject;
	}
};

CKEDITOR.dom.domObject.prototype = (function() {
	// Do not define other local variables here. We want to keep the native
	// listener closures as clean as possible.

	var getNativeListener = function( domObject, eventName ) {
			return function( domEvent ) {
				// In FF, when reloading the page with the editor focused, it may
				// throw an error because the CKEDITOR global is not anymore
				// available. So, we check it here first. (#2923)
				if ( typeof CKEDITOR != 'undefined' )
					domObject.fire( eventName, new CKEDITOR.dom.event( domEvent ) );
			};
		};

	return {

		/**
		 * Get the private `_` object which is bound to the native
		 * DOM object using {@link #getCustomData}.
		 *
		 *		var elementA = new CKEDITOR.dom.element( nativeElement );
		 *		elementA.getPrivate().value = 1;
		 *		...
		 *		var elementB = new CKEDITOR.dom.element( nativeElement );
		 *		elementB.getPrivate().value; // 1
		 *
		 * @returns {Object} The private object.
		 */
		getPrivate: function() {
			var priv;

			// Get the main private object from the custom data. Create it if not defined.
			if ( !( priv = this.getCustomData( '_' ) ) )
				this.setCustomData( '_', ( priv = {} ) );

			return priv;
		},

		// Docs inherited from event.
		on: function( eventName ) {
			// We customize the "on" function here. The basic idea is that we'll have
			// only one listener for a native event, which will then call all listeners
			// set to the event.

			// Get the listeners holder object.
			var nativeListeners = this.getCustomData( '_cke_nativeListeners' );

			if ( !nativeListeners ) {
				nativeListeners = {};
				this.setCustomData( '_cke_nativeListeners', nativeListeners );
			}

			// Check if we have a listener for that event.
			if ( !nativeListeners[ eventName ] ) {
				var listener = nativeListeners[ eventName ] = getNativeListener( this, eventName );

				if ( this.$.addEventListener )
					this.$.addEventListener( eventName, listener, !!CKEDITOR.event.useCapture );
				else if ( this.$.attachEvent )
					this.$.attachEvent( 'on' + eventName, listener );
			}

			// Call the original implementation.
			return CKEDITOR.event.prototype.on.apply( this, arguments );
		},

		// Docs inherited from event.
		removeListener: function( eventName ) {
			// Call the original implementation.
			CKEDITOR.event.prototype.removeListener.apply( this, arguments );

			// If we don't have listeners for this event, clean the DOM up.
			if ( !this.hasListeners( eventName ) ) {
				var nativeListeners = this.getCustomData( '_cke_nativeListeners' );
				var listener = nativeListeners && nativeListeners[ eventName ];
				if ( listener ) {
					if ( this.$.removeEventListener )
						this.$.removeEventListener( eventName, listener, false );
					else if ( this.$.detachEvent )
						this.$.detachEvent( 'on' + eventName, listener );

					delete nativeListeners[ eventName ];
				}
			}
		},

		/**
		 * Removes any listener set on this object.
		 *
		 * To avoid memory leaks we must assure that there are no
		 * references left after the object is no longer needed.
		 */
		removeAllListeners: function() {
			var nativeListeners = this.getCustomData( '_cke_nativeListeners' );
			for ( var eventName in nativeListeners ) {
				var listener = nativeListeners[ eventName ];
				if ( this.$.detachEvent )
					this.$.detachEvent( 'on' + eventName, listener );
				else if ( this.$.removeEventListener )
					this.$.removeEventListener( eventName, listener, false );

				delete nativeListeners[ eventName ];
			}
		}
	};
})();

(function( domObjectProto ) {
	var customData = {};

	CKEDITOR.on( 'reset', function() {
		customData = {};
	});

	/**
	 * Determines whether the specified object is equal to the current object.
	 *
	 *		var doc = new CKEDITOR.dom.document( document );
	 *		alert( doc.equals( CKEDITOR.document ) );	// true
	 *		alert( doc == CKEDITOR.document );			// false
	 *
	 * @param {Object} object The object to compare with the current object.
	 * @returns {Boolean} `true` if the object is equal.
	 */
	domObjectProto.equals = function( object ) {
		// Try/Catch to avoid IE permission error when object is from different document.
		try {
			return ( object && object.$ === this.$ );
		} catch ( er ) {
			return false;
		}
	};

	/**
	 * Sets a data slot value for this object. These values are shared by all
	 * instances pointing to that same DOM object.
	 *
	 * **Note:** The created data slot is only guarantied to be available on this unique dom node,
	 * thus any wish to continue access it from other element clones (either created by
	 * clone node or from `innerHtml`) will fail, for such usage, please use
	 * {@link CKEDITOR.dom.element#setAttribute} instead.
	 *
	 *		var element = new CKEDITOR.dom.element( 'span' );
	 *		element.setCustomData( 'hasCustomData', true );
	 *
	 * @param {String} key A key used to identify the data slot.
	 * @param {Object} value The value to set to the data slot.
	 * @returns {CKEDITOR.dom.domObject} This DOM object instance.
	 * @chainable
	 */
	domObjectProto.setCustomData = function( key, value ) {
		var expandoNumber = this.getUniqueId(),
			dataSlot = customData[ expandoNumber ] || ( customData[ expandoNumber ] = {} );

		dataSlot[ key ] = value;

		return this;
	};

	/**
	 * Gets the value set to a data slot in this object.
	 *
	 *		var element = new CKEDITOR.dom.element( 'span' );
	 *		alert( element.getCustomData( 'hasCustomData' ) );		// e.g. 'true'
	 *		alert( element.getCustomData( 'nonExistingKey' ) );		// null
	 *
	 * @param {String} key The key used to identify the data slot.
	 * @returns {Object} This value set to the data slot.
	 */
	domObjectProto.getCustomData = function( key ) {
		var expandoNumber = this.$[ 'data-cke-expando' ],
			dataSlot = expandoNumber && customData[ expandoNumber ];

		return ( dataSlot && key in dataSlot ) ? dataSlot[ key ] : null;
	};

	/**
	 * Removes the value in data slot under given `key`.
	 *
	 * @param {String} key
	 * @returns {Object} Removed value or `null` if not found.
	 */
	domObjectProto.removeCustomData = function( key ) {
		var expandoNumber = this.$[ 'data-cke-expando' ],
			dataSlot = expandoNumber && customData[ expandoNumber ],
			retval, hadKey;

		if ( dataSlot ) {
			retval = dataSlot[ key ];
			hadKey = key in dataSlot;
			delete dataSlot[ key ];
		}

		return hadKey ? retval : null;
	};

	/**
	 * Removes any data stored on this object.
	 * To avoid memory leaks we must assure that there are no
	 * references left after the object is no longer needed.
	 */
	domObjectProto.clearCustomData = function() {
		// Clear all event listeners
		this.removeAllListeners();

		var expandoNumber = this.$[ 'data-cke-expando' ];
		expandoNumber && delete customData[ expandoNumber ];
	};

	/**
	 * Gets an ID that can be used to identiquely identify this DOM object in
	 * the running session.
	 *
	 * @returns {Number} A unique ID.
	 */
	domObjectProto.getUniqueId = function() {
		return this.$[ 'data-cke-expando' ] || ( this.$[ 'data-cke-expando' ] = CKEDITOR.tools.getNextNumber() );
	};

	// Implement CKEDITOR.event.
	CKEDITOR.event.implementOn( domObjectProto );

})( CKEDITOR.dom.domObject.prototype );
