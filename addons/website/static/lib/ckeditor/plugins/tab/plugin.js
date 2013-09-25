/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

(function() {
	var meta = {
		editorFocus: false,
		modes: { wysiwyg:1,source:1 }
	};

	var blurCommand = {
		exec: function( editor ) {
			editor.container.focusNext( true, editor.tabIndex );
		}
	};

	var blurBackCommand = {
		exec: function( editor ) {
			editor.container.focusPrevious( true, editor.tabIndex );
		}
	};

	function selectNextCellCommand( backward ) {
		return {
			editorFocus: false,
			canUndo: false,
			modes: { wysiwyg:1 },
			exec: function( editor ) {
				if ( editor.editable().hasFocus ) {
					var sel = editor.getSelection(),
						path = new CKEDITOR.dom.elementPath( sel.getCommonAncestor(), sel.root ),
						cell;

					if ( ( cell = path.contains( { td:1,th:1 }, 1 ) ) ) {
						var resultRange = editor.createRange(),
							next = CKEDITOR.tools.tryThese( function() {
								var row = cell.getParent(),
									next = row.$.cells[ cell.$.cellIndex + ( backward ? -1 : 1 ) ];

								// Invalid any empty value.
								next.parentNode.parentNode;
								return next;
							}, function() {
								var row = cell.getParent(),
									table = row.getAscendant( 'table' ),
									nextRow = table.$.rows[ row.$.rowIndex + ( backward ? -1 : 1 ) ];

								return nextRow.cells[ backward ? nextRow.cells.length - 1 : 0 ];
							});

						// Clone one more row at the end of table and select the first newly established cell.
						if ( !( next || backward ) ) {
							var table = cell.getAscendant( 'table' ).$,
								cells = cell.getParent().$.cells;

							var newRow = new CKEDITOR.dom.element( table.insertRow( -1 ), editor.document );

							for ( var i = 0, count = cells.length; i < count; i++ ) {
								var newCell = newRow.append( new CKEDITOR.dom.element( cells[ i ], editor.document ).clone( false, false ) );
								!CKEDITOR.env.ie && newCell.appendBogus();
							}

							resultRange.moveToElementEditStart( newRow );
						} else if ( next ) {
							next = new CKEDITOR.dom.element( next );
							resultRange.moveToElementEditStart( next );
							// Avoid selecting empty block makes the cursor blind.
							if ( !( resultRange.checkStartOfBlock() && resultRange.checkEndOfBlock() ) )
								resultRange.selectNodeContents( next );
						} else
							return true;

						resultRange.select( true );
						return true;
					}
				}

				return false;
			}
		};
	}

	CKEDITOR.plugins.add( 'tab', {
		init: function( editor ) {
			var tabTools = editor.config.enableTabKeyTools !== false,
				tabSpaces = editor.config.tabSpaces || 0,
				tabText = '';

			while ( tabSpaces-- )
				tabText += '\xa0';

			if ( tabText ) {
				editor.on( 'key', function( ev ) {
					if ( ev.data.keyCode == 9 ) // TAB
					{
						editor.insertHtml( tabText );
						ev.cancel();
					}
				});
			}

			if ( tabTools ) {
				editor.on( 'key', function( ev ) {
					if ( ev.data.keyCode == 9 && editor.execCommand( 'selectNextCell' ) || // TAB
					ev.data.keyCode == ( CKEDITOR.SHIFT + 9 ) && editor.execCommand( 'selectPreviousCell' ) ) // SHIFT+TAB
					ev.cancel();
				});
			}

			editor.addCommand( 'blur', CKEDITOR.tools.extend( blurCommand, meta ) );
			editor.addCommand( 'blurBack', CKEDITOR.tools.extend( blurBackCommand, meta ) );
			editor.addCommand( 'selectNextCell', selectNextCellCommand() );
			editor.addCommand( 'selectPreviousCell', selectNextCellCommand( true ) );
		}
	});
})();

/**
 * Moves the UI focus to the element following this element in the tabindex order.
 *
 *		var element = CKEDITOR.document.getById( 'example' );
 *		element.focusNext();
 *
 * @param {Boolean} [ignoreChildren=false]
 * @param {Number} [indexToUse]
 * @member CKEDITOR.dom.element
 */
