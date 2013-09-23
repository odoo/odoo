/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

(function() {
	// #### checkSelectionChange : START

	// The selection change check basically saves the element parent tree of
	// the current node and check it on successive requests. If there is any
	// change on the tree, then the selectionChange event gets fired.
	function checkSelectionChange() {
		// A possibly available fake-selection.
		var sel = this._.fakeSelection,
			realSel;

		if ( sel ) {
			realSel = this.getSelection( 1 );

			// If real (not locked/stored) selection was moved from hidden container,
			// then the fake-selection must be invalidated.
			if ( !realSel || !realSel.isHidden() ) {
				// Remove the cache from fake-selection references in use elsewhere.
				sel.reset();

				// Have the code using the native selection.
				sel = 0;
			}
		}

		// If not fake-selection is available then get the native selection.
		if ( !sel ) {
			sel = realSel || this.getSelection( 1 );

			// Editor may have no selection at all.
			if ( !sel || sel.getType() == CKEDITOR.SELECTION_NONE )
				return;
		}

		this.fire( 'selectionCheck', sel );

		var currentPath = this.elementPath();
		if ( !currentPath.compare( this._.selectionPreviousPath ) ) {
			// Cache the active element, which we'll eventually lose on Webkit.
			if ( CKEDITOR.env.webkit )
				this._.previousActive = this.document.getActive();

			this._.selectionPreviousPath = currentPath;
			this.fire( 'selectionChange', { selection: sel, path: currentPath } );
		}
	}

	var checkSelectionChangeTimer, checkSelectionChangeTimeoutPending;

	function checkSelectionChangeTimeout() {
		// Firing the "OnSelectionChange" event on every key press started to
		// be too slow. This function guarantees that there will be at least
		// 200ms delay between selection checks.

		checkSelectionChangeTimeoutPending = true;

		if ( checkSelectionChangeTimer )
			return;

		checkSelectionChangeTimeoutExec.call( this );

		checkSelectionChangeTimer = CKEDITOR.tools.setTimeout( checkSelectionChangeTimeoutExec, 200, this );
	}

	function checkSelectionChangeTimeoutExec() {
		checkSelectionChangeTimer = null;

		if ( checkSelectionChangeTimeoutPending ) {
			// Call this with a timeout so the browser properly moves the
			// selection after the mouseup. It happened that the selection was
			// being moved after the mouseup when clicking inside selected text
			// with Firefox.
			CKEDITOR.tools.setTimeout( checkSelectionChange, 0, this );

			checkSelectionChangeTimeoutPending = false;
		}
	}

	// #### checkSelectionChange : END

	var isVisible = CKEDITOR.dom.walker.invisible( 1 );
	function rangeRequiresFix( range ) {
		function isTextCt( node, isAtEnd ) {
			if ( !node || node.type == CKEDITOR.NODE_TEXT )
				return false;

			var testRng = range.clone();
			return testRng[ 'moveToElementEdit' + ( isAtEnd ? 'End' : 'Start' ) ]( node );
		}

		// Range root must be the editable element, it's to avoid creating filler char
		// on any temporary internal selection.
		if ( !( range.root instanceof CKEDITOR.editable ) ) {
			return false;
		}

		var ct = range.startContainer;

		var previous = range.getPreviousNode( isVisible, null, ct ),
			next = range.getNextNode( isVisible, null, ct );

		// Any adjacent text container may absorb the cursor, e.g.
		// <p><strong>text</strong>^foo</p>
		// <p>foo^<strong>text</strong></p>
		// <div>^<p>foo</p></div>
		if ( isTextCt( previous ) || isTextCt( next, 1 ) )
			return true;

		// Empty block/inline element is also affected. <span>^</span>, <p>^</p> (#7222)
		if ( !( previous || next ) && !( ct.type == CKEDITOR.NODE_ELEMENT && ct.isBlockBoundary() && ct.getBogus() ) )
			return true;

		return false;
	}

	function createFillingChar( element ) {
		removeFillingChar( element, false );

		var fillingChar = element.getDocument().createText( '\u200B' );
		element.setCustomData( 'cke-fillingChar', fillingChar );

		return fillingChar;
	}

	function getFillingChar( element ) {
		return element.getCustomData( 'cke-fillingChar' );
	}

	// Checks if a filling char has been used, eventualy removing it (#1272).
	function checkFillingChar( element ) {
		var fillingChar = getFillingChar( element );
		if ( fillingChar ) {
			// Use this flag to avoid removing the filling char right after
			// creating it.
			if ( fillingChar.getCustomData( 'ready' ) )
				removeFillingChar( element );
			else
				fillingChar.setCustomData( 'ready', 1 );
		}
	}

	function removeFillingChar( element, keepSelection ) {
		var fillingChar = element && element.removeCustomData( 'cke-fillingChar' );
		if ( fillingChar ) {

			// Text selection position might get mangled by
			// subsequent dom modification, save it now for restoring. (#8617)
			if ( keepSelection !== false )
			{
				var bm,
					doc = element.getDocument(),
					sel = doc.getSelection().getNative(),
					// Be error proof.
					range = sel && sel.type != 'None' && sel.getRangeAt( 0 );

				if ( fillingChar.getLength() > 1 && range && range.intersectsNode( fillingChar.$ ) ) {
					bm = [ sel.anchorOffset, sel.focusOffset ];

					// Anticipate the offset change brought by the removed char.
					var startAffected = sel.anchorNode == fillingChar.$ && sel.anchorOffset > 0,
						endAffected = sel.focusNode == fillingChar.$ && sel.focusOffset > 0;
					startAffected && bm[ 0 ]--;
					endAffected && bm[ 1 ]--;

					// Revert the bookmark order on reverse selection.
					isReversedSelection( sel ) && bm.unshift( bm.pop() );
				}
			}

			// We can't simply remove the filling node because the user
			// will actually enlarge it when typing, so we just remove the
			// invisible char from it.
			fillingChar.setText( replaceFillingChar( fillingChar.getText() ) );

			// Restore the bookmark.
			if ( bm ) {
				var rng = sel.getRangeAt( 0 );
				rng.setStart( rng.startContainer, bm[ 0 ] );
				rng.setEnd( rng.startContainer, bm[ 1 ] );
				sel.removeAllRanges();
				sel.addRange( rng );
			}
		}
	}

	function replaceFillingChar( html ) {
		return html.replace( /\u200B( )?/g, function( match ) {
			// #10291 if filling char is followed by a space replace it with nbsp.
			return match[ 1 ] ? '\xa0' : '';
		} );
	}

	function isReversedSelection( sel ) {
		if ( !sel.isCollapsed ) {
			var range = sel.getRangeAt( 0 );
			// Potentially alter an reversed selection range.
			range.setStart( sel.anchorNode, sel.anchorOffset );
			range.setEnd( sel.focusNode, sel.focusOffset );
			return range.collapsed;
		}
	}

	// Read the comments in selection constructor.
	function fixInitialSelection( root, nativeSel, doFocus ) {
		// It may happen that setting proper selection will
		// cause focus to be fired (even without actually focusing root).
		// Cancel it because focus shouldn't be fired when retriving selection. (#10115)
		var listener = root.on( 'focus', function( evt ) {
			evt.cancel();
		}, null, null, -100 );

		// FF && Webkit.
		if ( !CKEDITOR.env.ie ) {
			var range = new CKEDITOR.dom.range( root );
			range.moveToElementEditStart( root );

			var nativeRange = root.getDocument().$.createRange();
			nativeRange.setStart( range.startContainer.$, range.startOffset );
			nativeRange.collapse( 1 );

			nativeSel.removeAllRanges();
			nativeSel.addRange( nativeRange );
		}
		else {
			// IE in specific case may also fire selectionchange.
			// We cannot block bubbling selectionchange, so at least we
			// can prevent from falling into inf recursion caused by fix for #9699
			// (see wysiwygarea plugin).
			// http://dev.ckeditor.com/ticket/10438#comment:13
			var listener2 = root.getDocument().on( 'selectionchange', function( evt ) {
				evt.cancel();
			}, null, null, -100 );
		}

		doFocus && root.focus();

		listener.removeListener();
		listener2 && listener2.removeListener();
	}

	// Creates cke_hidden_sel container and puts real selection there.
	function hideSelection( editor ) {
		var style = CKEDITOR.env.ie ? 'display:none' : 'position:fixed;top:0;left:-1000px',
			hiddenEl = CKEDITOR.dom.element.createFromHtml(
				'<div data-cke-hidden-sel="1" data-cke-temp="1" style="' + style + '">&nbsp;</div>',
				editor.document );

		editor.fire( 'lockSnapshot' );

		editor.editable().append( hiddenEl );

		var sel = editor.getSelection(),
			range = editor.createRange(),
			// Cancel selectionchange fired by selectRanges - prevent from firing selectionChange.
			listener = sel.root.on( 'selectionchange', function( evt ) {
				evt.cancel();
			}, null, null, 0 );

		range.setStartAt( hiddenEl, CKEDITOR.POSITION_AFTER_START );
		range.setEndAt( hiddenEl, CKEDITOR.POSITION_BEFORE_END );
		sel.selectRanges( [ range ] );

		listener.removeListener();

		editor.fire( 'unlockSnapshot' );

		// Set this value at the end, so reset() executed by selectRanges()
		// will clean up old hidden selection container.
		editor._.hiddenSelectionContainer = hiddenEl;
	}

	function removeHiddenSelectionContainer( editor ) {
		var hiddenEl = editor._.hiddenSelectionContainer;

		if ( hiddenEl ) {
			editor.fire( 'lockSnapshot' );
			hiddenEl.remove();
			editor.fire( 'unlockSnapshot' );
		}

		delete editor._.hiddenSelectionContainer;
	}

	// Object containing keystroke handlers for fake selection.
	var fakeSelectionDefaultKeystrokeHandlers = (function() {
		function leave( right ) {
			return function( evt ) {
				var range = evt.editor.createRange();

				// Move selection only if there's a editable place for it.
				// It no, then do nothing (keystroke will be blocked, widget selection kept).
				if ( range.moveToClosestEditablePosition( evt.selected, right ) )
					evt.editor.getSelection().selectRanges( [ range ] );

				// Prevent default.
				return false;
			};
		}

		function del( right ) {
			return function( evt ) {
				var editor = evt.editor,
					range = editor.createRange(),
					found;

				// If haven't found place for caret on the default side,
				// try to find it on the other side.
				if ( !( found = range.moveToClosestEditablePosition( evt.selected, right ) ) )
					found = range.moveToClosestEditablePosition( evt.selected, !right );

				if ( found )
					editor.getSelection().selectRanges( [ range ] );

				// Save the state before removing selected element.
				editor.fire( 'saveSnapshot' );

				evt.selected.remove();

				// Haven't found any editable space before removing element,
				// try to place the caret anywhere (most likely, in empty editable).
				if ( !found ) {
					range.moveToElementEditablePosition( editor.editable() );
					editor.getSelection().selectRanges( [ range ] );
				}

				editor.fire( 'saveSnapshot' );

				// Prevent default.
				return false;
			};
		}

		var leaveLeft = leave(),
			leaveRight = leave( 1 );

		return {
			37: leaveLeft,		// LEFT
			38: leaveLeft,		// UP
			39: leaveRight,		// RIGHT
			40: leaveRight,		// DOWN
			8: del(),			// BACKSPACE
			46: del( 1 )		// DELETE
		};
	})();

	// Handle left, right, delete and backspace keystrokes next to non-editable elements
	// by faking selection on them.
	function getOnKeyDownListener( editor ) {
		var keystrokes = { 37:1,39:1,8:1,46:1 };

		return function( evt ) {
			var keystroke = evt.data.getKeystroke();

			// Handle only left/right/del/bspace keys.
			if ( !keystrokes[ keystroke ] )
				return;

			var sel = editor.getSelection(),
				ranges = sel.getRanges(),
				range = ranges[ 0 ];

			// Handle only single range and it has to be collapsed.
			if ( ranges.length != 1 || !range.collapsed )
				return;

			var next = range[ keystroke < 38 ? 'getPreviousEditableNode' : 'getNextEditableNode' ]();

			if ( next && next.type == CKEDITOR.NODE_ELEMENT && next.getAttribute( 'contenteditable' ) == 'false' ) {
				editor.getSelection().fake( next );
				evt.data.preventDefault();
				evt.cancel();
			}
		};
	}

	// Setup all editor instances for the necessary selection hooks.
	CKEDITOR.on( 'instanceCreated', function( ev ) {
		var editor = ev.editor;

		/**
		 * @event selectionChange
		 *
		 * @member CKEDITOR.editor
 		 * @param {CKEDITOR.editor} editor This editor instance.
 		 * @param data
 		 * @param {CKEDITOR.dom.selection} data.selection
 		 * @param {CKEDITOR.dom.elementPath} data.path
		 */
		// TODO uncomment this after finishing works or just remove...
		// editor.define( 'selectionChange', { errorProof:1 } );

		editor.on( 'contentDom', function() {
			var doc = editor.document,
				outerDoc = CKEDITOR.document,
				editable = editor.editable(),
				body = doc.getBody(),
				html = doc.getDocumentElement();

			var isInline = editable.isInline();

			var restoreSel,
				lastSel;

			// Give the editable an initial selection on first focus,
			// put selection at a consistent position at the start
			// of the contents. (#9507)
			if ( CKEDITOR.env.gecko ) {
				editable.attachListener( editable, 'focus', function( evt ) {
					evt.removeListener();

					if ( restoreSel !== 0 ) {
						var nativ = editor.getSelection().getNative();
						// Do it only if the native selection is at an unwanted
						// place (at the very start of the editable). #10119
						if ( nativ && nativ.isCollapsed && nativ.anchorNode == editable.$ ) {
							var rng = editor.createRange();
							rng.moveToElementEditStart( editable );
							rng.select();
						}
					}
				}, null, null, -2 );
			}

			// Plays the magic here to restore/save dom selection on editable focus/blur.
			editable.attachListener( editable, CKEDITOR.env.webkit ? 'DOMFocusIn' : 'focus', function() {
				// On Webkit we use DOMFocusIn which is fired more often than focus - e.g. when moving from main editable
				// to nested editable (or the opposite). Unlock selection all, but restore only when it was locked
				// for the same active element, what will e.g. mean restoring after displaying dialog.
				if ( restoreSel && CKEDITOR.env.webkit )
					restoreSel = editor._.previousActive && editor._.previousActive.equals( doc.getActive() );

				editor.unlockSelection( restoreSel );
				restoreSel = 0;
			}, null, null, -1 );

			// Disable selection restoring when clicking in.
			editable.attachListener( editable, 'mousedown', function() {
				restoreSel = 0;
			});

			// Browsers could loose the selection once the editable lost focus,
			// in such case we need to reproduce it by saving a locked selection
			// and restoring it upon focus gain.
			if ( CKEDITOR.env.ie || CKEDITOR.env.opera || isInline ) {
				// Save a cloned version of current selection.
				function saveSel() {
					lastSel = new CKEDITOR.dom.selection( editor.getSelection() );
					lastSel.lock();
				}

				// For old IEs, we can retrieve the last correct DOM selection upon the "beforedeactivate" event.
				// For the rest, a more frequent check is required for each selection change made.
				if ( isMSSelection )
					editable.attachListener( editable, 'beforedeactivate', saveSel, null, null, -1 );
				else
					editable.attachListener( editor, 'selectionCheck', saveSel, null, null, -1 );

				// Lock the selection and mark it to be restored.
				// On Webkit we use DOMFocusOut which is fired more often than blur. I.e. it will also be
				// fired when nested editable is blurred.
				editable.attachListener( editable, CKEDITOR.env.webkit ? 'DOMFocusOut' : 'blur', function() {
					editor.lockSelection( lastSel );
					restoreSel = 1;
				}, null, null, -1 );

				// Disable selection restoring when clicking in.
				editable.attachListener( editable, 'mousedown', function() {
					restoreSel = 0;
				});
			}

			// The following selection related fixes applies to only framed editable.
			if ( CKEDITOR.env.ie && !isInline ) {
				var scroll;
				editable.attachListener( editable, 'mousedown', function( evt ) {
					// IE scrolls document to top on right mousedown
					// when editor has no focus, remember this scroll
					// position and revert it before context menu opens. (#5778)
					if ( evt.data.$.button == 2 ) {
						var sel = editor.document.$.selection;
						if ( sel.type == 'None' )
							scroll = editor.window.getScrollPosition();
					}
				});

				editable.attachListener( editable, 'mouseup', function( evt ) {
					// Restore recorded scroll position when needed on right mouseup.
					if ( evt.data.$.button == 2 && scroll ) {
						editor.document.$.documentElement.scrollLeft = scroll.x;
						editor.document.$.documentElement.scrollTop = scroll.y;
					}
					scroll = null;
				});

				// When content doc is in standards mode, IE doesn't focus the editor when
				// clicking at the region below body (on html element) content, we emulate
				// the normal behavior on old IEs. (#1659, #7932)
				if ( doc.$.compatMode != 'BackCompat' ) {
					if ( CKEDITOR.env.ie7Compat || CKEDITOR.env.ie6Compat ) {
						function moveRangeToPoint( range, x, y ) {
							// Error prune in IE7. (#9034, #9110)
							try { range.moveToPoint( x, y ); } catch ( e ) {}
						}

						html.on( 'mousedown', function( evt ) {
							evt = evt.data;

							// Expand the text range along with mouse move.
							function onHover( evt ) {
								evt = evt.data.$;
								if ( textRng ) {
									// Read the current cursor.
									var rngEnd = body.$.createTextRange();

									moveRangeToPoint( rngEnd, evt.x, evt.y );

									// Handle drag directions.
									textRng.setEndPoint(
										startRng.compareEndPoints( 'StartToStart', rngEnd ) < 0 ?
										'EndToEnd' : 'StartToStart', rngEnd );

									// Update selection with new range.
									textRng.select();
								}
							}

							function removeListeners() {
								outerDoc.removeListener( 'mouseup', onSelectEnd );
								html.removeListener( 'mouseup', onSelectEnd );
							}

							function onSelectEnd() {

								html.removeListener( 'mousemove', onHover );
								removeListeners();

								// Make it in effect on mouse up. (#9022)
								textRng.select();
							}


							// We're sure that the click happens at the region
							// below body, but not on scrollbar.
							if ( evt.getTarget().is( 'html' ) &&
									 evt.$.y < html.$.clientHeight &&
									 evt.$.x < html.$.clientWidth ) {
								// Start to build the text range.
								var textRng = body.$.createTextRange();
								moveRangeToPoint( textRng, evt.$.x, evt.$.y );

								// Records the dragging start of the above text range.
								var startRng = textRng.duplicate();

								html.on( 'mousemove', onHover );
								outerDoc.on( 'mouseup', onSelectEnd );
								html.on( 'mouseup', onSelectEnd );
							}
						});
					}

					// It's much simpler for IE8+, we just need to reselect the reported range.
					if ( CKEDITOR.env.version > 7 ) {
						html.on( 'mousedown', function( evt ) {
							if ( evt.data.getTarget().is( 'html' ) ) {
								// Limit the text selection mouse move inside of editable. (#9715)
								outerDoc.on( 'mouseup', onSelectEnd );
								html.on( 'mouseup', onSelectEnd );
							}

						});

						function removeListeners() {
							outerDoc.removeListener( 'mouseup', onSelectEnd );
							html.removeListener( 'mouseup', onSelectEnd );
						}

						function onSelectEnd() {
							removeListeners();

							// The event is not fired when clicking on the scrollbars,
							// so we can safely check the following to understand
							// whether the empty space following <body> has been clicked.
								var sel = CKEDITOR.document.$.selection,
									range = sel.createRange();
								// The selection range is reported on host, but actually it should applies to the content doc.
								if ( sel.type != 'None' && range.parentElement().ownerDocument == doc.$ )
									range.select();
						}
					}
				}
			}

			// We check the selection change:
			// 1. Upon "selectionchange" event from the editable element. (which might be faked event fired by our code)
			// 2. After the accomplish of keyboard and mouse events.
			editable.attachListener( editable, 'selectionchange', checkSelectionChange, editor );
			editable.attachListener( editable, 'keyup', checkSelectionChangeTimeout, editor );
			// Always fire the selection change on focus gain.
			// On Webkit do this on DOMFocusIn, because the selection is unlocked on it too and
			// we need synchronization between those listeners to not lost cached editor._.previousActive property
			// (which is updated on selectionCheck).
			editable.attachListener( editable, CKEDITOR.env.webkit ? 'DOMFocusIn' : 'focus', function() {
				editor.forceNextSelectionCheck();
				editor.selectionChange( 1 );
			});

			// #9699: On Webkit&Gecko in inline editor and on Opera in framed editor we have to check selection
			// when it was changed by dragging and releasing mouse button outside editable. Dragging (mousedown)
			// has to be initialized in editable, but for mouseup we listen on document element.
			// On Opera, listening on document element, helps even if mouse button is released outside iframe.
			if ( isInline ? ( CKEDITOR.env.webkit || CKEDITOR.env.gecko ) : CKEDITOR.env.opera ) {
				var mouseDown;
				editable.attachListener( editable, 'mousedown', function() {
					mouseDown = 1;
				});
				editable.attachListener( doc.getDocumentElement(), 'mouseup', function() {
					if ( mouseDown )
						checkSelectionChangeTimeout.call( editor );
					mouseDown = 0;
				});
			}
			// In all other cases listen on simple mouseup over editable, as we did before #9699.
			//
			// Use document instead of editable in non-IEs for observing mouseup
			// since editable won't fire the event if selection process started within iframe and ended out
			// of the editor (#9851).
			else
				editable.attachListener( CKEDITOR.env.ie ? editable : doc.getDocumentElement(), 'mouseup', checkSelectionChangeTimeout, editor );

			if ( CKEDITOR.env.webkit ) {
				// Before keystroke is handled by editor, check to remove the filling char.
				editable.attachListener( doc, 'keydown', function( evt ) {
					var key = evt.data.getKey();
					// Remove the filling char before some keys get
					// executed, so they'll not get blocked by it.
					switch ( key ) {
						case 13: // ENTER
						case 33: // PAGEUP
						case 34: // PAGEDOWN
						case 35: // HOME
						case 36: // END
						case 37: // LEFT-ARROW
						case 39: // RIGHT-ARROW
						case 8: // BACKSPACE
						case 45: // INS
						case 46: // DEl
							removeFillingChar( editable );
					}

				}, null, null, -1 );
			}

			// Automatically select non-editable element when navigating into
			// it by left/right or backspace/del keys.
			editable.attachListener( editable, 'keydown', getOnKeyDownListener( editor ), null, null, -1 );
		});

		// Clear the cached range path before unload. (#7174)
		editor.on( 'contentDomUnload', editor.forceNextSelectionCheck, editor );
		// Check selection change on data reload.
		editor.on( 'dataReady', function() {
			// Clean up fake selection after setting data.
			delete editor._.fakeSelection;
			delete editor._.hiddenSelectionContainer;

			editor.selectionChange( 1 );
		} );
		// When loaded data are ready check whether hidden selection container was not loaded.
		editor.on( 'loadSnapshot', function() {
			// TODO replace with el.find() which will be introduced in #9764,
			// because it may happen that hidden sel container won't be the last element.
			var el = editor.editable().getLast( function( node ) {
				return node.type == CKEDITOR.NODE_ELEMENT;
			} );

			if ( el && el.hasAttribute( 'data-cke-hidden-sel' ) )
				el.remove();
		}, null, null, 100 );

		function clearSelection() {
			var sel = editor.getSelection();
			sel && sel.removeAllRanges();
		}

		// Clear dom selection before editable destroying to fix some browser
		// craziness.

		// IE9 might cease to work if there's an object selection inside the iframe (#7639).
		CKEDITOR.env.ie9Compat && editor.on( 'beforeDestroy', clearSelection, null, null, 9 );
		// Webkit's selection will mess up after the data loading.
		CKEDITOR.env.webkit && editor.on( 'setData', clearSelection );

		// Invalidate locked selection when unloading DOM (e.g. after setData). (#9521)
		editor.on( 'contentDomUnload', function() {
			editor.unlockSelection();
		});

		editor.on( 'key', function( evt ) {
			if ( editor.mode != 'wysiwyg' )
				return;

			var sel = editor.getSelection();
			if ( !sel.isFake )
				return;

			var handler = fakeSelectionDefaultKeystrokeHandlers[ evt.data.keyCode ];
			if ( handler )
				return handler( { editor: editor, selected: sel.getSelectedElement(), selection: sel, keyEvent: evt } );
		} );
	});

	CKEDITOR.on( 'instanceReady', function( evt ) {
		var editor = evt.editor;

		// On WebKit only, we need a special "filling" char on some situations
		// (#1272). Here we set the events that should invalidate that char.
		if ( CKEDITOR.env.webkit ) {
			editor.on( 'selectionChange', function() {
				checkFillingChar( editor.editable() );
			}, null, null, -1 );
			editor.on( 'beforeSetMode', function() {
				removeFillingChar( editor.editable() );
			}, null, null, -1 );

			var fillingCharBefore, resetSelection;

			function beforeData() {
				var editable = editor.editable();
				if ( !editable )
					return;

				var fillingChar = getFillingChar( editable );

				if ( fillingChar ) {
					// If cursor is right blinking by side of the filler node, save it for restoring,
					// as the following text substitution will blind it. (#7437)
					var sel = editor.document.$.defaultView.getSelection();
					if ( sel.type == 'Caret' && sel.anchorNode == fillingChar.$ )
						resetSelection = 1;

					fillingCharBefore = fillingChar.getText();
					fillingChar.setText( replaceFillingChar( fillingCharBefore ) );
				}
			}

			function afterData() {
				var editable = editor.editable();
				if ( !editable )
					return;

				var fillingChar = getFillingChar( editable );

				if ( fillingChar ) {
					fillingChar.setText( fillingCharBefore );

					if ( resetSelection ) {
						editor.document.$.defaultView.getSelection().setPosition( fillingChar.$, fillingChar.getLength() );
						resetSelection = 0;
					}
				}
			}

			editor.on( 'beforeUndoImage', beforeData );
			editor.on( 'afterUndoImage', afterData );
			editor.on( 'beforeGetData', beforeData, null, null, 0 );
			editor.on( 'getData', afterData );
		}
	});

	/**
	 * Check the selection change in editor and potentially fires
	 * the {@link CKEDITOR.editor#event-selectionChange} event.
	 *
	 * @method
	 * @member CKEDITOR.editor
	 * @param {Boolean} [checkNow=false] Force the check to happen immediately
	 * instead of coming with a timeout delay (default).
	 */
	CKEDITOR.editor.prototype.selectionChange = function( checkNow ) {
		( checkNow ? checkSelectionChange : checkSelectionChangeTimeout ).call( this );
	};

	/**
	 * Retrieve the editor selection in scope of editable element.
	 *
	 * **Note:** Since the native browser selection provides only one single
	 * selection at a time per document, so if editor's editable element has lost focus,
	 * this method will return a null value unless the {@link CKEDITOR.editor#lockSelection}
	 * has been called beforehand so the saved selection is retrieved.
	 *
	 *		var selection = CKEDITOR.instances.editor1.getSelection();
	 *		alert( selection.getType() );
	 *
	 * @method
	 * @member CKEDITOR.editor
	 * @param {Boolean} forceRealSelection Return real selection, instead of saved or fake one.
	 * @returns {CKEDITOR.dom.selection} A selection object or null if not available for the moment.
	 */
	CKEDITOR.editor.prototype.getSelection = function( forceRealSelection ) {

		// Check if there exists a locked or fake selection.
		if ( ( this._.savedSelection || this._.fakeSelection ) && !forceRealSelection )
			return this._.savedSelection || this._.fakeSelection;

		// Editable element might be absent or editor might not be in a wysiwyg mode.
		var editable = this.editable();
		return editable && this.mode == 'wysiwyg' ? new CKEDITOR.dom.selection( editable ) : null;
	};

	/**
	 * Locks the selection made in the editor in order to make it possible to
	 * manipulate it without browser interference. A locked selection is
	 * cached and remains unchanged until it is released with the
	 * {@link CKEDITOR.editor#unlockSelection} method.
	 *
	 * @method
	 * @member CKEDITOR.editor
	 * @param {CKEDITOR.dom.selection} [sel] Specify the selection to be locked.
	 * @returns {Boolean} `true` if selection was locked.
	 */
	CKEDITOR.editor.prototype.lockSelection = function( sel ) {
		sel = sel || this.getSelection( 1 );
		if ( sel.getType() != CKEDITOR.SELECTION_NONE ) {
			!sel.isLocked && sel.lock();
			this._.savedSelection = sel;
			return true;
		}
		return false;
	};

	/**
	 * Unlocks the selection made in the editor and locked with the
	 * {@link CKEDITOR.editor#unlockSelection} method. An unlocked selection
	 * is no longer cached and can be changed.
	 *
	 * @method
	 * @member CKEDITOR.editor
	 * @param {Boolean} [restore] If set to `true`, the selection is
	 * restored back to the selection saved earlier by using the
	 * {@link CKEDITOR.dom.selection#lock} method.
	 */
	CKEDITOR.editor.prototype.unlockSelection = function( restore ) {
		var sel = this._.savedSelection;
		if ( sel ) {
			sel.unlock( restore );
			delete this._.savedSelection;
			return true;
		}

		return false;
	};

	/**
	 * @method
	 * @member CKEDITOR.editor
	 * @todo
	 */
	CKEDITOR.editor.prototype.forceNextSelectionCheck = function() {
		delete this._.selectionPreviousPath;
	};

	/**
	 * Gets the current selection in context of the document's body element.
	 *
	 *		var selection = CKEDITOR.instances.editor1.document.getSelection();
	 *		alert( selection.getType() );
	 *
	 * @method
	 * @member CKEDITOR.dom.document
	 * @returns {CKEDITOR.dom.selection} A selection object.
	 */
	CKEDITOR.dom.document.prototype.getSelection = function() {
		return new CKEDITOR.dom.selection( this );
	};

	/**
	 * Select this range as the only one with {@link CKEDITOR.dom.selection#selectRanges}.
	 *
	 * @method
	 * @returns {CKEDITOR.dom.selection}
	 * @member CKEDITOR.dom.range
	 */
	CKEDITOR.dom.range.prototype.select = function() {
		var sel = this.root instanceof CKEDITOR.editable ? this.root.editor.getSelection() : new CKEDITOR.dom.selection( this.root );

		sel.selectRanges( [ this ] );

		return sel;
	};

	/**
	 * No selection.
	 *
	 *		if ( editor.getSelection().getType() == CKEDITOR.SELECTION_NONE )
	 *			alert( 'Nothing is selected' );
	 *
	 * @readonly
	 * @property {Number} [=1]
	 * @member CKEDITOR
	 */
	CKEDITOR.SELECTION_NONE = 1;

	/**
	 * A text or a collapsed selection.
	 *
	 *		if ( editor.getSelection().getType() == CKEDITOR.SELECTION_TEXT )
	 *			alert( 'A text is selected' );
	 *
	 * @readonly
	 * @property {Number} [=2]
	 * @member CKEDITOR
	 */
	CKEDITOR.SELECTION_TEXT = 2;

	/**
	 * Element selection.
	 *
	 *		if ( editor.getSelection().getType() == CKEDITOR.SELECTION_ELEMENT )
	 *			alert( 'An element is selected' );
	 *
	 * @readonly
	 * @property {Number} [=3]
	 * @member CKEDITOR
	 */
	CKEDITOR.SELECTION_ELEMENT = 3;

	var isMSSelection = typeof window.getSelection != 'function',
		nextRev = 1;

	/**
	 * Manipulates the selection within a DOM element. If the current browser selection
	 * spans outside of the element, an empty selection object is returned.
	 *
	 * Despite the fact that selection's constructor allows to create selection instances,
	 * usually it's better to get selection from the editor instance:
	 *
	 *		var sel = editor.getSelection();
	 *
	 * See {@link CKEDITOR.editor#getSelection}.
	 *
	 * @class
	 * @constructor Creates a selection class instance.
	 *
	 *		// Selection scoped in document.
	 *		var sel = new CKEDITOR.dom.selection( CKEDITOR.document );
	 *
	 *		// Selection scoped in element with 'editable' id.
	 *		var sel = new CKEDITOR.dom.selection( CKEDITOR.document.getById( 'editable' ) );
	 *
	 *		// Cloning selection.
	 *		var clone = new CKEDITOR.dom.selection( sel );
	 *
	 * @param {CKEDITOR.dom.document/CKEDITOR.dom.element/CKEDITOR.dom.selection} target
	 * The DOM document/element that the DOM selection is restrained to. Only selection which spans
	 * within the target element is considered as valid.
	 *
	 * If {@link CKEDITOR.dom.selection} is passed, then its clone will be created.
	 */
	CKEDITOR.dom.selection = function( target ) {
		// Target is a selection - clone it.
		if ( target instanceof CKEDITOR.dom.selection ) {
			var selection = target;
			target = target.root;
		}

		var isElement = target instanceof CKEDITOR.dom.element,
			root;

		this.rev = selection ? selection.rev : nextRev++;
		this.document = target instanceof CKEDITOR.dom.document ? target : target.getDocument();
		this.root = root = isElement ? target : this.document.getBody();
		this.isLocked = 0;
		this._ = {
			cache: {}
		};

		// Clone selection.
		if ( selection ) {
			CKEDITOR.tools.extend( this._.cache, selection._.cache );
			this.isFake = selection.isFake;
			this.isLocked = selection.isLocked;
			return this;
		}

		// On WebKit, it may happen that we've already have focus
		// on the editable element while still having no selection
		// available. We normalize it here by replicating the
		// behavior of other browsers.
		//
		// Webkit's condition covers also the case when editable hasn't been focused
		// at all. Thanks to this hack Webkit always has selection in the right place.
		//
		// On FF and IE we only fix the first case, when editable was activated
		// but the selection is broken - usually this happens after setData if editor was focused.

		var sel = isMSSelection ? this.document.$.selection : this.document.getWindow().$.getSelection();

		if ( CKEDITOR.env.webkit ) {
			if ( sel.type == 'None' && this.document.getActive().equals( root ) || sel.type == 'Caret' && sel.anchorNode.nodeType == CKEDITOR.NODE_DOCUMENT )
				fixInitialSelection( root, sel );
		}
		else if ( CKEDITOR.env.gecko ) {
			if ( sel && this.document.getActive().equals( root ) &&
				sel.anchorNode && sel.anchorNode.nodeType == CKEDITOR.NODE_DOCUMENT )
				fixInitialSelection( root, sel, true );
		}
		else if ( CKEDITOR.env.ie ) {
			var active;

			// IE8,9 throw unspecified error when trying to access document.$.activeElement.
			try {
				active = this.document.getActive();
			} catch ( e ) {}

			// IEs 9+.
			if ( !isMSSelection ) {
				var anchorNode = sel && sel.anchorNode;

				if ( anchorNode )
					anchorNode = new CKEDITOR.dom.node( anchorNode );

				if ( active && active.equals( this.document.getDocumentElement() ) &&
					anchorNode && ( root.equals( anchorNode ) || root.contains( anchorNode ) ) )
					fixInitialSelection( root, null, true );
			}
			// IEs 7&8.
			else if ( sel.type == 'None' && active && active.equals( this.document.getDocumentElement() ) )
				fixInitialSelection( root, null, true );
		}

		// Check whether browser focus is really inside of the editable element.

		var nativeSel = this.getNative(),
			rangeParent,
			range;

		if ( nativeSel ) {
			if ( nativeSel.getRangeAt ) {
				range = nativeSel.rangeCount && nativeSel.getRangeAt( 0 );
				rangeParent = range && new CKEDITOR.dom.node( range.commonAncestorContainer );
			}
			// For old IEs.
			else {
				// Sometimes, mostly when selection is close to the table or hr,
				// IE throws "Unspecified error".
				try {
					range = nativeSel.createRange();
				} catch ( err ) {}
				rangeParent = range && CKEDITOR.dom.element.get( range.item && range.item( 0 ) || range.parentElement() );
			}
		}

		// Selection out of concerned range, empty the selection.
		// TODO check whether this condition cannot be reverted to its old
		// form (commented out) after we closed #10438.
		//if ( !( rangeParent && ( root.equals( rangeParent ) || root.contains( rangeParent ) ) ) ) {
		if ( !(
			rangeParent &&
			( rangeParent.type == CKEDITOR.NODE_ELEMENT || rangeParent.type == CKEDITOR.NODE_TEXT ) &&
			( this.root.equals( rangeParent ) || this.root.contains( rangeParent ) )
		) ) {

			this._.cache.type = CKEDITOR.SELECTION_NONE;
			this._.cache.startElement = null;
			this._.cache.selectedElement = null;
			this._.cache.selectedText = '';
			this._.cache.ranges = new CKEDITOR.dom.rangeList();
		}

		return this;
	};

	var styleObjectElements = { img:1,hr:1,li:1,table:1,tr:1,td:1,th:1,embed:1,object:1,ol:1,ul:1,a:1,input:1,form:1,select:1,textarea:1,button:1,fieldset:1,thead:1,tfoot:1 };

	CKEDITOR.dom.selection.prototype = {
		/**
		 * Gets the native selection object from the browser.
		 *
		 *		var selection = editor.getSelection().getNative();
		 *
		 * @returns {Object} The native browser selection object.
		 */
		getNative: function() {
			if ( this._.cache.nativeSel !== undefined )
				return this._.cache.nativeSel;

			return ( this._.cache.nativeSel = isMSSelection ? this.document.$.selection : this.document.getWindow().$.getSelection() );
		},

		/**
		 * Gets the type of the current selection. The following values are
		 * available:
		 *
		 * * {@link CKEDITOR#SELECTION_NONE} (1): No selection.
		 * * {@link CKEDITOR#SELECTION_TEXT} (2): A text or a collapsed selection is selected.
		 * * {@link CKEDITOR#SELECTION_ELEMENT} (3): An element is selected.
		 *
		 * Example:
		 *
		 *		if ( editor.getSelection().getType() == CKEDITOR.SELECTION_TEXT )
		 *			alert( 'A text is selected' );
		 *
		 * @method
		 * @returns {Number} One of the following constant values: {@link CKEDITOR#SELECTION_NONE},
		 * {@link CKEDITOR#SELECTION_TEXT} or {@link CKEDITOR#SELECTION_ELEMENT}.
		 */
		getType: isMSSelection ?
		function() {
			var cache = this._.cache;
			if ( cache.type )
				return cache.type;

			var type = CKEDITOR.SELECTION_NONE;

			try {
				var sel = this.getNative(),
					ieType = sel.type;

				if ( ieType == 'Text' )
					type = CKEDITOR.SELECTION_TEXT;

				if ( ieType == 'Control' )
					type = CKEDITOR.SELECTION_ELEMENT;

				// It is possible that we can still get a text range
				// object even when type == 'None' is returned by IE.
				// So we'd better check the object returned by
				// createRange() rather than by looking at the type.
				if ( sel.createRange().parentElement() )
					type = CKEDITOR.SELECTION_TEXT;
			} catch ( e ) {}

			return ( cache.type = type );
		} : function() {
			var cache = this._.cache;
			if ( cache.type )
				return cache.type;

			var type = CKEDITOR.SELECTION_TEXT;

			var sel = this.getNative();

			if ( !( sel && sel.rangeCount ) )
				type = CKEDITOR.SELECTION_NONE;
			else if ( sel.rangeCount == 1 ) {
				// Check if the actual selection is a control (IMG,
				// TABLE, HR, etc...).

				var range = sel.getRangeAt( 0 ),
					startContainer = range.startContainer;

				if ( startContainer == range.endContainer && startContainer.nodeType == 1 && ( range.endOffset - range.startOffset ) == 1 && styleObjectElements[ startContainer.childNodes[ range.startOffset ].nodeName.toLowerCase() ] ) {
					type = CKEDITOR.SELECTION_ELEMENT;
				}
			}

			return ( cache.type = type );
		},

		/**
		 * Retrieves the {@link CKEDITOR.dom.range} instances that represent the current selection.
		 *
		 * Note: Some browsers return multiple ranges even for a continuous selection. Firefox, for example, returns
		 * one range for each table cell when one or more table rows are selected.
		 *
		 *		var ranges = selection.getRanges();
		 *		alert( ranges.length );
		 *
		 * @method
		 * @param {Boolean} [onlyEditables] If set to `true`, this function retrives editable ranges only.
		 * @returns {Array} Range instances that represent the current selection.
		 */
		getRanges: (function() {
			var func = isMSSelection ? ( function() {
				function getNodeIndex( node ) {
					return new CKEDITOR.dom.node( node ).getIndex();
				}

				// Finds the container and offset for a specific boundary
				// of an IE range.
				var getBoundaryInformation = function( range, start ) {
						// Creates a collapsed range at the requested boundary.
						range = range.duplicate();
						range.collapse( start );

						// Gets the element that encloses the range entirely.
						var parent = range.parentElement(),
							doc = parent.ownerDocument;

						// Empty parent element, e.g. <i>^</i>
						if ( !parent.hasChildNodes() )
							return { container: parent, offset: 0 };

						var siblings = parent.children,
							child, sibling,
							testRange = range.duplicate(),
							startIndex = 0,
							endIndex = siblings.length - 1,
							index = -1,
							position, distance, container;

						// Binary search over all element childs to test the range to see whether
						// range is right on the boundary of one element.
						while ( startIndex <= endIndex ) {
							index = Math.floor( ( startIndex + endIndex ) / 2 );
							child = siblings[ index ];
							testRange.moveToElementText( child );
							position = testRange.compareEndPoints( 'StartToStart', range );

							if ( position > 0 )
								endIndex = index - 1;
							else if ( position < 0 )
								startIndex = index + 1;
							else {
								// IE9 report wrong measurement with compareEndPoints when range anchors between two BRs.
								// e.g. <p>text<br />^<br /></p> (#7433)
								if ( CKEDITOR.env.ie9Compat && child.tagName == 'BR' ) {
									// "Fall back" to w3c selection.
									var sel = doc.defaultView.getSelection();
									return {
										container: sel[ start ? 'anchorNode' : 'focusNode' ],
										offset: sel[ start ? 'anchorOffset' : 'focusOffset' ] };
								} else
									return { container: parent, offset: getNodeIndex( child ) };
							}
						}

						// All childs are text nodes,
						// or to the right hand of test range are all text nodes. (#6992)
						if ( index == -1 || index == siblings.length - 1 && position < 0 ) {
							// Adapt test range to embrace the entire parent contents.
							testRange.moveToElementText( parent );
							testRange.setEndPoint( 'StartToStart', range );

							// IE report line break as CRLF with range.text but
							// only LF with textnode.nodeValue, normalize them to avoid
							// breaking character counting logic below. (#3949)
							distance = testRange.text.replace( /(\r\n|\r)/g, '\n' ).length;

							siblings = parent.childNodes;

							// Actual range anchor right beside test range at the boundary of text node.
							if ( !distance ) {
								child = siblings[ siblings.length - 1 ];

								if ( child.nodeType != CKEDITOR.NODE_TEXT )
									return { container: parent, offset: siblings.length };
								else
									return { container: child, offset: child.nodeValue.length };
							}

							// Start the measuring until distance overflows, meanwhile count the text nodes.
							var i = siblings.length;
							while ( distance > 0 && i > 0 ) {
								sibling = siblings[ --i ];
								if ( sibling.nodeType == CKEDITOR.NODE_TEXT ) {
									container = sibling;
									distance -= sibling.nodeValue.length;
								}
							}

							return { container: container, offset: -distance };
						}
						// Test range was one offset beyond OR behind the anchored text node.
						else {
							// Adapt one side of test range to the actual range
							// for measuring the offset between them.
							testRange.collapse( position > 0 ? true : false );
							testRange.setEndPoint( position > 0 ? 'StartToStart' : 'EndToStart', range );

							// IE report line break as CRLF with range.text but
							// only LF with textnode.nodeValue, normalize them to avoid
							// breaking character counting logic below. (#3949)
							distance = testRange.text.replace( /(\r\n|\r)/g, '\n' ).length;

							// Actual range anchor right beside test range at the inner boundary of text node.
							if ( !distance )
								return { container: parent, offset: getNodeIndex( child ) + ( position > 0 ? 0 : 1 ) };

							// Start the measuring until distance overflows, meanwhile count the text nodes.
							while ( distance > 0 ) {
								try {
									sibling = child[ position > 0 ? 'previousSibling' : 'nextSibling' ];
									if ( sibling.nodeType == CKEDITOR.NODE_TEXT ) {
										distance -= sibling.nodeValue.length;
										container = sibling;
									}
									child = sibling;
								}
								// Measurement in IE could be somtimes wrong because of <select> element. (#4611)
								catch ( e ) {
									return { container: parent, offset: getNodeIndex( child ) };
								}
							}

							return { container: container, offset: position > 0 ? -distance : container.nodeValue.length + distance };
						}
					};

				return function() {
					// IE doesn't have range support (in the W3C way), so we
					// need to do some magic to transform selections into
					// CKEDITOR.dom.range instances.

					var sel = this.getNative(),
						nativeRange = sel && sel.createRange(),
						type = this.getType(),
						range;

					if ( !sel )
						return [];

					if ( type == CKEDITOR.SELECTION_TEXT ) {
						range = new CKEDITOR.dom.range( this.root );

						var boundaryInfo = getBoundaryInformation( nativeRange, true );
						range.setStart( new CKEDITOR.dom.node( boundaryInfo.container ), boundaryInfo.offset );

						boundaryInfo = getBoundaryInformation( nativeRange );
						range.setEnd( new CKEDITOR.dom.node( boundaryInfo.container ), boundaryInfo.offset );

						// Correct an invalid IE range case on empty list item. (#5850)
						if ( range.endContainer.getPosition( range.startContainer ) & CKEDITOR.POSITION_PRECEDING && range.endOffset <= range.startContainer.getIndex() ) {
							range.collapse();
						}

						return [ range ];
					} else if ( type == CKEDITOR.SELECTION_ELEMENT ) {
						var retval = [];

						for ( var i = 0; i < nativeRange.length; i++ ) {
							var element = nativeRange.item( i ),
								parentElement = element.parentNode,
								j = 0;

							range = new CKEDITOR.dom.range( this.root );

							for ( ; j < parentElement.childNodes.length && parentElement.childNodes[ j ] != element; j++ ) {
								/*jsl:pass*/
							}

							range.setStart( new CKEDITOR.dom.node( parentElement ), j );
							range.setEnd( new CKEDITOR.dom.node( parentElement ), j + 1 );
							retval.push( range );
						}

						return retval;
					}

					return [];
				};
			})() : function() {

					// On browsers implementing the W3C range, we simply
					// tranform the native ranges in CKEDITOR.dom.range
					// instances.

					var ranges = [],
						range,
						sel = this.getNative();

					if ( !sel )
						return ranges;

					for ( var i = 0; i < sel.rangeCount; i++ ) {
						var nativeRange = sel.getRangeAt( i );

						range = new CKEDITOR.dom.range( this.root );

						range.setStart( new CKEDITOR.dom.node( nativeRange.startContainer ), nativeRange.startOffset );
						range.setEnd( new CKEDITOR.dom.node( nativeRange.endContainer ), nativeRange.endOffset );
						ranges.push( range );
					}
					return ranges;
				};

			return function( onlyEditables ) {
				var cache = this._.cache;
				if ( cache.ranges && !onlyEditables )
					return cache.ranges;
				else if ( !cache.ranges )
					cache.ranges = new CKEDITOR.dom.rangeList( func.call( this ) );

				// Split range into multiple by read-only nodes.
				if ( onlyEditables ) {
					var ranges = cache.ranges;
					for ( var i = 0; i < ranges.length; i++ ) {
						var range = ranges[ i ];

						// Drop range spans inside one ready-only node.
						var parent = range.getCommonAncestor();
						if ( parent.isReadOnly() )
							ranges.splice( i, 1 );

						if ( range.collapsed )
							continue;

						// Range may start inside a non-editable element,
						// replace the range start after it.
						if ( range.startContainer.isReadOnly() ) {
							var current = range.startContainer,
								isElement;

							while ( current ) {
								isElement = current.type == CKEDITOR.NODE_ELEMENT;

								if ( ( isElement && current.is( 'body' ) ) || !current.isReadOnly() )
									break;

								if ( isElement && current.getAttribute( 'contentEditable' ) == 'false' )
									range.setStartAfter( current );

								current = current.getParent();
							}
						}

						var startContainer = range.startContainer,
							endContainer = range.endContainer,
							startOffset = range.startOffset,
							endOffset = range.endOffset,
							walkerRange = range.clone();

						// Enlarge range start/end with text node to avoid walker
						// being DOM destructive, it doesn't interfere our checking
						// of elements below as well.
						if ( startContainer && startContainer.type == CKEDITOR.NODE_TEXT ) {
							if ( startOffset >= startContainer.getLength() )
								walkerRange.setStartAfter( startContainer );
							else
								walkerRange.setStartBefore( startContainer );
						}

						if ( endContainer && endContainer.type == CKEDITOR.NODE_TEXT ) {
							if ( !endOffset )
								walkerRange.setEndBefore( endContainer );
							else
								walkerRange.setEndAfter( endContainer );
						}

						// Looking for non-editable element inside the range.
						var walker = new CKEDITOR.dom.walker( walkerRange );
						walker.evaluator = function( node ) {
							if ( node.type == CKEDITOR.NODE_ELEMENT && node.isReadOnly() ) {
								var newRange = range.clone();
								range.setEndBefore( node );

								// Drop collapsed range around read-only elements,
								// it make sure the range list empty when selecting
								// only non-editable elements.
								if ( range.collapsed )
									ranges.splice( i--, 1 );

								// Avoid creating invalid range.
								if ( !( node.getPosition( walkerRange.endContainer ) & CKEDITOR.POSITION_CONTAINS ) ) {
									newRange.setStartAfter( node );
									if ( !newRange.collapsed )
										ranges.splice( i + 1, 0, newRange );
								}

								return true;
							}

							return false;
						};

						walker.next();
					}
				}

				return cache.ranges;
			};
		})(),

		/**
		 * Gets the DOM element in which the selection starts.
		 *
		 *		var element = editor.getSelection().getStartElement();
		 *		alert( element.getName() );
		 *
		 * @returns {CKEDITOR.dom.element} The element at the beginning of the selection.
		 */
		getStartElement: function() {
			var cache = this._.cache;
			if ( cache.startElement !== undefined )
				return cache.startElement;

			var node;

			switch ( this.getType() ) {
				case CKEDITOR.SELECTION_ELEMENT:
					return this.getSelectedElement();

				case CKEDITOR.SELECTION_TEXT:

					var range = this.getRanges()[ 0 ];

					if ( range ) {
						if ( !range.collapsed ) {
							range.optimize();

							// Decrease the range content to exclude particial
							// selected node on the start which doesn't have
							// visual impact. ( #3231 )
							while ( 1 ) {
								var startContainer = range.startContainer,
									startOffset = range.startOffset;
								// Limit the fix only to non-block elements.(#3950)
								if ( startOffset == ( startContainer.getChildCount ? startContainer.getChildCount() : startContainer.getLength() ) && !startContainer.isBlockBoundary() )
									range.setStartAfter( startContainer );
								else
									break;
							}

							node = range.startContainer;

							if ( node.type != CKEDITOR.NODE_ELEMENT )
								return node.getParent();

							node = node.getChild( range.startOffset );

							if ( !node || node.type != CKEDITOR.NODE_ELEMENT )
								node = range.startContainer;
							else {
								var child = node.getFirst();
								while ( child && child.type == CKEDITOR.NODE_ELEMENT ) {
									node = child;
									child = child.getFirst();
								}
							}
						} else {
							node = range.startContainer;
							if ( node.type != CKEDITOR.NODE_ELEMENT )
								node = node.getParent();
						}

						node = node.$;
					}
			}

			return cache.startElement = ( node ? new CKEDITOR.dom.element( node ) : null );
		},

		/**
		 * Gets the currently selected element.
		 *
		 *		var element = editor.getSelection().getSelectedElement();
		 *		alert( element.getName() );
		 *
		 * @returns {CKEDITOR.dom.element} The selected element. Null if no
		 * selection is available or the selection type is not {@link CKEDITOR#SELECTION_ELEMENT}.
		 */
		getSelectedElement: function() {
			var cache = this._.cache;
			if ( cache.selectedElement !== undefined )
				return cache.selectedElement;

			var self = this;

			var node = CKEDITOR.tools.tryThese(
				// Is it native IE control type selection?
				function() {
					return self.getNative().createRange().item( 0 );
				},
				// Figure it out by checking if there's a single enclosed
				// node of the range.
				function() {
					var range = self.getRanges()[ 0 ].clone(),
						enclosed, selected;

					// Check first any enclosed element, e.g. <ul>[<li><a href="#">item</a></li>]</ul>
					for ( var i = 2; i && !( ( enclosed = range.getEnclosedNode() ) && ( enclosed.type == CKEDITOR.NODE_ELEMENT ) && styleObjectElements[ enclosed.getName() ] && ( selected = enclosed ) ); i-- ) {
						// Then check any deep wrapped element, e.g. [<b><i><img /></i></b>]
						range.shrink( CKEDITOR.SHRINK_ELEMENT );
					}

					return selected && selected.$;
				}
			);

			return cache.selectedElement = ( node ? new CKEDITOR.dom.element( node ) : null );
		},

		/**
		 * Retrieves the text contained within the range. An empty string is returned for non-text selection.
		 *
		 *		var text = editor.getSelection().getSelectedText();
		 *		alert( text );
		 *
		 * @since 3.6.1
		 * @returns {String} A string of text within the current selection.
		 */
		getSelectedText: function() {
			var cache = this._.cache;
			if ( cache.selectedText !== undefined )
				return cache.selectedText;

			var nativeSel = this.getNative(),
				text = isMSSelection ? nativeSel.type == 'Control' ? '' : nativeSel.createRange().text : nativeSel.toString();

			return ( cache.selectedText = text );
		},

		/**
		 * Locks the selection made in the editor in order to make it possible to
		 * manipulate it without browser interference. A locked selection is
		 * cached and remains unchanged until it is released with the {@link #unlock} method.
		 *
		 *		editor.getSelection().lock();
		 */
		lock: function() {
			// Call all cacheable function.
			this.getRanges();
			this.getStartElement();
			this.getSelectedElement();
			this.getSelectedText();

			// The native selection is not available when locked.
			this._.cache.nativeSel = null;

			this.isLocked = 1;
		},

		/**
		 * @todo
		 */
		unlock: function( restore ) {
			if ( !this.isLocked )
				return;

			if ( restore ) {
				var selectedElement = this.getSelectedElement(),
					ranges = !selectedElement && this.getRanges(),
					faked = this.isFake;
			}

			this.isLocked = 0;
			this.reset();

			if ( restore ) {
				// Saved selection may be outdated (e.g. anchored in offline nodes).
				// Avoid getting broken by such.
				var common = selectedElement || ranges[ 0 ] && ranges[ 0 ].getCommonAncestor();
				if ( !( common && common.getAscendant( 'body', 1 ) ) )
					return;

				if ( faked )
					this.fake( selectedElement );
				else if ( selectedElement )
					this.selectElement( selectedElement );
				else
					this.selectRanges( ranges );
			}
		},

		/**
		 * Clears the selection cache.
		 *
		 *		editor.getSelection().reset();
		 */
		reset: function() {
			this._.cache = {};
			this.isFake = 0;

			var editor = this.root.editor,
				listener;

			// Invalidate any fake selection available in the editor.
			if ( editor && editor._.fakeSelection ) {
				// Test whether this selection is the one that was
				// faked or its clone.
				if ( this.rev == editor._.fakeSelection.rev ) {
					delete editor._.fakeSelection;

					removeHiddenSelectionContainer( editor );
				}
				// TODO after #9786 use commented out lines instead of console.log.
				else
					window.console && console.log( 'Wrong selection instance resets fake selection.' );
				// else // %REMOVE_LINE%
				//	CKEDITOR.debug.error( 'Wrong selection instance resets fake selection.', CKEDITOR.DEBUG_CRITICAL ); // %REMOVE_LINE%
			}

			this.rev = nextRev++;
		},

		/**
		 * Makes the current selection of type {@link CKEDITOR#SELECTION_ELEMENT} by enclosing the specified element.
		 *
		 *		var element = editor.document.getById( 'sampleElement' );
		 *		editor.getSelection().selectElement( element );
		 *
		 * @param {CKEDITOR.dom.element} element The element to enclose in the selection.
		 */
		selectElement: function( element ) {
			var range = new CKEDITOR.dom.range( this.root );
			range.setStartBefore( element );
			range.setEndAfter( element );
			this.selectRanges( [ range ] );
		},

		/**
		 * Clears the original selection and adds the specified ranges to the document selection.
		 *
		 * 		// Move selection to the end of the editable element.
		 *		var range = editor.createRange();
		 *		range.moveToPosition( range.root, CKEDITOR.POSITION_BEFORE_END );
		 *		editor.getSelection().selectRanges( [ ranges ] );
		 *
		 * @param {Array} ranges An array of {@link CKEDITOR.dom.range} instances
		 * representing ranges to be added to the document.
		 */
		selectRanges: function( ranges ) {
			this.reset();

			if ( !ranges.length )
				return;

			// Refresh the locked selection.
			if ( this.isLocked ) {
				// making a new DOM selection will force the focus on editable in certain situation,
				// we have to save the currently focused element for later recovery.
				var focused = CKEDITOR.document.getActive();
				this.unlock();
				this.selectRanges( ranges );
				this.lock();
				// Return to the previously focused element.
				!focused.equals( this.root ) && focused.focus();
				return;
			}

			// Handle special case - automatic fake selection on non-editable elements.
			var enclosedNode;
			if (
				ranges.length == 1 && !ranges[ 0 ].collapsed &&
				( enclosedNode = ranges[ 0 ].getEnclosedNode() ) &&
				enclosedNode.type == CKEDITOR.NODE_ELEMENT && enclosedNode.getAttribute( 'contenteditable' ) == 'false'
			) {
				this.fake( enclosedNode );
				return;
			}

			if ( isMSSelection ) {
				var notWhitespaces = CKEDITOR.dom.walker.whitespaces( true ),
					fillerTextRegex = /\ufeff|\u00a0/,
					nonCells = { table:1,tbody:1,tr:1 };

				if ( ranges.length > 1 ) {
					// IE doesn't accept multiple ranges selection, so we join all into one.
					var last = ranges[ ranges.length - 1 ];
					ranges[ 0 ].setEnd( last.endContainer, last.endOffset );
				}

				var range = ranges[ 0 ];
				var collapsed = range.collapsed,
					isStartMarkerAlone, dummySpan, ieRange;

				// Try to make a object selection, be careful with selecting phase element in IE
				// will breaks the selection in non-framed environment.
				var selected = range.getEnclosedNode();
				if ( selected && selected.type == CKEDITOR.NODE_ELEMENT && selected.getName() in styleObjectElements && !( selected.is( 'a' ) && selected.getText() ) ) {
					try {
						ieRange = selected.$.createControlRange();
						ieRange.addElement( selected.$ );
						ieRange.select();
						return;
					} catch ( er ) {}
				}

				// IE doesn't support selecting the entire table row/cell, move the selection into cells, e.g.
				// <table><tbody><tr>[<td>cell</b></td>... => <table><tbody><tr><td>[cell</td>...
				if ( range.startContainer.type == CKEDITOR.NODE_ELEMENT && range.startContainer.getName() in nonCells || range.endContainer.type == CKEDITOR.NODE_ELEMENT && range.endContainer.getName() in nonCells ) {
					range.shrink( CKEDITOR.NODE_ELEMENT, true );
				}

				var bookmark = range.createBookmark();

				// Create marker tags for the start and end boundaries.
				var startNode = bookmark.startNode;

				var endNode;
				if ( !collapsed )
					endNode = bookmark.endNode;

				// Create the main range which will be used for the selection.
				ieRange = range.document.$.body.createTextRange();

				// Position the range at the start boundary.
				ieRange.moveToElementText( startNode.$ );
				ieRange.moveStart( 'character', 1 );

				if ( endNode ) {
					// Create a tool range for the end.
					var ieRangeEnd = range.document.$.body.createTextRange();

					// Position the tool range at the end.
					ieRangeEnd.moveToElementText( endNode.$ );

					// Move the end boundary of the main range to match the tool range.
					ieRange.setEndPoint( 'EndToEnd', ieRangeEnd );
					ieRange.moveEnd( 'character', -1 );
				} else {
					// The isStartMarkerAlone logic comes from V2. It guarantees that the lines
					// will expand and that the cursor will be blinking on the right place.
					// Actually, we are using this flag just to avoid using this hack in all
					// situations, but just on those needed.
					var next = startNode.getNext( notWhitespaces );
					var inPre = startNode.hasAscendant( 'pre' );
					isStartMarkerAlone = ( !( next && next.getText && next.getText().match( fillerTextRegex ) ) // already a filler there?
					&& ( inPre || !startNode.hasPrevious() || ( startNode.getPrevious().is && startNode.getPrevious().is( 'br' ) ) ) );

					// Append a temporary <span>&#65279;</span> before the selection.
					// This is needed to avoid IE destroying selections inside empty
					// inline elements, like <b></b> (#253).
					// It is also needed when placing the selection right after an inline
					// element to avoid the selection moving inside of it.
					dummySpan = range.document.createElement( 'span' );
					dummySpan.setHtml( '&#65279;' ); // Zero Width No-Break Space (U+FEFF). See #1359.
					dummySpan.insertBefore( startNode );

					if ( isStartMarkerAlone ) {
						// To expand empty blocks or line spaces after <br>, we need
						// instead to have any char, which will be later deleted using the
						// selection.
						// \ufeff = Zero Width No-Break Space (U+FEFF). (#1359)
						range.document.createText( '\ufeff' ).insertBefore( startNode );
					}
				}

				// Remove the markers (reset the position, because of the changes in the DOM tree).
				range.setStartBefore( startNode );
				startNode.remove();

				if ( collapsed ) {
					if ( isStartMarkerAlone ) {
						// Move the selection start to include the temporary \ufeff.
						ieRange.moveStart( 'character', -1 );

						ieRange.select();

						// Remove our temporary stuff.
						range.document.$.selection.clear();
					} else
						ieRange.select();

					range.moveToPosition( dummySpan, CKEDITOR.POSITION_BEFORE_START );
					dummySpan.remove();
				} else {
					range.setEndBefore( endNode );
					endNode.remove();
					ieRange.select();
				}
			} else {
				var sel = this.getNative();

				// getNative() returns null if iframe is "display:none" in FF. (#6577)
				if ( !sel )
					return;

				// Opera: The above hack work around a *visually wrong* text selection that
				// happens in certain situation. (#6874, #9447)
				if ( CKEDITOR.env.opera ) {
					var nativeRng = this.document.$.createRange();
					nativeRng.selectNodeContents( this.root.$ );
					sel.addRange( nativeRng );
				}

				this.removeAllRanges();

				for ( var i = 0; i < ranges.length; i++ ) {
					// Joining sequential ranges introduced by
					// readonly elements protection.
					if ( i < ranges.length - 1 ) {
						var left = ranges[ i ],
							right = ranges[ i + 1 ],
							between = left.clone();
						between.setStart( left.endContainer, left.endOffset );
						between.setEnd( right.startContainer, right.startOffset );

						// Don't confused by Firefox adjancent multi-ranges
						// introduced by table cells selection.
						if ( !between.collapsed ) {
							between.shrink( CKEDITOR.NODE_ELEMENT, true );
							var ancestor = between.getCommonAncestor(),
								enclosed = between.getEnclosedNode();

							// The following cases has to be considered:
							// 1. <span contenteditable="false">[placeholder]</span>
							// 2. <input contenteditable="false"  type="radio"/> (#6621)
							if ( ancestor.isReadOnly() || enclosed && enclosed.isReadOnly() ) {
								right.setStart( left.startContainer, left.startOffset );
								ranges.splice( i--, 1 );
								continue;
							}
						}
					}

					range = ranges[ i ];

					var nativeRange = this.document.$.createRange();
					var startContainer = range.startContainer;

					// In Opera, we have some cases when a collapsed text selection cursor will be moved out of the
					// anchor node:
					// 1. Inside of any empty inline. (#4657)
					// 2. In adjacent to any inline element.
					if ( CKEDITOR.env.opera && range.collapsed && startContainer.type == CKEDITOR.NODE_ELEMENT ) {

						var leftSib = startContainer.getChild( range.startOffset - 1 ),
							rightSib = startContainer.getChild( range.startOffset );

						if ( !leftSib && !rightSib && startContainer.is( CKEDITOR.dtd.$removeEmpty ) ||
								 leftSib && leftSib.type == CKEDITOR.NODE_ELEMENT ||
								 rightSib && rightSib.type == CKEDITOR.NODE_ELEMENT ) {
							range.insertNode( this.document.createText( '' ) );
							range.collapse( 1 );
						}
					}

					if ( range.collapsed && CKEDITOR.env.webkit && rangeRequiresFix( range ) ) {
						// Append a zero-width space so WebKit will not try to
						// move the selection by itself (#1272).
						var fillingChar = createFillingChar( this.root );
						range.insertNode( fillingChar );

						next = fillingChar.getNext();

						// If the filling char is followed by a <br>, whithout
						// having something before it, it'll not blink.
						// Let's remove it in this case.
						if ( next && !fillingChar.getPrevious() && next.type == CKEDITOR.NODE_ELEMENT && next.getName() == 'br' ) {
							removeFillingChar( this.root );
							range.moveToPosition( next, CKEDITOR.POSITION_BEFORE_START );
						} else
							range.moveToPosition( fillingChar, CKEDITOR.POSITION_AFTER_END );
					}

					nativeRange.setStart( range.startContainer.$, range.startOffset );

					try {
						nativeRange.setEnd( range.endContainer.$, range.endOffset );
					} catch ( e ) {
						// There is a bug in Firefox implementation (it would be too easy
						// otherwise). The new start can't be after the end (W3C says it can).
						// So, let's create a new range and collapse it to the desired point.
						if ( e.toString().indexOf( 'NS_ERROR_ILLEGAL_VALUE' ) >= 0 ) {
							range.collapse( 1 );
							nativeRange.setEnd( range.endContainer.$, range.endOffset );
						} else
							throw e;
					}

					// Select the range.
					sel.addRange( nativeRange );
				}
			}

			this.reset();

			// Fakes the IE DOM event "selectionchange" on editable.
			this.root.fire( 'selectionchange' );
		},

		/**
		 * Makes a "fake selection" of an element.
		 *
		 * A fake selection does not render UI artifacts over the selected
		 * element. Additionally, the browser native selection system is not
		 * aware of the fake selection. In practice, the native selection is
		 * moved to a hidden place where no native selection UI artifacts are
		 * displayed to the user.
		 *
		 * @param {CKEDITOR.dom.element} element The element to be "selected".
		 */
		fake: function( element ) {
			var editor = this.root.editor;

			hideSelection( editor );

			// Set this value after executing hiseSelection, because it may
			// cause reset() which overwrites cache.
			var cache = this._.cache;

			// Caches a range than holds the element.
			var range = new CKEDITOR.dom.range( element.getDocument() );
			range.setStartBefore( element );
			range.setEndAfter( element );
			cache.ranges = new CKEDITOR.dom.rangeList( range );

			// Put this element in the cache.
			cache.selectedElement = cache.startElement = element;
			cache.type = CKEDITOR.SELECTION_ELEMENT;

			// Properties that will not be available when isFake.
			cache.selectedText = cache.nativeSel = null;

			this.isFake = 1;
			this.rev = nextRev++;

			// Save this selection, so it can be returned by editor.getSelection().
			editor._.fakeSelection = this;

			// Fire selectionchange, just like a normal selection.
			this.root.fire( 'selectionchange' );
		},

		/**
		 * Checks whether selection is placed in hidden element.
		 *
		 * This method is to be used to verify whether fake selection
		 * (see {@link #fake}) is still hidden.
		 *
		 * **Note:** this method should be executed on real selection - e.g.:
		 *
		 *		editor.getSelection( true ).isHidden();
		 *
		 * @returns {Boolean}
		 */
		isHidden: function() {
			var el = this.getCommonAncestor();

			if ( el && el.type == CKEDITOR.NODE_TEXT )
				el = el.getParent();

			return !!( el && el.data( 'cke-hidden-sel' ) );
		},

		/**
		 * Creates a bookmark for each range of this selection (from {@link #getRanges})
		 * by calling the {@link CKEDITOR.dom.range#createBookmark} method,
		 * with extra care taken to avoid interference among those ranges. The arguments
		 * received are the same as with the underlying range method.
		 *
		 *		var bookmarks = editor.getSelection().createBookmarks();
		 *
		 * @returns {Array} Array of bookmarks for each range.
		 */
		createBookmarks: function( serializable ) {
			var bookmark = this.getRanges().createBookmarks( serializable );
			this.isFake && ( bookmark.isFake = 1 );
			return bookmark;
		},

		/**
		 * Creates a bookmark for each range of this selection (from {@link #getRanges})
		 * by calling the {@link CKEDITOR.dom.range#createBookmark2} method,
		 * with extra care taken to avoid interference among those ranges. The arguments
		 * received are the same as with the underlying range method.
		 *
		 *		var bookmarks = editor.getSelection().createBookmarks2();
		 *
		 * @returns {Array} Array of bookmarks for each range.
		 */
		createBookmarks2: function( normalized ) {
			var bookmark = this.getRanges().createBookmarks2( normalized );
			this.isFake && ( bookmark.isFake = 1 );
			return bookmark;
		},

		/**
		 * Selects the virtual ranges denoted by the bookmarks by calling {@link #selectRanges}.
		 *
		 *		var bookmarks = editor.getSelection().createBookmarks();
		 *		editor.getSelection().selectBookmarks( bookmarks );
		 *
		 * @param {Array} bookmarks The bookmarks representing ranges to be selected.
		 * @returns {CKEDITOR.dom.selection} This selection object, after the ranges were selected.
		 */
		selectBookmarks: function( bookmarks ) {
			var ranges = [];
			for ( var i = 0; i < bookmarks.length; i++ ) {
				var range = new CKEDITOR.dom.range( this.root );
				range.moveToBookmark( bookmarks[ i ] );
				ranges.push( range );
			}

			if ( bookmarks.isFake )
				this.fake( ranges[ 0 ].getEnclosedNode() );
			else
				this.selectRanges( ranges );

			return this;
		},

		/**
		 * Retrieves the common ancestor node of the first range and the last range.
		 *
		 *		var ancestor = editor.getSelection().getCommonAncestor();
		 *
		 * @returns {CKEDITOR.dom.element} The common ancestor of the selection or `null` if selection is empty.
		 */
		getCommonAncestor: function() {
			var ranges = this.getRanges();
			if ( !ranges.length )
				return null;

			var startNode = ranges[ 0 ].startContainer,
				endNode = ranges[ ranges.length - 1 ].endContainer;
			return startNode.getCommonAncestor( endNode );
		},

		/**
		 * Moves the scrollbar to the starting position of the current selection.
		 *
		 *		editor.getSelection().scrollIntoView();
		 */
		scrollIntoView: function() {

			// Scrolls the first range into view.
			if ( this.type != CKEDITOR.SELECTION_NONE )
				this.getRanges()[ 0 ].scrollIntoView();
		},

		/**
		 * Remove all the selection ranges from the document.
		 */
		removeAllRanges: function() {
			var nativ = this.getNative();

			try { nativ && nativ[ isMSSelection ? 'empty' : 'removeAllRanges' ](); }
			catch(er){}

			this.reset();
		}
	};

})();

/**
 * Selection's revision. This value is incremented every time new
 * selection is created or existing one is modified.
 *
 * @since 4.3
 * @readonly
 * @property {Number} rev
 */

/**
 * Document in which selection is anchored.
 *
 * @readonly
 * @property {CKEDITOR.dom.document} document
 */

/**
 * Selection's root element.
 *
 * @readonly
 * @property {CKEDITOR.dom.element} root
 */

/**
 * Whether selection is locked (cannot be modified).
 *
 * See {@link #lock} and {@link #unlock} methods.
 *
 * @readonly
 * @property {Boolean} isLocked
 */

/**
 * Whether selection is a fake selection.
 *
 * See {@link #fake} method.
 *
 * @readonly
 * @property {Boolean} isFake
 */
