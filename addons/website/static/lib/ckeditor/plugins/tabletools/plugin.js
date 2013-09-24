/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

(function() {
	var cellNodeRegex = /^(?:td|th)$/;

	function getSelectedCells( selection ) {
		var ranges = selection.getRanges();
		var retval = [];
		var database = {};

		function moveOutOfCellGuard( node ) {
			// Apply to the first cell only.
			if ( retval.length > 0 )
				return;

			// If we are exiting from the first </td>, then the td should definitely be
			// included.
			if ( node.type == CKEDITOR.NODE_ELEMENT && cellNodeRegex.test( node.getName() ) && !node.getCustomData( 'selected_cell' ) ) {
				CKEDITOR.dom.element.setMarker( database, node, 'selected_cell', true );
				retval.push( node );
			}
		}

		for ( var i = 0; i < ranges.length; i++ ) {
			var range = ranges[ i ];

			if ( range.collapsed ) {
				// Walker does not handle collapsed ranges yet - fall back to old API.
				var startNode = range.getCommonAncestor();
				var nearestCell = startNode.getAscendant( 'td', true ) || startNode.getAscendant( 'th', true );
				if ( nearestCell )
					retval.push( nearestCell );
			} else {
				var walker = new CKEDITOR.dom.walker( range );
				var node;
				walker.guard = moveOutOfCellGuard;

				while ( ( node = walker.next() ) ) {
					// If may be possible for us to have a range like this:
					// <td>^1</td><td>^2</td>
					// The 2nd td shouldn't be included.
					//
					// So we have to take care to include a td we've entered only when we've
					// walked into its children.

					if ( node.type != CKEDITOR.NODE_ELEMENT || !node.is( CKEDITOR.dtd.table ) ) {
						var parent = node.getAscendant( 'td', true ) || node.getAscendant( 'th', true );
						if ( parent && !parent.getCustomData( 'selected_cell' ) ) {
							CKEDITOR.dom.element.setMarker( database, parent, 'selected_cell', true );
							retval.push( parent );
						}
					}
				}
			}
		}

		CKEDITOR.dom.element.clearAllMarkers( database );

		return retval;
	}

	function getFocusElementAfterDelCells( cellsToDelete ) {
		var i = 0,
			last = cellsToDelete.length - 1,
			database = {},
			cell, focusedCell, tr;

		while ( ( cell = cellsToDelete[ i++ ] ) )
			CKEDITOR.dom.element.setMarker( database, cell, 'delete_cell', true );

		// 1.first we check left or right side focusable cell row by row;
		i = 0;
		while ( ( cell = cellsToDelete[ i++ ] ) ) {
			if ( ( focusedCell = cell.getPrevious() ) && !focusedCell.getCustomData( 'delete_cell' ) || ( focusedCell = cell.getNext() ) && !focusedCell.getCustomData( 'delete_cell' ) ) {
				CKEDITOR.dom.element.clearAllMarkers( database );
				return focusedCell;
			}
		}

		CKEDITOR.dom.element.clearAllMarkers( database );

		// 2. then we check the toppest row (outside the selection area square) focusable cell
		tr = cellsToDelete[ 0 ].getParent();
		if ( ( tr = tr.getPrevious() ) )
			return tr.getLast();

		// 3. last we check the lowerest  row focusable cell
		tr = cellsToDelete[ last ].getParent();
		if ( ( tr = tr.getNext() ) )
			return tr.getChild( 0 );

		return null;
	}

	function insertRow( selection, insertBefore ) {
		var cells = getSelectedCells( selection ),
			firstCell = cells[ 0 ],
			table = firstCell.getAscendant( 'table' ),
			doc = firstCell.getDocument(),
			startRow = cells[ 0 ].getParent(),
			startRowIndex = startRow.$.rowIndex,
			lastCell = cells[ cells.length - 1 ],
			endRowIndex = lastCell.getParent().$.rowIndex + lastCell.$.rowSpan - 1,
			endRow = new CKEDITOR.dom.element( table.$.rows[ endRowIndex ] ),
			rowIndex = insertBefore ? startRowIndex : endRowIndex,
			row = insertBefore ? startRow : endRow;

		var map = CKEDITOR.tools.buildTableMap( table ),
			cloneRow = map[ rowIndex ],
			nextRow = insertBefore ? map[ rowIndex - 1 ] : map[ rowIndex + 1 ],
			width = map[ 0 ].length;

		var newRow = doc.createElement( 'tr' );
		for ( var i = 0; cloneRow[ i ] && i < width; i++ ) {
			var cell;
			// Check whether there's a spanning row here, do not break it.
			if ( cloneRow[ i ].rowSpan > 1 && nextRow && cloneRow[ i ] == nextRow[ i ] ) {
				cell = cloneRow[ i ];
				cell.rowSpan += 1;
			} else {
				cell = new CKEDITOR.dom.element( cloneRow[ i ] ).clone();
				cell.removeAttribute( 'rowSpan' );
				!CKEDITOR.env.ie && cell.appendBogus();
				newRow.append( cell );
				cell = cell.$;
			}

			i += cell.colSpan - 1;
		}

		insertBefore ? newRow.insertBefore( row ) : newRow.insertAfter( row );
	}

	function deleteRows( selectionOrRow ) {
		if ( selectionOrRow instanceof CKEDITOR.dom.selection ) {
			var cells = getSelectedCells( selectionOrRow ),
				firstCell = cells[ 0 ],
				table = firstCell.getAscendant( 'table' ),
				map = CKEDITOR.tools.buildTableMap( table ),
				startRow = cells[ 0 ].getParent(),
				startRowIndex = startRow.$.rowIndex,
				lastCell = cells[ cells.length - 1 ],
				endRowIndex = lastCell.getParent().$.rowIndex + lastCell.$.rowSpan - 1,
				rowsToDelete = [];

			// Delete cell or reduce cell spans by checking through the table map.
			for ( var i = startRowIndex; i <= endRowIndex; i++ ) {
				var mapRow = map[ i ],
					row = new CKEDITOR.dom.element( table.$.rows[ i ] );

				for ( var j = 0; j < mapRow.length; j++ ) {
					var cell = new CKEDITOR.dom.element( mapRow[ j ] ),
						cellRowIndex = cell.getParent().$.rowIndex;

					if ( cell.$.rowSpan == 1 )
						cell.remove();
					// Row spanned cell.
					else {
						// Span row of the cell, reduce spanning.
						cell.$.rowSpan -= 1;
						// Root row of the cell, root cell to next row.
						if ( cellRowIndex == i ) {
							var nextMapRow = map[ i + 1 ];
							nextMapRow[ j - 1 ] ? cell.insertAfter( new CKEDITOR.dom.element( nextMapRow[ j - 1 ] ) ) : new CKEDITOR.dom.element( table.$.rows[ i + 1 ] ).append( cell, 1 );
						}
					}

					j += cell.$.colSpan - 1;
				}

				rowsToDelete.push( row );
			}

			var rows = table.$.rows;

			// Where to put the cursor after rows been deleted?
			// 1. Into next sibling row if any;
			// 2. Into previous sibling row if any;
			// 3. Into table's parent element if it's the very last row.
			var cursorPosition = new CKEDITOR.dom.element( rows[ endRowIndex + 1 ] || ( startRowIndex > 0 ? rows[ startRowIndex - 1 ] : null ) || table.$.parentNode );

			for ( i = rowsToDelete.length; i >= 0; i-- )
				deleteRows( rowsToDelete[ i ] );

			return cursorPosition;
		} else if ( selectionOrRow instanceof CKEDITOR.dom.element ) {
			table = selectionOrRow.getAscendant( 'table' );

			if ( table.$.rows.length == 1 )
				table.remove();
			else
				selectionOrRow.remove();
		}

		return null;
	}

	function getCellColIndex( cell, isStart ) {
		var row = cell.getParent(),
			rowCells = row.$.cells;

		var colIndex = 0;
		for ( var i = 0; i < rowCells.length; i++ ) {
			var mapCell = rowCells[ i ];
			colIndex += isStart ? 1 : mapCell.colSpan;
			if ( mapCell == cell.$ )
				break;
		}

		return colIndex - 1;
	}

	function getColumnsIndices( cells, isStart ) {
		var retval = isStart ? Infinity : 0;
		for ( var i = 0; i < cells.length; i++ ) {
			var colIndex = getCellColIndex( cells[ i ], isStart );
			if ( isStart ? colIndex < retval : colIndex > retval )
				retval = colIndex;
		}
		return retval;
	}

	function insertColumn( selection, insertBefore ) {
		var cells = getSelectedCells( selection ),
			firstCell = cells[ 0 ],
			table = firstCell.getAscendant( 'table' ),
			startCol = getColumnsIndices( cells, 1 ),
			lastCol = getColumnsIndices( cells ),
			colIndex = insertBefore ? startCol : lastCol;

		var map = CKEDITOR.tools.buildTableMap( table ),
			cloneCol = [],
			nextCol = [],
			height = map.length;

		for ( var i = 0; i < height; i++ ) {
			cloneCol.push( map[ i ][ colIndex ] );
			var nextCell = insertBefore ? map[ i ][ colIndex - 1 ] : map[ i ][ colIndex + 1 ];
			nextCol.push( nextCell );
		}

		for ( i = 0; i < height; i++ ) {
			var cell;

			if ( !cloneCol[ i ] )
				continue;

			// Check whether there's a spanning column here, do not break it.
			if ( cloneCol[ i ].colSpan > 1 && nextCol[ i ] == cloneCol[ i ] ) {
				cell = cloneCol[ i ];
				cell.colSpan += 1;
			} else {
				cell = new CKEDITOR.dom.element( cloneCol[ i ] ).clone();
				cell.removeAttribute( 'colSpan' );
				!CKEDITOR.env.ie && cell.appendBogus();
				cell[ insertBefore ? 'insertBefore' : 'insertAfter' ].call( cell, new CKEDITOR.dom.element( cloneCol[ i ] ) );
				cell = cell.$;
			}

			i += cell.rowSpan - 1;
		}
	}

	function deleteColumns( selectionOrCell ) {
		var cells = getSelectedCells( selectionOrCell ),
			firstCell = cells[ 0 ],
			lastCell = cells[ cells.length - 1 ],
			table = firstCell.getAscendant( 'table' ),
			map = CKEDITOR.tools.buildTableMap( table ),
			startColIndex, endColIndex,
			rowsToDelete = [];

		// Figure out selected cells' column indices.
		for ( var i = 0, rows = map.length; i < rows; i++ ) {
			for ( var j = 0, cols = map[ i ].length; j < cols; j++ ) {
				if ( map[ i ][ j ] == firstCell.$ )
					startColIndex = j;
				if ( map[ i ][ j ] == lastCell.$ )
					endColIndex = j;
			}
		}

		// Delete cell or reduce cell spans by checking through the table map.
		for ( i = startColIndex; i <= endColIndex; i++ ) {
			for ( j = 0; j < map.length; j++ ) {
				var mapRow = map[ j ],
					row = new CKEDITOR.dom.element( table.$.rows[ j ] ),
					cell = new CKEDITOR.dom.element( mapRow[ i ] );

				if ( cell.$ ) {
					if ( cell.$.colSpan == 1 )
						cell.remove();
					// Reduce the col spans.
					else
						cell.$.colSpan -= 1;

					j += cell.$.rowSpan - 1;

					if ( !row.$.cells.length )
						rowsToDelete.push( row );
				}
			}
		}

		var firstRowCells = table.$.rows[ 0 ] && table.$.rows[ 0 ].cells;

		// Where to put the cursor after columns been deleted?
		// 1. Into next cell of the first row if any;
		// 2. Into previous cell of the first row if any;
		// 3. Into table's parent element;
		var cursorPosition = new CKEDITOR.dom.element( firstRowCells[ startColIndex ] || ( startColIndex ? firstRowCells[ startColIndex - 1 ] : table.$.parentNode ) );

		// Delete table rows only if all columns are gone (do not remove empty row).
		if ( rowsToDelete.length == rows )
			table.remove();

		return cursorPosition;
	}

	function getFocusElementAfterDelCols( cells ) {
		var cellIndexList = [],
			table = cells[ 0 ] && cells[ 0 ].getAscendant( 'table' ),
			i, length, targetIndex, targetCell;

		// get the cellIndex list of delete cells
		for ( i = 0, length = cells.length; i < length; i++ )
			cellIndexList.push( cells[ i ].$.cellIndex );

		// get the focusable column index
		cellIndexList.sort();
		for ( i = 1, length = cellIndexList.length; i < length; i++ ) {
			if ( cellIndexList[ i ] - cellIndexList[ i - 1 ] > 1 ) {
				targetIndex = cellIndexList[ i - 1 ] + 1;
				break;
			}
		}

		if ( !targetIndex )
			targetIndex = cellIndexList[ 0 ] > 0 ? ( cellIndexList[ 0 ] - 1 ) : ( cellIndexList[ cellIndexList.length - 1 ] + 1 );

		// scan row by row to get the target cell
		var rows = table.$.rows;
		for ( i = 0, length = rows.length; i < length; i++ ) {
			targetCell = rows[ i ].cells[ targetIndex ];
			if ( targetCell )
				break;
		}

		return targetCell ? new CKEDITOR.dom.element( targetCell ) : table.getPrevious();
	}

	function insertCell( selection, insertBefore ) {
		var startElement = selection.getStartElement();
		var cell = startElement.getAscendant( 'td', 1 ) || startElement.getAscendant( 'th', 1 );

		if ( !cell )
			return;

		// Create the new cell element to be added.
		var newCell = cell.clone();
		if ( !CKEDITOR.env.ie )
			newCell.appendBogus();

		if ( insertBefore )
			newCell.insertBefore( cell );
		else
			newCell.insertAfter( cell );
	}

	function deleteCells( selectionOrCell ) {
		if ( selectionOrCell instanceof CKEDITOR.dom.selection ) {
			var cellsToDelete = getSelectedCells( selectionOrCell );
			var table = cellsToDelete[ 0 ] && cellsToDelete[ 0 ].getAscendant( 'table' );
			var cellToFocus = getFocusElementAfterDelCells( cellsToDelete );

			for ( var i = cellsToDelete.length - 1; i >= 0; i-- )
				deleteCells( cellsToDelete[ i ] );

			if ( cellToFocus )
				placeCursorInCell( cellToFocus, true );
			else if ( table )
				table.remove();
		} else if ( selectionOrCell instanceof CKEDITOR.dom.element ) {
			var tr = selectionOrCell.getParent();
			if ( tr.getChildCount() == 1 )
				tr.remove();
			else
				selectionOrCell.remove();
		}
	}

	// Remove filler at end and empty spaces around the cell content.
	function trimCell( cell ) {
		var bogus = cell.getBogus();
		bogus && bogus.remove();
		cell.trim();
	}

	function placeCursorInCell( cell, placeAtEnd ) {
		var range = new CKEDITOR.dom.range( cell.getDocument() );
		if ( !range[ 'moveToElementEdit' + ( placeAtEnd ? 'End' : 'Start' ) ]( cell ) ) {
			range.selectNodeContents( cell );
			range.collapse( placeAtEnd ? false : true );
		}
		range.select( true );
	}

	function cellInRow( tableMap, rowIndex, cell ) {
		var oRow = tableMap[ rowIndex ];
		if ( typeof cell == 'undefined' )
			return oRow;

		for ( var c = 0; oRow && c < oRow.length; c++ ) {
			if ( cell.is && oRow[ c ] == cell.$ )
				return c;
			else if ( c == cell )
				return new CKEDITOR.dom.element( oRow[ c ] );
		}
		return cell.is ? -1 : null;
	}

	function cellInCol( tableMap, colIndex ) {
		var oCol = [];
		for ( var r = 0; r < tableMap.length; r++ ) {
			var row = tableMap[ r ];
			oCol.push( row[ colIndex ] );

			// Avoid adding duplicate cells.
			if ( row[ colIndex ].rowSpan > 1 )
				r += row[ colIndex ].rowSpan - 1;
		}
		return oCol;
	}

	function mergeCells( selection, mergeDirection, isDetect ) {
		var cells = getSelectedCells( selection );

		// Invalid merge request if:
		// 1. In batch mode despite that less than two selected.
		// 2. In solo mode while not exactly only one selected.
		// 3. Cells distributed in different table groups (e.g. from both thead and tbody).
		var commonAncestor;
		if ( ( mergeDirection ? cells.length != 1 : cells.length < 2 ) || ( commonAncestor = selection.getCommonAncestor() ) && commonAncestor.type == CKEDITOR.NODE_ELEMENT && commonAncestor.is( 'table' ) ) {
			return false;
		}

		var cell,
			firstCell = cells[ 0 ],
			table = firstCell.getAscendant( 'table' ),
			map = CKEDITOR.tools.buildTableMap( table ),
			mapHeight = map.length,
			mapWidth = map[ 0 ].length,
			startRow = firstCell.getParent().$.rowIndex,
			startColumn = cellInRow( map, startRow, firstCell );

		if ( mergeDirection ) {
			var targetCell;
			try {
				var rowspan = parseInt( firstCell.getAttribute( 'rowspan' ), 10 ) || 1;
				var colspan = parseInt( firstCell.getAttribute( 'colspan' ), 10 ) || 1;

				targetCell = map[ mergeDirection == 'up' ? ( startRow - rowspan ) : mergeDirection == 'down' ? ( startRow + rowspan ) : startRow ][
					mergeDirection == 'left' ?
						( startColumn - colspan ) :
					mergeDirection == 'right' ? ( startColumn + colspan ) : startColumn ];

			} catch ( er ) {
				return false;
			}

			// 1. No cell could be merged.
			// 2. Same cell actually.
			if ( !targetCell || firstCell.$ == targetCell )
				return false;

			// Sort in map order regardless of the DOM sequence.
			cells[ ( mergeDirection == 'up' || mergeDirection == 'left' ) ? 'unshift' : 'push' ]( new CKEDITOR.dom.element( targetCell ) );
		}

		// Start from here are merging way ignorance (merge up/right, batch merge).
		var doc = firstCell.getDocument(),
			lastRowIndex = startRow,
			totalRowSpan = 0,
			totalColSpan = 0,
			// Use a documentFragment as buffer when appending cell contents.
			frag = !isDetect && new CKEDITOR.dom.documentFragment( doc ),
			dimension = 0;

		for ( var i = 0; i < cells.length; i++ ) {
			cell = cells[ i ];

			var tr = cell.getParent(),
				cellFirstChild = cell.getFirst(),
				colSpan = cell.$.colSpan,
				rowSpan = cell.$.rowSpan,
				rowIndex = tr.$.rowIndex,
				colIndex = cellInRow( map, rowIndex, cell );

			// Accumulated the actual places taken by all selected cells.
			dimension += colSpan * rowSpan;
			// Accumulated the maximum virtual spans from column and row.
			totalColSpan = Math.max( totalColSpan, colIndex - startColumn + colSpan );
			totalRowSpan = Math.max( totalRowSpan, rowIndex - startRow + rowSpan );

			if ( !isDetect ) {
				// Trim all cell fillers and check to remove empty cells.
				if ( trimCell( cell ), cell.getChildren().count() ) {
					// Merge vertically cells as two separated paragraphs.
					if ( rowIndex != lastRowIndex && cellFirstChild && !( cellFirstChild.isBlockBoundary && cellFirstChild.isBlockBoundary( { br:1 } ) ) ) {
						var last = frag.getLast( CKEDITOR.dom.walker.whitespaces( true ) );
						if ( last && !( last.is && last.is( 'br' ) ) )
							frag.append( 'br' );
					}

					cell.moveChildren( frag );
				}
				i ? cell.remove() : cell.setHtml( '' );
			}
			lastRowIndex = rowIndex;
		}

		if ( !isDetect ) {
			frag.moveChildren( firstCell );

			if ( !CKEDITOR.env.ie )
				firstCell.appendBogus();

			if ( totalColSpan >= mapWidth )
				firstCell.removeAttribute( 'rowSpan' );
			else
				firstCell.$.rowSpan = totalRowSpan;

			if ( totalRowSpan >= mapHeight )
				firstCell.removeAttribute( 'colSpan' );
			else
				firstCell.$.colSpan = totalColSpan;

			// Swip empty <tr> left at the end of table due to the merging.
			var trs = new CKEDITOR.dom.nodeList( table.$.rows ),
				count = trs.count();

			for ( i = count - 1; i >= 0; i-- ) {
				var tailTr = trs.getItem( i );
				if ( !tailTr.$.cells.length ) {
					tailTr.remove();
					count++;
					continue;
				}
			}

			return firstCell;
		}
		// Be able to merge cells only if actual dimension of selected
		// cells equals to the caculated rectangle.
		else
			return ( totalRowSpan * totalColSpan ) == dimension;
	}

	function verticalSplitCell( selection, isDetect ) {
		var cells = getSelectedCells( selection );
		if ( cells.length > 1 )
			return false;
		else if ( isDetect )
			return true;

		var cell = cells[ 0 ],
			tr = cell.getParent(),
			table = tr.getAscendant( 'table' ),
			map = CKEDITOR.tools.buildTableMap( table ),
			rowIndex = tr.$.rowIndex,
			colIndex = cellInRow( map, rowIndex, cell ),
			rowSpan = cell.$.rowSpan,
			newCell, newRowSpan, newCellRowSpan, newRowIndex;

		if ( rowSpan > 1 ) {
			newRowSpan = Math.ceil( rowSpan / 2 );
			newCellRowSpan = Math.floor( rowSpan / 2 );
			newRowIndex = rowIndex + newRowSpan;
			var newCellTr = new CKEDITOR.dom.element( table.$.rows[ newRowIndex ] ),
				newCellRow = cellInRow( map, newRowIndex ),
				candidateCell;

			newCell = cell.clone();

			// Figure out where to insert the new cell by checking the vitual row.
			for ( var c = 0; c < newCellRow.length; c++ ) {
				candidateCell = newCellRow[ c ];
				// Catch first cell actually following the column.
				if ( candidateCell.parentNode == newCellTr.$ && c > colIndex ) {
					newCell.insertBefore( new CKEDITOR.dom.element( candidateCell ) );
					break;
				} else
					candidateCell = null;
			}

			// The destination row is empty, append at will.
			if ( !candidateCell )
				newCellTr.append( newCell, true );
		} else {
			newCellRowSpan = newRowSpan = 1;

			newCellTr = tr.clone();
			newCellTr.insertAfter( tr );
			newCellTr.append( newCell = cell.clone() );

			var cellsInSameRow = cellInRow( map, rowIndex );
			for ( var i = 0; i < cellsInSameRow.length; i++ )
				cellsInSameRow[ i ].rowSpan++;
		}

		if ( !CKEDITOR.env.ie )
			newCell.appendBogus();

		cell.$.rowSpan = newRowSpan;
		newCell.$.rowSpan = newCellRowSpan;
		if ( newRowSpan == 1 )
			cell.removeAttribute( 'rowSpan' );
		if ( newCellRowSpan == 1 )
			newCell.removeAttribute( 'rowSpan' );

		return newCell;
	}

	function horizontalSplitCell( selection, isDetect ) {
		var cells = getSelectedCells( selection );
		if ( cells.length > 1 )
			return false;
		else if ( isDetect )
			return true;

		var cell = cells[ 0 ],
			tr = cell.getParent(),
			table = tr.getAscendant( 'table' ),
			map = CKEDITOR.tools.buildTableMap( table ),
			rowIndex = tr.$.rowIndex,
			colIndex = cellInRow( map, rowIndex, cell ),
			colSpan = cell.$.colSpan,
			newCell, newColSpan, newCellColSpan;

		if ( colSpan > 1 ) {
			newColSpan = Math.ceil( colSpan / 2 );
			newCellColSpan = Math.floor( colSpan / 2 );
		} else {
			newCellColSpan = newColSpan = 1;
			var cellsInSameCol = cellInCol( map, colIndex );
			for ( var i = 0; i < cellsInSameCol.length; i++ )
				cellsInSameCol[ i ].colSpan++;
		}
		newCell = cell.clone();
		newCell.insertAfter( cell );
		if ( !CKEDITOR.env.ie )
			newCell.appendBogus();

		cell.$.colSpan = newColSpan;
		newCell.$.colSpan = newCellColSpan;
		if ( newColSpan == 1 )
			cell.removeAttribute( 'colSpan' );
		if ( newCellColSpan == 1 )
			newCell.removeAttribute( 'colSpan' );

		return newCell;
	}
	// Context menu on table caption incorrect (#3834)
	var contextMenuTags = { thead:1,tbody:1,tfoot:1,td:1,tr:1,th:1 };

	CKEDITOR.plugins.tabletools = {
		requires: 'table,dialog,contextmenu',
		init: function( editor ) {
			var lang = editor.lang.table;

			function createDef( def ) {
				return CKEDITOR.tools.extend( def || {}, {
					contextSensitive: 1,
					refresh: function( editor, path ) {
						this.setState( path.contains( { td:1,th:1 }, 1 ) ? CKEDITOR.TRISTATE_OFF : CKEDITOR.TRISTATE_DISABLED );
					}
				});
			}
			function addCmd( name, def ) {
				var cmd = editor.addCommand( name, def );
				editor.addFeature( cmd );
			}

			addCmd( 'cellProperties', new CKEDITOR.dialogCommand( 'cellProperties', createDef( {
				allowedContent: 'td th{width,height,border-color,background-color,white-space,vertical-align,text-align}[colspan,rowspan]',
				requiredContent: 'table'
			} ) ) );
			CKEDITOR.dialog.add( 'cellProperties', this.path + 'dialogs/tableCell.js' );

			addCmd( 'rowDelete', createDef( {
				requiredContent: 'table',
				exec: function( editor ) {
					var selection = editor.getSelection();
					placeCursorInCell( deleteRows( selection ) );
				}
			} ) );

			addCmd( 'rowInsertBefore', createDef( {
				requiredContent: 'table',
				exec: function( editor ) {
					var selection = editor.getSelection();
					insertRow( selection, true );
				}
			} ) );

			addCmd( 'rowInsertAfter', createDef( {
				requiredContent: 'table',
				exec: function( editor ) {
					var selection = editor.getSelection();
					insertRow( selection );
				}
			} ) );

			addCmd( 'columnDelete', createDef( {
				requiredContent: 'table',
				exec: function( editor ) {
					var selection = editor.getSelection();
					var element = deleteColumns( selection );
					element && placeCursorInCell( element, true );
				}
			} ) );

			addCmd( 'columnInsertBefore', createDef( {
				requiredContent: 'table',
				exec: function( editor ) {
					var selection = editor.getSelection();
					insertColumn( selection, true );
				}
			} ) );

			addCmd( 'columnInsertAfter', createDef( {
				requiredContent: 'table',
				exec: function( editor ) {
					var selection = editor.getSelection();
					insertColumn( selection );
				}
			} ) );

			addCmd( 'cellDelete', createDef( {
				requiredContent: 'table',
				exec: function( editor ) {
					var selection = editor.getSelection();
					deleteCells( selection );
				}
			} ) );

			addCmd( 'cellMerge', createDef( {
				allowedContent: 'td[colspan,rowspan]',
				requiredContent: 'td[colspan,rowspan]',
				exec: function( editor ) {
					placeCursorInCell( mergeCells( editor.getSelection() ), true );
				}
			} ) );

			addCmd( 'cellMergeRight', createDef( {
				allowedContent: 'td[colspan]',
				requiredContent: 'td[colspan]',
				exec: function( editor ) {
					placeCursorInCell( mergeCells( editor.getSelection(), 'right' ), true );
				}
			} ) );

			addCmd( 'cellMergeDown', createDef( {
				allowedContent: 'td[rowspan]',
				requiredContent: 'td[rowspan]',
				exec: function( editor ) {
					placeCursorInCell( mergeCells( editor.getSelection(), 'down' ), true );
				}
			} ) );

			addCmd( 'cellVerticalSplit', createDef( {
				allowedContent: 'td[rowspan]',
				requiredContent: 'td[rowspan]',
				exec: function( editor ) {
					placeCursorInCell( verticalSplitCell( editor.getSelection() ) );
				}
			} ) );

			addCmd( 'cellHorizontalSplit', createDef( {
				allowedContent: 'td[colspan]',
				requiredContent: 'td[colspan]',
				exec: function( editor ) {
					placeCursorInCell( horizontalSplitCell( editor.getSelection() ) );
				}
			} ) );

			addCmd( 'cellInsertBefore', createDef( {
				requiredContent: 'table',
				exec: function( editor ) {
					var selection = editor.getSelection();
					insertCell( selection, true );
				}
			} ) );

			addCmd( 'cellInsertAfter', createDef( {
				requiredContent: 'table',
				exec: function( editor ) {
					var selection = editor.getSelection();
					insertCell( selection );
				}
			} ) );

			// If the "menu" plugin is loaded, register the menu items.
			if ( editor.addMenuItems ) {
				editor.addMenuItems({
					tablecell: {
						label: lang.cell.menu,
						group: 'tablecell',
						order: 1,
						getItems: function() {
							var selection = editor.getSelection(),
								cells = getSelectedCells( selection );
							return {
								tablecell_insertBefore: CKEDITOR.TRISTATE_OFF,
								tablecell_insertAfter: CKEDITOR.TRISTATE_OFF,
								tablecell_delete: CKEDITOR.TRISTATE_OFF,
								tablecell_merge: mergeCells( selection, null, true ) ? CKEDITOR.TRISTATE_OFF : CKEDITOR.TRISTATE_DISABLED,
								tablecell_merge_right: mergeCells( selection, 'right', true ) ? CKEDITOR.TRISTATE_OFF : CKEDITOR.TRISTATE_DISABLED,
								tablecell_merge_down: mergeCells( selection, 'down', true ) ? CKEDITOR.TRISTATE_OFF : CKEDITOR.TRISTATE_DISABLED,
								tablecell_split_vertical: verticalSplitCell( selection, true ) ? CKEDITOR.TRISTATE_OFF : CKEDITOR.TRISTATE_DISABLED,
								tablecell_split_horizontal: horizontalSplitCell( selection, true ) ? CKEDITOR.TRISTATE_OFF : CKEDITOR.TRISTATE_DISABLED,
								tablecell_properties: cells.length > 0 ? CKEDITOR.TRISTATE_OFF : CKEDITOR.TRISTATE_DISABLED
							};
						}
					},

					tablecell_insertBefore: {
						label: lang.cell.insertBefore,
						group: 'tablecell',
						command: 'cellInsertBefore',
						order: 5
					},

					tablecell_insertAfter: {
						label: lang.cell.insertAfter,
						group: 'tablecell',
						command: 'cellInsertAfter',
						order: 10
					},

					tablecell_delete: {
						label: lang.cell.deleteCell,
						group: 'tablecell',
						command: 'cellDelete',
						order: 15
					},

					tablecell_merge: {
						label: lang.cell.merge,
						group: 'tablecell',
						command: 'cellMerge',
						order: 16
					},

					tablecell_merge_right: {
						label: lang.cell.mergeRight,
						group: 'tablecell',
						command: 'cellMergeRight',
						order: 17
					},

					tablecell_merge_down: {
						label: lang.cell.mergeDown,
						group: 'tablecell',
						command: 'cellMergeDown',
						order: 18
					},

					tablecell_split_horizontal: {
						label: lang.cell.splitHorizontal,
						group: 'tablecell',
						command: 'cellHorizontalSplit',
						order: 19
					},

					tablecell_split_vertical: {
						label: lang.cell.splitVertical,
						group: 'tablecell',
						command: 'cellVerticalSplit',
						order: 20
					},

					tablecell_properties: {
						label: lang.cell.title,
						group: 'tablecellproperties',
						command: 'cellProperties',
						order: 21
					},

					tablerow: {
						label: lang.row.menu,
						group: 'tablerow',
						order: 1,
						getItems: function() {
							return {
								tablerow_insertBefore: CKEDITOR.TRISTATE_OFF,
								tablerow_insertAfter: CKEDITOR.TRISTATE_OFF,
								tablerow_delete: CKEDITOR.TRISTATE_OFF
							};
						}
					},

					tablerow_insertBefore: {
						label: lang.row.insertBefore,
						group: 'tablerow',
						command: 'rowInsertBefore',
						order: 5
					},

					tablerow_insertAfter: {
						label: lang.row.insertAfter,
						group: 'tablerow',
						command: 'rowInsertAfter',
						order: 10
					},

					tablerow_delete: {
						label: lang.row.deleteRow,
						group: 'tablerow',
						command: 'rowDelete',
						order: 15
					},

					tablecolumn: {
						label: lang.column.menu,
						group: 'tablecolumn',
						order: 1,
						getItems: function() {
							return {
								tablecolumn_insertBefore: CKEDITOR.TRISTATE_OFF,
								tablecolumn_insertAfter: CKEDITOR.TRISTATE_OFF,
								tablecolumn_delete: CKEDITOR.TRISTATE_OFF
							};
						}
					},

					tablecolumn_insertBefore: {
						label: lang.column.insertBefore,
						group: 'tablecolumn',
						command: 'columnInsertBefore',
						order: 5
					},

					tablecolumn_insertAfter: {
						label: lang.column.insertAfter,
						group: 'tablecolumn',
						command: 'columnInsertAfter',
						order: 10
					},

					tablecolumn_delete: {
						label: lang.column.deleteColumn,
						group: 'tablecolumn',
						command: 'columnDelete',
						order: 15
					}
				});
			}

			// If the "contextmenu" plugin is laoded, register the listeners.
			if ( editor.contextMenu ) {
				editor.contextMenu.addListener( function( element, selection, path ) {
					var cell = path.contains( { 'td':1,'th':1 }, 1 );
					if ( cell && !cell.isReadOnly() ) {
						return {
							tablecell: CKEDITOR.TRISTATE_OFF,
							tablerow: CKEDITOR.TRISTATE_OFF,
							tablecolumn: CKEDITOR.TRISTATE_OFF
						};
					}

					return null;
				});
			}
		},

		getSelectedCells: getSelectedCells

	};
	CKEDITOR.plugins.add( 'tabletools', CKEDITOR.plugins.tabletools );
})();

