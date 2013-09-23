/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview The "wysiwygarea" plugin. It registers the "wysiwyg" editing
 *		mode, which handles the main editing area space.
 */

(function() {
	CKEDITOR.plugins.add( 'wysiwygarea', {
		init: function( editor ) {
			if ( editor.config.fullPage ) {
				editor.addFeature( {
					allowedContent: 'html head title; style [media,type]; body (*)[id]; meta link [*]',
					requiredContent: 'body'
				} );
			}

			editor.addMode( 'wysiwyg', function( callback ) {
				var src = 'document.open();' +
					// In IE, the document domain must be set any time we call document.open().
					( CKEDITOR.env.ie ? '(' + CKEDITOR.tools.fixDomain + ')();' : '' ) +
					'document.close();';

				// With IE, the custom domain has to be taken care at first,
				// for other browers, the 'src' attribute should be left empty to
				// trigger iframe's 'load' event.
				src = CKEDITOR.env.air ? 'javascript:void(0)' : CKEDITOR.env.ie ? 'javascript:void(function(){' + encodeURIComponent( src ) + '}())'
					:
					'';

				var iframe = CKEDITOR.dom.element.createFromHtml( '<iframe src="' + src + '" frameBorder="0"></iframe>' );
				iframe.setStyles( { width: '100%', height: '100%' } );
				iframe.addClass( 'cke_wysiwyg_frame cke_reset' );

				var contentSpace = editor.ui.space( 'contents' );
				contentSpace.append( iframe );


				// Asynchronous iframe loading is only required in IE>8 and Gecko (other reasons probably).
				// Do not use it on WebKit as it'll break the browser-back navigation.
				var useOnloadEvent = CKEDITOR.env.ie || CKEDITOR.env.gecko;
				if ( useOnloadEvent )
					iframe.on( 'load', onLoad );

				var frameLabel = editor.title,
					frameDesc = editor.lang.common.editorHelp;

				if ( frameLabel ) {
					if ( CKEDITOR.env.ie )
						frameLabel += ', ' + frameDesc;

					iframe.setAttribute( 'title', frameLabel );
				}

				var labelId = CKEDITOR.tools.getNextId(),
					desc = CKEDITOR.dom.element.createFromHtml( '<span id="' + labelId + '" class="cke_voice_label">' + frameDesc + '</span>' );

				contentSpace.append( desc, 1 );

				// Remove the ARIA description.
				editor.on( 'beforeModeUnload', function( evt ) {
					evt.removeListener();
					desc.remove();
				});

				iframe.setAttributes({
					'aria-describedby': labelId,
					tabIndex: editor.tabIndex,
					allowTransparency: 'true'
				});

				// Execute onLoad manually for all non IE||Gecko browsers.
				!useOnloadEvent && onLoad();

				if ( CKEDITOR.env.webkit ) {
					// Webkit: iframe size doesn't auto fit well. (#7360)
					var onResize = function() {
						// Hide the iframe to get real size of the holder. (#8941)
						contentSpace.setStyle( 'width', '100%' );

						iframe.hide();
						iframe.setSize( 'width', contentSpace.getSize( 'width' ) );
						contentSpace.removeStyle( 'width' );
						iframe.show();
					};

					iframe.setCustomData( 'onResize', onResize );

					CKEDITOR.document.getWindow().on( 'resize', onResize );
				}

				editor.fire( 'ariaWidget', iframe );

				function onLoad( evt ) {
					evt && evt.removeListener();
					editor.editable( new framedWysiwyg( editor, iframe.$.contentWindow.document.body ) );
					editor.setData( editor.getData( 1 ), callback );
				}
			});
		}
	});

	function onDomReady( win ) {
		var editor = this.editor,
			doc = win.document,
			body = doc.body;

		// Remove helper scripts from the DOM.
		var script = doc.getElementById( 'cke_actscrpt' );
		script && script.parentNode.removeChild( script );
		script = doc.getElementById( 'cke_shimscrpt' );
		script && script.parentNode.removeChild( script );

		if ( CKEDITOR.env.gecko ) {
			// Force Gecko to change contentEditable from false to true on domReady
			// (because it's previously set to true on iframe's body creation).
			// Otherwise del/backspace and some other editable features will be broken in Fx <4
			// See: #107 and https://bugzilla.mozilla.org/show_bug.cgi?id=440916
			body.contentEditable = false;

			// Remove any leading <br> which is between the <body> and the comment.
			// This one fixes Firefox 3.6 bug: the browser inserts a leading <br>
			// on document.write if the body has contenteditable="true".
			if ( CKEDITOR.env.version < 20000 ) {
				body.innerHTML = body.innerHTML.replace( /^.*<!-- cke-content-start -->/, '' );

				// The above hack messes up the selection in FF36.
				// To clean this up, manually select collapsed range that
				// starts within the body.
				setTimeout( function() {
					var range = new CKEDITOR.dom.range( new CKEDITOR.dom.document( doc ) );
					range.setStart( new CKEDITOR.dom.node( body ), 0 );
					editor.getSelection().selectRanges( [ range ] );
				}, 0 );
			}
		}

		body.contentEditable = true;

		if ( CKEDITOR.env.ie ) {
			// Don't display the focus border.
			body.hideFocus = true;

			// Disable and re-enable the body to avoid IE from
			// taking the editing focus at startup. (#141 / #523)
			body.disabled = true;
			body.removeAttribute( 'disabled' );
		}

		delete this._.isLoadingData;

		// Play the magic to alter element reference to the reloaded one.
		this.$ = body;

		doc = new CKEDITOR.dom.document( doc );

		this.setup();

		if ( CKEDITOR.env.ie ) {
			doc.getDocumentElement().addClass( doc.$.compatMode );

			// Prevent IE from leaving new paragraph after deleting all contents in body. (#6966)
			editor.config.enterMode != CKEDITOR.ENTER_P && doc.on( 'selectionchange', function() {
				var body = doc.getBody(),
					sel = editor.getSelection(),
					range = sel && sel.getRanges()[ 0 ];

				if ( range && body.getHtml().match( /^<p>&nbsp;<\/p>$/i ) && range.startContainer.equals( body ) ) {
					// Avoid the ambiguity from a real user cursor position.
					setTimeout( function() {
						range = editor.getSelection().getRanges()[ 0 ];
						if ( !range.startContainer.equals( 'body' ) ) {
							body.getFirst().remove( 1 );
							range.moveToElementEditEnd( body );
							range.select();
						}
					}, 0 );
				}
			});
		}

		// ## START : disableNativeTableHandles and disableObjectResizing settings.

		// Enable dragging of position:absolute elements in IE.
		try {
			editor.document.$.execCommand( '2D-position', false, true );
		} catch ( e ) {}

		// IE, Opera and Safari may not support it and throw errors.
		try {
			editor.document.$.execCommand( 'enableInlineTableEditing', false, !editor.config.disableNativeTableHandles );
		} catch ( e ) {}

		if ( editor.config.disableObjectResizing ) {
			try {
				this.getDocument().$.execCommand( 'enableObjectResizing', false, false );
			} catch ( e ) {
				// For browsers in which the above method failed, we can cancel the resizing on the fly (#4208)
				this.attachListener( this, CKEDITOR.env.ie ? 'resizestart' : 'resize', function( evt ) {
					evt.data.preventDefault();
				});
			}
		}

		if ( CKEDITOR.env.gecko || CKEDITOR.env.ie && editor.document.$.compatMode == 'CSS1Compat' ) {
			this.attachListener( this, 'keydown', function( evt ) {
				var keyCode = evt.data.getKeystroke();

				// PageUp OR PageDown
				if ( keyCode == 33 || keyCode == 34 ) {
					// PageUp/PageDown scrolling is broken in document
					// with standard doctype, manually fix it. (#4736)
					if ( CKEDITOR.env.ie ) {
						setTimeout( function() {
							editor.getSelection().scrollIntoView();
						}, 0 );
					}
					// Page up/down cause editor selection to leak
					// outside of editable thus we try to intercept
					// the behavior, while it affects only happen
					// when editor contents are not overflowed. (#7955)
					else if ( editor.window.$.innerHeight > this.$.offsetHeight ) {
						var range = editor.createRange();
						range[ keyCode == 33 ? 'moveToElementEditStart' : 'moveToElementEditEnd' ]( this );
						range.select();
						evt.data.preventDefault();
					}
				}
			});
		}

		if ( CKEDITOR.env.ie ) {
			// [IE] Iframe will still keep the selection when blurred, if
			// focus is moved onto a non-editing host, e.g. link or button, but
			// it becomes a problem for the object type selection, since the resizer
			// handler attached on it will mark other part of the UI, especially
			// for the dialog. (#8157)
			// [IE<8 & Opera] Even worse For old IEs, the cursor will not vanish even if
			// the selection has been moved to another text input in some cases. (#4716)
			//
			// Now the range restore is disabled, so we simply force IE to clean
			// up the selection before blur.
			this.attachListener( doc, 'blur', function() {
				// Error proof when the editor is not visible. (#6375)
				try {
					doc.$.selection.empty();
				} catch ( er ) {}
			});
		}

		// ## END


		var title = editor.document.getElementsByTag( 'title' ).getItem( 0 );
		title.data( 'cke-title', editor.document.$.title );

		// [IE] JAWS will not recognize the aria label we used on the iframe
		// unless the frame window title string is used as the voice label,
		// backup the original one and restore it on output.
		if ( CKEDITOR.env.ie )
			editor.document.$.title = this._.docTitle;

		CKEDITOR.tools.setTimeout( function() {
			editor.fire( 'contentDom' );

			if ( this._.isPendingFocus ) {
				editor.focus();
				this._.isPendingFocus = false;
			}

			setTimeout( function() {
				editor.fire( 'dataReady' );
			}, 0 );

			// IE BUG: IE might have rendered the iframe with invisible contents.
			// (#3623). Push some inconsequential CSS style changes to force IE to
			// refresh it.
			//
			// Also, for some unknown reasons, short timeouts (e.g. 100ms) do not
			// fix the problem. :(
			if ( CKEDITOR.env.ie ) {
				setTimeout( function() {
					if ( editor.document ) {
						var $body = editor.document.$.body;
						$body.runtimeStyle.marginBottom = '0px';
						$body.runtimeStyle.marginBottom = '';
					}
				}, 1000 );
			}
		}, 0, this );
	}

	var framedWysiwyg = CKEDITOR.tools.createClass({
		$: function( editor ) {
			this.base.apply( this, arguments );

			this._.frameLoadedHandler = CKEDITOR.tools.addFunction( function( win ) {
				// Avoid opening design mode in a frame window thread,
				// which will cause host page scrolling.(#4397)
				CKEDITOR.tools.setTimeout( onDomReady, 0, this, win );
			}, this );

			this._.docTitle = this.getWindow().getFrame().getAttribute( 'title' );
		},

		base: CKEDITOR.editable,

		proto: {
			setData: function( data, isSnapshot ) {
				var editor = this.editor;

				if ( isSnapshot ) {
					this.setHtml( data );
					// Fire dataReady for the consistency with inline editors
					// and because it makes sense. (#10370)
					editor.fire( 'dataReady' );
				}
				else {
					this._.isLoadingData = true;
					editor._.dataStore = { id:1 };

					var config = editor.config,
						fullPage = config.fullPage,
						docType = config.docType;

					// Build the additional stuff to be included into <head>.
					var headExtra = CKEDITOR.tools.buildStyleHtml( iframeCssFixes() )
						                .replace( /<style>/, '<style data-cke-temp="1">' );

					if ( !fullPage )
						headExtra += CKEDITOR.tools.buildStyleHtml( editor.config.contentsCss );

					var baseTag = config.baseHref ? '<base href="' + config.baseHref + '" data-cke-temp="1" />' : '';

					if ( fullPage ) {
						// Search and sweep out the doctype declaration.
						data = data.replace( /<!DOCTYPE[^>]*>/i, function( match ) {
							editor.docType = docType = match;
							return '';
						}).replace( /<\?xml\s[^\?]*\?>/i, function( match ) {
							editor.xmlDeclaration = match;
							return '';
						});
					}

					// Get the HTML version of the data.
					data = editor.dataProcessor.toHtml( data );

					if ( fullPage ) {
						// Check if the <body> tag is available.
						if ( !( /<body[\s|>]/ ).test( data ) )
							data = '<body>' + data;

						// Check if the <html> tag is available.
						if ( !( /<html[\s|>]/ ).test( data ) )
							data = '<html>' + data + '</html>';

						// Check if the <head> tag is available.
						if ( !( /<head[\s|>]/ ).test( data ) )
							data = data.replace( /<html[^>]*>/, '$&<head><title></title></head>' );
						else if ( !( /<title[\s|>]/ ).test( data ) )
							data = data.replace( /<head[^>]*>/, '$&<title></title>' );

						// The base must be the first tag in the HEAD, e.g. to get relative
						// links on styles.
						baseTag && ( data = data.replace( /<head>/, '$&' + baseTag ) );

						// Inject the extra stuff into <head>.
						// Attention: do not change it before testing it well. (V2)
						// This is tricky... if the head ends with <meta ... content type>,
						// Firefox will break. But, it works if we place our extra stuff as
						// the last elements in the HEAD.
						data = data.replace( /<\/head\s*>/, headExtra + '$&' );

						// Add the DOCTYPE back to it.
						data = docType + data;
					} else {
						data = config.docType +
							'<html dir="' + config.contentsLangDirection + '"' +
								' lang="' + ( config.contentsLanguage || editor.langCode ) + '">' +
							'<head>' +
								'<title>' + this._.docTitle + '</title>' +
								baseTag +
								headExtra +
							'</head>' +
							'<body' + ( config.bodyId ? ' id="' + config.bodyId + '"' : '' ) +
								( config.bodyClass ? ' class="' + config.bodyClass + '"' : '' ) +
							'>' +
								data +
							'</body>' +
							'</html>';
					}

					if ( CKEDITOR.env.gecko ) {
						// Hack to make Fx put cursor at the start of doc on fresh focus.
						data = data.replace( /<body/, '<body contenteditable="true" ' );

						// Another hack which is used by onDomReady to remove a leading
						// <br> which is inserted by Firefox 3.6 when document.write is called.
						// This additional <br> is present because of contenteditable="true"
						if ( CKEDITOR.env.version < 20000 )
							data = data.replace( /<body[^>]*>/, '$&<!-- cke-content-start -->'  );
					}

					// The script that launches the bootstrap logic on 'domReady', so the document
					// is fully editable even before the editing iframe is fully loaded (#4455).
					var bootstrapCode =
						'<script id="cke_actscrpt" type="text/javascript"' + ( CKEDITOR.env.ie ? ' defer="defer" ' : '' ) + '>' +
							'var wasLoaded=0;' +	// It must be always set to 0 as it remains as a window property.
							'function onload(){' +
								'if(!wasLoaded)' +	// FF3.6 calls onload twice when editor.setData. Stop that.
									'window.parent.CKEDITOR.tools.callFunction(' + this._.frameLoadedHandler + ',window);' +
								'wasLoaded=1;' +
							'}' +
							( CKEDITOR.env.ie ? 'onload();' : 'document.addEventListener("DOMContentLoaded", onload, false );' ) +
						'</script>';

					// For IE<9 add support for HTML5's elements.
					// Note: this code must not be deferred.
					if ( CKEDITOR.env.ie && CKEDITOR.env.version < 9 ) {
						bootstrapCode +=
							'<script id="cke_shimscrpt">' +
								'window.parent.CKEDITOR.tools.enableHtml5Elements(document)' +
							'</script>';
					}

					data = data.replace( /(?=\s*<\/(:?head)>)/, bootstrapCode );

					// Current DOM will be deconstructed by document.write, cleanup required.
					this.clearCustomData();
					this.clearListeners();

					editor.fire( 'contentDomUnload' );

					var doc = this.getDocument();

					// Work around Firefox bug - error prune when called from XUL (#320),
					// defer it thanks to the async nature of this method.
					try { doc.write( data ); } catch ( e ) {
						setTimeout( function () { doc.write( data ); }, 0 );
					}
				}
			},

			getData: function( isSnapshot ) {
				if ( isSnapshot )
					return this.getHtml();
				else {
					var editor = this.editor,
						config = editor.config,
						fullPage = config.fullPage,
						docType = fullPage && editor.docType,
						xmlDeclaration = fullPage && editor.xmlDeclaration,
						doc = this.getDocument();

					var data = fullPage ? doc.getDocumentElement().getOuterHtml() : doc.getBody().getHtml();

					// BR at the end of document is bogus node for Mozilla. (#5293).
					// Prevent BRs from disappearing from the end of the content
					// while enterMode is ENTER_BR (#10146).
					if ( CKEDITOR.env.gecko && config.enterMode != CKEDITOR.ENTER_BR )
						data = data.replace( /<br>(?=\s*(:?$|<\/body>))/, '' );

					data = editor.dataProcessor.toDataFormat( data );

					if ( xmlDeclaration )
						data = xmlDeclaration + '\n' + data;
					if ( docType )
						data = docType + '\n' + data;

					return data;
				}
			},

			focus: function() {
				if ( this._.isLoadingData )
					this._.isPendingFocus = true;
				else
					framedWysiwyg.baseProto.focus.call( this );
			},

			detach: function() {
				var editor = this.editor,
					doc = editor.document,
					iframe = editor.window.getFrame();

				framedWysiwyg.baseProto.detach.call( this );

				// Memory leak proof.
				this.clearCustomData();
				doc.getDocumentElement().clearCustomData();
				iframe.clearCustomData();
				CKEDITOR.tools.removeFunction( this._.frameLoadedHandler );

				var onResize = iframe.removeCustomData( 'onResize' );
				onResize && onResize.removeListener();


				editor.fire( 'contentDomUnload' );

				// IE BUG: When destroying editor DOM with the selection remains inside
				// editing area would break IE7/8's selection system, we have to put the editing
				// iframe offline first. (#3812 and #5441)
				iframe.remove();
			}
		}
	});

	// DOM modification here should not bother dirty flag.(#4385)
	function restoreDirty( editor ) {
		if ( !editor.checkDirty() )
			setTimeout( function() {
			editor.resetDirty();
		}, 0 );
	}

	function iframeCssFixes() {
		var css = [];

		// IE>=8 stricts mode doesn't have 'contentEditable' in effect
		// on element unless it has layout. (#5562)
		if ( CKEDITOR.document.$.documentMode >= 8 ) {
			css.push( 'html.CSS1Compat [contenteditable=false]{min-height:0 !important}' );

			var selectors = [];

			for ( var tag in CKEDITOR.dtd.$removeEmpty )
				selectors.push( 'html.CSS1Compat ' + tag + '[contenteditable=false]' );

			css.push( selectors.join( ',' ) + '{display:inline-block}' );
		}
		// Set the HTML style to 100% to have the text cursor in affect (#6341)
		else if ( CKEDITOR.env.gecko ) {
			css.push( 'html{height:100% !important}' );
			css.push( 'img:-moz-broken{-moz-force-broken-image-icon:1;min-width:24px;min-height:24px}' );
		}

		// #6341: The text cursor must be set on the editor area.
		// #6632: Avoid having "text" shape of cursor in IE7 scrollbars.
		css.push( 'html{cursor:text;*cursor:auto}' );

		// Use correct cursor for these elements
		css.push( 'img,input,textarea{cursor:default}' );

		return css.join('\n');
	}
})();

