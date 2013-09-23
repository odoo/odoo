/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */
CKEDITOR.dialog.add( 'hiddenfield', function( editor ) {
	return {
		title: editor.lang.forms.hidden.title,
		hiddenField: null,
		minWidth: 350,
		minHeight: 110,
		onShow: function() {
			delete this.hiddenField;

			var editor = this.getParentEditor(),
				selection = editor.getSelection(),
				element = selection.getSelectedElement();

			if ( element && element.data( 'cke-real-element-type' ) && element.data( 'cke-real-element-type' ) == 'hiddenfield' ) {
				this.hiddenField = element;
				element = editor.restoreRealElement( this.hiddenField );
				this.setupContent( element );
				selection.selectElement( this.hiddenField );
			}
		},
		onOk: function() {
			var name = this.getValueOf( 'info', '_cke_saved_name' ),
				value = this.getValueOf( 'info', 'value' ),
				editor = this.getParentEditor(),
				element = CKEDITOR.env.ie && !( CKEDITOR.document.$.documentMode >= 8 ) ? editor.document.createElement( '<input name="' + CKEDITOR.tools.htmlEncode( name ) + '">' ) : editor.document.createElement( 'input' );

			element.setAttribute( 'type', 'hidden' );
			this.commitContent( element );
			var fakeElement = editor.createFakeElement( element, 'cke_hidden', 'hiddenfield' );
			if ( !this.hiddenField )
				editor.insertElement( fakeElement );
			else {
				fakeElement.replace( this.hiddenField );
				editor.getSelection().selectElement( fakeElement );
			}
			return true;
		},
		contents: [
			{
			id: 'info',
			label: editor.lang.forms.hidden.title,
			title: editor.lang.forms.hidden.title,
			elements: [
				{
				id: '_cke_saved_name',
				type: 'text',
				label: editor.lang.forms.hidden.name,
				'default': '',
				accessKey: 'N',
				setup: function( element ) {
					this.setValue( element.data( 'cke-saved-name' ) || element.getAttribute( 'name' ) || '' );
				},
				commit: function( element ) {
					if ( this.getValue() )
						element.setAttribute( 'name', this.getValue() );
					else {
						element.removeAttribute( 'name' );
					}
				}
			},
				{
				id: 'value',
				type: 'text',
				label: editor.lang.forms.hidden.value,
				'default': '',
				accessKey: 'V',
				setup: function( element ) {
					this.setValue( element.getAttribute( 'value' ) || '' );
				},
				commit: function( element ) {
					if ( this.getValue() )
						element.setAttribute( 'value', this.getValue() );
					else
						element.removeAttribute( 'value' );
				}
			}
			]
		}
		]
	};
});
