/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the {@link CKEDITOR.focusManager} class, which is used
 *		to handle the focus on editor instances..
 */

(function() {
	/**
	 * Manages the focus activity in an editor instance. This class is to be
	 * used mainly by UI elements coders when adding interface elements that need
	 * to set the focus state of the editor.
	 *
	 *		var focusManager = new CKEDITOR.focusManager( editor );
	 *		focusManager.focus();
	 *
	 * @class
	 * @constructor Creates a focusManager class instance.
	 * @param {CKEDITOR.editor} editor The editor instance.
	 */
	CKEDITOR.focusManager = function( editor ) {
		if ( editor.focusManager )
			return editor.focusManager;

		/**
		 * Indicates that the editor instance has focus.
		 *
		 *		alert( CKEDITOR.instances.editor1.focusManager.hasFocus ); // e.g. true
		 */
		this.hasFocus = false;

		/**
		 * Indicate the currently focused DOM element that makes the editor activated.
		 *
		 * @property {CKEDITOR.dom.domObject}
		 */
		this.currentActive = null;

		/**
		 * Object used to hold private stuff.
		 *
		 * @private
		 */
		this._ = {
			editor: editor
		};

		return this;
	};

	var SLOT_NAME = 'focusmanager',
		SLOT_NAME_LISTENERS = 'focusmanager_handlers';

	CKEDITOR.focusManager._ = {
		/**
		 * The delay (in milliseconds) to deactivate the editor when UI dom element has lost focus.
		 *
		 * @private
		 * @static
		 * @property {Number} [_.blurDelay=200]
		 */
		blurDelay: 200
	};

	CKEDITOR.focusManager.prototype = {

		/**
		 * Indicate this editor instance is activated (due to DOM focus change),
		 * the `activated` state is a symbolic indicator of an active user
		 * interaction session.
		 *
		 * **Note:** This method will not introduce UI focus
		 * impact on DOM, it's here to record editor UI focus state internally.
		 * If you want to make the cursor blink inside of the editable, use
		 * {@link CKEDITOR.editor#method-focus} instead.
		 *
		 *		var editor = CKEDITOR.instances.editor1;
		 *		editor.focusManage.focus( editor.editable() );
		 *
		 * @param {CKEDITOR.dom.element} [currentActive] The new value of {@link #currentActive} property.
		 */
		focus: function( currentActive ) {
			if ( this._.timer )
				clearTimeout( this._.timer );

			if ( currentActive )
				this.currentActive = currentActive;

			if ( !( this.hasFocus || this._.locked ) ) {
				// If another editor has the current focus, we first "blur" it. In
				// this way the events happen in a more logical sequence, like:
				//		"focus 1" > "blur 1" > "focus 2"
				// ... instead of:
				//		"focus 1" > "focus 2" > "blur 1"
				var current = CKEDITOR.currentInstance;
				current && current.focusManager.blur( 1 );

				this.hasFocus = true;

				var ct = this._.editor.container;
				ct && ct.addClass( 'cke_focus' );
				this._.editor.fire( 'focus' );
			}
		},

		/**
		 * Prevent from changing the focus manager state until next {@link #unlock} is called.
		 */
		lock: function() {
			this._.locked = 1;
		},

		/**
		 * Restore the automatic focus management, if {@link #lock} is called.
		 */
		unlock: function() {
			delete this._.locked;
		},

		/**
		 * Used to indicate that the editor instance has been deactivated by the specified
		 * element which has just lost focus.
		 *
		 * **Note:** that this functions acts asynchronously with a delay of 100ms to
		 * avoid temporary deactivation. Use instead the `noDelay` parameter
		 * to deactivate immediately.
		 *
		 *		var editor = CKEDITOR.instances.editor1;
		 *		editor.focusManager.blur();
		 *
		 * @param {Boolean} [noDelay=false] Deactivate immediately the editor instance synchronously.
		 */
		blur: function( noDelay ) {
			if ( this._.locked )
				return;

			function doBlur() {
				if ( this.hasFocus ) {
					this.hasFocus = false;

					var ct = this._.editor.container;
					ct && ct.removeClass( 'cke_focus' );
					this._.editor.fire( 'blur' );
				}
			}

			if ( this._.timer )
				clearTimeout( this._.timer );

			var delay = CKEDITOR.focusManager._.blurDelay;
			if ( noDelay || !delay ) {
				doBlur.call( this );
			} else {
				this._.timer = CKEDITOR.tools.setTimeout( function() {
					delete this._.timer;
					doBlur.call( this );
				}, delay, this );
			}
		},

		/**
		 * Register an UI DOM element to the focus manager, which will make the focus manager "hasFocus"
		 * once input focus is relieved on the element, it's to be used by plugins to expand the jurisdiction of the editor focus.
		 *
		 * @param {CKEDITOR.dom.element} element The container (top most) element of one UI part.
		 * @param {Boolean} isCapture If specified {@link CKEDITOR.event#useCapture} will be used when listening to the focus event.
		 */
		add: function( element, isCapture ) {
			var fm = element.getCustomData( SLOT_NAME );
			if ( !fm || fm != this ) {
				// If this element is already taken by another instance, dismiss it first.
				fm && fm.remove( element );

				var focusEvent = 'focus',
					blurEvent = 'blur';

				// Bypass the element's internal DOM focus change.
				if ( isCapture ) {

					// Use "focusin/focusout" events instead of capture phase in IEs,
					// which fires synchronously.
					if ( CKEDITOR.env.ie ) {
						focusEvent = 'focusin';
						blurEvent = 'focusout';
					} else
						CKEDITOR.event.useCapture = 1;
				}

				var listeners = {
					blur: function() {
						if ( element.equals( this.currentActive ) )
							this.blur();
					},
					focus: function() {
						this.focus( element );
					}
				};

				element.on( focusEvent, listeners.focus, this );
				element.on( blurEvent, listeners.blur, this );

				if ( isCapture )
					CKEDITOR.event.useCapture = 0;

				element.setCustomData( SLOT_NAME, this );
				element.setCustomData( SLOT_NAME_LISTENERS, listeners );
			}
		},

		/**
		 * Dismiss an element from the the focus manager delegations added by {@link #add}.
		 *
		 * @param {CKEDITOR.dom.element} element The element to be removed from the focusmanager.
		 */
		remove: function( element ) {
			element.removeCustomData( SLOT_NAME );
			var listeners = element.removeCustomData( SLOT_NAME_LISTENERS );
			element.removeListener( 'blur', listeners.blur );
			element.removeListener( 'focus', listeners.focus );
		}

	};

})();

/**
 * Fired when the editor instance receives the input focus.
 *
 *		editor.on( 'focus', function( e ) {
 *			alert( 'The editor named ' + e.editor.name + ' is now focused' );
 *		} );
 *
 * @event focus
 * @member CKEDITOR.editor
 * @param {CKEDITOR.editor} editor The editor instance.
 */

/**
 * Fired when the editor instance loses the input focus.
 *
 * **Note:** This event will **NOT** be triggered when focus is moved internally, e.g. from
 * the editable to other part of the editor UI like dialog.
 * If you're interested on only the editable focus state listen to the {@link CKEDITOR.editable#event-focus}
 * and {@link CKEDITOR.editable#blur} events instead.
 *
 *		editor.on( 'blur', function( e ) {
 *			alert( 'The editor named ' + e.editor.name + ' lost the focus' );
 *		} );
 *
 * @event blur
 * @member CKEDITOR.editor
 * @param {CKEDITOR.editor} editor The editor instance.
 */
