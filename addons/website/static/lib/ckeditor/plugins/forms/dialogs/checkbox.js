/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */
CKEDITOR.dialog.add( 'checkbox', function( editor ) {
	return {
		title: editor.lang.forms.checkboxAndRadio.checkboxTitle,
		minWidth: 350,
		minHeight: 140,
		onShow: function() {
			delete this.checkbox;

			var element = this.getParentEditor().getSelection().getSelectedElement();

			if ( element && element.getAttribute( 'type' ) == 'checkbox' ) {
				this.checkbox = element;
				this.setupContent( element );
			}
		},
		onOk: function() {
			var editor,
				element = this.checkbox,
				isInsertMode = !element;

			if ( isInsertMode ) {
				editor = this.getParentEditor();
				element = editor.document.createElement( 'input' );
				element.setAttribute( 'type', 'checkbox' );
				editor.insertElement( element );
			}
			this.commitContent({ element: element } );
		},
		contents: [
			{
			id: 'info',
			label: editor.lang.forms.checkboxAndRadio.checkboxTitle,
			title: editor.lang.forms.checkboxAndRadio.checkboxTitle,
			startupFocus: 'txtName',
			elements: [
				{
				id: 'txtName',
				type: 'text',
				label: editor.lang.common.name,
				'default': '',
				accessKey: 'N',
				setup: function( element ) {
					this.setValue( element.data( 'cke-saved-name' ) || element.getAttribute( 'name' ) || '' );
				},
				commit: function( data ) {
					var element = data.element;

					// IE failed to update 'name' property on input elements, protect it now.
					if ( this.getValue() )
						element.data( 'cke-saved-name', this.getValue() );
					else {
						element.data( 'cke-saved-name', false );
						element.removeAttribute( 'name' );
					}
				}
			},
				{
				id: 'txtValue',
				type: 'text',
				label: editor.lang.forms.checkboxAndRadio.value,
				'default': '',
				accessKey: 'V',
				setup: function( element ) {
					var value = element.getAttribute( 'value' );
					// IE Return 'on' as default attr value.
					this.setValue( CKEDITOR.env.ie && value == 'on' ? '' : value );
				},
				commit: function( data ) {
					var element = data.element,
						value = this.getValue();

					if ( value && !( CKEDITOR.env.ie && value == 'on' ) )
						element.setAttribute( 'value', value );
					else {
						if ( CKEDITOR.env.ie ) {
							// Remove attribute 'value' of checkbox (#4721).
							var checkbox = new CKEDITOR.dom.element( 'input', element.getDocument() );
							element.copyAttributes( checkbox, { value:1 } );
							checkbox.replace( element );
							editor.getSelection().selectElement( checkbox );
							data.element = checkbox;
						} else
							element.removeAttribute( 'value' );
					}
				}
			},
				{
				id: 'cmbSelected',
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

					if ( CKEDITOR.env.ie ) {
						var isElementChecked = !!element.getAttribute( 'checked' ),
							isChecked = !!this.getValue();

						if ( isElementChecked != isChecked ) {
							var replace = CKEDITOR.dom.element.createFromHtml( '<input type="checkbox"' + ( isChecked ? ' checked="checked"' : '' )
								+ '/>', editor.document );

							element.copyAttributes( replace, { type:1,checked:1 } );
							replace.replace( element );
							editor.getSelection().selectElement( replace );
							data.element = replace;
						}
					} else {
						var value = this.getValue();
						if ( value )
							element.setAttribute( 'checked', 'checked' );
						else
							element.removeAttribute( 'checked' );
					}
				}
			}
			]
		}
		]
	};
});
