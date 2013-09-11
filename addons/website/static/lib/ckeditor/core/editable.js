/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

(function() {
	/**
	 * Editable class which provides all editing related activities by
	 * the `contenteditable` element, dynamically get attached to editor instance.
	 *
	 * @class CKEDITOR.editable
	 * @extends CKEDITOR.dom.element
	 */
	CKEDITOR.editable = CKEDITOR.tools.createClass({
		base: CKEDITOR.dom.element,
		/**
		 * The constructor hold only generic editable creation logic that are commonly shared among all different editable elements.
		 *
		 * @constructor Creates an editable class instance.
		 * @param {CKEDITOR.editor} editor The editor instance on which the editable operates.
		 * @param {HTMLElement/CKEDITOR.dom.element} element Any DOM element that been used as the editor's
		 * editing container, e.g. it could be either an HTML element with the `contenteditable` attribute
		 * set to the true that handles wysiwyg editing or a `<textarea>` element that handles source editing.
		 */
		$: function( editor, element ) {
			// Transform the element into a CKEDITOR.dom.element instance.
			this.base( element.$ || element );

			this.editor = editor;

			/**
			 * Indicate whether the editable element has gained focus.
			 *
			 * @property {Boolean} hasFocus
			 */
			this.hasFocus = false;

			// The bootstrapping logic.
			this.setup();
		},
		proto: {

			focus: function() {

				var active;

				// [Webkit] When DOM focus is inside of nested contenteditable elements,
				// apply focus on the main editable will compromise it's text selection.
				if ( CKEDITOR.env.webkit && !this.hasFocus ) {
					// Restore focus on element which we cached (on selectionCheck) as previously active.
					active = this.editor._.previousActive || this.getDocument().getActive();
					if ( this.contains( active ) ) {
						active.focus();
						return;
					}
				}

				// [IE] Use instead "setActive" method to focus the editable if it belongs to
				// the host page document, to avoid bringing an unexpected scroll.
				try {
					this.$[ CKEDITOR.env.ie && this.getDocument().equals( CKEDITOR.document ) ? 'setActive' : 'focus' ]();
				} catch ( e ) {
					// IE throws unspecified error when focusing editable after closing dialog opened on nested editable.
					if ( !CKEDITOR.env.ie )
						throw e;
				}

				// Remedy if Safari doens't applies focus properly. (#279)
				if ( CKEDITOR.env.safari && !this.isInline() ) {
					active = CKEDITOR.document.getActive();
					if ( !active.equals( this.getWindow().getFrame() ) ) {
						this.getWindow().focus();
					}
				}
			},

			/**
			 * Overrides {@link CKEDITOR.dom.element#on} to have special `focus/blur` handling.
			 * The `focusin/focusout` events are used in IE to replace regular `focus/blur` events
			 * because we want to avoid the asynchronous nature of later ones.
			 */
			on: function( name, fn ) {
				var args = Array.prototype.slice.call( arguments, 0 );

				if ( CKEDITOR.env.ie && ( /^focus|blur$/ ).exec( name ) ) {
					name = name == 'focus' ? 'focusin' : 'focusout';

					// The "focusin/focusout" events bubbled, e.g. If there are elements with layout
					// they fire this event when clicking in to edit them but it must be ignored
					// to allow edit their contents. (#4682)
					fn = isNotBubbling( fn, this );
					args[ 0 ] = name;
					args[ 1 ] = fn;
				}

				return CKEDITOR.dom.element.prototype.on.apply( this, args );
			},

			/**
			 * Registers an event listener that needs to be removed on detaching.
			 *
			 * @see CKEDITOR.event#on
			 */
			attachListener: function( obj, event, fn, scope, listenerData, priority ) {
				!this._.listeners && ( this._.listeners = [] );
				// Register the listener.
				var args = Array.prototype.slice.call( arguments, 1 ),
					listener = obj.on.apply( obj, args );

				this._.listeners.push( listener );

				return listener;
			},

			/**
			 * Remove all event listeners registered from {@link #attachListener}.
			 */
			clearListeners: function() {
				var listeners = this._.listeners;
				// Don't get broken by this.
				try {
					while ( listeners.length )
						listeners.pop().removeListener();
				} catch ( e ) {}
			},

			/**
			 * Restore all attribution changes made by {@link #changeAttr }.
			 */
			restoreAttrs : function() {
				var changes = this._.attrChanges, orgVal;
				for ( var attr in changes )
				{
					if ( changes.hasOwnProperty( attr ) )
					{
						orgVal = changes[ attr ];
						// Restore original attribute.
						orgVal !== null ? this.setAttribute( attr, orgVal ) : this.removeAttribute( attr );
					}
				}
			},

			/**
			 * Adds a CSS class name to this editable that needs to be removed on detaching.
			 *
			 * @param {String} className The class name to be added.
			 * @see CKEDITOR.dom.element#addClass
			 */
			attachClass: function( cls ) {
				var classes = this.getCustomData( 'classes' );
				if ( !this.hasClass( cls ) ) {
					!classes && ( classes = [] ), classes.push( cls );
					this.setCustomData( 'classes', classes );
					this.addClass( cls );
				}
			},

			/**
			 * Make an attribution change that would be reverted on editable detaching.
			 * @param {String} attr The attribute name to be changed.
			 * @param {String} val The value of specified attribute.
			 */
			changeAttr : function( attr, val ) {

				var orgVal = this.getAttribute( attr );
				if ( val !== orgVal )
				{
					!this._.attrChanges && ( this._.attrChanges = {} );

					// Saved the original attribute val.
					if ( !( attr in this._.attrChanges ) )
						this._.attrChanges[ attr ] = orgVal;

					this.setAttribute( attr, val );
				}
			},

			/**
			 * @see CKEDITOR.editor#insertHtml
			 */
			insertHtml: function( data, mode ) {
				beforeInsert( this );
				// Default mode is 'html'.
				insert( this, mode || 'html', data );
			},

			/**
			 * @see CKEDITOR.editor#insertText
			 */
			insertText: function( text ) {
				beforeInsert( this );

				var editor = this.editor,
					mode = editor.getSelection().getStartElement().hasAscendant( 'pre', true ) ? CKEDITOR.ENTER_BR : editor.activeEnterMode,
					isEnterBrMode = mode == CKEDITOR.ENTER_BR,
					tools = CKEDITOR.tools;

				// CRLF -> LF
				var html = tools.htmlEncode( text.replace( /\r\n/g, '\n' ) );

				// Tab -> &nbsp x 4;
				html = html.replace( /\t/g, '&nbsp;&nbsp; &nbsp;' );

				var paragraphTag = mode == CKEDITOR.ENTER_P ? 'p' : 'div';

				// Two line-breaks create one paragraphing block.
				if ( !isEnterBrMode ) {
					var duoLF = /\n{2}/g;
					if ( duoLF.test( html ) )
					{
						var openTag = '<' + paragraphTag + '>', endTag = '</' + paragraphTag + '>';
						html = openTag + html.replace( duoLF, function() { return  endTag + openTag; } ) + endTag;
					}
				}

				// One <br> per line-break.
				html = html.replace( /\n/g, '<br>' );

				// Compensate padding <br> at the end of block, avoid loosing them during insertion.
				if ( !isEnterBrMode ) {
					html = html.replace( new RegExp( '<br>(?=</' + paragraphTag + '>)' ), function( match ) {
						return tools.repeat( match, 2 );
					});
				}

				// Preserve spaces at the ends, so they won't be lost after insertion (merged with adjacent ones).
				html = html.replace( /^ | $/g, '&nbsp;' );

				// Finally, preserve whitespaces that are to be lost.
				html = html.replace( /(>|\s) /g, function( match, before ) {
					return before + '&nbsp;';
				} ).replace( / (?=<)/g, '&nbsp;' );

				insert( this, 'text', html );
			},

			/**
			 * @see CKEDITOR.editor#insertElement
			 */
			insertElement: function( element ) {
				beforeInsert( this );

				var editor = this.editor,
					enterMode = editor.activeEnterMode,
					selection = editor.getSelection(),
					ranges = selection.getRanges(),
					elementName = element.getName(),
					isBlock = CKEDITOR.dtd.$block[ elementName ];

				var range, clone, lastElement;

				for ( var i = ranges.length - 1; i >= 0; i-- ) {
					range = ranges[ i ];

					if ( !range.checkReadOnly() ) {
						// Remove the original contents, merge split nodes.
						range.deleteContents( 1 );

						clone = !i && element || element.clone( 1 );

						// If we're inserting a block at dtd-violated position, split
						// the parent blocks until we reach blockLimit.
						var current, dtd;
						if ( isBlock ) {
							while ( ( current = range.getCommonAncestor( 0, 1 ) ) &&
							        ( dtd = CKEDITOR.dtd[ current.getName() ] ) &&
							        !( dtd && dtd[ elementName ] ) ) {
								// Split up inline elements.
								if ( current.getName() in CKEDITOR.dtd.span )
									range.splitElement( current );
								// If we're in an empty block which indicate a new paragraph,
								// simply replace it with the inserting block.(#3664)
								else if ( range.checkStartOfBlock() && range.checkEndOfBlock() ) {
									range.setStartBefore( current );
									range.collapse( true );
									current.remove();
								} else
									range.splitBlock( enterMode == CKEDITOR.ENTER_DIV ? 'div' : 'p', editor.editable() );
							}
						}

						// Insert the new node.
						range.insertNode( clone );

						// Save the last element reference so we can make the
						// selection later.
						if ( !lastElement )
							lastElement = clone;
					}
				}

				if ( lastElement ) {
					range.moveToPosition( lastElement, CKEDITOR.POSITION_AFTER_END );

					// If we're inserting a block element, the new cursor position must be
					// optimized. (#3100,#5436,#8950)
					if ( isBlock ) {

						// Find next, meaningful element.
						var next = lastElement.getNext( function( node ) {
							return isNotEmpty( node ) && !isBogus( node );
						} );

						if ( next && next.type == CKEDITOR.NODE_ELEMENT &&
						     next.is( CKEDITOR.dtd.$block ) ) {

							// If the next one is a text block, move cursor to the start of it's content.
							if ( next.getDtd()[ '#' ] )
								range.moveToElementEditStart( next );
							// Otherwise move cursor to the before end of the last element.
							else
								range.moveToElementEditEnd( lastElement );
						}
						// Open a new line if the block is inserted at the end of parent.
						else if ( !next && enterMode != CKEDITOR.ENTER_BR ) {
							next = range.fixBlock( true, enterMode == CKEDITOR.ENTER_DIV ? 'div' : 'p' );
							range.moveToElementEditStart( next );
						}
					}
				}

				selection.selectRanges( [ range ] );

				// Do not scroll after inserting, because Opera may fail on certain element (e.g. iframe/iframe.html).
				afterInsert( this, CKEDITOR.env.opera );
			},

			/**
			 * @see CKEDITOR.editor#setData
			 */
			setData: function( data, isSnapshot ) {
				if ( !isSnapshot )
					data = this.editor.dataProcessor.toHtml( data );

				this.setHtml( data );
				this.editor.fire( 'dataReady' );
			},

			/**
			 * @see CKEDITOR.editor#getData
			 */
			getData: function( isSnapshot ) {
				var data = this.getHtml();

				if ( !isSnapshot )
					data = this.editor.dataProcessor.toDataFormat( data );

				return data;
			},

			/**
			 * Change the read-only state on this editable.
			 *
			 * @param {Boolean} isReadOnly
			 */
			setReadOnly: function( isReadOnly ) {
				this.setAttribute( 'contenteditable', !isReadOnly );
			},

			/**
			 * Detach this editable object from the DOM (remove classes, listeners, etc.)
			 */
			detach: function() {
				// Cleanup the element.
				this.removeClass( 'cke_editable' );

				// Save the editor reference which will be lost after
				// calling detach from super class.
				var editor = this.editor;

				this._.detach();

				delete editor.document;
				delete editor.window;
			},

			/**
			 * Check if the editable is one of the host page element, indicates the
			 * an inline editing environment.
			 *
			 * @returns {Boolean}
			 */
			isInline : function () {
				return this.getDocument().equals( CKEDITOR.document );
			},

			/**
			 * Editable element bootstrapping.
			 *
			 * @private
			 */
			setup: function() {
				var editor = this.editor;

				// Handle the load/read of editor data/snapshot.
				this.attachListener( editor, 'beforeGetData', function() {
					var data = this.getData();

					// Post processing html output of wysiwyg editable.
					if ( !this.is( 'textarea' ) ) {
						// Reset empty if the document contains only one empty paragraph.
						if ( editor.config.ignoreEmptyParagraph !== false )
							data = data.replace( emptyParagraphRegexp, function( match, lookback ) { return lookback; } );
					}

					editor.setData( data, null, 1 );
				}, this );

				this.attachListener( editor, 'getSnapshot', function( evt ) {
					evt.data = this.getData( 1 );
				}, this );

				this.attachListener( editor, 'afterSetData', function() {
					this.setData( editor.getData( 1 ) );
				}, this );
				this.attachListener( editor, 'loadSnapshot', function( evt ) {
					this.setData( evt.data, 1 );
				}, this );

				// Delegate editor focus/blur to editable.
				this.attachListener( editor, 'beforeFocus', function() {
					var sel = editor.getSelection(),
						ieSel = sel && sel.getNative();

					// IE considers control-type element as separate
					// focus host when selected, avoid destroying the
					// selection in such case. (#5812) (#8949)
					if ( ieSel && ieSel.type == 'Control' )
						return;

					this.focus();
				}, this );

				this.attachListener( editor, 'insertHtml', function( evt ) {
					this.insertHtml( evt.data.dataValue, evt.data.mode );
				}, this );
				this.attachListener( editor, 'insertElement', function( evt ) {
					this.insertElement( evt.data );
				}, this );
				this.attachListener( editor, 'insertText', function( evt ) {
					this.insertText( evt.data );
				}, this );

				// Update editable state.
				this.setReadOnly( editor.readOnly );

				// The editable class.
				this.attachClass( 'cke_editable' );

				// The element mode css class.
				this.attachClass( editor.elementMode == CKEDITOR.ELEMENT_MODE_INLINE ?
					'cke_editable_inline' :
					editor.elementMode == CKEDITOR.ELEMENT_MODE_REPLACE ||
					editor.elementMode == CKEDITOR.ELEMENT_MODE_APPENDTO ?
					'cke_editable_themed' : ''
				);

				this.attachClass( 'cke_contents_' + editor.config.contentsLangDirection );

				// Setup editor keystroke handlers on this element.
				var keystrokeHandler = editor.keystrokeHandler;

				// If editor is read-only, then make sure that BACKSPACE key
				// is blocked to prevent browser history navigation.
				keystrokeHandler.blockedKeystrokes[ 8 ] = +editor.readOnly;

				editor.keystrokeHandler.attach( this );

				// Update focus states.
				this.on( 'blur', function( evt ) {
					// Opera might raise undesired blur event on editable, check if it's
					// really blurred, otherwise cancel the event. (#9459)
					if ( CKEDITOR.env.opera ) {
						var active = CKEDITOR.document.getActive();
						if ( active.equals( this.isInline() ? this : this.getWindow().getFrame() ) ) {
							evt.cancel();
							return;
						}
					}

					this.hasFocus = false;
				}, null, null, -1 );

				this.on( 'focus', function() {
					this.hasFocus = true;
				}, null, null, -1 );

				// Register to focus manager.
				editor.focusManager.add( this );

				// Inherit the initial focus on editable element.
				if ( this.equals( CKEDITOR.document.getActive() ) ) {
					this.hasFocus = true;
					// Pending until this editable has attached.
					editor.once( 'contentDom', function() {
						editor.focusManager.focus();
					});
				}

				// Apply tab index on demand, with original direction saved.
				if ( this.isInline() ) {

					// tabIndex of the editable is different than editor's one.
					// Update the attribute of the editable.
					this.changeAttr( 'tabindex', editor.tabIndex );
				}

				// The above is all we'll be doing for a <textarea> editable.
				if ( this.is( 'textarea' ) )
					return;

				// The DOM document which the editing acts upon.
				editor.document = this.getDocument();
				editor.window = this.getWindow();

				var doc = editor.document;

				this.changeAttr( 'spellcheck', !editor.config.disableNativeSpellChecker );

				// Apply contents direction on demand, with original direction saved.
				var dir = editor.config.contentsLangDirection;
				if ( this.getDirection( 1 ) != dir )
					this.changeAttr( 'dir', dir );

				// Create the content stylesheet for this document.
				var styles = CKEDITOR.getCss();
				if ( styles ) {
					var head = doc.getHead();
					if ( !head.getCustomData( 'stylesheet' ) ) {
						var sheet = doc.appendStyleText( styles );
						sheet = new CKEDITOR.dom.element( sheet.ownerNode || sheet.owningElement );
						head.setCustomData( 'stylesheet', sheet );
						sheet.data( 'cke-temp', 1 );
					}
				}

				// Update the stylesheet sharing count.
				var ref = doc.getCustomData( 'stylesheet_ref' ) || 0;
				doc.setCustomData( 'stylesheet_ref', ref + 1 );

				// Pass this configuration to styles system.
				this.setCustomData( 'cke_includeReadonly', !editor.config.disableReadonlyStyling );

				// Prevent the browser opening read-only links. (#6032)
				this.attachListener( this, 'click', function( ev ) {
					ev = ev.data;
					var target = ev.getTarget();
					if ( target.is( 'a' ) && ev.$.button != 2 && target.isReadOnly() )
						ev.preventDefault();
				} );

				// Override keystrokes which should have deletion behavior
				//  on fully selected element . (#4047) (#7645)
				this.attachListener( editor, 'key', function( evt ) {
					if ( editor.readOnly )
						return true;

					var keyCode = evt.data.keyCode, isHandled;

					// Backspace OR Delete.
					if ( keyCode in { 8:1,46:1 } ) {
						var sel = editor.getSelection(),
							selected,
							range = sel.getRanges()[ 0 ],
							path = range.startPath(),
							block,
							parent,
							next,
							rtl = keyCode == 8;

						// Remove the entire list/table on fully selected content. (#7645)
						if ( ( selected = getSelectedTableList( sel ) ) ) {
							// Make undo snapshot.
							editor.fire( 'saveSnapshot' );

							// Delete any element that 'hasLayout' (e.g. hr,table) in IE8 will
							// break up the selection, safely manage it here. (#4795)
							range.moveToPosition( selected, CKEDITOR.POSITION_BEFORE_START );
							// Remove the control manually.
							selected.remove();
							range.select();

							editor.fire( 'saveSnapshot' );

							isHandled = 1;
						}
						else if ( range.collapsed )
						{
							// Handle the following special cases: (#6217)
							// 1. Del/Backspace key before/after table;
							// 2. Backspace Key after start of table.
							if ( ( block = path.block ) &&
								 range[ rtl ? 'checkStartOfBlock' : 'checkEndOfBlock' ]() &&
								 ( next = block[ rtl ? 'getPrevious' : 'getNext' ]( isNotWhitespace ) ) &&
								 next.is( 'table' ) )
							{
								editor.fire( 'saveSnapshot' );

								// Remove the current empty block.
								if ( range[ rtl ? 'checkEndOfBlock' : 'checkStartOfBlock' ]() )
									block.remove();

								// Move cursor to the beginning/end of table cell.
								range[ 'moveToElementEdit' + ( rtl ? 'End' : 'Start' ) ]( next );
								range.select();

								editor.fire( 'saveSnapshot' );

								isHandled = 1;
							}
							else if ( path.blockLimit && path.blockLimit.is( 'td' ) &&
									  ( parent = path.blockLimit.getAscendant( 'table' ) ) &&
									  range.checkBoundaryOfElement( parent, rtl ? CKEDITOR.START : CKEDITOR.END ) &&
									  ( next = parent[ rtl ? 'getPrevious' : 'getNext' ]( isNotWhitespace ) ) )
							{
								editor.fire( 'saveSnapshot' );

								// Move cursor to the end of previous block.
								range[ 'moveToElementEdit' + ( rtl ? 'End' : 'Start' ) ]( next );

								// Remove any previous empty block.
								if ( range.checkStartOfBlock() && range.checkEndOfBlock() )
									next.remove();
								else
									range.select();

								editor.fire( 'saveSnapshot' );

								isHandled = 1;
							}
							// BACKSPACE/DEL pressed at the start/end of table cell.
							else if ( ( parent = path.contains( [ 'td', 'th', 'caption' ] ) ) &&
								      range.checkBoundaryOfElement( parent, rtl ? CKEDITOR.START : CKEDITOR.END ) ) {
								isHandled = 1;
							}
						}

					}

					return !isHandled;
				} );

				this.attachListener( this, 'dblclick', function( evt ) {
					if ( editor.readOnly )
						return false;

					var data = { element: evt.data.getTarget() };
					editor.fire( 'doubleclick', data );
				} );

				// Prevent automatic submission in IE #6336
				CKEDITOR.env.ie && this.attachListener( this, 'click', blockInputClick );

				// Gecko/Webkit need some help when selecting control type elements. (#3448)
				if ( !( CKEDITOR.env.ie || CKEDITOR.env.opera ) ) {
					this.attachListener( this, 'mousedown', function( ev ) {
						var control = ev.data.getTarget();
						if ( control.is( 'img', 'hr', 'input', 'textarea', 'select' ) ) {
							editor.getSelection().selectElement( control );

							// Prevent focus from stealing from the editable. (#9515)
							if ( control.is( 'input', 'textarea', 'select' ) )
								ev.data.preventDefault();
						}
					} );
				}

				// Prevent right click from selecting an empty block even
				// when selection is anchored inside it. (#5845)
				if ( CKEDITOR.env.gecko ) {
					this.attachListener( this, 'mouseup', function( ev ) {
						if ( ev.data.$.button == 2 ) {
							var target = ev.data.getTarget();

							if ( !target.getOuterHtml().replace( emptyParagraphRegexp, '' ) ) {
								var range = editor.createRange();
								range.moveToElementEditStart( target );
								range.select( true );
							}
						}
					} );
				}

				// Webkit: avoid from editing form control elements content.
				if ( CKEDITOR.env.webkit ) {
					// Prevent from tick checkbox/radiobox/select
					this.attachListener( this, 'click', function( ev ) {
						if ( ev.data.getTarget().is( 'input', 'select' ) )
							ev.data.preventDefault();
					});

					// Prevent from editig textfield/textarea value.
					this.attachListener( this, 'mouseup', function( ev ) {
						if ( ev.data.getTarget().is( 'input', 'textarea' ) )
							ev.data.preventDefault();
					});
				}
			}
		},

		_: {
			detach: function() {
				// Update the editor cached data with current data.
				this.editor.setData( this.editor.getData(), 0, 1 );

				this.clearListeners();
				this.restoreAttrs();

				// Cleanup our custom classes.
				var classes;
				if ( ( classes = this.removeCustomData( 'classes' ) ) ) {
					while ( classes.length )
						this.removeClass( classes.pop() );
				}

				// Remove contents stylesheet from document if it's the last usage.
				var doc = this.getDocument(),
					head = doc.getHead();
				if ( head.getCustomData( 'stylesheet' ) ) {
					var refs = doc.getCustomData( 'stylesheet_ref' );
					if ( !( --refs ) ) {
						doc.removeCustomData( 'stylesheet_ref' );
						var sheet = head.removeCustomData( 'stylesheet' );
						sheet.remove();
					} else
						doc.setCustomData( 'stylesheet_ref', refs );
				}

				// Free up the editor reference.
				delete this.editor;
			}
		}
	});

	/**
	 * Create, retrieve or detach an editable element of the editor,
	 * this method should always be used instead of calling directly {@link CKEDITOR.editable}.
	 *
	 * @method editable
	 * @member CKEDITOR.editor
	 * @param {CKEDITOR.dom.element/CKEDITOR.editable} elementOrEditable The
	 * DOM element to become the editable or a {@link CKEDITOR.editable} object.
	 */
	CKEDITOR.editor.prototype.editable = function( element ) {
		var editable = this._.editable;

		// This editor has already associated with
		// an editable element, silently fails.
		if ( editable && element )
			return 0;

		if ( arguments.length ) {
			editable = this._.editable = element ? ( element instanceof CKEDITOR.editable ? element : new CKEDITOR.editable( this, element ) ) :
			// Detach the editable from editor.
			( editable && editable.detach(), null );
		}

		// Just retrieve the editable.
		return editable;
	};

	// Auto-fixing block-less content by wrapping paragraph (#3190), prevent
	// non-exitable-block by padding extra br.(#3189)
	// Returns truly value when dom was changed, falsy otherwise.
	function fixDom( evt ) {
		var editor = evt.editor,
			editable = editor.editable(),
			path = evt.data.path,
			blockLimit = path.blockLimit,
			selection = evt.data.selection,
			range = selection.getRanges()[ 0 ],
			enterMode = editor.activeEnterMode;

		if ( CKEDITOR.env.gecko ) {
			// v3: check if this is needed.
			// activateEditing( editor );

			// Ensure bogus br could help to move cursor (out of styles) to the end of block. (#7041)
			var pathBlock = path.block || path.blockLimit || path.root,
				lastNode = pathBlock && pathBlock.getLast( isNotEmpty );

			// Check some specialities of the current path block:
			// 1. It is really displayed as block; (#7221)
			// 2. It doesn't end with one inner block; (#7467)
			// 3. It doesn't have bogus br yet.
			if ( pathBlock && pathBlock.isBlockBoundary() &&
				!( lastNode && lastNode.type == CKEDITOR.NODE_ELEMENT && lastNode.isBlockBoundary() ) &&
				!pathBlock.is( 'pre' ) && !pathBlock.getBogus() ) {

				pathBlock.appendBogus();
			}
		}

		// When we're in block enter mode, a new paragraph will be established
		// to encapsulate inline contents inside editable. (#3657)
		if ( shouldAutoParagraph( editor, path.block, blockLimit ) && range.collapsed ) {
			var testRng = range.clone();
			testRng.enlarge( CKEDITOR.ENLARGE_BLOCK_CONTENTS );
			var walker = new CKEDITOR.dom.walker( testRng );
			walker.guard = function( node ) {
				return !isNotEmpty( node ) ||
				       node.type == CKEDITOR.NODE_COMMENT ||
				       node.isReadOnly();
			};

			// 1. Inline content discovered under cursor;
			// 2. Empty editable.
			if ( !walker.checkForward() ||
			     testRng.checkStartOfBlock() && testRng.checkEndOfBlock() ) {

				var fixedBlock = range.fixBlock( true, editor.activeEnterMode == CKEDITOR.ENTER_DIV ? 'div' : 'p' );

				// For IE, we should remove any filler node which was introduced before.
				if ( CKEDITOR.env.ie ) {
					var first = fixedBlock.getFirst( isNotEmpty );
					if ( first && isNbsp( first ) ) {
						first.remove();
					}
				}

				range.select();
				// Cancel this selection change in favor of the next (correct).  (#6811)
				evt.cancel();
			}
		}
	}

	function blockInputClick( evt ) {
		var element = evt.data.getTarget();
		if ( element.is( 'input' ) ) {
			var type = element.getAttribute( 'type' );
			if ( type == 'submit' || type == 'reset' )
				evt.data.preventDefault();
		}
	}

	function isBlankParagraph( block ) {
		return block.getOuterHtml().match( emptyParagraphRegexp );
	}

	function isNotEmpty( node ) {
		return isNotWhitespace( node ) && isNotBookmark( node );
	}

	function isNbsp( node ) {
		return node.type == CKEDITOR.NODE_TEXT && CKEDITOR.tools.trim( node.getText() ).match( /^(?:&nbsp;|\xa0)$/ );
	}

	// Elements that could blink the cursor anchoring beside it, like hr, page-break. (#6554)
	function nonEditable( element ) {
		return element.isBlockBoundary() && CKEDITOR.dtd.$empty[ element.getName() ];
	}

	function isNotBubbling( fn, src ) {
		return function( evt ) {
			var other = CKEDITOR.dom.element.get( evt.data.$.toElement || evt.data.$.fromElement || evt.data.$.relatedTarget );
			if ( ! ( other && ( src.equals( other ) || src.contains( other ) ) ) )
				fn.call( this, evt );
		};
	}

	var isBogus = CKEDITOR.dom.walker.bogus();

	// Check if the entire table/list contents is selected.
	function getSelectedTableList( sel ) {
		var selected,
			range = sel.getRanges()[ 0 ],
			editable = sel.root,
			path = range.startPath(),
			structural = { table:1,ul:1,ol:1,dl:1 };

		if ( path.contains( structural ) ) {
			function guard( forwardGuard ) {
				return function( node, isWalkOut ) {
					// Save the encountered node as selected if going down the DOM structure
					// and the node is structured element.
					if ( isWalkOut && node.type == CKEDITOR.NODE_ELEMENT && node.is( structural ) )
						selected = node;

					// Stop the walker when either traversing another non-empty node at the same
					// DOM level as in previous step.
					// NOTE: When going forwards, stop if encountered a bogus.
					if ( !isWalkOut && isNotEmpty( node ) && !( forwardGuard && isBogus( node ) ) )
						return false;
				};
			}

			// Clone the original range.
			var walkerRng = range.clone();

			// Enlarge the range: X<ul><li>[Y]</li></ul>X => [X<ul><li>]Y</li></ul>X
			walkerRng.collapse( 1 );
			walkerRng.setStartAt( editable, CKEDITOR.POSITION_AFTER_START );

			// Create a new walker.
			var walker = new CKEDITOR.dom.walker( walkerRng );

			// Assign a new guard to the walker.
			walker.guard = guard();

			// Go backwards checking for selected structural node.
			walker.checkBackward();

			// If there's a selected structured element when checking backwards,
			// then check the same forwards.
			if ( selected ) {
				// Clone the original range.
				walkerRng = range.clone();

				// Enlarge the range (assuming <ul> is selected element from guard):
				//
				// 	   X<ul><li>[Y]</li></ul>X    =>    X<ul><li>Y[</li></ul>]X
				//
				// If the walker went deeper down DOM than a while ago when traversing
				// backwards, then it doesn't make sense: an element must be selected
				// symmetrically. By placing range end **after previously selected node**,
				// we make sure we don't go no deeper in DOM when going forwards.
				walkerRng.collapse();
				walkerRng.setEndAt( selected, CKEDITOR.POSITION_AFTER_END );

				// Create a new walker.
				walker = new CKEDITOR.dom.walker( walkerRng );

				// Assign a new guard to the walker.
				walker.guard = guard( true );

				// Reset selected node.
				selected = false;

				// Go forwards checking for selected structural node.
				walker.checkForward();

				return selected;
			}
		}

		return null;
	}

	// Whether in given context (pathBlock, pathBlockLimit and editor settings)
	// editor should automatically wrap inline contents with blocks.
	function shouldAutoParagraph( editor, pathBlock, pathBlockLimit ) {
		return editor.config.autoParagraph !== false &&
			editor.activeEnterMode != CKEDITOR.ENTER_BR &&
			editor.editable().equals( pathBlockLimit ) && !pathBlock;
	}

	// Matching an empty paragraph at the end of document.
	var emptyParagraphRegexp = /(^|<body\b[^>]*>)\s*<(p|div|address|h\d|center|pre)[^>]*>\s*(?:<br[^>]*>|&nbsp;|\u00A0|&#160;)?\s*(:?<\/\2>)?\s*(?=$|<\/body>)/gi;

	var isNotWhitespace = CKEDITOR.dom.walker.whitespaces( true ),
		isNotBookmark = CKEDITOR.dom.walker.bookmark( false, true );

	CKEDITOR.on( 'instanceLoaded', function( evt ) {
		var editor = evt.editor;

		// and flag that the element was locked by our code so it'll be editable by the editor functions (#6046).
		editor.on( 'insertElement', function( evt ) {
			var element = evt.data;
			if ( element.type == CKEDITOR.NODE_ELEMENT && ( element.is( 'input' ) || element.is( 'textarea' ) ) ) {
				// // The element is still not inserted yet, force attribute-based check.
				if ( element.getAttribute( 'contentEditable' ) != "false" )
					element.data( 'cke-editable', element.hasAttribute( 'contenteditable' ) ? 'true' : '1' );
				element.setAttribute( 'contentEditable', false );
			}
		});

		editor.on( 'selectionChange', function( evt ) {
			if ( editor.readOnly )
				return;

			// Auto fixing on some document structure weakness to enhance usabilities. (#3190 and #3189)
			var sel = editor.getSelection();
			// Do it only when selection is not locked. (#8222)
			if ( sel && !sel.isLocked ) {
				var isDirty = editor.checkDirty();

				// Lock undoM before touching DOM to prevent
				// recording these changes as separate snapshot.
				editor.fire( 'lockSnapshot' );
				fixDom( evt );
				editor.fire( 'unlockSnapshot' );

				!isDirty && editor.resetDirty();
			}
		});
	});


	CKEDITOR.on( 'instanceCreated', function( evt ) {
		var editor = evt.editor;

		editor.on( 'mode', function() {

			var editable = editor.editable();

			// Setup proper ARIA roles and properties for inline editable, framed
			// editable is instead handled by plugin.
			if ( editable && editable.isInline() ) {

				var ariaLabel = editor.title;

				editable.changeAttr( 'role', 'textbox' );
				editable.changeAttr( 'aria-label', ariaLabel );

				if ( ariaLabel )
					editable.changeAttr( 'title', ariaLabel );

				// Put the voice label in different spaces, depending on element mode, so
				// the DOM element get auto detached on mode reload or editor destroy.
				var ct = this.ui.space( this.elementMode == CKEDITOR.ELEMENT_MODE_INLINE ? 'top' : 'contents' );
				if ( ct ) {
					var ariaDescId = CKEDITOR.tools.getNextId(),
						desc = CKEDITOR.dom.element.createFromHtml( '<span id="' + ariaDescId + '" class="cke_voice_label">' + this.lang.common.editorHelp + '</span>' );
					ct.append( desc );
					editable.changeAttr( 'aria-describedby', ariaDescId );
				}
			}
		});
	});

	// #9222: Show text cursor in Gecko.
	// Show default cursor over control elements on all non-IEs.
	CKEDITOR.addCss( '.cke_editable{cursor:text}.cke_editable img,.cke_editable input,.cke_editable textarea{cursor:default}' );

	//
	// Functions related to insertXXX methods
	//
	var insert = (function() {
		'use strict';

		var DTD = CKEDITOR.dtd;

		// Inserts the given (valid) HTML into the range position (with range content deleted),
		// guarantee it's result to be a valid DOM tree.
		function insert( editable, type, data ) {
			var editor = editable.editor,
				doc = editable.getDocument(),
				selection = editor.getSelection(),
				// HTML insertion only considers the first range.
				// Note: getRanges will be overwritten for tests since we want to test
				// 		custom ranges and bypass native selections.
				// TODO what should we do with others? Remove?
				range = selection.getRanges()[ 0 ],
				dontFilter = false;

			if ( type == 'unfiltered_html' ) {
				type = 'html';
				dontFilter = true;
			}

			// Check range spans in non-editable.
			if ( range.checkReadOnly() )
				return;

			// RANGE PREPARATIONS

			var path = new CKEDITOR.dom.elementPath( range.startContainer, range.root ),
				// Let root be the nearest block that's impossible to be split
				// during html processing.
				blockLimit = path.blockLimit || range.root,
				// The "state" value.
				that = {
					type: type,
					dontFilter: dontFilter,
					editable: editable,
					editor: editor,
					range: range,
					blockLimit: blockLimit,
					// During pre-processing / preparations startContainer of affectedRange should be placed
					// in this element in which inserted or moved (in case when we merge blocks) content
					// could create situation that will need merging inline elements.
					// Examples:
					// <div><b>A</b>^B</div> + <b>C</b> => <div><b>A</b><b>C</b>B</div> - affected container is <div>.
					// <p><b>A[B</b></p><p><b>C]D</b></p> + E => <p><b>AE</b></p><p><b>D</b></p> =>
					//		<p><b>AE</b><b>D</b></p> - affected container is <p> (in text mode).
					mergeCandidates: [],
					zombies: []
				};

			prepareRangeToDataInsertion( that );

			// DATA PROCESSING

			// Select range and stop execution.
			// If data has been totally emptied after the filtering,
			// any insertion is pointless (#10339).
			if ( data && processDataForInsertion( that, data ) ) {
				// DATA INSERTION
				insertDataIntoRange( that );
			}

			// FINAL CLEANUP
			// Set final range position and clean up.

			cleanupAfterInsertion( that );

			// Make the final range selection.
			range.select();

			afterInsert( editable );
		}

		// Prepare range to its data deletion.
		// Delete its contents.
		// Prepare it to insertion.
		function prepareRangeToDataInsertion( that ) {
			var range = that.range,
				mergeCandidates = that.mergeCandidates,
				node, marker, path, startPath, endPath, previous, bm;

			// If range starts in inline element then insert a marker, so empty
			// inline elements won't be removed while range.deleteContents
			// and we will be able to move range back into this element.
			// E.g. 'aa<b>[bb</b>]cc' -> (after deleting) 'aa<b><span/></b>cc'
			if ( that.type == 'text' && range.shrink( CKEDITOR.SHRINK_ELEMENT, true, false ) ) {
				marker = CKEDITOR.dom.element.createFromHtml( '<span>&nbsp;</span>', range.document );
				range.insertNode( marker );
				range.setStartAfter( marker );
			}

			// By using path we can recover in which element was startContainer
			// before deleting contents.
			// Start and endPathElements will be used to squash selected blocks, after removing
			// selection contents. See rule 5.
			startPath = new CKEDITOR.dom.elementPath( range.startContainer );
			that.endPath = endPath = new CKEDITOR.dom.elementPath( range.endContainer );

			if ( !range.collapsed ) {
				// Anticipate the possibly empty block at the end of range after deletion.
				node = endPath.block || endPath.blockLimit;
				var ancestor = range.getCommonAncestor();
				if ( node && !( node.equals( ancestor ) || node.contains( ancestor ) ) &&
				     range.checkEndOfBlock() ) {
					that.zombies.push( node );
				}

				range.deleteContents();
			}

			// Rule 4.
			// Move range into the previous block.
			while (
				( previous = getRangePrevious( range ) ) && checkIfElement( previous ) && previous.isBlockBoundary() &&
				// Check if previousNode was parent of range's startContainer before deleteContents.
				startPath.contains( previous )
			)
				range.moveToPosition( previous, CKEDITOR.POSITION_BEFORE_END );

			// Rule 5.
			mergeAncestorElementsOfSelectionEnds( range, that.blockLimit, startPath, endPath );

			// Rule 1.
			if ( marker ) {
				// If marker was created then move collapsed range into its place.
				range.setEndBefore( marker );
				range.collapse();
				marker.remove();
			}

			// Split inline elements so HTML will be inserted with its own styles.
			path = range.startPath();
			if ( ( node = path.contains( isInline, false, 1 ) ) ) {
				range.splitElement( node );
				that.inlineStylesRoot = node;
				that.inlineStylesPeak = path.lastElement;
			}

			// Record inline merging candidates for later cleanup in place.
			bm = range.createBookmark();

			// 1. Inline siblings.
			node = bm.startNode.getPrevious( isNotEmpty );
			node && checkIfElement( node ) && isInline( node ) && mergeCandidates.push( node );
			node = bm.startNode.getNext( isNotEmpty );
			node && checkIfElement( node ) && isInline( node ) && mergeCandidates.push( node );

			// 2. Inline parents.
			node = bm.startNode;
			while ( ( node = node.getParent() ) && isInline( node ) )
				mergeCandidates.push( node );

			range.moveToBookmark( bm );
		}

		function processDataForInsertion( that, data ) {
			var range = that.range;

			// Rule 8. - wrap entire data in inline styles.
			// (e.g. <p><b>x^z</b></p> + <p>a</p><p>b</p> -> <b><p>a</p><p>b</p></b>)
			// Incorrect tags order will be fixed by htmlDataProcessor.
			if ( that.type == 'text' && that.inlineStylesRoot )
				data = wrapDataWithInlineStyles( data, that );


			var context = that.blockLimit.getName();

			// Wrap data to be inserted, to avoid loosing leading whitespaces
			// when going through the below procedure.
			if ( /^\s+|\s+$/.test( data ) && 'span' in CKEDITOR.dtd[ context ] ) {
				var protect = '<span data-cke-marker="1">&nbsp;</span>';
				data =  protect + data + protect;
			}

			// Process the inserted html, in context of the insertion root.
			// Don't use the "fix for body" feature as auto paragraphing must
			// be handled during insertion.
			data = that.editor.dataProcessor.toHtml( data, {
				context: null,
				fixForBody: false,
				dontFilter: that.dontFilter,
				// Use the current, contextual settings.
				filter: that.editor.activeFilter,
				enterMode: that.editor.activeEnterMode
			} );


			// Build the node list for insertion.
			var doc = range.document,
				wrapper = doc.createElement( 'body' );

			wrapper.setHtml( data );

			// Eventually remove the temporaries.
			if ( protect ) {
				wrapper.getFirst().remove();
				wrapper.getLast().remove();
			}

			// Rule 7.
			var block = range.startPath().block;
			if ( block &&													// Apply when there exists path block after deleting selection's content...
				!( block.getChildCount() == 1 && block.getBogus() ) ) {		// ... and the only content of this block isn't a bogus.
				stripBlockTagIfSingleLine( wrapper );
			}

			that.dataWrapper = wrapper;

			return data;
		}

		function insertDataIntoRange( that ) {
			var range = that.range,
				doc = range.document,
				path,
				blockLimit = that.blockLimit,
				nodesData, nodeData, node,
				nodeIndex = 0,
				bogus,
				bogusNeededBlocks = [],
				pathBlock, fixBlock,
				splittingContainer = 0,
				dontMoveCaret = 0,
				insertionContainer, toSplit, newContainer,
				startContainer = range.startContainer,
				endContainer = that.endPath.elements[ 0 ],
				filteredNodes,
				// If endContainer was merged into startContainer: <p>a[b</p><p>c]d</p>
				// or it's equal to startContainer: <p>a^b</p>
				// or different situation happened :P
				// then there's no separate container for the end of selection.
				pos = endContainer.getPosition( startContainer ),
				separateEndContainer = !!endContainer.getCommonAncestor( startContainer ) // endC is not detached.
				&& pos != CKEDITOR.POSITION_IDENTICAL && !( pos & CKEDITOR.POSITION_CONTAINS + CKEDITOR.POSITION_IS_CONTAINED ); // endC & endS are in separate branches.

			nodesData = extractNodesData( that.dataWrapper, that );

			removeBrsAdjacentToPastedBlocks( nodesData, range );

			for ( ; nodeIndex < nodesData.length; nodeIndex++ ) {
				nodeData = nodesData[ nodeIndex ];

				// Ignore trailing <brs>
				if ( nodeData.isLineBreak && splitOnLineBreak( range, blockLimit, nodeData ) ) {
					// Do not move caret towards the text (in cleanupAfterInsertion),
					// because caret was placed after a line break.
					dontMoveCaret = nodeIndex > 0;
					continue;
				}

				path = range.startPath();

				// Auto paragraphing.
				if ( !nodeData.isBlock && shouldAutoParagraph( that.editor, path.block, path.blockLimit ) && ( fixBlock = autoParagraphTag( that.editor ) ) ) {
					fixBlock = doc.createElement( fixBlock );
					!CKEDITOR.env.ie && fixBlock.appendBogus();
					range.insertNode( fixBlock );
					if ( !CKEDITOR.env.ie && ( bogus = fixBlock.getBogus() ) )
						bogus.remove();
					range.moveToPosition( fixBlock, CKEDITOR.POSITION_BEFORE_END );
				}

				node = range.startPath().block;

				// Remove any bogus element on the current path block for now, and mark
				// it for later compensation.
				if ( node && !node.equals( pathBlock ) ) {
					bogus = node.getBogus();
					if ( bogus ) {
						bogus.remove();
						bogusNeededBlocks.push( node );
					}

					pathBlock = node;
				}

				// First not allowed node reached - start splitting original container
				if ( nodeData.firstNotAllowed )
					splittingContainer = 1;

				if ( splittingContainer && nodeData.isElement ) {
					insertionContainer = range.startContainer;
					toSplit = null;

					// Find the first ancestor that can contain current node.
					// This one won't be split.
					while ( insertionContainer && !DTD[ insertionContainer.getName() ][ nodeData.name ] ) {
						if ( insertionContainer.equals( blockLimit ) ) {
							insertionContainer = null;
							break;
						}

						toSplit = insertionContainer;
						insertionContainer = insertionContainer.getParent();
					}

					// If split has to be done - do it and mark both ends as a possible zombies.
					if ( insertionContainer ) {
						if ( toSplit ) {
							newContainer = range.splitElement( toSplit );
							that.zombies.push( newContainer );
							that.zombies.push( toSplit );
						}
					}
					// Unable to make the insertion happen in place, resort to the content filter.
					else {
						// If everything worked fine insertionContainer == blockLimit here.
						filteredNodes = filterElement( nodeData.node, blockLimit.getName(), !nodeIndex, nodeIndex == nodesData.length - 1 );
					}
				}

				if ( filteredNodes ) {
					while ( ( node = filteredNodes.pop() ) )
						range.insertNode( node );
					filteredNodes = 0;
				} else
					// Insert current node at the start of range.
					range.insertNode( nodeData.node );

				// Move range to the endContainer for the final allowed elements.
				if ( nodeData.lastNotAllowed && nodeIndex < nodesData.length - 1 ) {
					// If separateEndContainer exists move range there.
					// Otherwise try to move range to container created during splitting.
					// If this doesn't work - don't move range.
					newContainer = separateEndContainer ? endContainer : newContainer;
					newContainer && range.setEndAt( newContainer, CKEDITOR.POSITION_AFTER_START );
					splittingContainer = 0;
				}

				// Collapse range after insertion to end.
				range.collapse();
			}

			that.dontMoveCaret = dontMoveCaret;
			that.bogusNeededBlocks = bogusNeededBlocks;
		}

		function cleanupAfterInsertion( that ) {
			var range = that.range,
				node, testRange, parent, movedIntoInline,
				bogusNeededBlocks = that.bogusNeededBlocks,
				// Create a bookmark to defend against the following range deconstructing operations.
				bm = range.createBookmark();

			// Remove all elements that could be created while splitting nodes
			// with ranges at its start|end.
			// E.g. remove <div><p></p></div>
			// But not <div><p> </p></div>
			// And replace <div><p><span data="cke-bookmark"/></p></div> with found bookmark.
			while ( ( node = that.zombies.pop() ) ) {
				// Detached element.
				if ( !node.getParent() )
					continue;

				testRange = range.clone();
				testRange.moveToElementEditStart( node );
				testRange.removeEmptyBlocksAtEnd();
			}

			if ( bogusNeededBlocks ) {
				// Bring back all block bogus nodes.
				while ( ( node = bogusNeededBlocks.pop() ) )
					node.append( CKEDITOR.env.ie ? range.document.createText( '\u00a0' ) : range.document.createElement( 'br' ) );
			}

			// Eventually merge identical inline elements.
			while ( ( node = that.mergeCandidates.pop() ) )
				node.mergeSiblings();

			range.moveToBookmark( bm );

			// Rule 3.
			// Shrink range to the BEFOREEND of previous innermost editable node in source order.

			if ( !that.dontMoveCaret ) {
				node = getRangePrevious( range );

				while ( node && checkIfElement( node ) && !node.is( DTD.$empty ) ) {
					if ( node.isBlockBoundary() )
						range.moveToPosition( node, CKEDITOR.POSITION_BEFORE_END );
					else {
						// Don't move into inline element (which ends with a text node)
						// found which contains white-space at its end.
						// If not - move range's end to the end of this element.
						if ( isInline( node ) && node.getHtml().match( /(\s|&nbsp;)$/g ) ) {
							movedIntoInline = null;
							break;
						}

						movedIntoInline = range.clone();
						movedIntoInline.moveToPosition( node, CKEDITOR.POSITION_BEFORE_END );
					}

					node = node.getLast( isNotEmpty );
				}

				movedIntoInline && range.moveToRange( movedIntoInline );
			}

		}

		//
		// HELPERS ------------------------------------------------------------
		//

		function autoParagraphTag( editor ) {
			return ( editor.activeEnterMode != CKEDITOR.ENTER_BR && editor.config.autoParagraph !== false ) ? editor.activeEnterMode == CKEDITOR.ENTER_DIV ? 'div' : 'p' : false;
		}

		function checkIfElement( node ) {
			return node.type == CKEDITOR.NODE_ELEMENT;
		}

		function extractNodesData( dataWrapper, that ) {
			var node, sibling, nodeName, allowed,
				nodesData = [],
				startContainer = that.range.startContainer,
				path = that.range.startPath(),
				allowedNames = DTD[ startContainer.getName() ],
				nodeIndex = 0,
				nodesList = dataWrapper.getChildren(),
				nodesCount = nodesList.count(),
				firstNotAllowed = -1,
				lastNotAllowed = -1,
				lineBreak = 0,
				blockSibling;

			// Selection start within a list.
			var insideOfList = path.contains( DTD.$list );

			for ( ; nodeIndex < nodesCount; ++nodeIndex ) {
				node = nodesList.getItem( nodeIndex );

				if ( checkIfElement( node ) ) {
					nodeName = node.getName();

					// Extract only the list items, when insertion happens
					// inside of a list, reads as rearrange list items. (#7957)
					if ( insideOfList && nodeName in CKEDITOR.dtd.$list ) {
						nodesData = nodesData.concat( extractNodesData( node, that ) );
						continue;
					}

					allowed = !!allowedNames[ nodeName ];

					// Mark <brs data-cke-eol="1"> at the beginning and at the end.
					if ( nodeName == 'br' && node.data( 'cke-eol' ) && ( !nodeIndex || nodeIndex == nodesCount - 1 ) ) {
						sibling = nodeIndex ? nodesData[ nodeIndex - 1 ].node : nodesList.getItem( nodeIndex + 1 );

						// Line break has to have sibling which is not an <br>.
						lineBreak = sibling && ( !checkIfElement( sibling ) || !sibling.is( 'br' ) );
						// Line break has block element as a sibling.
						blockSibling = sibling && checkIfElement( sibling ) && DTD.$block[ sibling.getName() ];
					}

					if ( firstNotAllowed == -1 && !allowed )
						firstNotAllowed = nodeIndex;
					if ( !allowed )
						lastNotAllowed = nodeIndex;

					nodesData.push( {
						isElement: 1,
						isLineBreak: lineBreak,
						isBlock: node.isBlockBoundary(),
						hasBlockSibling: blockSibling,
						node: node,
						name: nodeName,
						allowed: allowed
					} );

					lineBreak = 0;
					blockSibling = 0;
				} else
					nodesData.push( { isElement:0,node:node,allowed:1 } );
			}

			// Mark first node that cannot be inserted directly into startContainer
			// and last node for which startContainer has to be split.
			if ( firstNotAllowed > -1 )
				nodesData[ firstNotAllowed ].firstNotAllowed = 1;
			if ( lastNotAllowed > -1 )
				nodesData[ lastNotAllowed ].lastNotAllowed = 1;

			return nodesData;
		}

		// TODO: Review content transformation rules on filtering element.
		function filterElement( element, parentName, isFirst, isLast ) {
			var nodes = filterElementInner( element, parentName ),
				nodes2 = [],
				nodesCount = nodes.length,
				nodeIndex = 0,
				node,
				afterSpace = 0,
				lastSpaceIndex = -1;

			// Remove duplicated spaces and spaces at the:
			// * beginnig if filtered element isFirst (isFirst that's going to be inserted)
			// * end if filtered element isLast.
			for ( ; nodeIndex < nodesCount; nodeIndex++ ) {
				node = nodes[ nodeIndex ];

				if ( node == ' ' ) {
					// Don't push doubled space and if it's leading space for insertion.
					if ( !afterSpace && !( isFirst && !nodeIndex ) ) {
						nodes2.push( new CKEDITOR.dom.text( ' ' ) );
						lastSpaceIndex = nodes2.length;
					}
					afterSpace = 1;
				} else {
					nodes2.push( node );
					afterSpace = 0;
				}
			}

			// Remove trailing space.
			if ( isLast && lastSpaceIndex == nodes2.length )
				nodes2.pop();

			return nodes2;
		}

		function filterElementInner( element, parentName ) {
			var nodes = [],
				children = element.getChildren(),
				childrenCount = children.count(),
				child,
				childIndex = 0,
				allowedNames = DTD[ parentName ],
				surroundBySpaces = !element.is( DTD.$inline ) || element.is( 'br' );

			if ( surroundBySpaces )
				nodes.push( ' ' );

			for ( ; childIndex < childrenCount; childIndex++ ) {
				child = children.getItem( childIndex );

				if ( checkIfElement( child ) && !child.is( allowedNames ) )
					nodes = nodes.concat( filterElementInner( child, parentName ) );
				else
					nodes.push( child );
			}

			if ( surroundBySpaces )
				nodes.push( ' ' );

			return nodes;
		}

		function getRangePrevious( range ) {
			return checkIfElement( range.startContainer ) && range.startContainer.getChild( range.startOffset - 1 );
		}

		function isInline( node ) {
			return node && checkIfElement( node ) && ( node.is( DTD.$removeEmpty ) || node.is( 'a' ) && !node.isBlockBoundary() );
		}

		var blockMergedTags = { p:1,div:1,h1:1,h2:1,h3:1,h4:1,h5:1,h6:1,ul:1,ol:1,li:1,pre:1,dl:1,blockquote:1 };

		// See rule 5. in TCs.
		// Initial situation:
		// <ul><li>AA^</li></ul><ul><li>BB</li></ul>
		// We're looking for 2nd <ul>, comparing with 1st <ul> and merging.
		// We're not merging if caret is between these elements.
		function mergeAncestorElementsOfSelectionEnds( range, blockLimit, startPath, endPath ) {
			var walkerRange = range.clone(),
				walker, nextNode, previousNode;

			walkerRange.setEndAt( blockLimit, CKEDITOR.POSITION_BEFORE_END );
			walker = new CKEDITOR.dom.walker( walkerRange );

			if ( ( nextNode = walker.next() )							// Find next source node
				&& checkIfElement( nextNode )							// which is an element
				&& blockMergedTags[ nextNode.getName() ]				// that can be merged.
				&& ( previousNode = nextNode.getPrevious() )			// Take previous one
				&& checkIfElement( previousNode )						// which also has to be an element.
				&& !previousNode.getParent().equals( range.startContainer ) // Fail if caret is on the same level.
																		// This means that caret is between these nodes.
				&& startPath.contains( previousNode )					// Elements path of start of selection has
				&& endPath.contains( nextNode )							// to contain prevNode and vice versa.
				&& nextNode.isIdentical( previousNode ) )				// Check if elements are identical.
			{
				// Merge blocks and repeat.
				nextNode.moveChildren( previousNode );
				nextNode.remove();
				mergeAncestorElementsOfSelectionEnds( range, blockLimit, startPath, endPath );
			}
		}

		// If last node that will be inserted is a block (but not a <br>)
		// and it will be inserted right before <br> remove this <br>.
		// Do the same for the first element that will be inserted and preceding <br>.
		function removeBrsAdjacentToPastedBlocks( nodesData, range ) {
			var succeedingNode = range.endContainer.getChild( range.endOffset ),
				precedingNode = range.endContainer.getChild( range.endOffset - 1 );

			if ( succeedingNode )
				remove( succeedingNode, nodesData[ nodesData.length - 1 ] );

			if ( precedingNode && remove( precedingNode, nodesData[ 0 ] ) ) {
				// If preceding <br> was removed - move range left.
				range.setEnd( range.endContainer, range.endOffset - 1 );
				range.collapse();
			}

			function remove( maybeBr, maybeBlockData ) {
				if ( maybeBlockData.isBlock && maybeBlockData.isElement && !maybeBlockData.node.is( 'br' ) &&
					checkIfElement( maybeBr ) && maybeBr.is( 'br' ) ) {
					maybeBr.remove();
					return 1;
				}
			}
		}

		// Return 1 if <br> should be skipped when inserting, 0 otherwise.
		function splitOnLineBreak( range, blockLimit, nodeData ) {
			var firstBlockAscendant, pos;

			if ( nodeData.hasBlockSibling )
				return 1;

			firstBlockAscendant = range.startContainer.getAscendant( DTD.$block, 1 );
			if ( !firstBlockAscendant || !firstBlockAscendant.is( { div:1,p:1 } ) )
				return 0;

			pos = firstBlockAscendant.getPosition( blockLimit );

			if ( pos == CKEDITOR.POSITION_IDENTICAL || pos == CKEDITOR.POSITION_CONTAINS )
				return 0;

			var newContainer = range.splitElement( firstBlockAscendant );
			range.moveToPosition( newContainer, CKEDITOR.POSITION_AFTER_START );

			return 1;
		}

		var stripSingleBlockTags = { p:1,div:1,h1:1,h2:1,h3:1,h4:1,h5:1,h6:1 },
			inlineButNotBr = CKEDITOR.tools.extend( {}, DTD.$inline );
		delete inlineButNotBr.br;

		// Rule 7.
		function stripBlockTagIfSingleLine( dataWrapper ) {
			var block, children;

			if ( dataWrapper.getChildCount() == 1 &&					// Only one node bein inserted.
				checkIfElement( block = dataWrapper.getFirst() ) &&		// And it's an element.
				block.is( stripSingleBlockTags ) )						// That's <p> or <div> or header.
			{
				// Check children not containing block.
				children = block.getElementsByTag( '*' );
				for ( var i = 0, child, count = children.count(); i < count; i++ ) {
					child = children.getItem( i );
					if ( !child.is( inlineButNotBr ) )
						return;
				}

				block.moveChildren( block.getParent( 1 ) );
				block.remove();
			}
		}

		function wrapDataWithInlineStyles( data, that ) {
			var element = that.inlineStylesPeak,
				doc = element.getDocument(),
				wrapper = doc.createText( '{cke-peak}' ),
				limit = that.inlineStylesRoot.getParent();

			while ( !element.equals( limit ) ) {
				wrapper = wrapper.appendTo( element.clone() );
				element = element.getParent();
			}

			// Don't use String.replace because it fails in IE7 if special replacement
			// characters ($$, $&, etc.) are in data (#10367).
			return wrapper.getOuterHtml().split( '{cke-peak}' ).join( data );
		}

		return insert;
	})();

	function beforeInsert( editable ) {
		// TODO: For unknown reason we must call directly on the editable to put the focus immediately.
		editable.editor.focus();

		editable.editor.fire( 'saveSnapshot' );
	}

	function afterInsert( editable, noScroll ) {
		var editor = editable.editor;

		// Scroll using selection, not ranges, to affect native pastes.
		!noScroll && editor.getSelection().scrollIntoView();

		// Save snaps after the whole execution completed.
		// This's a workaround for make DOM modification's happened after
		// 'insertElement' to be included either, e.g. Form-based dialogs' 'commitContents'
		// call.
		setTimeout( function() {
			editor.fire( 'saveSnapshot' );
		}, 0 );
	}

})();

/**
 * Whether the editor must output an empty value (`''`) if it's contents is made
 * by an empty paragraph only.
 *
 *		config.ignoreEmptyParagraph = false;
 *
 * @cfg {Boolean} [ignoreEmptyParagraph=true]
 * @member CKEDITOR.config
 */

/**
 * @event focus
 * @todo
 */

 /**
 * @event blur
 * @todo
 */
