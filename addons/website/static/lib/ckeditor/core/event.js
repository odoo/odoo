/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the {@link CKEDITOR.event} class, which serves as the
 *		base for classes and objects that require event handling features.
 */

if ( !CKEDITOR.event ) {
	/**
	 * Creates an event class instance. This constructor is rearely used, being
	 * the {@link #implementOn} function used in class prototypes directly
	 * instead.
	 *
	 * This is a base class for classes and objects that require event
	 * handling features.
	 *
	 * Do not confuse this class with {@link CKEDITOR.dom.event} which is
	 * instead used for DOM events. The CKEDITOR.event class implements the
	 * internal event system used by the CKEditor to fire API related events.
	 *
	 * @class
	 * @constructor Creates an event class instance.
	 */
	CKEDITOR.event = function() {};

	/**
	 * Implements the {@link CKEDITOR.event} features in an object.
	 *
	 *		var myObject = { message: 'Example' };
	 *		CKEDITOR.event.implementOn( myObject );
	 *
	 *		myObject.on( 'testEvent', function() {
	 *			alert( this.message );
	 *		} );
	 *		myObject.fire( 'testEvent' ); // 'Example'
	 *
	 * @static
	 * @param {Object} targetObject The object into which implement the features.
	 */
	CKEDITOR.event.implementOn = function( targetObject ) {
		var eventProto = CKEDITOR.event.prototype;

		for ( var prop in eventProto ) {
			if ( targetObject[ prop ] == undefined )
				targetObject[ prop ] = eventProto[ prop ];
		}
	};

	CKEDITOR.event.prototype = (function() {
		// Returns the private events object for a given object.
		var getPrivate = function( obj ) {
				var _ = ( obj.getPrivate && obj.getPrivate() ) || obj._ || ( obj._ = {} );
				return _.events || ( _.events = {} );
			};

		var eventEntry = function( eventName ) {
				this.name = eventName;
				this.listeners = [];
			};

		eventEntry.prototype = {
			// Get the listener index for a specified function.
			// Returns -1 if not found.
			getListenerIndex: function( listenerFunction ) {
				for ( var i = 0, listeners = this.listeners; i < listeners.length; i++ ) {
					if ( listeners[ i ].fn == listenerFunction )
						return i;
				}
				return -1;
			}
		};

		// Retrieve the event entry on the event host (create it if needed).
		function getEntry( name ) {
			// Get the event entry (create it if needed).
			var events = getPrivate( this );
			return events[ name ] || ( events[ name ] = new eventEntry( name ) );
		}

		return {
			/**
			 * Predefine some intrinsic properties on a specific event name.
			 *
			 * @param {String} name The event name
			 * @param meta
			 * @param [meta.errorProof=false] Whether the event firing should catch error thrown from a per listener call.
			 */
			define: function( name, meta ) {
				var entry = getEntry.call( this, name );
				CKEDITOR.tools.extend( entry, meta, true );
			},

			/**
			 * Registers a listener to a specific event in the current object.
			 *
			 *		someObject.on( 'someEvent', function() {
			 *			alert( this == someObject );		// true
			 *		} );
			 *
			 *		someObject.on( 'someEvent', function() {
			 *			alert( this == anotherObject );		// true
			 *		}, anotherObject );
			 *
			 *		someObject.on( 'someEvent', function( event ) {
			 *			alert( event.listenerData );		// 'Example'
			 *		}, null, 'Example' );
			 *
			 *		someObject.on( 'someEvent', function() { ... } );						// 2nd called
			 *		someObject.on( 'someEvent', function() { ... }, null, null, 100 );		// 3rd called
			 *		someObject.on( 'someEvent', function() { ... }, null, null, 1 );		// 1st called
			 *
			 * @param {String} eventName The event name to which listen.
			 * @param {Function} listenerFunction The function listening to the
			 * event. A single {@link CKEDITOR.eventInfo} object instanced
			 * is passed to this function containing all the event data.
			 * @param {Object} [scopeObj] The object used to scope the listener
			 * call (the `this` object). If omitted, the current object is used.
			 * @param {Object} [listenerData] Data to be sent as the
			 * {@link CKEDITOR.eventInfo#listenerData} when calling the
			 * listener.
			 * @param {Number} [priority=10] The listener priority. Lower priority
			 * listeners are called first. Listeners with the same priority
			 * value are called in registration order.
			 * @returns {Object} An object containing the `removeListener`
			 * function, which can be used to remove the listener at any time.
			 */
			on: function( eventName, listenerFunction, scopeObj, listenerData, priority ) {
				// Create the function to be fired for this listener.
				function listenerFirer( editor, publisherData, stopFn, cancelFn ) {
					var ev = {
						name: eventName,
						sender: this,
						editor: editor,
						data: publisherData,
						listenerData: listenerData,
						stop: stopFn,
						cancel: cancelFn,
						removeListener: removeListener
					};

					var ret = listenerFunction.call( scopeObj, ev );

					return ret === false ? false : ev.data;
				}

				function removeListener() {
					me.removeListener( eventName, listenerFunction );
				}

				var event = getEntry.call( this, eventName );

				if ( event.getListenerIndex( listenerFunction ) < 0 ) {
					// Get the listeners.
					var listeners = event.listeners;

					// Fill the scope.
					if ( !scopeObj )
						scopeObj = this;

					// Default the priority, if needed.
					if ( isNaN( priority ) )
						priority = 10;

					var me = this;

					listenerFirer.fn = listenerFunction;
					listenerFirer.priority = priority;

					// Search for the right position for this new listener, based on its
					// priority.
					for ( var i = listeners.length - 1; i >= 0; i-- ) {
						// Find the item which should be before the new one.
						if ( listeners[ i ].priority <= priority ) {
							// Insert the listener in the array.
							listeners.splice( i + 1, 0, listenerFirer );
							return { removeListener: removeListener };
						}
					}

					// If no position has been found (or zero length), put it in
					// the front of list.
					listeners.unshift( listenerFirer );
				}

				return { removeListener: removeListener };
			},

			/**
			 * Similiar with {@link #on} but the listener will be called only once upon the next event firing.
			 *
			 * @see CKEDITOR.event#on
			 */
			once: function() {
				var fn = arguments[ 1 ];

				arguments[ 1 ] = function( evt ) {
					evt.removeListener();
					return fn.apply( this, arguments );
				};

				return this.on.apply( this, arguments );
			},

			/**
			 * @static
			 * @property {Boolean} useCapture
			 * @todo
			 */

			/**
			 * Register event handler under the capturing stage on supported target.
			 */
			capture: function() {
				CKEDITOR.event.useCapture = 1;
				var retval = this.on.apply( this, arguments );
				CKEDITOR.event.useCapture = 0;
				return retval;
			},

			/**
			 * Fires an specific event in the object. All registered listeners are
			 * called at this point.
			 *
			 *		someObject.on( 'someEvent', function() { ... } );
			 *		someObject.on( 'someEvent', function() { ... } );
			 *		someObject.fire( 'someEvent' );				// Both listeners are called.
			 *
			 *		someObject.on( 'someEvent', function( event ) {
			 *			alert( event.data );					// 'Example'
			 *		} );
			 *		someObject.fire( 'someEvent', 'Example' );
			 *
			 * @method
			 * @param {String} eventName The event name to fire.
			 * @param {Object} [data] Data to be sent as the
			 * {@link CKEDITOR.eventInfo#data} when calling the listeners.
			 * @param {CKEDITOR.editor} [editor] The editor instance to send as the
			 * {@link CKEDITOR.eventInfo#editor} when calling the listener.
			 * @returns {Boolean/Object} A boolean indicating that the event is to be
			 * canceled, or data returned by one of the listeners.
			 */
			fire: (function() {
				// Create the function that marks the event as stopped.
				var stopped = 0;
				var stopEvent = function() {
						stopped = 1;
					};

				// Create the function that marks the event as canceled.
				var canceled = 0;
				var cancelEvent = function() {
						canceled = 1;
					};

				return function( eventName, data, editor ) {
					// Get the event entry.
					var event = getPrivate( this )[ eventName ];

					// Save the previous stopped and cancelled states. We may
					// be nesting fire() calls.
					var previousStopped = stopped,
						previousCancelled = canceled;

					// Reset the stopped and canceled flags.
					stopped = canceled = 0;

					if ( event ) {
						var listeners = event.listeners;

						if ( listeners.length ) {
							// As some listeners may remove themselves from the
							// event, the original array length is dinamic. So,
							// let's make a copy of all listeners, so we are
							// sure we'll call all of them.
							listeners = listeners.slice( 0 );

							var retData;
							// Loop through all listeners.
							for ( var i = 0; i < listeners.length; i++ ) {
								// Call the listener, passing the event data.
								if ( event.errorProof ) {
									try {
										retData = listeners[ i ].call( this, editor, data, stopEvent, cancelEvent );
									} catch ( er ) {}
								} else
									retData = listeners[ i ].call( this, editor, data, stopEvent, cancelEvent );

								if ( retData === false )
									canceled = 1;
								else if ( typeof retData != 'undefined' )
									data = retData;

								// No further calls is stopped or canceled.
								if ( stopped || canceled )
									break;
							}
						}
					}

					var ret = canceled ? false : ( typeof data == 'undefined' ? true : data );

					// Restore the previous stopped and canceled states.
					stopped = previousStopped;
					canceled = previousCancelled;

					return ret;
				};
			})(),

			/**
			 * Fires an specific event in the object, releasing all listeners
			 * registered to that event. The same listeners are not called again on
			 * successive calls of it or of {@link #fire}.
			 *
			 *		someObject.on( 'someEvent', function() { ... } );
			 *		someObject.fire( 'someEvent' );			// Above listener called.
			 *		someObject.fireOnce( 'someEvent' );		// Above listener called.
			 *		someObject.fire( 'someEvent' );			// No listeners called.
			 *
			 * @param {String} eventName The event name to fire.
			 * @param {Object} [data] Data to be sent as the
			 * {@link CKEDITOR.eventInfo#data} when calling the listeners.
			 * @param {CKEDITOR.editor} [editor] The editor instance to send as the
			 * {@link CKEDITOR.eventInfo#editor} when calling the listener.
			 * @returns {Boolean/Object} A booloan indicating that the event is to be
			 * canceled, or data returned by one of the listeners.
			 */
			fireOnce: function( eventName, data, editor ) {
				var ret = this.fire( eventName, data, editor );
				delete getPrivate( this )[ eventName ];
				return ret;
			},

			/**
			 * Unregisters a listener function from being called at the specified
			 * event. No errors are thrown if the listener has not been registered previously.
			 *
			 *		var myListener = function() { ... };
			 *		someObject.on( 'someEvent', myListener );
			 *		someObject.fire( 'someEvent' );					// myListener called.
			 *		someObject.removeListener( 'someEvent', myListener );
			 *		someObject.fire( 'someEvent' );					// myListener not called.
			 *
			 * @param {String} eventName The event name.
			 * @param {Function} listenerFunction The listener function to unregister.
			 */
			removeListener: function( eventName, listenerFunction ) {
				// Get the event entry.
				var event = getPrivate( this )[ eventName ];

				if ( event ) {
					var index = event.getListenerIndex( listenerFunction );
					if ( index >= 0 )
						event.listeners.splice( index, 1 );
				}
			},

			/**
			 * Remove all existing listeners on this object, for cleanup purpose.
			 */
			removeAllListeners: function() {
				var events = getPrivate( this );
				for ( var i in events )
					delete events[ i ];
			},

			/**
			 * Checks if there is any listener registered to a given event.
			 *
			 *		var myListener = function() { ... };
			 *		someObject.on( 'someEvent', myListener );
			 *		alert( someObject.hasListeners( 'someEvent' ) );	// true
			 *		alert( someObject.hasListeners( 'noEvent' ) );		// false
			 *
			 * @param {String} eventName The event name.
			 * @returns {Boolean}
			 */
			hasListeners: function( eventName ) {
				var event = getPrivate( this )[ eventName ];
				return ( event && event.listeners.length > 0 );
			}
		};
	})();
}