/**
 * Create a two-dimension array that reflects the actual layout of table cells,
 * with cell spans, with mappings to the original td elements.
 *
 * @param {CKEDITOR.dom.element} table
 * @member CKEDITOR.tools
 */
CKEDITOR.tools.buildTableMap = function( table ) {
	var aRows = table.$.rows;

	// Row and Column counters.
	var r = -1;

	var aMap = [];

	for ( var i = 0; i < aRows.length; i++ ) {
		r++;
		!aMap[ r ] && ( aMap[ r ] = [] );

		var c = -1;

		for ( var j = 0; j < aRows[ i ].cells.length; j++ ) {
			var oCell = aRows[ i ].cells[ j ];

			c++;
			while ( aMap[ r ][ c ] )
				c++;

			var iColSpan = isNaN( oCell.colSpan ) ? 1 : oCell.colSpan;
			var iRowSpan = isNaN( oCell.rowSpan ) ? 1 : oCell.rowSpan;

			for ( var rs = 0; rs < iRowSpan; rs++ ) {
				if ( !aMap[ r + rs ] )
					aMap[ r + rs ] = [];

				for ( var cs = 0; cs < iColSpan; cs++ ) {
					aMap[ r + rs ][ c + cs ] = aRows[ i ].cells[ j ];
				}
			}

			c += iColSpan - 1;
		}
	}
	return aMap;
};
