/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the "virtual" {@link CKEDITOR.eventInfo} class, which
 *		contains the defintions of the event object passed to event listeners.
 *		This file is for documentation purposes only.
 */

/**
 * Virtual class that illustrates the features of the event object to be
 * passed to event listeners by a {@link CKEDITOR.event} based object.
 *
 * This class is not really part of the API.
 *
 * @class CKEDITOR.eventInfo
 * @abstract
 */

/**
 * The event name.
 *
 *		someObject.on( 'someEvent', function( event ) {
 *			alert( event.name ); // 'someEvent'
 *		} );
 *		someObject.fire( 'someEvent' );
 *
 * @property {String} name
 */

/**
 * The object that publishes (sends) the event.
 *
 *		someObject.on( 'someEvent', function( event ) {
 *			alert( event.sender == someObject ); // true
 *		} );
 *		someObject.fire( 'someEvent' );
 *
 * @property sender
 */

/**
 * The editor instance that holds the sender. May be the same as sender. May be
 * null if the sender is not part of an editor instance, like a component
 * running in standalone mode.
 *
 *		myButton.on( 'someEvent', function( event ) {
 *			alert( event.editor == myEditor ); // true
 *		} );
 *		myButton.fire( 'someEvent', null, myEditor );
 *
 * @property {CKEDITOR.editor} editor
 */

/**
 * Any kind of additional data. Its format and usage is event dependent.
 *
 *		someObject.on( 'someEvent', function( event ) {
 *			alert( event.data ); // 'Example'
 *		} );
 *		someObject.fire( 'someEvent', 'Example' );
 *
 * @property data
 */

/**
 * Any extra data appended during the listener registration.
 *
 *		someObject.on( 'someEvent', function( event ) {
 *			alert( event.listenerData ); // 'Example'
 *		}, null, 'Example' );
 *
 * @property listenerData
 */

/**
 * Indicates that no further listeners are to be called.
 *
 *		someObject.on( 'someEvent', function( event ) {
 *			event.stop();
 *		} );
 *		someObject.on( 'someEvent', function( event ) {
 *			// This one will not be called.
 *		} );
 *		alert( someObject.fire( 'someEvent' ) ); // false
 *
 * @method stop
 */

/**
 * Indicates that the event is to be cancelled (if cancelable).
 *
 *		someObject.on( 'someEvent', function( event ) {
 *			event.cancel();
 *		} );
 *		someObject.on( 'someEvent', function( event ) {
 *			// This one will not be called.
 *		} );
 *		alert( someObject.fire( 'someEvent' ) ); // true
 *
 * @method cancel
 */

/**
 * Removes the current listener.
 *
 *		someObject.on( 'someEvent', function( event ) {
 *			event.removeListener();
 *			// Now this function won't be called again by 'someEvent'.
 *		} );
 *
 * @method removeListener
 */
