/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * Controls keystrokes typing in an editor instance.
 *
 * @class
 * @constructor Creates a keystrokeHandler class instance.
 * @param {CKEDITOR.editor} editor The editor instance.
 */
CKEDITOR.keystrokeHandler = function( editor ) {
	if ( editor.keystrokeHandler )
		return editor.keystrokeHandler;

	/**
	 * List of keystrokes associated to commands. Each entry points to the
	 * command to be executed.
	 *
	 * Since CKEditor 4 there's no need to modify this property directly during the runtime.
	 * Use {@link CKEDITOR.editor#setKeystroke} instead.
	 */
	this.keystrokes = {};

	/**
	 * List of keystrokes that should be blocked if not defined at
	 * {@link #keystrokes}. In this way it is possible to block the default
	 * browser behavior for those keystrokes.
	 */
	this.blockedKeystrokes = {};

	this._ = {
		editor: editor
	};

	return this;
};

(function() {
	var cancel;

	var onKeyDown = function( event ) {
			// The DOM event object is passed by the "data" property.
			event = event.data;

			var keyCombination = event.getKeystroke();
			var command = this.keystrokes[ keyCombination ];
			var editor = this._.editor;

			cancel = ( editor.fire( 'key', { keyCode: keyCombination } ) === false );

			if ( !cancel ) {
				if ( command ) {
					var data = { from: 'keystrokeHandler' };
					cancel = ( editor.execCommand( command, data ) !== false );
				}

				if ( !cancel )
					cancel = !!this.blockedKeystrokes[ keyCombination ];
			}

			if ( cancel )
				event.preventDefault( true );

			return !cancel;
		};

	var onKeyPress = function( event ) {
			if ( cancel ) {
				cancel = false;
				event.data.preventDefault( true );
			}
		};

	CKEDITOR.keystrokeHandler.prototype = {
		/**
		 * Attaches this keystroke handle to a DOM object. Keystrokes typed
		 * over this object will get handled by this keystrokeHandler.
		 *
		 * @param {CKEDITOR.dom.domObject} domObject The DOM object to attach to.
		 */
		attach: function( domObject ) {
			// For most browsers, it is enough to listen to the keydown event
			// only.
			domObject.on( 'keydown', onKeyDown, this );

			// Some browsers instead, don't cancel key events in the keydown, but in the
			// keypress. So we must do a longer trip in those cases.
			if ( CKEDITOR.env.opera || ( CKEDITOR.env.gecko && CKEDITOR.env.mac ) )
				domObject.on( 'keypress', onKeyPress, this );
		}
	};
})();

/**
 * A list associating keystrokes to editor commands. Each element in the list
 * is an array where the first item is the keystroke, and the second is the
 * name of the command to be executed.
 *
 * This setting should be used to define (as well as to overwrite or remove) keystrokes
 * set by plugins (like `link` and `basicstyles`). If you want to set a keystroke
 * for your plugin or during the runtime, use {@link CKEDITOR.editor#setKeystroke} instead.
 *
 * Since default keystrokes are set by {@link CKEDITOR.editor#setKeystroke}
 * method, by default `config.keystrokes` is an empty array.
 *
 * See {@link CKEDITOR.editor#setKeystroke} documentation for more details
 * regarding the start up order.
 *
 *		// Change default CTRL + L keystroke for 'link' command to CTRL + SHIFT + L.
 *		config.keystrokes = [
 *			...
 *			[ CKEDITOR.CTRL + CKEDITOR.SHIFT + 76, 'link' ],	// CTRL + SHIFT + L
 *			...
 *		];
 *
 * To reset a particular keystroke, the following approach can be used:
 *
 *		// Disable default CTRL + L keystroke which executes link command by default.
 *		config.keystrokes = [
 *			...
 *			[ CKEDITOR.CTRL + 76, null ],						// CTRL + L
 *			...
 *		];
 *
 * To reset all default keystrokes an {@link CKEDITOR#instanceReady} callback should be
 * used. This is since editor defaults are merged rather than overwritten by
 * user keystrokes.
 *
 * **Note**: This can be potentially harmful for an editor. Avoid this unless you're
 * aware of the consequences.
 *
 *		// Reset all default keystrokes.
 *		config.on.instanceReady = function() {
 *			this.keystrokeHandler.keystrokes = [];
 *		};
 *
 * @cfg {Array} [keystrokes=[]]
 * @member CKEDITOR.config
 */

/**
 * Fired when any keyboard key (or combination) is pressed into the editing area.
 *
 * @event key
 * @member CKEDITOR.editor
 * @param data
 * @param {Number} data.keyCode A number representing the key code (or combination).
 * It is the sum of the current key code and the {@link CKEDITOR#CTRL}, {@link CKEDITOR#SHIFT}
 * and {@link CKEDITOR#ALT} constants, if those are pressed.
 * @param {CKEDITOR.editor} editor This editor instance.
 */
