/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

CKEDITOR.plugins.add( 'contextmenu', {
	requires: 'menu',
	lang: 'af,ar,bg,bn,bs,ca,cs,cy,da,de,el,en,en-au,en-ca,en-gb,eo,es,et,eu,fa,fi,fo,fr,fr-ca,gl,gu,he,hi,hr,hu,id,is,it,ja,ka,km,ko,ku,lt,lv,mk,mn,ms,nb,nl,no,pl,pt,pt-br,ro,ru,si,sk,sl,sq,sr,sr-latn,sv,th,tr,ug,uk,vi,zh,zh-cn', // %REMOVE_LINE_CORE%

	// Make sure the base class (CKEDITOR.menu) is loaded before it (#3318).
	onLoad: function() {
		/**
		 * @class
		 * @extends CKEDITOR.menu
		 */
		CKEDITOR.plugins.contextMenu = CKEDITOR.tools.createClass({
			base: CKEDITOR.menu,

			/**
			 * @constructor
			 */
			$: function( editor ) {
				this.base.call( this, editor, {
					panel: {
						className: 'cke_menu_panel',
						attributes: {
							'aria-label': editor.lang.contextmenu.options
						}
					}
				});
			},

			proto: {
				addTarget: function( element, nativeContextMenuOnCtrl ) {
					// Opera doesn't support 'contextmenu' event, we have duo approaches employed here:
					// 1. Inherit the 'button override' hack we introduced in v2 (#4530), while this require the Opera browser
					//  option 'Allow script to detect context menu/right click events' to be always turned on.
					// 2. Considering the fact that ctrl/meta key is not been occupied
					//  for multiple range selecting (like Gecko), we use this key
					//  combination as a fallback for triggering context-menu. (#4530)
					if ( CKEDITOR.env.opera && !( 'oncontextmenu' in document.body ) ) {
						var contextMenuOverrideButton;
						element.on( 'mousedown', function( evt ) {
							evt = evt.data;
							if ( evt.$.button != 2 ) {
								if ( evt.getKeystroke() == CKEDITOR.CTRL + 1 )
									element.fire( 'contextmenu', evt );
								return;
							}

							if ( nativeContextMenuOnCtrl && ( CKEDITOR.env.mac ? evt.$.metaKey : evt.$.ctrlKey ) )
								return;

							var target = evt.getTarget();

							if ( !contextMenuOverrideButton ) {
								var ownerDoc = target.getDocument();
								contextMenuOverrideButton = ownerDoc.createElement( 'input' );
								contextMenuOverrideButton.$.type = 'button';
								ownerDoc.getBody().append( contextMenuOverrideButton );
							}

							contextMenuOverrideButton.setAttribute( 'style', 'position:absolute;top:' + ( evt.$.clientY - 2 ) +
								'px;left:' + ( evt.$.clientX - 2 ) +
								'px;width:5px;height:5px;opacity:0.01' );

						});

						element.on( 'mouseup', function( evt ) {
							if ( contextMenuOverrideButton ) {
								contextMenuOverrideButton.remove();
								contextMenuOverrideButton = undefined;
								// Simulate 'contextmenu' event.
								element.fire( 'contextmenu', evt.data );
							}
						});
					}

					element.on( 'contextmenu', function( event ) {
						var domEvent = event.data;

						if ( nativeContextMenuOnCtrl &&
						// Safari on Windows always show 'ctrlKey' as true in 'contextmenu' event,
						// which make this property unreliable. (#4826)
						( CKEDITOR.env.webkit ? holdCtrlKey : ( CKEDITOR.env.mac ? domEvent.$.metaKey : domEvent.$.ctrlKey ) ) )
							return;


						// Cancel the browser context menu.
						domEvent.preventDefault();

						var doc = domEvent.getTarget().getDocument(),
							offsetParent = domEvent.getTarget().getDocument().getDocumentElement(),
							fromFrame = !doc.equals( CKEDITOR.document ),
							scroll = doc.getWindow().getScrollPosition(),
							offsetX = fromFrame ? domEvent.$.clientX : domEvent.$.pageX || scroll.x + domEvent.$.clientX,
							offsetY = fromFrame ? domEvent.$.clientY : domEvent.$.pageY || scroll.y + domEvent.$.clientY;

						CKEDITOR.tools.setTimeout( function() {
							this.open( offsetParent, null, offsetX, offsetY );

							// IE needs a short while to allow selection change before opening menu. (#7908)
						}, CKEDITOR.env.ie ? 200 : 0, this );
					}, this );

					if ( CKEDITOR.env.opera ) {
						// 'contextmenu' event triggered by Windows menu key is unpreventable,
						// cancel the key event itself. (#6534)
						element.on( 'keypress', function( evt ) {
							var domEvent = evt.data;

							if ( domEvent.$.keyCode === 0 )
								domEvent.preventDefault();
						});
					}

					if ( CKEDITOR.env.webkit ) {
						var holdCtrlKey,
							onKeyDown = function( event ) {
								holdCtrlKey = CKEDITOR.env.mac ? event.data.$.metaKey : event.data.$.ctrlKey;
							},
							resetOnKeyUp = function() {
								holdCtrlKey = 0;
							};

						element.on( 'keydown', onKeyDown );
						element.on( 'keyup', resetOnKeyUp );
						element.on( 'contextmenu', resetOnKeyUp );
					}
				},

				open: function( offsetParent, corner, offsetX, offsetY ) {
					this.editor.focus();
					offsetParent = offsetParent || CKEDITOR.document.getDocumentElement();

					// #9362: Force selection check to update commands' states in the new context.
					this.editor.selectionChange( 1 );

					this.show( offsetParent, corner, offsetX, offsetY );
				}
			}
		});
	},

	beforeInit: function( editor ) {
		var contextMenu = editor.contextMenu = new CKEDITOR.plugins.contextMenu( editor );

		editor.on( 'contentDom', function() {
			contextMenu.addTarget( editor.editable(), editor.config.browserContextMenuOnCtrl !== false );
		});

		editor.addCommand( 'contextMenu', {
			exec: function() {
				editor.contextMenu.open( editor.document.getBody() );
			}
		});

		editor.setKeystroke( CKEDITOR.SHIFT + 121 /*F10*/, 'contextMenu' );
		editor.setKeystroke( CKEDITOR.CTRL + CKEDITOR.SHIFT + 121 /*F10*/, 'contextMenu' );
	}
});

/**
 * Whether to show the browser native context menu when the *Ctrl* or
 * *Meta* (Mac) key is pressed on opening the context menu with the
 * right mouse button click or the *Menu* key.
 *
 *		config.browserContextMenuOnCtrl = false;
 *
 * @since 3.0.2
 * @cfg {Boolean} [browserContextMenuOnCtrl=true]
 * @member CKEDITOR.config
 */
