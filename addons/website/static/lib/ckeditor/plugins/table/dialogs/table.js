/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

(function() {
	var defaultToPixel = CKEDITOR.tools.cssLength;

	var commitValue = function( data ) {
			var id = this.id;
			if ( !data.info )
				data.info = {};
			data.info[ id ] = this.getValue();
		};

	function tableColumns( table ) {
		var cols = 0,
			maxCols = 0;
		for ( var i = 0, row, rows = table.$.rows.length; i < rows; i++ ) {
			row = table.$.rows[ i ], cols = 0;
			for ( var j = 0, cell, cells = row.cells.length; j < cells; j++ ) {
				cell = row.cells[ j ];
				cols += cell.colSpan;
			}

			cols > maxCols && ( maxCols = cols );
		}

		return maxCols;
	}


	// Whole-positive-integer validator.
	function validatorNum( msg ) {
		return function() {
			var value = this.getValue(),
				pass = !!( CKEDITOR.dialog.validate.integer()( value ) && value > 0 );

			if ( !pass ) {
				alert( msg );
				this.select();
			}

			return pass;
		};
	}

	function tableDialog( editor, command ) {
		var makeElement = function( name ) {
				return new CKEDITOR.dom.element( name, editor.document );
			};

		var editable = editor.editable();

		var dialogadvtab = editor.plugins.dialogadvtab;

		return {
			title: editor.lang.table.title,
			minWidth: 310,
			minHeight: CKEDITOR.env.ie ? 310 : 280,

			onLoad: function() {
				var dialog = this;

				var styles = dialog.getContentElement( 'advanced', 'advStyles' );

				if ( styles ) {
					styles.on( 'change', function( evt ) {
						// Synchronize width value.
						var width = this.getStyle( 'width', '' ),
							txtWidth = dialog.getContentElement( 'info', 'txtWidth' );

						txtWidth && txtWidth.setValue( width, true );

						// Synchronize height value.
						var height = this.getStyle( 'height', '' ),
							txtHeight = dialog.getContentElement( 'info', 'txtHeight' );

						txtHeight && txtHeight.setValue( height, true );
					});
				}
			},

			onShow: function() {
				// Detect if there's a selected table.
				var selection = editor.getSelection(),
					ranges = selection.getRanges(),
					table;

				var rowsInput = this.getContentElement( 'info', 'txtRows' ),
					colsInput = this.getContentElement( 'info', 'txtCols' ),
					widthInput = this.getContentElement( 'info', 'txtWidth' ),
					heightInput = this.getContentElement( 'info', 'txtHeight' );

				if ( command == 'tableProperties' ) {
					var selected = selection.getSelectedElement();
					if ( selected && selected.is( 'table' ) )
						table = selected;
					else if ( ranges.length > 0 ) {
						// Webkit could report the following range on cell selection (#4948):
						// <table><tr><td>[&nbsp;</td></tr></table>]
						if ( CKEDITOR.env.webkit )
							ranges[ 0 ].shrink( CKEDITOR.NODE_ELEMENT );

						table = editor.elementPath( ranges[ 0 ].getCommonAncestor( true ) ).contains( 'table', 1 );
					}

					// Save a reference to the selected table, and push a new set of default values.
					this._.selectedElement = table;
				}

				// Enable or disable the row, cols, width fields.
				if ( table ) {
					this.setupContent( table );
					rowsInput && rowsInput.disable();
					colsInput && colsInput.disable();
				} else {
					rowsInput && rowsInput.enable();
					colsInput && colsInput.enable();
				}

				// Call the onChange method for the widht and height fields so
				// they get reflected into the Advanced tab.
				widthInput && widthInput.onChange();
				heightInput && heightInput.onChange();
			},
			onOk: function() {
				var selection = editor.getSelection(),
					bms = this._.selectedElement && selection.createBookmarks();

				var table = this._.selectedElement || makeElement( 'table' ),
					me = this,
					data = {};

				this.commitContent( data, table );

				if ( data.info ) {
					var info = data.info;

					// Generate the rows and cols.
					if ( !this._.selectedElement ) {
						var tbody = table.append( makeElement( 'tbody' ) ),
							rows = parseInt( info.txtRows, 10 ) || 0,
							cols = parseInt( info.txtCols, 10 ) || 0;

						for ( var i = 0; i < rows; i++ ) {
							var row = tbody.append( makeElement( 'tr' ) );
							for ( var j = 0; j < cols; j++ ) {
								var cell = row.append( makeElement( 'td' ) );
								if ( !CKEDITOR.env.ie )
									cell.append( makeElement( 'br' ) );
							}
						}
					}

					// Modify the table headers. Depends on having rows and cols generated
					// correctly so it can't be done in commit functions.

					// Should we make a <thead>?
					var headers = info.selHeaders;
					if ( !table.$.tHead && ( headers == 'row' || headers == 'both' ) ) {
						var thead = new CKEDITOR.dom.element( table.$.createTHead() );
						tbody = table.getElementsByTag( 'tbody' ).getItem( 0 );
						var theRow = tbody.getElementsByTag( 'tr' ).getItem( 0 );

						// Change TD to TH:
						for ( i = 0; i < theRow.getChildCount(); i++ ) {
							var th = theRow.getChild( i );
							// Skip bookmark nodes. (#6155)
							if ( th.type == CKEDITOR.NODE_ELEMENT && !th.data( 'cke-bookmark' ) ) {
								th.renameNode( 'th' );
								th.setAttribute( 'scope', 'col' );
							}
						}
						thead.append( theRow.remove() );
					}

					if ( table.$.tHead !== null && !( headers == 'row' || headers == 'both' ) ) {
						// Move the row out of the THead and put it in the TBody:
						thead = new CKEDITOR.dom.element( table.$.tHead );
						tbody = table.getElementsByTag( 'tbody' ).getItem( 0 );

						var previousFirstRow = tbody.getFirst();
						while ( thead.getChildCount() > 0 ) {
							theRow = thead.getFirst();
							for ( i = 0; i < theRow.getChildCount(); i++ ) {
								var newCell = theRow.getChild( i );
								if ( newCell.type == CKEDITOR.NODE_ELEMENT ) {
									newCell.renameNode( 'td' );
									newCell.removeAttribute( 'scope' );
								}
							}
							theRow.insertBefore( previousFirstRow );
						}
						thead.remove();
					}

					// Should we make all first cells in a row TH?
					if ( !this.hasColumnHeaders && ( headers == 'col' || headers == 'both' ) ) {
						for ( row = 0; row < table.$.rows.length; row++ ) {
							newCell = new CKEDITOR.dom.element( table.$.rows[ row ].cells[ 0 ] );
							newCell.renameNode( 'th' );
							newCell.setAttribute( 'scope', 'row' );
						}
					}

					// Should we make all first TH-cells in a row make TD? If 'yes' we do it the other way round :-)
					if ( ( this.hasColumnHeaders ) && !( headers == 'col' || headers == 'both' ) ) {
						for ( i = 0; i < table.$.rows.length; i++ ) {
							row = new CKEDITOR.dom.element( table.$.rows[ i ] );
							if ( row.getParent().getName() == 'tbody' ) {
								newCell = new CKEDITOR.dom.element( row.$.cells[ 0 ] );
								newCell.renameNode( 'td' );
								newCell.removeAttribute( 'scope' );
							}
						}
					}

					// Set the width and height.
					info.txtHeight ? table.setStyle( 'height', info.txtHeight ) : table.removeStyle( 'height' );
					info.txtWidth ? table.setStyle( 'width', info.txtWidth ) : table.removeStyle( 'width' );

					if ( !table.getAttribute( 'style' ) )
						table.removeAttribute( 'style' );
				}

				// Insert the table element if we're creating one.
				if ( !this._.selectedElement ) {
					editor.insertElement( table );
					// Override the default cursor position after insertElement to place
					// cursor inside the first cell (#7959), IE needs a while.
					setTimeout( function() {
						var firstCell = new CKEDITOR.dom.element( table.$.rows[ 0 ].cells[ 0 ] );
						var range = editor.createRange();
						range.moveToPosition( firstCell, CKEDITOR.POSITION_AFTER_START );
						range.select();
					}, 0 );
				}
				// Properly restore the selection, (#4822) but don't break
				// because of this, e.g. updated table caption.
				else
					try {
					selection.selectBookmarks( bms );
				} catch ( er ) {}
			},
			contents: [
				{
				id: 'info',
				label: editor.lang.table.title,
				elements: [
					{
					type: 'hbox',
					widths: [ null, null ],
					styles: [ 'vertical-align:top' ],
					children: [
						{
						type: 'vbox',
						padding: 0,
						children: [
							{
							type: 'text',
							id: 'txtRows',
							'default': 3,
							label: editor.lang.table.rows,
							required: true,
							controlStyle: 'width:5em',
							validate: validatorNum( editor.lang.table.invalidRows ),
							setup: function( selectedElement ) {
								this.setValue( selectedElement.$.rows.length );
							},
							commit: commitValue
						},
							{
							type: 'text',
							id: 'txtCols',
							'default': 2,
							label: editor.lang.table.columns,
							required: true,
							controlStyle: 'width:5em',
							validate: validatorNum( editor.lang.table.invalidCols ),
							setup: function( selectedTable ) {
								this.setValue( tableColumns( selectedTable ) );
							},
							commit: commitValue
						},
							{
							type: 'html',
							html: '&nbsp;'
						},
							{
							type: 'select',
							id: 'selHeaders',
							requiredContent: 'th',
							'default': '',
							label: editor.lang.table.headers,
							items: [
								[ editor.lang.table.headersNone, '' ],
								[ editor.lang.table.headersRow, 'row' ],
								[ editor.lang.table.headersColumn, 'col' ],
								[ editor.lang.table.headersBoth, 'both' ]
								],
							setup: function( selectedTable ) {
								// Fill in the headers field.
								var dialog = this.getDialog();
								dialog.hasColumnHeaders = true;

								// Check if all the first cells in every row are TH
								for ( var row = 0; row < selectedTable.$.rows.length; row++ ) {
									// If just one cell isn't a TH then it isn't a header column
									var headCell = selectedTable.$.rows[ row ].cells[ 0 ];
									if ( headCell && headCell.nodeName.toLowerCase() != 'th' ) {
										dialog.hasColumnHeaders = false;
										break;
									}
								}

								// Check if the table contains <thead>.
								if ( ( selectedTable.$.tHead !== null ) )
									this.setValue( dialog.hasColumnHeaders ? 'both' : 'row' );
								else
									this.setValue( dialog.hasColumnHeaders ? 'col' : '' );
							},
							commit: commitValue
						},
							{
							type: 'text',
							id: 'txtBorder',
							requiredContent: 'table[border]',
							// Avoid setting border which will then disappear.
							'default': editor.filter.check( 'table[border]' ) ? 1 : 0,
							label: editor.lang.table.border,
							controlStyle: 'width:3em',
							validate: CKEDITOR.dialog.validate[ 'number' ]( editor.lang.table.invalidBorder ),
							setup: function( selectedTable ) {
								this.setValue( selectedTable.getAttribute( 'border' ) || '' );
							},
							commit: function( data, selectedTable ) {
								if ( this.getValue() )
									selectedTable.setAttribute( 'border', this.getValue() );
								else
									selectedTable.removeAttribute( 'border' );
							}
						},
							{
							id: 'cmbAlign',
							type: 'select',
							requiredContent: 'table[align]',
							'default': '',
							label: editor.lang.common.align,
							items: [
								[ editor.lang.common.notSet, '' ],
								[ editor.lang.common.alignLeft, 'left' ],
								[ editor.lang.common.alignCenter, 'center' ],
								[ editor.lang.common.alignRight, 'right' ]
								],
							setup: function( selectedTable ) {
								this.setValue( selectedTable.getAttribute( 'align' ) || '' );
							},
							commit: function( data, selectedTable ) {
								if ( this.getValue() )
									selectedTable.setAttribute( 'align', this.getValue() );
								else
									selectedTable.removeAttribute( 'align' );
							}
						}
						]
					},
						{
						type: 'vbox',
						padding: 0,
						children: [
							{
							type: 'hbox',
							widths: [ '5em' ],
							children: [
								{
								type: 'text',
								id: 'txtWidth',
								requiredContent: 'table{width}',
								controlStyle: 'width:5em',
								label: editor.lang.common.width,
								title: editor.lang.common.cssLengthTooltip,
								// Smarter default table width. (#9600)
								'default': editor.filter.check( 'table{width}' ) ? ( editable.getSize( 'width' ) < 500 ? '100%' : 500 ) : 0,
								getValue: defaultToPixel,
								validate: CKEDITOR.dialog.validate.cssLength( editor.lang.common.invalidCssLength.replace( '%1', editor.lang.common.width ) ),
								onChange: function() {
									var styles = this.getDialog().getContentElement( 'advanced', 'advStyles' );
									styles && styles.updateStyle( 'width', this.getValue() );
								},
								setup: function( selectedTable ) {
									var val = selectedTable.getStyle( 'width' );
									this.setValue( val );
								},
								commit: commitValue
							}
							]
						},
							{
							type: 'hbox',
							widths: [ '5em' ],
							children: [
								{
								type: 'text',
								id: 'txtHeight',
								requiredContent: 'table{height}',
								controlStyle: 'width:5em',
								label: editor.lang.common.height,
								title: editor.lang.common.cssLengthTooltip,
								'default': '',
								getValue: defaultToPixel,
								validate: CKEDITOR.dialog.validate.cssLength( editor.lang.common.invalidCssLength.replace( '%1', editor.lang.common.height ) ),
								onChange: function() {
									var styles = this.getDialog().getContentElement( 'advanced', 'advStyles' );
									styles && styles.updateStyle( 'height', this.getValue() );
								},

								setup: function( selectedTable ) {
									var val = selectedTable.getStyle( 'height' );
									val && this.setValue( val );
								},
								commit: commitValue
							}
							]
						},
							{
							type: 'html',
							html: '&nbsp;'
						},
							{
							type: 'text',
							id: 'txtCellSpace',
							requiredContent: 'table[cellspacing]',
							controlStyle: 'width:3em',
							label: editor.lang.table.cellSpace,
							'default': editor.filter.check( 'table[cellspacing]' ) ? 1 : 0,
							validate: CKEDITOR.dialog.validate.number( editor.lang.table.invalidCellSpacing ),
							setup: function( selectedTable ) {
								this.setValue( selectedTable.getAttribute( 'cellSpacing' ) || '' );
							},
							commit: function( data, selectedTable ) {
								if ( this.getValue() )
									selectedTable.setAttribute( 'cellSpacing', this.getValue() );
								else
									selectedTable.removeAttribute( 'cellSpacing' );
							}
						},
							{
							type: 'text',
							id: 'txtCellPad',
							requiredContent: 'table[cellpadding]',
							controlStyle: 'width:3em',
							label: editor.lang.table.cellPad,
							'default': editor.filter.check( 'table[cellpadding]' ) ? 1 : 0,
							validate: CKEDITOR.dialog.validate.number( editor.lang.table.invalidCellPadding ),
							setup: function( selectedTable ) {
								this.setValue( selectedTable.getAttribute( 'cellPadding' ) || '' );
							},
							commit: function( data, selectedTable ) {
								if ( this.getValue() )
									selectedTable.setAttribute( 'cellPadding', this.getValue() );
								else
									selectedTable.removeAttribute( 'cellPadding' );
							}
						}
						]
					}
					]
				},
					{
					type: 'html',
					align: 'right',
					html: ''
				},
					{
					type: 'vbox',
					padding: 0,
					children: [
						{
						type: 'text',
						id: 'txtCaption',
						requiredContent: 'caption',
						label: editor.lang.table.caption,
						setup: function( selectedTable ) {
							this.enable();

							var nodeList = selectedTable.getElementsByTag( 'caption' );
							if ( nodeList.count() > 0 ) {
								var caption = nodeList.getItem( 0 );
								var firstElementChild = caption.getFirst( CKEDITOR.dom.walker.nodeType( CKEDITOR.NODE_ELEMENT ) );

								if ( firstElementChild && !firstElementChild.equals( caption.getBogus() ) ) {
									this.disable();
									this.setValue( caption.getText() );
									return;
								}

								caption = CKEDITOR.tools.trim( caption.getText() );
								this.setValue( caption );
							}
						},
						commit: function( data, table ) {
							if ( !this.isEnabled() )
								return;

							var caption = this.getValue(),
								captionElement = table.getElementsByTag( 'caption' );
							if ( caption ) {
								if ( captionElement.count() > 0 ) {
									captionElement = captionElement.getItem( 0 );
									captionElement.setHtml( '' );
								} else {
									captionElement = new CKEDITOR.dom.element( 'caption', editor.document );
									if ( table.getChildCount() )
										captionElement.insertBefore( table.getFirst() );
									else
										captionElement.appendTo( table );
								}
								captionElement.append( new CKEDITOR.dom.text( caption, editor.document ) );
							} else if ( captionElement.count() > 0 ) {
								for ( var i = captionElement.count() - 1; i >= 0; i-- )
									captionElement.getItem( i ).remove();
							}
						}
					},
						{
						type: 'text',
						id: 'txtSummary',
						requiredContent: 'table[summary]',
						label: editor.lang.table.summary,
						setup: function( selectedTable ) {
							this.setValue( selectedTable.getAttribute( 'summary' ) || '' );
						},
						commit: function( data, selectedTable ) {
							if ( this.getValue() )
								selectedTable.setAttribute( 'summary', this.getValue() );
							else
								selectedTable.removeAttribute( 'summary' );
						}
					}
					]
				}
				]
			},
				dialogadvtab && dialogadvtab.createAdvancedTab( editor, null, 'table' )
				]
		};
	}

	CKEDITOR.dialog.add( 'table', function( editor ) {
		return tableDialog( editor, 'table' );
	});
	CKEDITOR.dialog.add( 'tableProperties', function( editor ) {
		return tableDialog( editor, 'tableProperties' );
	});
})();
