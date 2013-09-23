/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

 /** @class CKEDITOR */

/**
 * The class name used to identify `<textarea>` elements to be replaced
 * by CKEditor instances. Set it to empty/`null` to disable this feature.
 *
 *		CKEDITOR.replaceClass = 'rich_editor';
 *
 * @cfg {String} [replaceClass='ckeditor']
 */
CKEDITOR.replaceClass = 'ckeditor';

(function() {
	/**
	 * Replaces a `<textarea>` or a DOM element (`<div>`) with a CKEditor
	 * instance. For textareas, the initial value in the editor will be the
	 * textarea value. For DOM elements, their `innerHTML` will be used
	 * instead. We recommend using `<textarea>` and `<div>` elements only.
	 *
	 *		<textarea id="myfield" name="myfield"></textarea>
	 *		...
	 *		CKEDITOR.replace( 'myfield' );
	 *
	 *		var textarea = document.body.appendChild( document.createElement( 'textarea' ) );
	 *		CKEDITOR.replace( textarea );
	 *
	 * @param {Object/String} element The DOM element (textarea), its ID, or name.
	 * @param {Object} [config] The specific configuration to apply to this
	 * editor instance. Configuration set here will override the global CKEditor settings
	 * (see {@link CKEDITOR.config}).
	 * @returns {CKEDITOR.editor} The editor instance created.
	 */
	CKEDITOR.replace = function( element, config ) {
		return createInstance( element, config, null, CKEDITOR.ELEMENT_MODE_REPLACE );
	};

	/**
	 * Creates a new editor instance at the end of a specific DOM element.
	 *
	 *		<div id="editorSpace"></div>
	 *		...
	 *		CKEDITOR.appendTo( 'editorSpace' );
	 *
	 * @param {Object/String} element The DOM element, its ID, or name.
	 * @param {Object} [config] The specific configuration to apply to this
	 * editor instance. Configuration set here will override the global CKEditor settings
	 * (see {@link CKEDITOR.config}).
	 * @param {String} [data] Since 3.3. Initial value for the instance.
	 * @returns {CKEDITOR.editor} The editor instance created.
	 */
	CKEDITOR.appendTo = function( element, config, data )
	{
		return createInstance( element, config, data, CKEDITOR.ELEMENT_MODE_APPENDTO );
	};

	/**
	 * Replaces all `<textarea>` elements available in the document with
	 * editor instances.
	 *
	 *		// Replace all <textarea> elements in the page.
	 *		CKEDITOR.replaceAll();
	 *
	 *		// Replace all <textarea class="myClassName"> elements in the page.
	 *		CKEDITOR.replaceAll( 'myClassName' );
	 *
	 *		// Selectively replace <textarea> elements, based on custom assertions.
	 *		CKEDITOR.replaceAll( function( textarea, config ) {
	 *			// An assertion function that needs to be evaluated for the <textarea>
	 *			// to be replaced. It must explicitely return "false" to ignore a
	 *			// specific <textarea>.
	 *			// You can also customize the editor instance by having the function
	 *			// modify the "config" parameter.
	 *		} );
	 * 
	 * @param {String} [className] The `<textarea>` class name.
	 * @param {Function} [function] An assertion function that must return `true` for a `<textarea>`
	 * to be replaced with the editor. If the function returns `false`, the `<textarea>` element
	 * will not be replaced.
	 */
	CKEDITOR.replaceAll = function() {
		var textareas = document.getElementsByTagName( 'textarea' );

		for ( var i = 0; i < textareas.length; i++ ) {
			var config = null,
				textarea = textareas[ i ];

			// The "name" and/or "id" attribute must exist.
			if ( !textarea.name && !textarea.id )
				continue;

			if ( typeof arguments[ 0 ] == 'string' ) {
				// The textarea class name could be passed as the function
				// parameter.

				var classRegex = new RegExp( '(?:^|\\s)' + arguments[ 0 ] + '(?:$|\\s)' );

				if ( !classRegex.test( textarea.className ) )
					continue;
			} else if ( typeof arguments[ 0 ] == 'function' ) {
				// An assertion function could be passed as the function parameter.
				// It must explicitly return "false" to ignore a specific <textarea>.
				config = {};
				if ( arguments[ 0 ]( textarea, config ) === false )
					continue;
			}

			this.replace( textarea, config );
		}
	};

	/** @class CKEDITOR.editor */

	/**
	 * Registers an editing mode. This function is to be used mainly by plugins.
	 *
	 * @param {String} mode The mode name.
	 * @param {Function} exec The function that performs the actual mode change.
	 */
	CKEDITOR.editor.prototype.addMode = function( mode, exec ) {
		( this._.modes || ( this._.modes = {} ) )[ mode ] = exec;
	};

	/**
	 * Changes the editing mode of this editor instance.
	 *
	 * **Note:** The mode switch could be asynchronous depending on the mode provider.
	 * Use the `callback` to hook subsequent code.
	 *
	 *		// Switch to "source" view.
	 *		CKEDITOR.instances.editor1.setMode( 'source' );
	 *		// Switch to "wysiwyg" view and be notified on completion.
	 *		CKEDITOR.instances.editor1.setMode( 'wysiwyg', function() { alert( 'wysiwyg mode loaded!' ); } );
	 *
	 * @param {String} [newMode] If not specified, the {@link CKEDITOR.config#startupMode} will be used.
	 * @param {Function} [callback] Optional callback function which is invoked once the mode switch has succeeded.
	 */
	CKEDITOR.editor.prototype.setMode = function( newMode, callback ) {
		var editor = this;

		var modes = this._.modes;

		// Mode loading quickly fails.
		if ( newMode == editor.mode || !modes || !modes[ newMode ] )
			return;

		editor.fire( 'beforeSetMode', newMode );

		if ( editor.mode ) {
			var isDirty = editor.checkDirty();

			editor._.previousMode = editor.mode;

			editor.fire( 'beforeModeUnload' );

			// Detach the current editable.
			editor.editable( 0 );

			// Clear up the mode space.
			editor.ui.space( 'contents' ).setHtml( '' );

			editor.mode = '';
		}

		// Fire the mode handler.
		this._.modes[ newMode ]( function() {
			// Set the current mode.
			editor.mode = newMode;

			if ( isDirty !== undefined ) {
				!isDirty && editor.resetDirty();
			}

			// Delay to avoid race conditions (setMode inside setMode).
			setTimeout( function() {
				editor.fire( 'mode' );
				callback && callback.call( editor );
			}, 0);
		});
	};

	/**
	 * Resizes the editor interface.
	 *
	 *		editor.resize( 900, 300 );
	 *
	 *		editor.resize( '100%', 450, true );
	 *
	 * @param {Number/String} width The new width. It can be an integer denoting a value
	 * in pixels or a CSS size value with unit.
	 * @param {Number/String} height The new height. It can be an integer denoting a value
	 * in pixels or a CSS size value with unit.
	 * @param {Boolean} [isContentHeight] Indicates that the provided height is to
	 * be applied to the editor content area, and not to the entire editor
	 * interface. Defaults to `false`.
	 * @param {Boolean} [resizeInner] Indicates that it is the inner interface
	 * element that must be resized, not the outer element. The default theme
	 * defines the editor interface inside a pair of `<span>` elements
	 * (`<span><span>...</span></span>`). By default the first,
	 * outer `<span>` element receives the sizes. If this parameter is set to
	 * `true`, the second, inner `<span>` is resized instead.
	 */
	CKEDITOR.editor.prototype.resize = function( width, height, isContentHeight, resizeInner ) {
		var container = this.container,
			contents = this.ui.space( 'contents' ),
			contentsFrame = CKEDITOR.env.webkit && this.document && this.document.getWindow().$.frameElement,
			outer = resizeInner ? container.getChild( 1 ) : container;

		// Set as border box width. (#5353)
		outer.setSize( 'width', width, true );

		// WebKit needs to refresh the iframe size to avoid rendering issues. (1/2) (#8348)
		contentsFrame && ( contentsFrame.style.width = '1%' );

		// Get the height delta between the outer table and the content area.
		// If we're setting the content area's height, then we don't need the delta.
		var delta = isContentHeight ? 0 : ( outer.$.offsetHeight || 0 ) - ( contents.$.clientHeight || 0 );
		contents.setStyle( 'height', Math.max( height - delta, 0 ) + 'px' );

		// WebKit needs to refresh the iframe size to avoid rendering issues. (2/2) (#8348)
		contentsFrame && ( contentsFrame.style.width = '100%' );

		// Emit a resize event.
		this.fire( 'resize' );
	};

	/**
	 * Gets the element that can be used to check the editor size. This method
	 * is mainly used by the `resize` plugin, which adds a UI handle that can be used
	 * to resize the editor.
	 *
	 * @param {Boolean} forContents Whether to return the "contents" part of the theme instead of the container.
	 * @returns {CKEDITOR.dom.element} The resizable element.
	 */
	CKEDITOR.editor.prototype.getResizable = function( forContents ) {
		return forContents ? this.ui.space( 'contents' ) : this.container;
	};

	function createInstance( element, config, data, mode ) {
		if ( !CKEDITOR.env.isCompatible )
			return null;

		element = CKEDITOR.dom.element.get( element );

		// Avoid multiple inline editor instances on the same element.
		if ( element.getEditor() )
			throw 'The editor instance "' + element.getEditor().name + '" is already attached to the provided element.';

		// Create the editor instance.
		var editor = new CKEDITOR.editor( config, element, mode );

		if ( mode == CKEDITOR.ELEMENT_MODE_REPLACE ) {
			// Do not replace the textarea right now, just hide it. The effective
			// replacement will be done later in the editor creation lifecycle.
			element.setStyle( 'visibility', 'hidden' );

			// #8031 Remember if textarea was required and remove the attribute.
			editor._.required = element.hasAttribute( 'required' );
			element.removeAttribute( 'required' );
		}

		data && editor.setData( data, null, true );

		// Once the editor is loaded, start the UI.
		editor.on( 'loaded', function() {
			loadTheme( editor );

			if ( mode == CKEDITOR.ELEMENT_MODE_REPLACE && editor.config.autoUpdateElement && element.$.form )
				editor._attachToForm();

			editor.setMode( editor.config.startupMode, function() {
				// Clean on startup.
				editor.resetDirty();

				// Editor is completely loaded for interaction.
				editor.status = 'ready';
				editor.fireOnce( 'instanceReady' );
				CKEDITOR.fire( 'instanceReady', null, editor );
			});
		});

		editor.on( 'destroy', destroy );
		return editor;
	}

	function destroy() {
		var editor = this,
			container = editor.container,
			element = editor.element;

		if ( container ) {
			container.clearCustomData();
			container.remove();
		}

		if ( element ) {
			element.clearCustomData();
			if ( editor.elementMode == CKEDITOR.ELEMENT_MODE_REPLACE ) {
				element.show();
				if ( editor._.required )
					element.setAttribute( 'required', 'required' );
			}
			delete editor.element;
		}
	}

	var themedTpl;

	function loadTheme( editor ) {
		var name = editor.name,
			element = editor.element,
			elementMode = editor.elementMode;

		// Get the HTML for the predefined spaces.
		var topHtml = editor.fire( 'uiSpace', { space: 'top', html: '' } ).html;
		var bottomHtml = editor.fire( 'uiSpace', { space: 'bottom', html: '' } ).html;

		if ( !themedTpl ) {
			themedTpl = CKEDITOR.addTemplate( 'maincontainer', '<{outerEl}' +
				' id="cke_{name}"' +
				' class="{id} cke cke_reset cke_chrome cke_editor_{name} cke_{langDir} ' + CKEDITOR.env.cssClass + '" ' +
				' dir="{langDir}"' +
				' lang="{langCode}"' +
				' role="application"' +
				' aria-labelledby="cke_{name}_arialbl">' +
				'<span id="cke_{name}_arialbl" class="cke_voice_label">{voiceLabel}</span>' +
					'<{outerEl} class="cke_inner cke_reset" role="presentation">' +
						'{topHtml}' +
						'<{outerEl} id="{contentId}" class="cke_contents cke_reset" role="presentation"></{outerEl}>' +
						'{bottomHtml}' +
					'</{outerEl}>' +
				'</{outerEl}>' );
		}

		var container = CKEDITOR.dom.element.createFromHtml( themedTpl.output({
			id: editor.id,
			name: name,
			langDir: editor.lang.dir,
			langCode: editor.langCode,
			voiceLabel: [ editor.lang.editor, editor.name ].join( ', ' ),
			topHtml: topHtml ? '<span id="' + editor.ui.spaceId( 'top' ) + '" class="cke_top cke_reset_all" role="presentation" style="height:auto">' + topHtml + '</span>' : '',
			contentId: editor.ui.spaceId( 'contents' ),
			bottomHtml: bottomHtml ? '<span id="' + editor.ui.spaceId( 'bottom' ) + '" class="cke_bottom cke_reset_all" role="presentation">' + bottomHtml + '</span>' : '',
			outerEl: CKEDITOR.env.ie ? 'span' : 'div'	// #9571
		}));

		if ( elementMode == CKEDITOR.ELEMENT_MODE_REPLACE ) {
			element.hide();
			container.insertAfter( element );
		} else
			element.append( container );

		editor.container = container;

		// Make top and bottom spaces unelectable, but not content space,
		// otherwise the editable area would be affected.
		topHtml && editor.ui.space( 'top' ).unselectable();
		bottomHtml && editor.ui.space( 'bottom' ).unselectable();

		var width = editor.config.width, height = editor.config.height;
		if ( width )
			container.setStyle( 'width', CKEDITOR.tools.cssLength( width ) );

		// The editor height is applied to the contents space.
		if ( height )
			editor.ui.space( 'contents' ).setStyle( 'height', CKEDITOR.tools.cssLength( height ) );

		// Disable browser context menu for editor's chrome.
		container.disableContextMenu();

		// Redirect the focus into editor for webkit. (#5713)
		CKEDITOR.env.webkit && container.on( 'focus', function() {
			editor.focus();
		});

		editor.fireOnce( 'uiReady' );
	}

	// Replace all textareas with the default class name.
	CKEDITOR.domReady( function() {
		CKEDITOR.replaceClass && CKEDITOR.replaceAll( CKEDITOR.replaceClass );
	});
})();

