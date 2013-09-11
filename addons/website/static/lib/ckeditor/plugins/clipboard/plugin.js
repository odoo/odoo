/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @ignore
 * File overview: Clipboard support.
 */

//
// EXECUTION FLOWS:
// -- CTRL+C
//		* browser's default behaviour
// -- CTRL+V
//		* listen onKey (onkeydown)
//		* simulate 'beforepaste' for non-IEs on editable
//		* simulate 'paste' for Fx2/Opera on editable
//		* listen 'onpaste' on editable ('onbeforepaste' for IE)
//		* fire 'beforePaste' on editor
//		* !canceled && getClipboardDataByPastebin
//		* fire 'paste' on editor
//		* !canceled && fire 'afterPaste' on editor
// -- CTRL+X
//		* listen onKey (onkeydown)
//		* fire 'saveSnapshot' on editor
//		* browser's default behaviour
//		* deferred second 'saveSnapshot' event
// -- Copy command
//		* tryToCutCopy
//			* execCommand
//		* !success && alert
// -- Cut command
//		* fixCut
//		* tryToCutCopy
//			* execCommand
//		* !success && alert
// -- Paste command
//		* fire 'paste' on editable ('beforepaste' for IE)
//		* !canceled && execCommand 'paste'
//		* !success && fire 'pasteDialog' on editor
// -- Paste from native context menu & menubar
//		(Fx & Webkits are handled in 'paste' default listner.
//		Opera cannot be handled at all because it doesn't fire any events
//		Special treatment is needed for IE, for which is this part of doc)
//		* listen 'onpaste'
//		* cancel native event
//		* fire 'beforePaste' on editor
//		* !canceled && getClipboardDataByPastebin
//		* execIECommand( 'paste' ) -> this fires another 'paste' event, so cancel it
//		* fire 'paste' on editor
//		* !canceled && fire 'afterPaste' on editor
//
//
// PASTE EVENT - PREPROCESSING:
// -- Possible dataValue types: auto, text, html.
// -- Possible dataValue contents:
//		* text (possible \n\r)
//		* htmlified text (text + br,div,p - no presentional markup & attrs - depends on browser)
//		* html
// -- Possible flags:
//		* htmlified - if true then content is a HTML even if no markup inside. This flag is set
//			for content from editable pastebins, because they 'htmlify' pasted content.
//
// -- Type: auto:
//		* content: htmlified text ->	filter, unify text markup (brs, ps, divs), set type: text
//		* content: html ->				filter, set type: html
// -- Type: text:
//		* content: htmlified text ->	filter, unify text markup
//		* content: html ->				filter, strip presentional markup, unify text markup
// -- Type: html:
//		* content: htmlified text ->	filter, unify text markup
//		* content: html ->				filter
//
// -- Phases:
//		* filtering (priorities 3-5) - e.g. pastefromword filters
//		* content type sniffing (priority 6)
//		* markup transformations for text (priority 6)
//

'use strict';