/**
 * Disables the ability of resize objects (image and tables) in the editing area.
 *
 *		config.disableObjectResizing = true;
 *
 * @cfg
 * @member CKEDITOR.config
 */
CKEDITOR.config.disableObjectResizing = false;

/**
 * Disables the "table tools" offered natively by the browser (currently
 * Firefox only) to make quick table editing operations, like adding or
 * deleting rows and columns.
 *
 *		config.disableNativeTableHandles = false;
 *
 * @cfg
 * @member CKEDITOR.config
 */
CKEDITOR.config.disableNativeTableHandles = true;

/**
 * Disables the built-in words spell checker if browser provides one.
 *
 * **Note:** Although word suggestions provided by browsers (natively) will
 * not appear in CKEditor's default context menu,
 * users can always reach the native context menu by holding the
 * *Ctrl* key when right-clicking if {@link #browserContextMenuOnCtrl}
 * is enabled or you're simply not using the context menu plugin.
 *
 *		config.disableNativeSpellChecker = false;
 *
 * @cfg
 * @member CKEDITOR.config
 */
CKEDITOR.config.disableNativeSpellChecker = true;

/**
 * The CSS file(s) to be used to apply style to the contents. It should
 * reflect the CSS used in the final pages where the contents are to be
 * used.
 *
 *		config.contentsCss = '/css/mysitestyles.css';
 *		config.contentsCss = ['/css/mysitestyles.css', '/css/anotherfile.css'];
 *
 * @cfg {String/Array} [contentsCss=CKEDITOR.basePath + 'contents.css']
 * @member CKEDITOR.config
 */
CKEDITOR.config.contentsCss = CKEDITOR.basePath + 'contents.css';

/**
 * Language code of  the writting language which is used to author the editor
 * contents.
 *
 *		config.contentsLanguage = 'fr';
 *
 * @cfg {String} [contentsLanguage=same value with editor's UI language]
 * @member CKEDITOR.config
 */

/**
 * The base href URL used to resolve relative and absolute URLs in the
 * editor content.
 *
 *		config.baseHref = 'http://www.example.com/path/';
 *
 * @cfg {String} [baseHref='']
 * @member CKEDITOR.config
 */

/**
 * Whether automatically create wrapping blocks around inline contents inside document body,
 * this helps to ensure the integrality of the block enter mode.
 *
 * **Note:** Changing the default value might introduce unpredictable usability issues.
 *
 *		config.autoParagraph = false;
 *
 * @since 3.6
 * @cfg {Boolean} [autoParagraph=true]
 * @member CKEDITOR.config
 */

/**
 * Fired when some elements are added to the document.
 *
 * @event ariaWidget
 * @member CKEDITOR.editor
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param {CKEDITOR.dom.element} data The element being added.
 */
