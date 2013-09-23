/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */
CKEDITOR.dialog.add( 'radio', function( editor ) {
	return {
		title: editor.lang.forms.checkboxAndRadio.radioTitle,
		minWidth: 350,
		minHeight: 140,
		onShow: function() {
			delete this.radioButton;

			var element = this.getParentEditor().getSelection().getSelectedElement();
			if ( element && element.getName() == 'input' && element.getAttribute( 'type' ) == 'radio' ) {
				this.radioButton = element;
				this.setupContent( element );
			}
		},
		onOk: function() {
			var editor,
				element = this.radioButton,
				isInsertMode = !element;

			if ( isInsertMode ) {
				editor = this.getParentEditor();
				element = editor.document.createElement( 'input' );
				element.setAttribute( 'type', 'radio' );
			}

			if ( isInsertMode )
				editor.insertElement( element );
			this.commitContent({ element: element } );
		},
		contents: [
			{
			id: 'info',
			label: editor.lang.forms.checkboxAndRadio.radioTitle,
			title: editor.lang.forms.checkboxAndRadio.radioTitle,
			elements: [
				{
				id: 'name',
				type: 'text',
				label: editor.lang.common.name,
				'default': '',
				accessKey: 'N',
				setup: function( element ) {
					this.setValue( element.data( 'cke-saved-name' ) || element.getAttribute( 'name' ) || '' );
				},
				commit: function( data ) {
					var element = data.element;

					if ( this.getValue() )
						element.data( 'cke-saved-name', this.getValue() );
					else {
						element.data( 'cke-saved-name', false );
						element.removeAttribute( 'name' );
					}
				}
			},
				{
				id: 'value',
				type: 'text',
				label: editor.lang.forms.checkboxAndRadio.value,
				'default': '',
				accessKey: 'V',
				setup: function( element ) {
					this.setValue( element.getAttribute( 'value' ) || '' );
				},
				commit: function( data ) {
					var element = data.element;

					if ( this.getValue() )
						element.setAttribute( 'value', this.getValue() );
					else
						element.removeAttribute( 'value' );
				}
			},
				{
				id: 'checked',
				type: 'checkbox',
				label: editor.lang.forms.checkboxAndRadio.selected,
				'default': '',
				accessKey: 'S',
				value: "checked",
				setup: function( element ) {
					this.setValue( element.getAttribute( 'checked' ) );
				},
				commit: function( data ) {
					var element = data.element;

					if ( !( CKEDITOR.env.ie || CKEDITOR.env.opera ) ) {
						if ( this.getValue() )
							element.setAttribute( 'checked', 'checked' );
						else
							element.removeAttribute( 'checked' );
					} else {
						var isElementChecked = element.getAttribute( 'checked' );
						var isChecked = !!this.getValue();

						if ( isElementChecked != isChecked ) {
							var replace = CKEDITOR.dom.element.createFromHtml( '<input type="radio"' + ( isChecked ? ' checked="checked"' : '' )
								+ '></input>', editor.document );
							element.copyAttributes( replace, { type:1,checked:1 } );
							replace.replace( element );
							editor.getSelection().selectElement( replace );
							data.element = replace;
						}
					}
				}
			}
			]
		}
		]
	};
});
