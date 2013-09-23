/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Forms Plugin
 */

CKEDITOR.plugins.add( 'forms', {
	requires: 'dialog,fakeobjects',
	lang: 'af,ar,bg,bn,bs,ca,cs,cy,da,de,el,en,en-au,en-ca,en-gb,eo,es,et,eu,fa,fi,fo,fr,fr-ca,gl,gu,he,hi,hr,hu,id,is,it,ja,ka,km,ko,ku,lt,lv,mk,mn,ms,nb,nl,no,pl,pt,pt-br,ro,ru,si,sk,sl,sq,sr,sr-latn,sv,th,tr,ug,uk,vi,zh,zh-cn', // %REMOVE_LINE_CORE%
	icons: 'button,checkbox,form,hiddenfield,imagebutton,radio,select,select-rtl,textarea,textarea-rtl,textfield', // %REMOVE_LINE_CORE%
	hidpi: true, // %REMOVE_LINE_CORE%
	onLoad: function() {
		CKEDITOR.addCss( '.cke_editable form' +
			'{' +
				'border: 1px dotted #FF0000;' +
				'padding: 2px;' +
			'}\n' );

		CKEDITOR.addCss( 'img.cke_hidden' +
			'{' +
				'background-image: url(' + CKEDITOR.getUrl( this.path + 'images/hiddenfield.gif' ) + ');' +
				'background-position: center center;' +
				'background-repeat: no-repeat;' +
				'border: 1px solid #a9a9a9;' +
				'width: 16px !important;' +
				'height: 16px !important;' +
			'}' );

	},
	init: function( editor ) {
		var lang = editor.lang,
			order = 0,
			textfieldTypes = { email:1,password:1,search:1,tel:1,text:1,url:1 },
			allowedContent = {
				checkbox: 'input[type,name,checked]',
				radio: 'input[type,name,checked]',
				textfield: 'input[type,name,value,size,maxlength]',
				textarea: 'textarea[cols,rows,name]',
				select: 'select[name,size,multiple]; option[value,selected]',
				button: 'input[type,name,value]',
				form: 'form[action,name,id,enctype,target,method]',
				hiddenfield: 'input[type,name,value]',
				imagebutton: 'input[type,alt,src]{width,height,border,border-width,border-style,margin,float}'
			},
			requiredContent = {
				checkbox: 'input',
				radio: 'input',
				textfield: 'input',
				textarea: 'textarea',
				select: 'select',
				button: 'input',
				form: 'form',
				hiddenfield: 'input',
				imagebutton: 'input'
			};

		// All buttons use the same code to register. So, to avoid
		// duplications, let's use this tool function.
		var addButtonCommand = function( buttonName, commandName, dialogFile ) {
				var def = {
					allowedContent: allowedContent[ commandName ],
					requiredContent: requiredContent[ commandName ]
				};
				commandName == 'form' && ( def.context = 'form' );

				editor.addCommand( commandName, new CKEDITOR.dialogCommand( commandName, def ) );

				editor.ui.addButton && editor.ui.addButton( buttonName, {
					label: lang.common[ buttonName.charAt( 0 ).toLowerCase() + buttonName.slice( 1 ) ],
					command: commandName,
					toolbar: 'forms,' + ( order += 10 )
				});
				CKEDITOR.dialog.add( commandName, dialogFile );
			};

		var dialogPath = this.path + 'dialogs/';
		!editor.blockless && addButtonCommand( 'Form', 'form', dialogPath + 'form.js' );
		addButtonCommand( 'Checkbox', 'checkbox', dialogPath + 'checkbox.js' );
		addButtonCommand( 'Radio', 'radio', dialogPath + 'radio.js' );
		addButtonCommand( 'TextField', 'textfield', dialogPath + 'textfield.js' );
		addButtonCommand( 'Textarea', 'textarea', dialogPath + 'textarea.js' );
		addButtonCommand( 'Select', 'select', dialogPath + 'select.js' );
		addButtonCommand( 'Button', 'button', dialogPath + 'button.js' );

		// If the "image" plugin is loaded.
		var imagePlugin = CKEDITOR.plugins.get( 'image' );
		imagePlugin && addButtonCommand( 'ImageButton', 'imagebutton', CKEDITOR.plugins.getPath( 'image' ) + 'dialogs/image.js' );

		addButtonCommand( 'HiddenField', 'hiddenfield', dialogPath + 'hiddenfield.js' );

		// If the "menu" plugin is loaded, register the menu items.
		if ( editor.addMenuItems ) {
			var items = {
				checkbox: {
					label: lang.forms.checkboxAndRadio.checkboxTitle,
					command: 'checkbox',
					group: 'checkbox'
				},

				radio: {
					label: lang.forms.checkboxAndRadio.radioTitle,
					command: 'radio',
					group: 'radio'
				},

				textfield: {
					label: lang.forms.textfield.title,
					command: 'textfield',
					group: 'textfield'
				},

				hiddenfield: {
					label: lang.forms.hidden.title,
					command: 'hiddenfield',
					group: 'hiddenfield'
				},

				imagebutton: {
					label: lang.image.titleButton,
					command: 'imagebutton',
					group: 'imagebutton'
				},

				button: {
					label: lang.forms.button.title,
					command: 'button',
					group: 'button'
				},

				select: {
					label: lang.forms.select.title,
					command: 'select',
					group: 'select'
				},

				textarea: {
					label: lang.forms.textarea.title,
					command: 'textarea',
					group: 'textarea'
				}
			};

			!editor.blockless && ( items.form = {
				label: lang.forms.form.menu,
				command: 'form',
				group: 'form'
			});

			editor.addMenuItems( items );

		}

		// If the "contextmenu" plugin is loaded, register the listeners.
		if ( editor.contextMenu ) {
			!editor.blockless && editor.contextMenu.addListener( function( element, selection, path ) {
				var form = path.contains( 'form', 1 );
				if ( form && !form.isReadOnly() )
					return { form: CKEDITOR.TRISTATE_OFF };
			});

			editor.contextMenu.addListener( function( element ) {
				if ( element && !element.isReadOnly() ) {
					var name = element.getName();

					if ( name == 'select' )
						return { select: CKEDITOR.TRISTATE_OFF };

					if ( name == 'textarea' )
						return { textarea: CKEDITOR.TRISTATE_OFF };

					if ( name == 'input' ) {
						var type = element.getAttribute( 'type' ) || 'text';
						switch ( type ) {
							case 'button':
							case 'submit':
							case 'reset':
								return { button: CKEDITOR.TRISTATE_OFF };

							case 'checkbox':
								return { checkbox: CKEDITOR.TRISTATE_OFF };

							case 'radio':
								return { radio: CKEDITOR.TRISTATE_OFF };

							case 'image':
								return imagePlugin ? { imagebutton: CKEDITOR.TRISTATE_OFF } : null;
						}

						if ( textfieldTypes[ type ] )
							return { textfield: CKEDITOR.TRISTATE_OFF };
					}

					if ( name == 'img' && element.data( 'cke-real-element-type' ) == 'hiddenfield' )
						return { hiddenfield: CKEDITOR.TRISTATE_OFF };
				}
			});
		}

		editor.on( 'doubleclick', function( evt ) {
			var element = evt.data.element;

			if ( !editor.blockless && element.is( 'form' ) )
				evt.data.dialog = 'form';
			else if ( element.is( 'select' ) )
				evt.data.dialog = 'select';
			else if ( element.is( 'textarea' ) )
				evt.data.dialog = 'textarea';
			else if ( element.is( 'img' ) && element.data( 'cke-real-element-type' ) == 'hiddenfield' )
				evt.data.dialog = 'hiddenfield';
			else if ( element.is( 'input' ) ) {
				var type = element.getAttribute( 'type' ) || 'text';
				switch ( type ) {
					case 'button':
					case 'submit':
					case 'reset':
						evt.data.dialog = 'button';
						break;
					case 'checkbox':
						evt.data.dialog = 'checkbox';
						break;
					case 'radio':
						evt.data.dialog = 'radio';
						break;
					case 'image':
						evt.data.dialog = 'imagebutton';
						break;
				}
				if ( textfieldTypes[ type ] )
					evt.data.dialog = 'textfield';
			}
		});
	},

	afterInit: function( editor ) {
		var dataProcessor = editor.dataProcessor,
			htmlFilter = dataProcessor && dataProcessor.htmlFilter,
			dataFilter = dataProcessor && dataProcessor.dataFilter;

		// Cleanup certain IE form elements default values.
		if ( CKEDITOR.env.ie ) {
			htmlFilter && htmlFilter.addRules({
				elements: {
					input: function( input ) {
						var attrs = input.attributes,
							type = attrs.type;
						// Old IEs don't provide type for Text inputs #5522
						if ( !type )
							attrs.type = 'text';
						if ( type == 'checkbox' || type == 'radio' )
							attrs.value == 'on' && delete attrs.value;
					}
				}
			});
		}

		if ( dataFilter ) {
			dataFilter.addRules({
				elements: {
					input: function( element ) {
						if ( element.attributes.type == 'hidden' )
							return editor.createFakeParserElement( element, 'cke_hidden', 'hiddenfield' );
					}
				}
			});
		}
	}
});

if ( CKEDITOR.env.ie ) {
	CKEDITOR.dom.element.prototype.hasAttribute = CKEDITOR.tools.override( CKEDITOR.dom.element.prototype.hasAttribute, function( original ) {
		return function( name ) {
			var $attr = this.$.attributes.getNamedItem( name );

			if ( this.getName() == 'input' ) {
				switch ( name ) {
					case 'class':
						return this.$.className.length > 0;
					case 'checked':
						return !!this.$.checked;
					case 'value':
						var type = this.getAttribute( 'type' );
						return type == 'checkbox' || type == 'radio' ? this.$.value != 'on' : this.$.value;
				}
			}

			return original.apply( this, arguments );
		};
	});
}
