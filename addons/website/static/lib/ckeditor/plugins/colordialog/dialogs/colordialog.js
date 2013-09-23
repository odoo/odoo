/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

CKEDITOR.dialog.add( 'colordialog', function( editor ) {
	// Define some shorthands.
	var $el = CKEDITOR.dom.element,
		$doc = CKEDITOR.document,
		lang = editor.lang.colordialog;

	// Reference the dialog.
	var dialog;

	var spacer = {
		type: 'html',
		html: '&nbsp;'
	};

	var selected;

	function clearSelected() {
		$doc.getById( selHiColorId ).removeStyle( 'background-color' );
		dialog.getContentElement( 'picker', 'selectedColor' ).setValue( '' );
		selected && selected.removeAttribute( 'aria-selected' );
		selected = null;
	}

	function updateSelected( evt ) {
		var target = evt.data.getTarget(),
			color;

		if ( target.getName() == 'td' && ( color = target.getChild( 0 ).getHtml() ) ) {
			selected = target;
			selected.setAttribute( 'aria-selected', true );
			dialog.getContentElement( 'picker', 'selectedColor' ).setValue( color );
		}
	}

	// Basing black-white decision off of luma scheme using the Rec. 709 version
	function whiteOrBlack( color ) {
		color = color.replace( /^#/, '' );
		for ( var i = 0, rgb = []; i <= 2; i++ )
			rgb[ i ] = parseInt( color.substr( i * 2, 2 ), 16 );
		var luma = ( 0.2126 * rgb[ 0 ] ) + ( 0.7152 * rgb[ 1 ] ) + ( 0.0722 * rgb[ 2 ] );
		return '#' + ( luma >= 165 ? '000' : 'fff' );
	}

	// Distinguish focused and hover states.
	var focused, hovered;

	// Apply highlight style.
	function updateHighlight( event ) {
		// Convert to event.
		!event.name && ( event = new CKEDITOR.event( event ) );

		var isFocus = !( /mouse/ ).test( event.name ),
			target = event.data.getTarget(),
			color;

		if ( target.getName() == 'td' && ( color = target.getChild( 0 ).getHtml() ) ) {
			removeHighlight( event );

			isFocus ? focused = target : hovered = target;

			// Apply outline style to show focus.
			if ( isFocus ) {
				target.setStyle( 'border-color', whiteOrBlack( color ) );
				target.setStyle( 'border-style', 'dotted' );
			}

			$doc.getById( hicolorId ).setStyle( 'background-color', color );
			$doc.getById( hicolorTextId ).setHtml( color );
		}
	}

	function clearHighlight() {
		var color = focused.getChild( 0 ).getHtml();
		focused.setStyle( 'border-color', color );
		focused.setStyle( 'border-style', 'solid' );
		$doc.getById( hicolorId ).removeStyle( 'background-color' );
		$doc.getById( hicolorTextId ).setHtml( '&nbsp;' );
		focused = null;
	}

	// Remove previously focused style.
	function removeHighlight( event ) {
		var isFocus = !( /mouse/ ).test( event.name ),
			target = isFocus && focused;

		if ( target ) {
			var color = target.getChild( 0 ).getHtml();
			target.setStyle( 'border-color', color );
			target.setStyle( 'border-style', 'solid' );
		}

		if ( !( focused || hovered ) ) {
			$doc.getById( hicolorId ).removeStyle( 'background-color' );
			$doc.getById( hicolorTextId ).setHtml( '&nbsp;' );
		}
	}

	function onKeyStrokes( evt ) {
		var domEvt = evt.data;

		var element = domEvt.getTarget();
		var relative, nodeToMove;
		var keystroke = domEvt.getKeystroke(),
			rtl = editor.lang.dir == 'rtl';

		switch ( keystroke ) {
			// UP-ARROW
			case 38:
				// relative is TR
				if ( ( relative = element.getParent().getPrevious() ) ) {
					nodeToMove = relative.getChild( [ element.getIndex() ] );
					nodeToMove.focus();
				}
				domEvt.preventDefault();
				break;
				// DOWN-ARROW
			case 40:
				// relative is TR
				if ( ( relative = element.getParent().getNext() ) ) {
					nodeToMove = relative.getChild( [ element.getIndex() ] );
					if ( nodeToMove && nodeToMove.type == 1 ) {
						nodeToMove.focus();
					}
				}
				domEvt.preventDefault();
				break;

				// SPACE
				// ENTER
			case 32:
			case 13:
				updateSelected( evt );
				domEvt.preventDefault();
				break;

				// RIGHT-ARROW
			case rtl ? 37:
				39 :
				// relative is TD
				if ( ( nodeToMove = element.getNext() ) ) {
					if ( nodeToMove.type == 1 ) {
						nodeToMove.focus();
						domEvt.preventDefault( true );
					}
				}
				// relative is TR
				else if ( ( relative = element.getParent().getNext() ) ) {
					nodeToMove = relative.getChild( [ 0 ] );
					if ( nodeToMove && nodeToMove.type == 1 ) {
						nodeToMove.focus();
						domEvt.preventDefault( true );
					}
				}
				break;

				// LEFT-ARROW
			case rtl ? 39:
				37 :
				// relative is TD
				if ( ( nodeToMove = element.getPrevious() ) ) {
					nodeToMove.focus();
					domEvt.preventDefault( true );
				}
				// relative is TR
				else if ( ( relative = element.getParent().getPrevious() ) ) {
					nodeToMove = relative.getLast();
					nodeToMove.focus();
					domEvt.preventDefault( true );
				}
				break;
			default:
				// Do not stop not handled events.
				return;
		}
	}

	function createColorTable() {
		table = CKEDITOR.dom.element.createFromHtml( '<table tabIndex="-1" aria-label="' + lang.options + '"' +
			' role="grid" style="border-collapse:separate;" cellspacing="0">' +
			'<caption class="cke_voice_label">' + lang.options + '</caption>' +
			'<tbody role="presentation"></tbody></table>' );

		table.on( 'mouseover', updateHighlight );
		table.on( 'mouseout', removeHighlight );

		// Create the base colors array.
		var aColors = [ '00', '33', '66', '99', 'cc', 'ff' ];

		// This function combines two ranges of three values from the color array into a row.
		function appendColorRow( rangeA, rangeB ) {
			for ( var i = rangeA; i < rangeA + 3; i++ ) {
				var row = new $el( table.$.insertRow( -1 ) );
				row.setAttribute( 'role', 'row' );

				for ( var j = rangeB; j < rangeB + 3; j++ ) {
					for ( var n = 0; n < 6; n++ ) {
						appendColorCell( row.$, '#' + aColors[ j ] + aColors[ n ] + aColors[ i ] );
					}
				}
			}
		}

		// This function create a single color cell in the color table.
		function appendColorCell( targetRow, color ) {
			var cell = new $el( targetRow.insertCell( -1 ) );
			cell.setAttribute( 'class', 'ColorCell' );
			cell.setAttribute( 'tabIndex', -1 );
			cell.setAttribute( 'role', 'gridcell' );

			cell.on( 'keydown', onKeyStrokes );
			cell.on( 'click', updateSelected );
			cell.on( 'focus', updateHighlight );
			cell.on( 'blur', removeHighlight );

			cell.setStyle( 'background-color', color );
			cell.setStyle( 'border', '1px solid ' + color );

			cell.setStyle( 'width', '14px' );
			cell.setStyle( 'height', '14px' );

			var colorLabel = numbering( 'color_table_cell' );
			cell.setAttribute( 'aria-labelledby', colorLabel );
			cell.append( CKEDITOR.dom.element.createFromHtml( '<span id="' + colorLabel + '" class="cke_voice_label">' + color + '</span>', CKEDITOR.document ) );
		}

		appendColorRow( 0, 0 );
		appendColorRow( 3, 0 );
		appendColorRow( 0, 3 );
		appendColorRow( 3, 3 );

		// Create the last row.
		var oRow = new $el( table.$.insertRow( -1 ) );
		oRow.setAttribute( 'role', 'row' );

		// Create the gray scale colors cells.
		for ( var n = 0; n < 6; n++ ) {
			appendColorCell( oRow.$, '#' + aColors[ n ] + aColors[ n ] + aColors[ n ] );
		}

		// Fill the row with black cells.
		for ( var i = 0; i < 12; i++ ) {
			appendColorCell( oRow.$, '#000000' );
		}
	}

	var numbering = function( id ) {
			return CKEDITOR.tools.getNextId() + '_' + id;
		},
		hicolorId = numbering( 'hicolor' ),
		hicolorTextId = numbering( 'hicolortext' ),
		selHiColorId = numbering( 'selhicolor' ),
		table;

	createColorTable();

	return {
		title: lang.title,
		minWidth: 360,
		minHeight: 220,
		onLoad: function() {
			// Update reference.
			dialog = this;
		},
		onHide: function() {
			clearSelected();
			clearHighlight();
		},
		contents: [
			{
			id: 'picker',
			label: lang.title,
			accessKey: 'I',
			elements: [
				{
				type: 'hbox',
				padding: 0,
				widths: [ '70%', '10%', '30%' ],
				children: [
					{
					type: 'html',
					html: '<div></div>',
					onLoad: function() {
						CKEDITOR.document.getById( this.domId ).append( table );
					},
					focus: function() {
						// Restore the previously focused cell,
						// otherwise put the initial focus on the first table cell.
						( focused || this.getElement().getElementsByTag( 'td' ).getItem( 0 ) ).focus();
					}
				},
					spacer,
				{
					type: 'vbox',
					padding: 0,
					widths: [ '70%', '5%', '25%' ],
					children: [
						{
						type: 'html',
						html: '<span>' + lang.highlight + '</span>\
												<div id="' + hicolorId + '" style="border: 1px solid; height: 74px; width: 74px;"></div>\
												<div id="' + hicolorTextId + '">&nbsp;</div><span>' + lang.selected + '</span>\
												<div id="' + selHiColorId + '" style="border: 1px solid; height: 20px; width: 74px;"></div>'
					},
						{
						type: 'text',
						label: lang.selected,
						labelStyle: 'display:none',
						id: 'selectedColor',
						style: 'width: 74px',
						onChange: function() {
							// Try to update color preview with new value. If fails, then set it no none.
							try {
								$doc.getById( selHiColorId ).setStyle( 'background-color', this.getValue() );
							} catch ( e ) {
								clearSelected();
							}
						}
					},
						spacer,
					{
						type: 'button',
						id: 'clear',
						style: 'margin-top: 5px',
						label: lang.clear,
						onClick: clearSelected
					}
					]
				}
				]
			}
			]
		}
		]
	};
});
