/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

(function() {
	var pxUnit = CKEDITOR.tools.cssLength,
		needsIEHacks = CKEDITOR.env.ie && ( CKEDITOR.env.ie7Compat || CKEDITOR.env.quirks );

	function getWidth( el ) {
		return CKEDITOR.env.ie ? el.$.clientWidth : parseInt( el.getComputedStyle( 'width' ), 10 );
	}

	function getBorderWidth( element, side ) {
		var computed = element.getComputedStyle( 'border-' + side + '-width' ),
			borderMap = {
				thin: '0px',
				medium: '1px',
				thick: '2px'
			};

		if ( computed.indexOf( 'px' ) < 0 ) {
			// look up keywords
			if ( computed in borderMap && element.getComputedStyle( 'border-style' ) != 'none' )
				computed = borderMap[ computed ];
			else
				computed = 0;
		}

		return parseInt( computed, 10 );
	}

	// Gets the table row that contains the most columns.
	function getMasterPillarRow( table ) {
		var $rows = table.$.rows,
			maxCells = 0,
			cellsCount, $elected, $tr;

		for ( var i = 0, len = $rows.length; i < len; i++ ) {
			$tr = $rows[ i ];
			cellsCount = $tr.cells.length;

			if ( cellsCount > maxCells ) {
				maxCells = cellsCount;
				$elected = $tr;
			}
		}

		return $elected;
	}

	function buildTableColumnPillars( table ) {
		var pillars = [],
			pillarIndex = -1,
			rtl = ( table.getComputedStyle( 'direction' ) == 'rtl' );

		// Get the raw row element that cointains the most columns.
		var $tr = getMasterPillarRow( table );

		// Get the tbody element and position, which will be used to set the
		// top and bottom boundaries.
		var tbody = new CKEDITOR.dom.element( table.$.tBodies[ 0 ] ),
			tbodyPosition = tbody.getDocumentPosition();

		// Loop thorugh all cells, building pillars after each one of them.
		for ( var i = 0, len = $tr.cells.length; i < len; i++ ) {
			// Both the current cell and the successive one will be used in the
			// pillar size calculation.
			var td = new CKEDITOR.dom.element( $tr.cells[ i ] ),
				nextTd = $tr.cells[ i + 1 ] && new CKEDITOR.dom.element( $tr.cells[ i + 1 ] );

			pillarIndex += td.$.colSpan || 1;

			// Calculate the pillar boundary positions.
			var pillarLeft, pillarRight, pillarWidth;

			var x = td.getDocumentPosition().x;

			// Calculate positions based on the current cell.
			rtl ? pillarRight = x + getBorderWidth( td, 'left' ) : pillarLeft = x + td.$.offsetWidth - getBorderWidth( td, 'right' );

			// Calculate positions based on the next cell, if available.
			if ( nextTd ) {
				x = nextTd.getDocumentPosition().x;

				rtl ? pillarLeft = x + nextTd.$.offsetWidth - getBorderWidth( nextTd, 'right' ) : pillarRight = x + getBorderWidth( nextTd, 'left' );
			}
			// Otherwise calculate positions based on the table (for last cell).
			else {
				x = table.getDocumentPosition().x;

				rtl ? pillarLeft = x : pillarRight = x + table.$.offsetWidth;
			}

			pillarWidth = Math.max( pillarRight - pillarLeft, 3 );

			// The pillar should reflects exactly the shape of the hovered
			// column border line.
			pillars.push({
				table: table,
				index: pillarIndex,
				x: pillarLeft,
				y: tbodyPosition.y,
				width: pillarWidth,
				height: tbody.$.offsetHeight,
				rtl: rtl } );
		}

		return pillars;
	}

	function getPillarAtPosition( pillars, positionX ) {
		for ( var i = 0, len = pillars.length; i < len; i++ ) {
			var pillar = pillars[ i ];

			if ( positionX >= pillar.x && positionX <= ( pillar.x + pillar.width ) )
				return pillar;
		}

		return null;
	}

	function cancel( evt ) {
		( evt.data || evt ).preventDefault();
	}

	function columnResizer( editor ) {
		var pillar, document, resizer, isResizing, startOffset, currentShift;

		var leftSideCells, rightSideCells, leftShiftBoundary, rightShiftBoundary;

		function detach() {
			pillar = null;
			currentShift = 0;
			isResizing = 0;

			document.removeListener( 'mouseup', onMouseUp );
			resizer.removeListener( 'mousedown', onMouseDown );
			resizer.removeListener( 'mousemove', onMouseMove );

			document.getBody().setStyle( 'cursor', 'auto' );

			// Hide the resizer (remove it on IE7 - #5890).
			needsIEHacks ? resizer.remove() : resizer.hide();
		}

		function resizeStart() {
			// Before starting to resize, figure out which cells to change
			// and the boundaries of this resizing shift.

			var columnIndex = pillar.index,
				map = CKEDITOR.tools.buildTableMap( pillar.table ),
				leftColumnCells = [],
				rightColumnCells = [],
				leftMinSize = Number.MAX_VALUE,
				rightMinSize = leftMinSize,
				rtl = pillar.rtl;

			for ( var i = 0, len = map.length; i < len; i++ ) {
				var row = map[ i ],
					leftCell = row[ columnIndex + ( rtl ? 1 : 0 ) ],
					rightCell = row[ columnIndex + ( rtl ? 0 : 1 ) ];

				leftCell = leftCell && new CKEDITOR.dom.element( leftCell );
				rightCell = rightCell && new CKEDITOR.dom.element( rightCell );

				if ( !leftCell || !rightCell || !leftCell.equals( rightCell ) ) {
					leftCell && ( leftMinSize = Math.min( leftMinSize, getWidth( leftCell ) ) );
					rightCell && ( rightMinSize = Math.min( rightMinSize, getWidth( rightCell ) ) );

					leftColumnCells.push( leftCell );
					rightColumnCells.push( rightCell );
				}
			}

			// Cache the list of cells to be resized.
			leftSideCells = leftColumnCells;
			rightSideCells = rightColumnCells;

			// Cache the resize limit boundaries.
			leftShiftBoundary = pillar.x - leftMinSize;
			rightShiftBoundary = pillar.x + rightMinSize;

			resizer.setOpacity( 0.5 );
			startOffset = parseInt( resizer.getStyle( 'left' ), 10 );
			currentShift = 0;
			isResizing = 1;

			resizer.on( 'mousemove', onMouseMove );

			// Prevent the native drag behavior otherwise 'mousemove' won't fire.
			document.on( 'dragstart', cancel );
		}

		function resizeEnd() {
			isResizing = 0;

			resizer.setOpacity( 0 );

			currentShift && resizeColumn();

			var table = pillar.table;
			setTimeout( function() {
				table.removeCustomData( '_cke_table_pillars' );
			}, 0 );

			document.removeListener( 'dragstart', cancel );
		}

		function resizeColumn() {
			var rtl = pillar.rtl,
				cellsCount = rtl ? rightSideCells.length : leftSideCells.length;

			// Perform the actual resize to table cells, only for those by side of the pillar.
			for ( var i = 0; i < cellsCount; i++ ) {
				var leftCell = leftSideCells[ i ],
					rightCell = rightSideCells[ i ],
					table = pillar.table;

				// Defer the resizing to avoid any interference among cells.
				CKEDITOR.tools.setTimeout( function( leftCell, leftOldWidth, rightCell, rightOldWidth, tableWidth, sizeShift ) {
					leftCell && leftCell.setStyle( 'width', pxUnit( Math.max( leftOldWidth + sizeShift, 0 ) ) );
					rightCell && rightCell.setStyle( 'width', pxUnit( Math.max( rightOldWidth - sizeShift, 0 ) ) );

					// If we're in the last cell, we need to resize the table as well
					if ( tableWidth )
						table.setStyle( 'width', pxUnit( tableWidth + sizeShift * ( rtl ? -1 : 1 ) ) );
				}, 0, this, [
					leftCell, leftCell && getWidth( leftCell ),
					rightCell, rightCell && getWidth( rightCell ),
					( !leftCell || !rightCell ) && ( getWidth( table ) + getBorderWidth( table, 'left' ) + getBorderWidth( table, 'right' ) ),
					currentShift ] );
			}
		}

		function onMouseDown( evt ) {
			cancel( evt );

			resizeStart();

			document.on( 'mouseup', onMouseUp, this );
		}

		function onMouseUp( evt ) {
			evt.removeListener();

			resizeEnd();
		}

		function onMouseMove( evt ) {
			move( evt.data.getPageOffset().x );
		}

		document = editor.document;

		resizer = CKEDITOR.dom.element.createFromHtml( '<div data-cke-temp=1 contenteditable=false unselectable=on ' +
			'style="position:absolute;cursor:col-resize;filter:alpha(opacity=0);opacity:0;' +
				'padding:0;background-color:#004;background-image:none;border:0px none;z-index:10"></div>', document );

		// Except on IE6/7 (#5890), place the resizer after body to prevent it
		// from being editable.
		if ( !needsIEHacks )
			document.getDocumentElement().append( resizer );

		this.attachTo = function( targetPillar ) {
			// Accept only one pillar at a time.
			if ( isResizing )
				return;

			// On IE6/7, we append the resizer everytime we need it. (#5890)
			if ( needsIEHacks ) {
				document.getBody().append( resizer );
				currentShift = 0;
			}

			pillar = targetPillar;

			resizer.setStyles({
				width: pxUnit( targetPillar.width ),
				height: pxUnit( targetPillar.height ),
				left: pxUnit( targetPillar.x ),
				top: pxUnit( targetPillar.y )
			});

			// In IE6/7, it's not possible to have custom cursors for floating
			// elements in an editable document. Show the resizer in that case,
			// to give the user a visual clue.
			needsIEHacks && resizer.setOpacity( 0.25 );

			resizer.on( 'mousedown', onMouseDown, this );

			document.getBody().setStyle( 'cursor', 'col-resize' );

			// Display the resizer to receive events but don't show it,
			// only change the cursor to resizable shape.
			resizer.show();
		};

		var move = this.move = function( posX ) {
				if ( !pillar )
					return 0;

				if ( !isResizing && ( posX < pillar.x || posX > ( pillar.x + pillar.width ) ) ) {
					detach();
					return 0;
				}

				var resizerNewPosition = posX - Math.round( resizer.$.offsetWidth / 2 );

				if ( isResizing ) {
					if ( resizerNewPosition == leftShiftBoundary || resizerNewPosition == rightShiftBoundary )
						return 1;

					resizerNewPosition = Math.max( resizerNewPosition, leftShiftBoundary );
					resizerNewPosition = Math.min( resizerNewPosition, rightShiftBoundary );

					currentShift = resizerNewPosition - startOffset;
				}

				resizer.setStyle( 'left', pxUnit( resizerNewPosition ) );

				return 1;
			};
	}

	function clearPillarsCache( evt ) {
		var target = evt.data.getTarget();

		if ( evt.name == 'mouseout' ) {
			// Bypass interal mouse move.
			if ( !target.is( 'table' ) )
				return;

			var dest = new CKEDITOR.dom.element( evt.data.$.relatedTarget || evt.data.$.toElement );
			while ( dest && dest.$ && !dest.equals( target ) && !dest.is( 'body' ) )
				dest = dest.getParent();
			if ( !dest || dest.equals( target ) )
				return;
		}

		target.getAscendant( 'table', 1 ).removeCustomData( '_cke_table_pillars' );
		evt.removeListener();
	}

	CKEDITOR.plugins.add( 'tableresize', {
		requires: 'tabletools',

		init: function( editor ) {
			editor.on( 'contentDom', function() {
				var resizer;

				editor.document.getBody().on( 'mousemove', function( evt ) {
					evt = evt.data;

					var pageX = evt.getPageOffset().x;

					// If we're already attached to a pillar, simply move the
					// resizer.
					if ( resizer && resizer.move( pageX ) ) {
						cancel( evt );
						return;
					}

					// Considering table, tr, td, tbody but nothing else.
					var target = evt.getTarget(),
						table, pillars;

					if ( !target.is( 'table' ) && !target.getAscendant( 'tbody', 1 ) )
						return;

					table = target.getAscendant( 'table', 1 );

					if ( !( pillars = table.getCustomData( '_cke_table_pillars' ) ) ) {
						// Cache table pillars calculation result.
						table.setCustomData( '_cke_table_pillars', ( pillars = buildTableColumnPillars( table ) ) );
						table.on( 'mouseout', clearPillarsCache );
						table.on( 'mousedown', clearPillarsCache );
					}

					var pillar = getPillarAtPosition( pillars, pageX );
					if ( pillar ) {
						!resizer && ( resizer = new columnResizer( editor ) );
						resizer.attachTo( pillar );
					}
				});
			});
		}
	});

})();