(function() {
	// Register the plugin.
	CKEDITOR.plugins.add( 'clipboard', {
		requires: 'dialog',
		lang: 'af,ar,bg,bn,bs,ca,cs,cy,da,de,el,en,en-au,en-ca,en-gb,eo,es,et,eu,fa,fi,fo,fr,fr-ca,gl,gu,he,hi,hr,hu,id,is,it,ja,ka,km,ko,ku,lt,lv,mk,mn,ms,nb,nl,no,pl,pt,pt-br,ro,ru,si,sk,sl,sq,sr,sr-latn,sv,th,tr,ug,uk,vi,zh,zh-cn', // %REMOVE_LINE_CORE%
		icons: 'copy,copy-rtl,cut,cut-rtl,paste,paste-rtl', // %REMOVE_LINE_CORE%
		hidpi: true, // %REMOVE_LINE_CORE%
		init: function( editor ) {
			var textificationFilter;

			initClipboard( editor );

			CKEDITOR.dialog.add( 'paste', CKEDITOR.getUrl( this.path + 'dialogs/paste.js' ) );

			editor.on( 'paste', function( evt ) {
				var data = evt.data.dataValue,
					blockElements = CKEDITOR.dtd.$block;

				// Filter webkit garbage.
				if ( data.indexOf( 'Apple-' ) > -1 ) {
					// Replace special webkit's &nbsp; with simple space, because webkit
					// produces them even for normal spaces.
					data = data.replace( /<span class="Apple-converted-space">&nbsp;<\/span>/gi, ' ' );

					// Strip <span> around white-spaces when not in forced 'html' content type.
					// This spans are created only when pasting plain text into Webkit,
					// but for safety reasons remove them always.
					if ( evt.data.type != 'html' )
						data = data.replace( /<span class="Apple-tab-span"[^>]*>([^<]*)<\/span>/gi, function( all, spaces ) {
						// Replace tabs with 4 spaces like Fx does.
						return spaces.replace( /\t/g, '&nbsp;&nbsp; &nbsp;' );
					});

					// This br is produced only when copying & pasting HTML content.
					if ( data.indexOf( '<br class="Apple-interchange-newline">' ) > -1 ) {
						evt.data.startsWithEOL = 1;
						evt.data.preSniffing = 'html'; // Mark as not text.
						data = data.replace( /<br class="Apple-interchange-newline">/, '' );
					}

					// Remove all other classes.
					data = data.replace( /(<[^>]+) class="Apple-[^"]*"/gi, '$1' );
				}

				// Strip editable that was copied from inside. (#9534)
				if ( data.match( /^<[^<]+cke_(editable|contents)/i ) ) {
					var tmp,
						editable_wrapper,
						wrapper = new CKEDITOR.dom.element( 'div' );

					wrapper.setHtml( data );
					// Verify for sure and check for nested editor UI parts. (#9675)
					while ( wrapper.getChildCount() == 1 &&
							( tmp = wrapper.getFirst() ) &&
							tmp.type == CKEDITOR.NODE_ELEMENT &&	// Make sure first-child is element.
							( tmp.hasClass( 'cke_editable' ) || tmp.hasClass( 'cke_contents' ) ) ) {
						wrapper = editable_wrapper = tmp;
					}

					// If editable wrapper was found strip it and bogus <br> (added on FF).
					if ( editable_wrapper )
						data = editable_wrapper.getHtml().replace( /<br>$/i, '' );
				}

				if ( CKEDITOR.env.ie ) {
					// &nbsp; <p> -> <p> (br.cke-pasted-remove will be removed later)
					data = data.replace( /^&nbsp;(?: |\r\n)?<(\w+)/g, function( match, elementName ) {
						if ( elementName.toLowerCase() in blockElements ) {
							evt.data.preSniffing = 'html'; // Mark as not a text.
							return '<' + elementName;
						}
						return match;
					});
				} else if ( CKEDITOR.env.webkit ) {
					// </p><div><br></div> -> </p><br>
					// We don't mark br, because this situation can happen for htmlified text too.
					data = data.replace( /<\/(\w+)><div><br><\/div>$/, function( match, elementName ) {
						if ( elementName in blockElements ) {
							evt.data.endsWithEOL = 1;
							return '</' + elementName + '>';
						}
						return match;
					});
				} else if ( CKEDITOR.env.gecko ) {
					// Firefox adds bogus <br> when user pasted text followed by space(s).
					data = data.replace( /(\s)<br>$/, '$1' );
				}

				evt.data.dataValue = data;
			}, null, null, 3 );

			editor.on( 'paste', function( evt ) {
				var dataObj = evt.data,
					type = dataObj.type,
					data = dataObj.dataValue,
					trueType,
					// Default is 'html'.
					defaultType = editor.config.clipboard_defaultContentType || 'html';

				// If forced type is 'html' we don't need to know true data type.
				if ( type == 'html' || dataObj.preSniffing == 'html' )
					trueType = 'html';
				else
					trueType = recogniseContentType( data );

				// Unify text markup.
				if ( trueType == 'htmlifiedtext' )
					data = htmlifiedTextHtmlification( editor.config, data );
				// Strip presentional markup & unify text markup.
				else if ( type == 'text' && trueType == 'html' ) {
					// Init filter only if needed and cache it.
					data = htmlTextification( editor.config, data, textificationFilter || ( textificationFilter = getTextificationFilter( editor ) ) );
				}

				if ( dataObj.startsWithEOL )
					data = '<br data-cke-eol="1">' + data;
				if ( dataObj.endsWithEOL )
					data += '<br data-cke-eol="1">';

				if ( type == 'auto' )
					type = ( trueType == 'html' || defaultType == 'html' ) ? 'html' : 'text';

				dataObj.type = type;
				dataObj.dataValue = data;
				delete dataObj.preSniffing;
				delete dataObj.startsWithEOL;
				delete dataObj.endsWithEOL;
			}, null, null, 6 );

			// Inserts processed data into the editor at the end of the
			// events chain.
			editor.on( 'paste', function( evt ) {
				var data = evt.data;

				editor.insertHtml( data.dataValue, data.type );

				// Deferr 'afterPaste' so all other listeners for 'paste' will be fired first.
				setTimeout( function() {
					editor.fire( 'afterPaste' );
				}, 0 );
			}, null, null, 1000 );

			editor.on( 'pasteDialog', function( evt ) {
				// TODO it's possible that this setTimeout is not needed any more,
				// because of changes introduced in the same commit as this comment.
				// Editor.getClipboardData adds listner to the dialog's events which are
				// fired after a while (not like 'showDialog').
				setTimeout( function() {
					// Open default paste dialog.
					editor.openDialog( 'paste', evt.data );
				}, 0 );
			});
		}
	});

	function initClipboard( editor ) {
		var preventBeforePasteEvent = 0,
			preventPasteEvent = 0,
			inReadOnly = 0,
			// Safari doesn't like 'beforepaste' event - it sometimes doesn't
			// properly handles ctrl+c. Probably some race-condition between events.
			// Chrome and Firefox works well with both events, so better to use 'paste'
			// which will handle pasting from e.g. browsers' menu bars.
			// IE7/8 doesn't like 'paste' event for which it's throwing random errors.
			mainPasteEvent = CKEDITOR.env.ie ? 'beforepaste' : 'paste';

		addListeners();
		addButtonsCommands();

		/**
		 * Gets clipboard data by directly accessing the clipboard (IE only) or opening paste dialog.
		 *
		 *		editor.getClipboardData( { title: 'Get my data' }, function( data ) {
		 *			if ( data )
		 *				alert( data.type + ' ' + data.dataValue );
		 *		} );
		 *
		 * @member CKEDITOR.editor
		 * @param {Object} options
		 * @param {String} [options.title] Title of paste dialog.
		 * @param {Function} callback Function that will be executed with `data.type` and `data.dataValue`
		 * or `null` if none of the capturing method succeeded.
		 */
		editor.getClipboardData = function( options, callback ) {
			var beforePasteNotCanceled = false,
				dataType = 'auto',
				dialogCommited = false;

			// Options are optional - args shift.
			if ( !callback ) {
				callback = options;
				options = null;
			}

			// Listen with maximum priority to handle content before everyone else.
			// This callback will handle paste event that will be fired if direct
			// access to the clipboard succeed in IE.
			editor.on( 'paste', onPaste, null, null, 0 );

			// Listen at the end of listeners chain to see if event wasn't canceled
			// and to retrieve modified data.type.
			editor.on( 'beforePaste', onBeforePaste, null, null, 1000 );

			// getClipboardDataDirectly() will fire 'beforePaste' synchronously, so we can
			// check if it was canceled and if any listener modified data.type.

			// If command didn't succeed (only IE allows to access clipboard and only if
			// user agrees) open and handle paste dialog.
			if ( getClipboardDataDirectly() === false ) {
				// Direct access to the clipboard wasn't successful so remove listener.
				editor.removeListener( 'paste', onPaste );

				// If beforePaste was canceled do not open dialog.
				// Add listeners only if dialog really opened. 'pasteDialog' can be canceled.
				if ( beforePasteNotCanceled && editor.fire( 'pasteDialog', onDialogOpen ) ) {
					editor.on( 'pasteDialogCommit', onDialogCommit );

					// 'dialogHide' will be fired after 'pasteDialogCommit'.
					editor.on( 'dialogHide', function( evt ) {
						evt.removeListener();
						evt.data.removeListener( 'pasteDialogCommit', onDialogCommit );

						// Because Opera has to wait a while in pasteDialog we have to wait here.
						setTimeout( function() {
							// Notify even if user canceled dialog (clicked 'cancel', ESC, etc).
							if ( !dialogCommited )
								callback( null );
						}, 10 );
					});
				} else
					callback( null );
			}

			function onPaste( evt ) {
				evt.removeListener();
				evt.cancel();
				callback( evt.data );
			}

			function onBeforePaste( evt ) {
				evt.removeListener();
				beforePasteNotCanceled = true;
				dataType = evt.data.type;
			}

			function onDialogCommit( evt ) {
				evt.removeListener();
				// Cancel pasteDialogCommit so paste dialog won't automatically fire
				// 'paste' evt by itself.
				evt.cancel();
				dialogCommited = true;
				callback( { type: dataType, dataValue: evt.data } );
			}

			function onDialogOpen() {
				this.customTitle = ( options && options.title );
			}
		};

		function addButtonsCommands() {
			addButtonCommand( 'Cut', 'cut', createCutCopyCmd( 'cut' ), 10, 1 );
			addButtonCommand( 'Copy', 'copy', createCutCopyCmd( 'copy' ), 20, 4 );
			addButtonCommand( 'Paste', 'paste', createPasteCmd(), 30, 8 );

			function addButtonCommand( buttonName, commandName, command, toolbarOrder, ctxMenuOrder ) {
				var lang = editor.lang.clipboard[ commandName ];

				editor.addCommand( commandName, command );
				editor.ui.addButton && editor.ui.addButton( buttonName, {
					label: lang,
					command: commandName,
					toolbar: 'clipboard,' + toolbarOrder
				});

				// If the "menu" plugin is loaded, register the menu item.
				if ( editor.addMenuItems ) {
					editor.addMenuItem( commandName, {
						label: lang,
						command: commandName,
						group: 'clipboard',
						order: ctxMenuOrder
					});
				}
			}
		}

		function addListeners() {
			editor.on( 'key', onKey );
			editor.on( 'contentDom', addListenersToEditable );

			// For improved performance, we're checking the readOnly state on selectionChange instead of hooking a key event for that.
			editor.on( 'selectionChange', function( evt ) {
				inReadOnly = evt.data.selection.getRanges()[ 0 ].checkReadOnly();
				setToolbarStates();
			});

			// If the "contextmenu" plugin is loaded, register the listeners.
			if ( editor.contextMenu ) {
				editor.contextMenu.addListener( function( element, selection ) {
					inReadOnly = selection.getRanges()[ 0 ].checkReadOnly();
					return {
						cut: stateFromNamedCommand( 'Cut' ),
						copy: stateFromNamedCommand( 'Copy' ),
						paste: stateFromNamedCommand( 'Paste' )
					};
				});
			}
		}

		// Add events listeners to editable.
		function addListenersToEditable() {
			var editable = editor.editable();

			// We'll be catching all pasted content in one line, regardless of whether
			// it's introduced by a document command execution (e.g. toolbar buttons) or
			// user paste behaviors (e.g. CTRL+V).
			editable.on( mainPasteEvent, function( evt ) {
				if ( CKEDITOR.env.ie && preventBeforePasteEvent )
					return;

				// If you've just asked yourself why preventPasteEventNow() is not here, but
				// in listener for CTRL+V and exec method of 'paste' command
				// you've asked the same question we did.
				//
				// THE ANSWER:
				//
				// First thing to notice - this answer makes sense only for IE,
				// because other browsers don't listen for 'paste' event.
				//
				// What would happen if we move preventPasteEventNow() here?
				// For:
				// * CTRL+V - IE fires 'beforepaste', so we prevent 'paste' and pasteDataFromClipboard(). OK.
				// * editor.execCommand( 'paste' ) - we fire 'beforepaste', so we prevent
				//		'paste' and pasteDataFromClipboard() and doc.execCommand( 'Paste' ). OK.
				// * native context menu - IE fires 'beforepaste', so we prevent 'paste', but unfortunately
				//		on IE we fail with pasteDataFromClipboard() here, because of... we don't know why, but
				//		we just fail, so... we paste nothing. FAIL.
				// * native menu bar - the same as for native context menu.
				//
				// But don't you know any way to distinguish first two cases from last two?
				// Only one - special flag set in CTRL+V handler and exec method of 'paste'
				// command. And that's what we did using preventPasteEventNow().

				pasteDataFromClipboard( evt );
			});

			// It's not possible to clearly handle all four paste methods (ctrl+v, native menu bar
			// native context menu, editor's command) in one 'paste/beforepaste' event in IE.
			//
			// For ctrl+v & editor's command it's easy to handle pasting in 'beforepaste' listener,
			// so we do this. For another two methods it's better to use 'paste' event.
			//
			// 'paste' is always being fired after 'beforepaste' (except of weird one on opening native
			// context menu), so for two methods handled in 'beforepaste' we're canceling 'paste'
			// using preventPasteEvent state.
			//
			// 'paste' event in IE is being fired before getClipboardDataByPastebin executes its callback.
			//
			// QUESTION: Why didn't you handle all 4 paste methods in handler for 'paste'?
			//		Wouldn't this just be simpler?
			// ANSWER: Then we would have to evt.data.preventDefault() only for native
			//		context menu and menu bar pastes. The same with execIECommand().
			//		That would force us to mark CTRL+V and editor's paste command with
			//		special flag, other than preventPasteEvent. But we still would have to
			//		have preventPasteEvent for the second event fired by execIECommand.
			//		Code would be longer and not cleaner.
			CKEDITOR.env.ie && editable.on( 'paste', function( evt ) {
				if ( preventPasteEvent )
					return;
				// Cancel next 'paste' event fired by execIECommand( 'paste' )
				// at the end of this callback.
				preventPasteEventNow();

				// Prevent native paste.
				evt.data.preventDefault();

				pasteDataFromClipboard( evt );

				// Force IE to paste content into pastebin so pasteDataFromClipboard will work.
				if ( !execIECommand( 'paste' ) )
					editor.openDialog( 'paste' );
			});

			// [IE] Dismiss the (wrong) 'beforepaste' event fired on context/toolbar menu open. (#7953)
			if ( CKEDITOR.env.ie ) {
				editable.on( 'contextmenu', preventBeforePasteEventNow, null, null, 0 );

				editable.on( 'beforepaste', function( evt ) {
					if ( evt.data && !evt.data.$.ctrlKey )
						preventBeforePasteEventNow();
				}, null, null, 0 );

			}

			editable.on( 'beforecut', function() {
				!preventBeforePasteEvent && fixCut( editor );
			});

			var mouseupTimeout;

			// Use editor.document instead of editable in non-IEs for observing mouseup
			// since editable won't fire the event if selection process started within
			// iframe and ended out of the editor (#9851).
			editable.attachListener( CKEDITOR.env.ie ? editable : editor.document.getDocumentElement(), 'mouseup', function() {
				mouseupTimeout = setTimeout( function() {
					setToolbarStates();
				}, 0 );
			});

			// Make sure that deferred mouseup callback isn't executed after editor instance
			// had been destroyed. This may happen when editor.destroy() is called in parallel
			// with mouseup event (i.e. a button with onclick callback) (#10219).
			editor.on( 'destroy', function() {
				clearTimeout( mouseupTimeout );
			});

			editable.on( 'keyup', setToolbarStates );
		}

		// Create object representing Cut or Copy commands.
		function createCutCopyCmd( type ) {
			return {
				type: type,
				canUndo: type == 'cut', // We can't undo copy to clipboard.
				startDisabled: true,
				exec: function( data ) {
					// Attempts to execute the Cut and Copy operations.
					function tryToCutCopy( type ) {
						if ( CKEDITOR.env.ie )
							return execIECommand( type );

						// non-IEs part
						try {
							// Other browsers throw an error if the command is disabled.
							return editor.document.$.execCommand( type, false, null );
						} catch ( e ) {
							return false;
						}
					}

					this.type == 'cut' && fixCut();

					var success = tryToCutCopy( this.type );

					if ( !success )
						alert( editor.lang.clipboard[ this.type + 'Error' ] ); // Show cutError or copyError.

					return success;
				}
			};
		}

		function createPasteCmd() {
			return {
				// Snapshots are done manually by editable.insertXXX methods.
				canUndo: false,
				async: true,

				exec: function( editor, data ) {
					var fire = function( data, withBeforePaste ) {
							data && firePasteEvents( data.type, data.dataValue, !!withBeforePaste );

							editor.fire( 'afterCommandExec', {
								name: 'paste',
								command: cmd,
								returnValue: !!data
							});
						},
						cmd = this;

					// Check data precisely - don't open dialog on empty string.
					if ( typeof data == 'string' )
						fire( { type: 'auto', dataValue: data }, 1 );
					else
						editor.getClipboardData( fire );
				}
			};
		}

		function preventPasteEventNow() {
			preventPasteEvent = 1;
			// For safety reason we should wait longer than 0/1ms.
			// We don't know how long execution of quite complex getClipboardData will take
			// and in for example 'paste' listner execCommand() (which fires 'paste') is called
			// after getClipboardData finishes.
			// Luckily, it's impossible to immediately fire another 'paste' event we want to handle,
			// because we only handle there native context menu and menu bar.
			setTimeout( function() {
				preventPasteEvent = 0;
			}, 100 );
		}

		function preventBeforePasteEventNow() {
			preventBeforePasteEvent = 1;
			setTimeout( function() {
				preventBeforePasteEvent = 0;
			}, 10 );
		}

		// Tries to execute any of the paste, cut or copy commands in IE. Returns a
		// boolean indicating that the operation succeeded.
		// @param {String} command *LOWER CASED* name of command ('paste', 'cut', 'copy').
		function execIECommand( command ) {
			var doc = editor.document,
				body = doc.getBody(),
				enabled = false,
				onExec = function() {
					enabled = true;
				};

			// The following seems to be the only reliable way to detect that
			// clipboard commands are enabled in IE. It will fire the
			// onpaste/oncut/oncopy events only if the security settings allowed
			// the command to execute.
			body.on( command, onExec );

			// IE6/7: document.execCommand has problem to paste into positioned element.
			( CKEDITOR.env.version > 7 ? doc.$ : doc.$.selection.createRange() )[ 'execCommand' ]( command );

			body.removeListener( command, onExec );

			return enabled;
		}

		function firePasteEvents( type, data, withBeforePaste ) {
			var eventData = { type: type };

			if ( withBeforePaste ) {
				// Fire 'beforePaste' event so clipboard flavor get customized
				// by other plugins.
				if ( !editor.fire( 'beforePaste', eventData ) )
					return false; // Event canceled
			}

			// The very last guard to make sure the paste has successfully happened.
			// This check should be done after firing 'beforePaste' because for native paste
			// 'beforePaste' is by default fired even for empty clipboard.
			if ( !data )
				return false;

			// Reuse eventData.type because the default one could be changed by beforePaste listeners.
			eventData.dataValue = data;

			return editor.fire( 'paste', eventData );
		}

		// Cutting off control type element in IE standards breaks the selection entirely. (#4881)
		function fixCut() {
			if ( !CKEDITOR.env.ie || CKEDITOR.env.quirks )
				return;

			var sel = editor.getSelection(),
				control, range, dummy;

			if ( ( sel.getType() == CKEDITOR.SELECTION_ELEMENT ) && ( control = sel.getSelectedElement() ) ) {
				range = sel.getRanges()[ 0 ];
				dummy = editor.document.createText( '' );
				dummy.insertBefore( control );
				range.setStartBefore( dummy );
				range.setEndAfter( control );
				sel.selectRanges( [ range ] );

				// Clear up the fix if the paste wasn't succeeded.
				setTimeout( function() {
					// Element still online?
					if ( control.getParent() ) {
						dummy.remove();
						sel.selectElement( control );
					}
				}, 0 );
			}
		}

		// Allow to peek clipboard content by redirecting the
		// pasting content into a temporary bin and grab the content of it.
		function getClipboardDataByPastebin( evt, callback ) {
			var doc = editor.document,
				editable = editor.editable(),
				cancel = function( evt ) {
					evt.cancel();
				},
				ff3x = CKEDITOR.env.gecko && CKEDITOR.env.version <= 10902,
				blurListener;

			// Avoid recursions on 'paste' event or consequent paste too fast. (#5730)
			if ( doc.getById( 'cke_pastebin' ) )
				return;

			var sel = editor.getSelection();
			var bms = sel.createBookmarks();

			// Create container to paste into.
			// For rich content we prefer to use "body" since it holds
			// the least possibility to be splitted by pasted content, while this may
			// breaks the text selection on a frame-less editable, "div" would be
			// the best one in that case.
			// In another case on old IEs moving the selection into a "body" paste bin causes error panic.
			// Body can't be also used for Opera which fills it with <br>
			// what is indistinguishable from pasted <br> (copying <br> in Opera isn't possible,
			// but it can be copied from other browser).
			var pastebin = new CKEDITOR.dom.element(
				( CKEDITOR.env.webkit || editable.is( 'body' ) ) && !( CKEDITOR.env.ie || CKEDITOR.env.opera ) ? 'body' : 'div', doc );

			pastebin.setAttribute( 'id', 'cke_pastebin' );

			// Append bogus to prevent Opera from doing this. (#9522)
			if ( CKEDITOR.env.opera )
				pastebin.appendBogus();

			var containerOffset = 0,
				offsetParent,
				win = doc.getWindow();

			// Seems to be the only way to avoid page scroll in Fx 3.x.
			if ( ff3x ) {
				pastebin.insertAfter( bms[ 0 ].startNode );
				pastebin.setStyle( 'display', 'inline' );
			} else {
				if ( CKEDITOR.env.webkit ) {
					// It's better to paste close to the real paste destination, so inherited styles
					// (which Webkits will try to compensate by styling span) differs less from the destination's one.
					editable.append( pastebin );
					// Style pastebin like .cke_editable, to minimize differences between origin and destination. (#9754)
					pastebin.addClass( 'cke_editable' );

					// Compensate position of offsetParent.
					if ( !editable.is( 'body' ) ) {
						// We're not able to get offsetParent from pastebin (body element), so check whether
						// its parent (editable) is positioned.
						if ( editable.getComputedStyle( 'position' ) != 'static' )
							offsetParent = editable;
						// And if not - safely get offsetParent from editable.
						else
							offsetParent = CKEDITOR.dom.element.get( editable.$.offsetParent );

						containerOffset = offsetParent.getDocumentPosition().y;
					}
				} else {
					// Opera and IE doesn't allow to append to html element.
					editable.getAscendant( CKEDITOR.env.ie || CKEDITOR.env.opera ? 'body' : 'html', 1 ).append( pastebin );
				}

				pastebin.setStyles({
					position: 'absolute',
					// Position the bin at the top (+10 for safety) of viewport to avoid any subsequent document scroll.
					top: ( win.getScrollPosition().y - containerOffset + 10 ) + 'px',
					width: '1px',
					// Caret has to fit in that height, otherwise browsers like Chrome & Opera will scroll window to show it.
					// Set height equal to viewport's height - 20px (safety gaps), minimum 1px.
					height: Math.max( 1, win.getViewPaneSize().height - 20 ) + 'px',
					overflow: 'hidden',
					// Reset styles that can mess up pastebin position.
					margin: 0,
					padding: 0
				});
			}

			// Check if the paste bin now establishes new editing host.
			var isEditingHost = pastebin.getParent().isReadOnly();

			if ( isEditingHost ) {
				// Hide the paste bin.
				pastebin.setOpacity( 0 );
				// And make it editable.
				pastebin.setAttribute( 'contenteditable', true );
			}
			// Transparency is not enough since positioned non-editing host always shows
			// resize handler, pull it off the screen instead.
			else
				pastebin.setStyle( editor.config.contentsLangDirection == 'ltr' ? 'left' : 'right', '-1000px' );

			editor.on( 'selectionChange', cancel, null, null, 0 );

			// Webkit fill fire blur on editable when moving selection to
			// pastebin (if body is used). Cancel it because it causes incorrect
			// selection lock in case of inline editor.
			if ( CKEDITOR.env.webkit )
				blurListener = editable.once( 'blur', cancel, null, null, -100 );

			// Temporarily move selection to the pastebin.
			isEditingHost && pastebin.focus();
			var range = new CKEDITOR.dom.range( pastebin );
			range.selectNodeContents( pastebin );
			var selPastebin = range.select();

			// If non-native paste is executed, IE will open security alert and blur editable.
			// Editable will then lock selection inside itself and after accepting security alert
			// this selection will be restored. We overwrite stored selection, so it's restored
			// in pastebin. (#9552)
			if ( CKEDITOR.env.ie ) {
				blurListener = editable.once( 'blur', function( evt ) {
					editor.lockSelection( selPastebin );
				} );
			}

			var scrollTop = CKEDITOR.document.getWindow().getScrollPosition().y;

			// Wait a while and grab the pasted contents.
			setTimeout( function() {
				// Restore main window's scroll position which could have been changed
				// by browser in cases described in #9771.
				if ( CKEDITOR.env.webkit || CKEDITOR.env.opera )
					CKEDITOR.document[ CKEDITOR.env.webkit ? 'getBody' : 'getDocumentElement' ]().$.scrollTop = scrollTop;

				// Blur will be fired only on non-native paste. In other case manually remove listener.
				blurListener && blurListener.removeListener();

				// Restore properly the document focus. (#8849)
				if ( CKEDITOR.env.ie )
					editable.focus();

				// IE7: selection must go before removing pastebin. (#8691)
				sel.selectBookmarks( bms );
				pastebin.remove();

				// Grab the HTML contents.
				// We need to look for a apple style wrapper on webkit it also adds
				// a div wrapper if you copy/paste the body of the editor.
				// Remove hidden div and restore selection.
				var bogusSpan;
				if ( CKEDITOR.env.webkit && ( bogusSpan = pastebin.getFirst() ) && ( bogusSpan.is && bogusSpan.hasClass( 'Apple-style-span' ) ) )
					pastebin = bogusSpan;

				editor.removeListener( 'selectionChange', cancel );
				callback( pastebin.getHtml() );
			}, 0 );
		}

		// Try to get content directly from clipboard, without native event
		// being fired before. In other words - synthetically get clipboard data
		// if it's possible.
		// mainPasteEvent will be fired, so if forced native paste:
		// * worked, getClipboardDataByPastebin will grab it,
		// * didn't work, pastebin will be empty and editor#paste won't be fired.
		function getClipboardDataDirectly() {
			if ( CKEDITOR.env.ie ) {
				// Prevent IE from pasting at the begining of the document.
				editor.focus();

				// Command will be handled by 'beforepaste', but as
				// execIECommand( 'paste' ) will fire also 'paste' event
				// we're canceling it.
				preventPasteEventNow();

				// #9247: Lock focus to prevent IE from hiding toolbar for inline editor.
				var focusManager = editor.focusManager;
				focusManager.lock();

				if ( editor.editable().fire( mainPasteEvent ) && !execIECommand( 'paste' ) ) {
					focusManager.unlock();
					return false;
				}
				focusManager.unlock();
			} else {
				try {
					if ( editor.editable().fire( mainPasteEvent ) && !editor.document.$.execCommand( 'Paste', false, null ) ) {
						throw 0;
					}
				} catch ( e ) {
					return false;
				}
			}

			return true;
		}

		// Listens for some clipboard related keystrokes, so they get customized.
		// Needs to be bind to keydown event.
		function onKey( event ) {
			if ( editor.mode != 'wysiwyg' )
				return;

			switch ( event.data.keyCode ) {
				// Paste
				case CKEDITOR.CTRL + 86: // CTRL+V
				case CKEDITOR.SHIFT + 45: // SHIFT+INS
					var editable = editor.editable();

					// Cancel 'paste' event because ctrl+v is for IE handled
					// by 'beforepaste'.
					preventPasteEventNow();

					// Simulate 'beforepaste' event for all none-IEs.
					!CKEDITOR.env.ie && editable.fire( 'beforepaste' );

					// Simulate 'paste' event for Opera/Firefox2.
					if ( CKEDITOR.env.opera || CKEDITOR.env.gecko && CKEDITOR.env.version < 10900 )
						editable.fire( 'paste' );
					return;

					// Cut
				case CKEDITOR.CTRL + 88: // CTRL+X
				case CKEDITOR.SHIFT + 46: // SHIFT+DEL
					// Save Undo snapshot.
					editor.fire( 'saveSnapshot' ); // Save before cut
					setTimeout( function() {
						editor.fire( 'saveSnapshot' ); // Save after cut
					}, 0 );
			}
		}

		function pasteDataFromClipboard( evt ) {
			// Default type is 'auto', but can be changed by beforePaste listeners.
			var eventData = { type: 'auto' };
			// Fire 'beforePaste' event so clipboard flavor get customized by other plugins.
			// If 'beforePaste' is canceled continue executing getClipboardDataByPastebin and then do nothing
			// (do not fire 'paste', 'afterPaste' events). This way we can grab all - synthetically
			// and natively pasted content and prevent its insertion into editor
			// after canceling 'beforePaste' event.
			var beforePasteNotCanceled = editor.fire( 'beforePaste', eventData );

			getClipboardDataByPastebin( evt, function( data ) {
				// Clean up.
				data = data.replace( /<span[^>]+data-cke-bookmark[^<]*?<\/span>/ig, '' );

				// Fire remaining events (without beforePaste)
				beforePasteNotCanceled && firePasteEvents( eventData.type, data, 0, 1 );
			});
		}

		function setToolbarStates() {
			if ( editor.mode != 'wysiwyg' )
				return;

			var pasteState = stateFromNamedCommand( 'Paste' );

			editor.getCommand( 'cut' ).setState( stateFromNamedCommand( 'Cut' ) );
			editor.getCommand( 'copy' ).setState( stateFromNamedCommand( 'Copy' ) );
			editor.getCommand( 'paste' ).setState( pasteState );
			editor.fire( 'pasteState', pasteState );
		}

		function stateFromNamedCommand( command ) {
			var retval;

			if ( inReadOnly && command in { Paste:1,Cut:1 } )
				return CKEDITOR.TRISTATE_DISABLED;

			if ( command == 'Paste' ) {
				// IE Bug: queryCommandEnabled('paste') fires also 'beforepaste(copy/cut)',
				// guard to distinguish from the ordinary sources (either
				// keyboard paste or execCommand) (#4874).
				CKEDITOR.env.ie && ( preventBeforePasteEvent = 1 );
				try {
					// Always return true for Webkit (which always returns false)
					retval = editor.document.$.queryCommandEnabled( command ) || CKEDITOR.env.webkit;
				} catch ( er ) {}
				preventBeforePasteEvent = 0;
			}
			// Cut, Copy - check if the selection is not empty
			else {
				var sel = editor.getSelection(),
					ranges = sel.getRanges();
				retval = sel.getType() != CKEDITOR.SELECTION_NONE && !( ranges.length == 1 && ranges[ 0 ].collapsed );
			}

			return retval ? CKEDITOR.TRISTATE_OFF : CKEDITOR.TRISTATE_DISABLED;
		}
	}

	// Returns:
	// * 'htmlifiedtext' if content looks like transformed by browser from plain text.
	//		See clipboard/paste.html TCs for more info.
	// * 'html' if it is not 'htmlifiedtext'.
	function recogniseContentType( data ) {
		if ( CKEDITOR.env.webkit ) {
			// Plain text or ( <div><br></div> and text inside <div> ).
			if ( !data.match( /^[^<]*$/g ) && !data.match( /^(<div><br( ?\/)?><\/div>|<div>[^<]*<\/div>)*$/gi ) )
				return 'html';
		} else if ( CKEDITOR.env.ie ) {
			// Text and <br> or ( text and <br> in <p> - paragraphs can be separated by new \r\n ).
			if ( !data.match( /^([^<]|<br( ?\/)?>)*$/gi ) && !data.match( /^(<p>([^<]|<br( ?\/)?>)*<\/p>|(\r\n))*$/gi ) )
				return 'html';
		} else if ( CKEDITOR.env.gecko || CKEDITOR.env.opera ) {
			// Text or <br>.
			if ( !data.match( /^([^<]|<br( ?\/)?>)*$/gi ) )
				return 'html';
		} else
			return 'html';

		return 'htmlifiedtext';
	}

	// This function transforms what browsers produce when
	// pasting plain text into editable element (see clipboard/paste.html TCs
	// for more info) into correct HTML (similar to that produced by text2Html).
	function htmlifiedTextHtmlification( config, data ) {
		function repeatParagraphs( repeats ) {
			// Repeat blocks floor((n+1)/2) times.
			// Even number of repeats - add <br> at the beginning of last <p>.
			return CKEDITOR.tools.repeat( '</p><p>', ~~ ( repeats / 2 ) ) + ( repeats % 2 == 1 ? '<br>' : '' );
		}

			// Replace adjacent white-spaces (EOLs too - Fx sometimes keeps them) with one space.
		data = data.replace( /\s+/g, ' ' )
			// Remove spaces from between tags.
			.replace( /> +</g, '><' )
			// Normalize XHTML syntax and upper cased <br> tags.
			.replace( /<br ?\/>/gi, '<br>' );

		// IE - lower cased tags.
		data = data.replace( /<\/?[A-Z]+>/g, function( match ) {
			return match.toLowerCase();
		});

		// Don't touch single lines (no <br|p|div>) - nothing to do here.
		if ( data.match( /^[^<]$/ ) )
			return data;

		// Webkit.
		if ( CKEDITOR.env.webkit && data.indexOf( '<div>' ) > -1 ) {
				// One line break at the beginning - insert <br>
			data = data.replace( /^(<div>(<br>|)<\/div>)(?!$|(<div>(<br>|)<\/div>))/g, '<br>' )
				// Two or more - reduce number of new lines by one.
				.replace( /^(<div>(<br>|)<\/div>){2}(?!$)/g, '<div></div>' );

			// Two line breaks create one paragraph in Webkit.
			if ( data.match( /<div>(<br>|)<\/div>/ ) ) {
				data = '<p>' + data.replace( /(<div>(<br>|)<\/div>)+/g, function( match ) {
					return repeatParagraphs( match.split( '</div><div>' ).length + 1 );
				}) + '</p>';
			}

			// One line break create br.
			data = data.replace( /<\/div><div>/g, '<br>' );

			// Remove remaining divs.
			data = data.replace( /<\/?div>/g, '' );
		}

		// Opera and Firefox and enterMode != BR.
		if ( ( CKEDITOR.env.gecko || CKEDITOR.env.opera ) && config.enterMode != CKEDITOR.ENTER_BR ) {
			// Remove bogus <br> - Fx generates two <brs> for one line break.
			// For two line breaks it still produces two <brs>, but it's better to ignore this case than the first one.
			if ( CKEDITOR.env.gecko )
				data = data.replace( /^<br><br>$/, '<br>' );

			// This line satisfy edge case when for Opera we have two line breaks
			//data = data.replace( /)

			if ( data.indexOf( '<br><br>' ) > -1 ) {
				// Two line breaks create one paragraph, three - 2, four - 3, etc.
				data = '<p>' + data.replace( /(<br>){2,}/g, function( match ) {
					return repeatParagraphs( match.length / 4 );
				}) + '</p>';
			}
		}

		return switchEnterMode( config, data );
	}

	// Filter can be editor dependent.
	function getTextificationFilter( editor ) {
		var filter = new CKEDITOR.htmlParser.filter();

		// Elements which creates vertical breaks (have vert margins) - took from HTML5 spec.
		// http://dev.w3.org/html5/markup/Overview.html#toc
		var replaceWithParaIf = { blockquote:1,dl:1,fieldset:1,h1:1,h2:1,h3:1,h4:1,h5:1,h6:1,ol:1,p:1,table:1,ul:1 },

			// All names except of <br>.
			stripInlineIf = CKEDITOR.tools.extend({ br: 0 }, CKEDITOR.dtd.$inline ),

			// What's finally allowed (cke:br will be removed later).
			allowedIf = { p:1,br:1,'cke:br':1 },

			knownIf = CKEDITOR.dtd,

			// All names that will be removed (with content).
			removeIf = CKEDITOR.tools.extend( { area:1,basefont:1,embed:1,iframe:1,map:1,object:1,param:1 }, CKEDITOR.dtd.$nonBodyContent, CKEDITOR.dtd.$cdata );

		var flattenTableCell = function( element ) {
				delete element.name;
				element.add( new CKEDITOR.htmlParser.text( ' ' ) );
			},
			// Squash adjacent headers into one. <h1>A</h1><h2>B</h2> -> <h1>A<br>B</h1><h2></h2>
			// Empty ones will be removed later.
			squashHeader = function( element ) {
				var next = element,
					br, el;

				while ( ( next = next.next ) && next.name && next.name.match( /^h\d$/ ) ) {
					// TODO shitty code - waitin' for htmlParse.element fix.
					br = new CKEDITOR.htmlParser.element( 'cke:br' );
					br.isEmpty = true;
					element.add( br );
					while ( ( el = next.children.shift() ) )
						element.add( el );
				}
			};

		filter.addRules( {
			elements: {
				h1: squashHeader,
				h2: squashHeader,
				h3: squashHeader,
				h4: squashHeader,
				h5: squashHeader,
				h6: squashHeader,

				img: function( element ) {
					var alt = CKEDITOR.tools.trim( element.attributes.alt || '' ),
						txt = ' ';

					// Replace image with its alt if it doesn't look like an url or is empty.
					if ( alt && !alt.match( /(^http|\.(jpe?g|gif|png))/i ) )
						txt = ' [' + alt + '] ';

					return new CKEDITOR.htmlParser.text( txt );
				},

				td: flattenTableCell,
				th: flattenTableCell,

				$: function( element ) {
					var initialName = element.name,
						br;

					// Remove entirely.
					if ( removeIf[ initialName ] )
						return false;

					// Remove all attributes.
					element.attributes = [];

					// Pass brs.
					if ( initialName == 'br' )
						return element;

					// Elements that we want to replace with paragraphs.
					if ( replaceWithParaIf[ initialName ] )
						element.name = 'p';

					// Elements that we want to strip (tags only, without the content).
					else if ( stripInlineIf[ initialName ] )
						delete element.name;

					// Surround other known element with <brs> and strip tags.
					else if ( knownIf[ initialName ] ) {
						// TODO shitty code - waitin' for htmlParse.element fix.
						br = new CKEDITOR.htmlParser.element( 'cke:br' );
						br.isEmpty = true;

						// Replace hrs (maybe sth else too?) with only one br.
						if ( CKEDITOR.dtd.$empty[ initialName ] )
							return br;

						element.add( br, 0 );
						br = br.clone();
						br.isEmpty = true;
						element.add( br );
						delete element.name;
					}

					// Final cleanup - if we can still find some not allowed elements then strip their names.
					if ( !allowedIf[ element.name ] )
						delete element.name;

					return element;
				}
			}
		}, {
			// Apply this filter to every element.
			applyToAll: true
		} );

		return filter;
	}

	function htmlTextification( config, data, filter ) {
		var fragment = new CKEDITOR.htmlParser.fragment.fromHtml( data ),
			writer = new CKEDITOR.htmlParser.basicWriter();

		fragment.writeHtml( writer, filter );
		data = writer.getHtml();

		// Cleanup cke:brs.
		data = data.replace( /\s*(<\/?[a-z:]+ ?\/?>)\s*/g, '$1' )	// Remove spaces around tags.
			.replace( /(<cke:br \/>){2,}/g, '<cke:br />' )			// Join multiple adjacent cke:brs
			.replace( /(<cke:br \/>)(<\/?p>|<br \/>)/g, '$2' )		// Strip cke:brs adjacent to original brs or ps.
			.replace( /(<\/?p>|<br \/>)(<cke:br \/>)/g, '$1' )
			.replace( /<(cke:)?br( \/)?>/g, '<br>' )				// Finally - rename cke:brs to brs and fix <br /> to <br>.
			.replace( /<p><\/p>/g, '' );							// Remove empty paragraphs.

		// Fix nested ps. E.g.:
		// <p>A<p>B<p>C</p>D<p>E</p>F</p>G
		// <p>A</p><p>B</p><p>C</p><p>D</p><p>E</p><p>F</p>G
		var nested = 0;
		data = data.replace( /<\/?p>/g, function( match ) {
			if ( match == '<p>' ) {
				if ( ++nested > 1 )
					return '</p><p>';
			} else {
				if ( --nested > 0 )
					return '</p><p>';
			}

			return match;
		}).replace( /<p><\/p>/g, '' ); // Step before: </p></p> -> </p><p></p><p>. Fix this here.

		return switchEnterMode( config, data );
	}

	function switchEnterMode( config, data ) {
		if ( config.enterMode == CKEDITOR.ENTER_BR ) {
			data = data.replace( /(<\/p><p>)+/g, function( match ) {
				return CKEDITOR.tools.repeat( '<br>', match.length / 7 * 2 );
			}).replace( /<\/?p>/g, '' );
		} else if ( config.enterMode == CKEDITOR.ENTER_DIV ) {
			data = data.replace( /<(\/)?p>/g, '<$1div>' );
		}

		return data;
	}
})();

