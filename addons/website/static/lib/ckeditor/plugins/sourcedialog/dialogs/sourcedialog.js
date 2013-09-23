/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

CKEDITOR.dialog.add( 'sourcedialog', function( editor ) {
	var size = CKEDITOR.document.getWindow().getViewPaneSize();

	// Make it maximum 800px wide, but still fully visible in the viewport.
	var width = Math.min( size.width - 70, 800);

	// Make it use 2/3 of the viewport height.
	var height = size.height / 1.5;

	// Store old editor data to avoid unnecessary setData.
	var oldData;

	return {
		title: editor.lang.sourcedialog.title,
		minWidth: 100,
		minHeight: 100,

		onShow: function() {
			this.setValueOf( 'main', 'data', oldData = editor.getData() );
		},

		onOk: (function() {
			function setData( newData ) {
				var that = this;

				editor.setData( newData, function() {
					that.hide();

					// Ensure correct selection.
					var range = editor.createRange();
					range.moveToElementEditStart( editor.editable() );
					range.select();
				} );
			}

			return function( event ) {
				// Remove CR from input data for reliable comparison with editor data.
				var newData = this.getValueOf( 'main', 'data' ).replace( /\r/g, '' );

				// Avoid unnecessary setData. Also preserve selection
				// when user changed his mind and goes back to wysiwyg editing.
				if ( newData === oldData )
					return true;

				// Set data asynchronously to avoid errors in IE.
				CKEDITOR.env.ie ?
						CKEDITOR.tools.setTimeout( setData, 0, this, newData )
					:
						setData.call( this, newData );

				// Don't let the dialog close before setData is over.
				return false;
			};
		})(),

		contents: [{
			id: 'main',
			label: editor.lang.sourcedialog.title,
			elements: [{
				type: 'textarea',
				type: 'textarea',
				id: 'data',
				dir: 'ltr',
				inputStyle: 'cursor:auto;' +
					'width:' + width + 'px;' +
					'height:' + height + 'px;' +
					'tab-size:4;' +
					'text-align:left;',
				'class': 'cke_source'
			}]
		}]
	};
});
