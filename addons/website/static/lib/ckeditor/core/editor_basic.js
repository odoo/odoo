/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

if ( !CKEDITOR.editor ) {
	// Documented at editor.js.
	CKEDITOR.editor = function() {
		// Push this editor to the pending list. It'll be processed later once
		// the full editor code is loaded.
		CKEDITOR._.pending.push( [ this, arguments ] );

		// Call the CKEDITOR.event constructor to initialize this instance.
		CKEDITOR.event.call( this );
	};

	// Both fire and fireOnce will always pass this editor instance as the
	// "editor" param in CKEDITOR.event.fire. So, we override it to do that
	// automaticaly.
	CKEDITOR.editor.prototype.fire = function( eventName, data ) {
		if ( eventName in { instanceReady:1,loaded:1 } )
			this[ eventName ] = true;

		return CKEDITOR.event.prototype.fire.call( this, eventName, data, this );
	};

	CKEDITOR.editor.prototype.fireOnce = function( eventName, data ) {
		if ( eventName in { instanceReady:1,loaded:1 } )
			this[ eventName ] = true;

		return CKEDITOR.event.prototype.fireOnce.call( this, eventName, data, this );
	};

	// "Inherit" (copy actually) from CKEDITOR.event.
	CKEDITOR.event.implementOn( CKEDITOR.editor.prototype );
}
