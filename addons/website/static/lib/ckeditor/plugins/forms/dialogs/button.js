/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */
CKEDITOR.dialog.add( 'button', function( editor ) {
	function commitAttributes( element ) {
		var val = this.getValue();
		if ( val ) {
			element.attributes[ this.id ] = val;
			if ( this.id == 'name' )
				element.attributes[ 'data-cke-saved-name' ] = val;
		} else {
			delete element.attributes[ this.id ];
			if ( this.id == 'name' )
				delete element.attributes[ 'data-cke-saved-name' ];
		}
	}

	return {
		title: editor.lang.forms.button.title,
		minWidth: 350,
		minHeight: 150,
		onShow: function() {
			delete this.button;
			var element = this.getParentEditor().getSelection().getSelectedElement();
			if ( element && element.is( 'input' ) ) {
				var type = element.getAttribute( 'type' );
				if ( type in { button:1,reset:1,submit:1 } ) {
					this.button = element;
					this.setupContent( element );
				}
			}
		},
		onOk: function() {
			var editor = this.getParentEditor(),
				element = this.button,
				isInsertMode = !element;

			var fake = element ? CKEDITOR.htmlParser.fragment.fromHtml( element.getOuterHtml() ).children[ 0 ] : new CKEDITOR.htmlParser.element( 'input' );
			this.commitContent( fake );

			var writer = new CKEDITOR.htmlParser.basicWriter();
			fake.writeHtml( writer );
			var newElement = CKEDITOR.dom.element.createFromHtml( writer.getHtml(), editor.document );

			if ( isInsertMode )
				editor.insertElement( newElement );
			else {
				newElement.replace( element );
				editor.getSelection().selectElement( newElement );
			}
		},
		contents: [
			{
			id: 'info',
			label: editor.lang.forms.button.title,
			title: editor.lang.forms.button.title,
			elements: [
				{
				id: 'name',
				type: 'text',
				label: editor.lang.common.name,
				'default': '',
				setup: function( element ) {
					this.setValue( element.data( 'cke-saved-name' ) || element.getAttribute( 'name' ) || '' );
				},
				commit: commitAttributes
			},
				{
				id: 'value',
				type: 'text',
				label: editor.lang.forms.button.text,
				accessKey: 'V',
				'default': '',
				setup: function( element ) {
					this.setValue( element.getAttribute( 'value' ) || '' );
				},
				commit: commitAttributes
			},
				{
				id: 'type',
				type: 'select',
				label: editor.lang.forms.button.type,
				'default': 'button',
				accessKey: 'T',
				items: [
					[ editor.lang.forms.button.typeBtn, 'button' ],
					[ editor.lang.forms.button.typeSbm, 'submit' ],
					[ editor.lang.forms.button.typeRst, 'reset' ]
					],
				setup: function( element ) {
					this.setValue( element.getAttribute( 'type' ) || '' );
				},
				commit: commitAttributes
			}
			]
		}
		]
	};
});
