/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

(function() {
	var guardElements = { table:1,ul:1,ol:1,blockquote:1,div:1 },
		directSelectionGuardElements = {},
		// All guard elements which can have a direction applied on them.
		allGuardElements = {};
	CKEDITOR.tools.extend( directSelectionGuardElements, guardElements, { tr:1,p:1,div:1,li:1 } );
	CKEDITOR.tools.extend( allGuardElements, directSelectionGuardElements, { td:1 } );

	function setToolbarStates( editor, path ) {
		var useComputedState = editor.config.useComputedState,
			selectedElement;

		useComputedState = useComputedState === undefined || useComputedState;

		// We can use computedState provided by the browser or traverse parents manually.
		if ( !useComputedState )
			selectedElement = getElementForDirection( path.lastElement, editor.editable() );

		selectedElement = selectedElement || path.block || path.blockLimit;

		// If we're having BODY here, user probably done CTRL+A, let's try to get the enclosed node, if any.
		if ( selectedElement.equals( editor.editable() ) ) {
			var enclosedNode = editor.getSelection().getRanges()[ 0 ].getEnclosedNode();
			enclosedNode && enclosedNode.type == CKEDITOR.NODE_ELEMENT && ( selectedElement = enclosedNode );
		}

		if ( !selectedElement )
			return;

		var selectionDir = useComputedState ? selectedElement.getComputedStyle( 'direction' ) : selectedElement.getStyle( 'direction' ) || selectedElement.getAttribute( 'dir' );

		editor.getCommand( 'bidirtl' ).setState( selectionDir == 'rtl' ? CKEDITOR.TRISTATE_ON : CKEDITOR.TRISTATE_OFF );
		editor.getCommand( 'bidiltr' ).setState( selectionDir == 'ltr' ? CKEDITOR.TRISTATE_ON : CKEDITOR.TRISTATE_OFF );
	}

	function handleMixedDirContent( editor, path ) {
		var directionNode = path.block || path.blockLimit || editor.editable();
		var pathDir = directionNode.getDirection( 1 );
		if ( pathDir != ( editor._.selDir || editor.lang.dir ) ) {
			editor._.selDir = pathDir;
			editor.fire( 'contentDirChanged', pathDir );
		}
	}

	// Returns element with possibility of applying the direction.
	// @param node
	function getElementForDirection( node, root ) {
		while ( node && !( node.getName() in allGuardElements || node.equals( root ) ) ) {
			var parent = node.getParent();
			if ( !parent )
				break;

			node = parent;
		}

		return node;
	}

	function switchDir( element, dir, editor, database ) {
		if ( element.isReadOnly() || element.equals( editor.editable() ) )
			return;

		// Mark this element as processed by switchDir.
		CKEDITOR.dom.element.setMarker( database, element, 'bidi_processed', 1 );

		// Check whether one of the ancestors has already been styled.
		var parent = element,
			editable = editor.editable();
		while ( ( parent = parent.getParent() ) && !parent.equals( editable ) ) {
			if ( parent.getCustomData( 'bidi_processed' ) ) {
				// Ancestor style must dominate.
				element.removeStyle( 'direction' );
				element.removeAttribute( 'dir' );
				return;
			}
		}

		var useComputedState = ( 'useComputedState' in editor.config ) ? editor.config.useComputedState : 1;

		var elementDir = useComputedState ? element.getComputedStyle( 'direction' ) : element.getStyle( 'direction' ) || element.hasAttribute( 'dir' );

		// Stop if direction is same as present.
		if ( elementDir == dir )
			return;

		// Clear direction on this element.
		element.removeStyle( 'direction' );

		// Do the second check when computed state is ON, to check
		// if we need to apply explicit direction on this element.
		if ( useComputedState ) {
			element.removeAttribute( 'dir' );
			if ( dir != element.getComputedStyle( 'direction' ) )
				element.setAttribute( 'dir', dir );
		} else
			// Set new direction for this element.
			element.setAttribute( 'dir', dir );

		editor.forceNextSelectionCheck();

		return;
	}

	function getFullySelected( range, elements, enterMode ) {
		var ancestor = range.getCommonAncestor( false, true );

		range = range.clone();
		range.enlarge( enterMode == CKEDITOR.ENTER_BR ? CKEDITOR.ENLARGE_LIST_ITEM_CONTENTS : CKEDITOR.ENLARGE_BLOCK_CONTENTS );

		if ( range.checkBoundaryOfElement( ancestor, CKEDITOR.START ) && range.checkBoundaryOfElement( ancestor, CKEDITOR.END ) ) {
			var parent;
			while ( ancestor && ancestor.type == CKEDITOR.NODE_ELEMENT && ( parent = ancestor.getParent() ) && parent.getChildCount() == 1 && !( ancestor.getName() in elements ) )
				ancestor = parent;

			return ancestor.type == CKEDITOR.NODE_ELEMENT && ( ancestor.getName() in elements ) && ancestor;
		}
	}

	function bidiCommand( dir ) {
		return {
			// It applies to a "block-like" context.
			context: 'p',
			allowedContent: {
				'h1 h2 h3 h4 h5 h6 table ul ol blockquote div tr p div li td': {
					propertiesOnly: true,
					attributes: 'dir'
				}
			},
			requiredContent: 'p[dir]',
			refresh: function( editor, path ) {
				setToolbarStates( editor, path );
				handleMixedDirContent( editor, path );
			},
			exec: function( editor ) {
				var selection = editor.getSelection(),
					enterMode = editor.config.enterMode,
					ranges = selection.getRanges();

				if ( ranges && ranges.length ) {
					var database = {};

					// Creates bookmarks for selection, as we may split some blocks.
					var bookmarks = selection.createBookmarks();

					var rangeIterator = ranges.createIterator(),
						range,
						i = 0;

					while ( ( range = rangeIterator.getNextRange( 1 ) ) ) {
						// Apply do directly selected elements from guardElements.
						var selectedElement = range.getEnclosedNode();

						// If this is not our element of interest, apply to fully selected elements from guardElements.
						if ( !selectedElement || selectedElement && !( selectedElement.type == CKEDITOR.NODE_ELEMENT && selectedElement.getName() in directSelectionGuardElements ) )
							selectedElement = getFullySelected( range, guardElements, enterMode );

						selectedElement && switchDir( selectedElement, dir, editor, database );

						var iterator, block;

						// Walker searching for guardElements.
						var walker = new CKEDITOR.dom.walker( range );

						var start = bookmarks[ i ].startNode,
							end = bookmarks[ i++ ].endNode;

						walker.evaluator = function( node ) {
							return !!( node.type == CKEDITOR.NODE_ELEMENT && node.getName() in guardElements && !( node.getName() == ( enterMode == CKEDITOR.ENTER_P ? 'p' : 'div' ) && node.getParent().type == CKEDITOR.NODE_ELEMENT && node.getParent().getName() == 'blockquote' )
							// Element must be fully included in the range as well. (#6485).
							&& node.getPosition( start ) & CKEDITOR.POSITION_FOLLOWING && ( ( node.getPosition( end ) & CKEDITOR.POSITION_PRECEDING + CKEDITOR.POSITION_CONTAINS ) == CKEDITOR.POSITION_PRECEDING ) );
						};

						while ( ( block = walker.next() ) )
							switchDir( block, dir, editor, database );

						iterator = range.createIterator();
						iterator.enlargeBr = enterMode != CKEDITOR.ENTER_BR;

						while ( ( block = iterator.getNextParagraph( enterMode == CKEDITOR.ENTER_P ? 'p' : 'div' ) ) )
							switchDir( block, dir, editor, database );
					}

					CKEDITOR.dom.element.clearAllMarkers( database );

					editor.forceNextSelectionCheck();
					// Restore selection position.
					selection.selectBookmarks( bookmarks );

					editor.focus();
				}
			}
		};
	}

	CKEDITOR.plugins.add( 'bidi', {
		lang: 'af,ar,bg,bn,bs,ca,cs,cy,da,de,el,en,en-au,en-ca,en-gb,eo,es,et,eu,fa,fi,fo,fr,fr-ca,gl,gu,he,hi,hr,hu,id,is,it,ja,ka,km,ko,ku,lt,lv,mk,mn,ms,nb,nl,no,pl,pt,pt-br,ro,ru,si,sk,sl,sq,sr,sr-latn,sv,th,tr,ug,uk,vi,zh,zh-cn', // %REMOVE_LINE_CORE%
		icons: 'bidiltr,bidirtl', // %REMOVE_LINE_CORE%
		hidpi: true, // %REMOVE_LINE_CORE%
		init: function( editor ) {
			if ( editor.blockless )
				return;

			// All buttons use the same code to register. So, to avoid
			// duplications, let's use this tool function.
			function addButtonCommand( buttonName, buttonLabel, commandName, commandDef, order ) {
				editor.addCommand( commandName, new CKEDITOR.command( editor, commandDef ) );

				if ( editor.ui.addButton ) {
					editor.ui.addButton( buttonName, {
						label: buttonLabel,
						command: commandName,
						toolbar: 'bidi,' + order
					});
				}
			}

			var lang = editor.lang.bidi;

			if ( editor.ui.addToolbarGroup )
				editor.ui.addToolbarGroup( 'bidi', 'align', 'paragraph' );

			addButtonCommand( 'BidiLtr', lang.ltr, 'bidiltr', bidiCommand( 'ltr' ), 10 );
			addButtonCommand( 'BidiRtl', lang.rtl, 'bidirtl', bidiCommand( 'rtl' ), 20 );

			editor.on( 'contentDom', function() {
				editor.document.on( 'dirChanged', function( evt ) {
					editor.fire( 'dirChanged', {
						node: evt.data,
						dir: evt.data.getDirection( 1 )
					});
				});
			});

			// Indicate that the current selection is in different direction than the UI.
			editor.on( 'contentDirChanged', function( evt ) {
				var func = ( editor.lang.dir != evt.data ? 'add' : 'remove' ) + 'Class';
				var toolbar = editor.ui.space( editor.config.toolbarLocation );
				if ( toolbar )
					toolbar[ func ]( 'cke_mixed_dir_content' );
			});
		}
	});

	// If the element direction changed, we need to switch the margins of
	// the element and all its children, so it will get really reflected
	// like a mirror. (#5910)
	function isOffline( el ) {
		var html = el.getDocument().getBody().getParent();
		while ( el ) {
			if ( el.equals( html ) )
				return false;
			el = el.getParent();
		}
		return true;
	}

	function dirChangeNotifier( org ) {
		var isAttribute = org == elementProto.setAttribute,
			isRemoveAttribute = org == elementProto.removeAttribute,
			dirStyleRegexp = /\bdirection\s*:\s*(.*?)\s*(:?$|;)/;

		return function( name, val ) {
			if ( !this.isReadOnly() ) {
				var orgDir;
				if ( ( name == ( isAttribute || isRemoveAttribute ? 'dir' : 'direction' ) || name == 'style' && ( isRemoveAttribute || dirStyleRegexp.test( val ) ) ) && !isOffline( this ) ) {
					orgDir = this.getDirection( 1 );
					var retval = org.apply( this, arguments );
					if ( orgDir != this.getDirection( 1 ) ) {
						this.getDocument().fire( 'dirChanged', this );
						return retval;
					}
				}
			}

			return org.apply( this, arguments );
		};
	}

	var elementProto = CKEDITOR.dom.element.prototype,
		methods = [ 'setStyle', 'removeStyle', 'setAttribute', 'removeAttribute' ];
	for ( var i = 0; i < methods.length; i++ )
		elementProto[ methods[ i ] ] = CKEDITOR.tools.override( elementProto[ methods[ i ] ], dirChangeNotifier );
})();

/**
 * Fired when the language direction of an element is changed.
 *
 * @event dirChanged
 * @member CKEDITOR.editor
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param data
 * @param {CKEDITOR.dom.node} data.node The element that is being changed.
 * @param {String} data.dir The new direction.
 */

/**
 * Fired when the language direction in the specific cursor position is changed
 *
 * @event contentDirChanged
 * @member CKEDITOR.editor
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param {String} data The direction in the current position.
 */
