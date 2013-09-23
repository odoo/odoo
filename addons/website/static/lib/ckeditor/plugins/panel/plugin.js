/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

(function() {
	CKEDITOR.plugins.add( 'panel', {
		beforeInit: function( editor ) {
			editor.ui.addHandler( CKEDITOR.UI_PANEL, CKEDITOR.ui.panel.handler );
		}
	});

	/**
	 * Panel UI element.
	 *
	 * @readonly
	 * @property {String} [='panel']
	 * @member CKEDITOR
	 */
	CKEDITOR.UI_PANEL = 'panel';

	/**
	 * @class
	 * @constructor Creates a panel class instance.
	 * @param {CKEDITOR.dom.document} document
	 * @param {Object} definition
	 */
	CKEDITOR.ui.panel = function( document, definition ) {
		// Copy all definition properties to this object.
		if ( definition )
			CKEDITOR.tools.extend( this, definition );

		// Set defaults.
		CKEDITOR.tools.extend( this, {
			className: '',
			css: []
		});

		this.id = CKEDITOR.tools.getNextId();
		this.document = document;
		this.isFramed = this.forceIFrame || this.css.length;

		this._ = {
			blocks: {}
		};
	};

	/**
	 * Represents panel handler object.
	 *
	 * @class
	 * @singleton
	 * @extends CKEDITOR.ui.handlerDefinition
	 */
	CKEDITOR.ui.panel.handler = {
		/**
		 * Transforms a panel definition in a {@link CKEDITOR.ui.panel} instance.
		 *
		 * @param {Object} definition
		 * @returns {CKEDITOR.ui.panel}
		 */
		create: function( definition ) {
			return new CKEDITOR.ui.panel( definition );
		}
	};

	var panelTpl = CKEDITOR.addTemplate( 'panel', '<div lang="{langCode}" id="{id}" dir={dir}' +
		' class="cke cke_reset_all {editorId} cke_panel cke_panel {cls} cke_{dir}"' +
		' style="z-index:{z-index}" role="presentation">' +
		'{frame}' +
		'</div>' );

	var frameTpl = CKEDITOR.addTemplate( 'panel-frame', '<iframe id="{id}" class="cke_panel_frame" role="presentation" frameborder="0" src="{src}"></iframe>' );

	var frameDocTpl = CKEDITOR.addTemplate( 'panel-frame-inner', '<!DOCTYPE html>' +
		'<html class="cke_panel_container {env}" dir="{dir}" lang="{langCode}">' +
			'<head>{css}</head>' +
			'<body class="cke_{dir}"' +
				' style="margin:0;padding:0" onload="{onload}"></body>' +
		'<\/html>' );

	/** @class CKEDITOR.ui.panel */
	CKEDITOR.ui.panel.prototype = {
		/**
		 * Renders the combo.
		 *
		 * @param {CKEDITOR.editor} editor The editor instance which this button is
		 * to be used by.
		 * @param {Array} [output] The output array to which append the HTML relative
		 * to this button.
		 */
		render: function( editor, output ) {
			this.getHolderElement = function() {
				var holder = this._.holder;

				if ( !holder ) {
					if ( this.isFramed ) {
						var iframe = this.document.getById( this.id + '_frame' ),
							parentDiv = iframe.getParent(),
							doc = iframe.getFrameDocument();

						// Make it scrollable on iOS. (#8308)
						CKEDITOR.env.iOS && parentDiv.setStyles({
							'overflow': 'scroll',
							'-webkit-overflow-scrolling': 'touch'
						});

						var onLoad = CKEDITOR.tools.addFunction( CKEDITOR.tools.bind( function( ev ) {
							this.isLoaded = true;
							if ( this.onLoad )
								this.onLoad();
						}, this ) );

						doc.write( frameDocTpl.output( CKEDITOR.tools.extend({
							css: CKEDITOR.tools.buildStyleHtml( this.css ),
							onload: 'window.parent.CKEDITOR.tools.callFunction(' + onLoad + ');'
						}, data ) ) );

						var win = doc.getWindow();

						// Register the CKEDITOR global.
						win.$.CKEDITOR = CKEDITOR;

						// Arrow keys for scrolling is only preventable with 'keypress' event in Opera (#4534).
						doc.on( 'key' + ( CKEDITOR.env.opera ? 'press' : 'down' ), function( evt ) {
							var keystroke = evt.data.getKeystroke(),
								dir = this.document.getById( this.id ).getAttribute( 'dir' );

							// Delegate key processing to block.
							if ( this._.onKeyDown && this._.onKeyDown( keystroke ) === false ) {
								evt.data.preventDefault();
								return;
							}

							// ESC/ARROW-LEFT(ltr) OR ARROW-RIGHT(rtl)
							if ( keystroke == 27 || keystroke == ( dir == 'rtl' ? 39 : 37 ) ) {
								if ( this.onEscape && this.onEscape( keystroke ) === false )
									evt.data.preventDefault();
							}
						}, this );

						holder = doc.getBody();
						holder.unselectable();
						CKEDITOR.env.air && CKEDITOR.tools.callFunction( onLoad );
					} else
						holder = this.document.getById( this.id );

					this._.holder = holder;
				}

				return holder;
			};

			var data = {
				editorId: editor.id,
				id: this.id,
				langCode: editor.langCode,
				dir: editor.lang.dir,
				cls: this.className,
				frame: '',
				env: CKEDITOR.env.cssClass,
				'z-index': editor.config.baseFloatZIndex + 1
			};

			if ( this.isFramed ) {
				// With IE, the custom domain has to be taken care at first,
				// for other browers, the 'src' attribute should be left empty to
				// trigger iframe's 'load' event.
				var src =
					CKEDITOR.env.air ? 'javascript:void(0)' :
					CKEDITOR.env.ie ? 'javascript:void(function(){' + encodeURIComponent(
						'document.open();' +
						// In IE, the document domain must be set any time we call document.open().
						'(' + CKEDITOR.tools.fixDomain + ')();' +
						'document.close();'
					) + '}())' :
					'';

				data.frame = frameTpl.output({
					id: this.id + '_frame',
					src: src
				});
			}

			var html = panelTpl.output( data );

			if ( output )
				output.push( html );

			return html;
		},

		/**
		 * @todo
		 */
		addBlock: function( name, block ) {
			block = this._.blocks[ name ] = block instanceof CKEDITOR.ui.panel.block ? block : new CKEDITOR.ui.panel.block( this.getHolderElement(), block );

			if ( !this._.currentBlock )
				this.showBlock( name );

			return block;
		},

		/**
		 * @todo
		 */
		getBlock: function( name ) {
			return this._.blocks[ name ];
		},

		/**
		 * @todo
		 */
		showBlock: function( name ) {
			var blocks = this._.blocks,
				block = blocks[ name ],
				current = this._.currentBlock;

			// ARIA role works better in IE on the body element, while on the iframe
			// for FF. (#8864)
			var holder = !this.forceIFrame || CKEDITOR.env.ie ? this._.holder : this.document.getById( this.id + '_frame' );

			if ( current ) {
				// Clean up the current block's effects on holder.
				holder.removeAttributes( current.attributes );
				current.hide();
			}

			this._.currentBlock = block;

			holder.setAttributes( block.attributes );
			CKEDITOR.fire( 'ariaWidget', holder );

			// Reset the focus index, so it will always go into the first one.
			block._.focusIndex = -1;

			this._.onKeyDown = block.onKeyDown && CKEDITOR.tools.bind( block.onKeyDown, block );

			block.show();

			return block;
		},

		/**
		 * @todo
		 */
		destroy: function() {
			this.element && this.element.remove();
		}
	};

	/**
	 * @class
	 *
	 * @todo class and all methods
	 */
	CKEDITOR.ui.panel.block = CKEDITOR.tools.createClass({
		/**
		 * Creates a block class instances.
		 *
		 * @constructor
		 * @todo
		 */
		$: function( blockHolder, blockDefinition ) {
			this.element = blockHolder.append( blockHolder.getDocument().createElement( 'div', {
				attributes: {
					'tabIndex': -1,
					'class': 'cke_panel_block',
					'role': 'presentation',
					'tabindex': 0
				},
				styles: {
					display: 'none'
				}
			} ) );

			// Copy all definition properties to this object.
			if ( blockDefinition )
				CKEDITOR.tools.extend( this, blockDefinition );


			// Set the a11y attributes of this element ...
			this.element.setAttributes( {
				'aria-label': this.attributes[ 'aria-label' ],
				'title': this.attributes.title || this.attributes[ 'aria-label' ]
			} );

			// ...  and remove them from being set in the panel main element.
			delete this.attributes[ 'aria-label' ];
			delete this.attributes.title;

			this.keys = {};

			this._.focusIndex = -1;

			// Disable context menu for panels.
			this.element.disableContextMenu();
		},

		_: {

			/**
			 * Mark the item specified by the index as current activated.
			 */
			markItem: function( index ) {
				if ( index == -1 )
					return;
				var links = this.element.getElementsByTag( 'a' );
				var item = links.getItem( this._.focusIndex = index );

				// Safari need focus on the iframe window first(#3389), but we need
				// lock the blur to avoid hiding the panel.
				if ( CKEDITOR.env.webkit || CKEDITOR.env.opera )
					item.getDocument().getWindow().focus();
				item.focus();

				this.onMark && this.onMark( item );
			}
		},

		proto: {
			show: function() {
				this.element.setStyle( 'display', '' );
			},

			hide: function() {
				if ( !this.onHide || this.onHide.call( this ) !== true )
					this.element.setStyle( 'display', 'none' );
			},

			onKeyDown: function( keystroke ) {
				var keyAction = this.keys[ keystroke ];
				switch ( keyAction ) {
					// Move forward.
					case 'next':
						var index = this._.focusIndex,
							links = this.element.getElementsByTag( 'a' ),
							link;

						while ( ( link = links.getItem( ++index ) ) ) {
							// Move the focus only if the element is marked with
							// the _cke_focus and it it's visible (check if it has
							// width).
							if ( link.getAttribute( '_cke_focus' ) && link.$.offsetWidth ) {
								this._.focusIndex = index;
								link.focus();
								break;
							}
						}
						return false;

						// Move backward.
					case 'prev':
						index = this._.focusIndex;
						links = this.element.getElementsByTag( 'a' );

						while ( index > 0 && ( link = links.getItem( --index ) ) ) {
							// Move the focus only if the element is marked with
							// the _cke_focus and it it's visible (check if it has
							// width).
							if ( link.getAttribute( '_cke_focus' ) && link.$.offsetWidth ) {
								this._.focusIndex = index;
								link.focus();
								break;
							}
						}
						return false;

					case 'click':
					case 'mouseup':
						index = this._.focusIndex;
						link = index >= 0 && this.element.getElementsByTag( 'a' ).getItem( index );

						if ( link )
							link.$[ keyAction ] ? link.$[ keyAction ]() : link.$[ 'on' + keyAction ]();

						return false;
				}

				return true;
			}
		}
	});

})();

/**
 * Fired when a panel is added to the document.
 *
 * @event ariaWidget
 * @member CKEDITOR
 * @param {Object} data The element wrapping the panel.
 */