/**
 * The current editing mode. An editing mode basically provides
 * different ways of editing or viewing the contents.
 *
 *		alert( CKEDITOR.instances.editor1.mode ); // (e.g.) 'wysiwyg'
 *
 * @readonly
 * @property {String} mode
 */

/**
 * The mode to load at the editor startup. It depends on the plugins
 * loaded. By default, the `wysiwyg` and `source` modes are available.
 *
 *		config.startupMode = 'source';
 *
 * @cfg {String} [startupMode='wysiwyg']
 * @member CKEDITOR.config
 */
CKEDITOR.config.startupMode = 'wysiwyg';

/**
 * Fired after the editor instance is resized through
 * the {@link CKEDITOR.editor#method-resize CKEDITOR.resize} method.
 *
 * @event resize
 * @param {CKEDITOR.editor} editor This editor instance.
 */

/**
 * Fired before changing the editing mode. See also
 * {@link #beforeSetMode} and {@link #event-mode}.
 *
 * @event beforeModeUnload
 * @param {CKEDITOR.editor} editor This editor instance.
 */

/**
 * Fired before the editor mode is set. See also
 * {@link #event-mode} and {@link #beforeModeUnload}.
 *
 * @since 3.5.3
 * @event beforeSetMode
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param {String} data The name of the mode which is about to be set.
 */

/**
 * Fired after setting the editing mode. See also {@link #beforeSetMode} and {@link #beforeModeUnload}
 *
 * @event mode
 * @param {CKEDITOR.editor} editor This editor instance.
 */

/**
 * Fired when the editor (replacing a `<textarea>` which has a `required` attribute) is empty during form submission.
 *
 * This event replaces native required fields validation that the browsers cannot
 * perform when CKEditor replaces `<textarea>` elements.
 *
 * You can cancel this event to prevent the page from submitting data.
 *
 *		editor.on( 'required', function( evt ) {
 *			alert( 'Article content is required.' );
 *			evt.cancel();
 *		} );
 *
 * @event required
 * @param {CKEDITOR.editor} editor This editor instance.
 */