/**
 * The default content type is used when pasted data cannot be clearly recognized as HTML or text.
 *
 * For example: `'foo'` may come from a plain text editor or a website. It isn't possible to recognize content
 * type in this case, so default will be used. However, it's clear that `'<b>example</b> text'` is an HTML
 * and its origin is webpage, email or other rich text editor.
 *
 * **Note:** If content type is text, then styles of context of paste are preserved.
 *
 *		CKEDITOR.config.clipboard_defaultContentType = 'text';
 *
 * @since 4.0
 * @cfg {'html'/'text'} [clipboard_defaultContentType='html']
 * @member CKEDITOR.config
 */

/**
 * Fired when a clipboard operation is about to be taken into the editor.
 * Listeners can manipulate the data to be pasted before having it effectively
 * inserted into the document.
 *
 * @since 3.1
 * @event paste
 * @member CKEDITOR.editor
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param data
 * @param {String} data.type Type of data in `data.dataValue`. Usually `html` or `text`, but for listeners
 * with priority less than 6 it may be also `auto`, what means that content type hasn't been recognised yet
 * (this will be done by content type sniffer that listens with priority 6).
 * @param {String} data.dataValue HTML to be pasted.
 */

/**
 * Internal event to open the Paste dialog.
 *
 * @private
 * @event pasteDialog
 * @member CKEDITOR.editor
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param {Function} [data] Callback that will be passed to {@link CKEDITOR.editor#openDialog}.
 */