CKEDITOR.dom.element.prototype.focusNext = function( ignoreChildren, indexToUse ) {
	var $ = this.$,
		curTabIndex = ( indexToUse === undefined ? this.getTabIndex() : indexToUse ),
		passedCurrent, enteredCurrent, elected, electedTabIndex, element, elementTabIndex;

	if ( curTabIndex <= 0 ) {
		// If this element has tabindex <= 0 then we must simply look for any
		// element following it containing tabindex=0.

		element = this.getNextSourceNode( ignoreChildren, CKEDITOR.NODE_ELEMENT );

		while ( element ) {
			if ( element.isVisible() && element.getTabIndex() === 0 ) {
				elected = element;
				break;
			}

			element = element.getNextSourceNode( false, CKEDITOR.NODE_ELEMENT );
		}
	} else {
		// If this element has tabindex > 0 then we must look for:
		//		1. An element following this element with the same tabindex.
		//		2. The first element in source other with the lowest tabindex
		//		   that is higher than this element tabindex.
		//		3. The first element with tabindex=0.

		element = this.getDocument().getBody().getFirst();

		while ( ( element = element.getNextSourceNode( false, CKEDITOR.NODE_ELEMENT ) ) ) {
			if ( !passedCurrent ) {
				if ( !enteredCurrent && element.equals( this ) ) {
					enteredCurrent = true;

					// Ignore this element, if required.
					if ( ignoreChildren ) {
						if ( !( element = element.getNextSourceNode( true, CKEDITOR.NODE_ELEMENT ) ) )
							break;
						passedCurrent = 1;
					}
				} else if ( enteredCurrent && !this.contains( element ) )
					passedCurrent = 1;
			}

			if ( !element.isVisible() || ( elementTabIndex = element.getTabIndex() ) < 0 )
				continue;

			if ( passedCurrent && elementTabIndex == curTabIndex ) {
				elected = element;
				break;
			}

			if ( elementTabIndex > curTabIndex && ( !elected || !electedTabIndex || elementTabIndex < electedTabIndex ) ) {
				elected = element;
				electedTabIndex = elementTabIndex;
			} else if ( !elected && elementTabIndex === 0 ) {
				elected = element;
				electedTabIndex = elementTabIndex;
			}
		}
	}

	if ( elected )
		elected.focus();
};

/**
 * Moves the UI focus to the element before this element in the tabindex order.
 *
 *		var element = CKEDITOR.document.getById( 'example' );
 *		element.focusPrevious();
 *
 * @param {Boolean} [ignoreChildren=false]
 * @param {Number} [indexToUse]
 * @member CKEDITOR.dom.element
 */
CKEDITOR.dom.element.prototype.focusPrevious = function( ignoreChildren, indexToUse ) {
	var $ = this.$,
		curTabIndex = ( indexToUse === undefined ? this.getTabIndex() : indexToUse ),
		passedCurrent, enteredCurrent, elected,
		electedTabIndex = 0,
		elementTabIndex;

	var element = this.getDocument().getBody().getLast();

	while ( ( element = element.getPreviousSourceNode( false, CKEDITOR.NODE_ELEMENT ) ) ) {
		if ( !passedCurrent ) {
			if ( !enteredCurrent && element.equals( this ) ) {
				enteredCurrent = true;

				// Ignore this element, if required.
				if ( ignoreChildren ) {
					if ( !( element = element.getPreviousSourceNode( true, CKEDITOR.NODE_ELEMENT ) ) )
						break;
					passedCurrent = 1;
				}
			} else if ( enteredCurrent && !this.contains( element ) )
				passedCurrent = 1;
		}

		if ( !element.isVisible() || ( elementTabIndex = element.getTabIndex() ) < 0 )
			continue;

		if ( curTabIndex <= 0 ) {
			// If this element has tabindex <= 0 then we must look for:
			//		1. An element before this one containing tabindex=0.
			//		2. The last element with the highest tabindex.

			if ( passedCurrent && elementTabIndex === 0 ) {
				elected = element;
				break;
			}

			if ( elementTabIndex > electedTabIndex ) {
				elected = element;
				electedTabIndex = elementTabIndex;
			}
		} else {
			// If this element has tabindex > 0 we must look for:
			//		1. An element preceeding this one, with the same tabindex.
			//		2. The last element in source other with the highest tabindex
			//		   that is lower than this element tabindex.

			if ( passedCurrent && elementTabIndex == curTabIndex ) {
				elected = element;
				break;
			}

			if ( elementTabIndex < curTabIndex && ( !elected || elementTabIndex > electedTabIndex ) ) {
				elected = element;
				electedTabIndex = elementTabIndex;
			}
		}
	}

	if ( elected )
		elected.focus();
};

/**
 * Intructs the editor to add a number of spaces (`&nbsp;`) to the text when
 * hitting the *TAB* key. If set to zero, the *TAB* key will be used to move the
 * cursor focus to the next element in the page, out of the editor focus.
 *
 *		config.tabSpaces = 4;
 *
 * @cfg {Number} [tabSpaces=0]
 * @member CKEDITOR.config
 */

/**
 * Allow context-sensitive tab key behaviors, including the following scenarios:
 *
 * When selection is anchored inside **table cells**:
 *
 * * If *TAB* is pressed, select the contents of the "next" cell. If in the last
 *     cell in the table, add a new row to it and focus its first cell.
 * * If *SHIFT+TAB* is pressed, select the contents of the "previous" cell.
 *     Do nothing when it's in the first cell.
 *
 * Example:
 *
 *		config.enableTabKeyTools = false;
 *
 * @cfg {Boolean} [enableTabKeyTools=true]
 * @member CKEDITOR.config
 */

// If the TAB key is not supposed to be enabled for navigation, the following
// settings could be used alternatively:
// config.keystrokes.push(
//	[ CKEDITOR.ALT + 38 /*Arrow Up*/, 'selectPreviousCell' ],
//	[ CKEDITOR.ALT + 40 /*Arrow Down*/, 'selectNextCell' ]
// );
