/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the "virtual" dialog, dialog content and dialog button
 * definition classes.
 */

/**
 * The definition of a dialog window.
 *
 * This class is not really part of the API. It just illustrates the properties
 * that developers can use to define and create dialogs.
 *
 *		// There is no constructor for this class, the user just has to define an
 *		// object with the appropriate properties.
 *
 *		CKEDITOR.dialog.add( 'testOnly', function( editor ) {
 *			return {
 *				title:			'Test Dialog',
 *				resizable:		CKEDITOR.DIALOG_RESIZE_BOTH,
 *				minWidth:		500,
 *				minHeight:		400,
 *				contents: [
 *					{
 *						id:			'tab1',
 *						label:		'First Tab',
 *						title:		'First Tab Title',
 *						accessKey:	'Q',
 *						elements: [
 *							{
 *								type:			'text',
 *								label:			'Test Text 1',
 *								id:				'testText1',
 *								'default':		'hello world!'
 *							}
 *						]
 *					}
 *				]
 *			};
 *		} );
 *
 * @class CKEDITOR.dialog.definition
 */

/**
 * The dialog title, displayed in the dialog's header. Required.
 *
 * @property {String} title
 */

/**
 * How the dialog can be resized, must be one of the four contents defined below.
 *
 * * {@link CKEDITOR#DIALOG_RESIZE_NONE}
 * * {@link CKEDITOR#DIALOG_RESIZE_WIDTH}
 * * {@link CKEDITOR#DIALOG_RESIZE_HEIGHT}
 * * {@link CKEDITOR#DIALOG_RESIZE_BOTH}
 *
 * @property {Number} [resizable=CKEDITOR.DIALOG_RESIZE_NONE]
 */

/**
 * The minimum width of the dialog, in pixels.
 *
 * @property {Number} [minWidth=600]
 */

/**
 * The minimum height of the dialog, in pixels.
 *
 * @property {Number} [minHeight=400]
 */


/**
 * The initial width of the dialog, in pixels.
 *
 * @since 3.5.3
 * @property {Number} [width=CKEDITOR.dialog.definition#minWidth]
 */

/**
 * The initial height of the dialog, in pixels.
 *
 * @since 3.5.3
 * @property {Number} [height=CKEDITOR.dialog.definition.minHeight]
 */

/**
 * The buttons in the dialog, defined as an array of
 * {@link CKEDITOR.dialog.definition.button} objects.
 *
 * @property {Array} [buttons=[ CKEDITOR.dialog.okButton, CKEDITOR.dialog.cancelButton ]]
 */

/**
 * The contents in the dialog, defined as an array of
 * {@link CKEDITOR.dialog.definition.content} objects. Required.
 *
 * @property {Array} contents
 */

/**
 * The function to execute when OK is pressed.
 *
 * @property {Function} onOk
 */

/**
 * The function to execute when Cancel is pressed.
 *
 * @property {Function} onCancel
 */

/**
 * The function to execute when the dialog is displayed for the first time.
 *
 * @property {Function} onLoad
 */

/**
 * The function to execute when the dialog is loaded (executed every time the dialog is opened).
 *
 * @property {Function} onShow
 */

/**
 * This class is not really part of the API. It just illustrates the properties
 * that developers can use to define and create dialog content pages.
 *
 * @class CKEDITOR.dialog.definition.content.
 */

/**
 * The id of the content page.
 *
 * @property {String} id
 */

/**
 * The tab label of the content page.
 *
 * @property {String} label
 */

/**
 * The popup message of the tab label.
 *
 * @property {String} title
 */

/**
 * The CTRL hotkey for switching to the tab.
 *
 *		contentDefinition.accessKey = 'Q'; // Switch to this page when CTRL-Q is pressed.
 *
 * @property {String} accessKey
 */

/**
 * The UI elements contained in this content page, defined as an array of
 * {@link CKEDITOR.dialog.definition.uiElement} objects.
 *
 * @property {Array} elements
 */

/**
 * The definition of user interface element (textarea, radio etc).
 *
 * This class is not really part of the API. It just illustrates the properties
 * that developers can use to define and create dialog UI elements.
 *
 * @class CKEDITOR.dialog.definition.uiElement
 * @see CKEDITOR.ui.dialog.uiElement
 */

/**
 * The id of the UI element.
 *
 * @property {String} id
 */

/**
 * The type of the UI element. Required.
 *
 * @property {String} type
 */

/**
 * The popup label of the UI element.
 *
 * @property {String} title
 */

/**
 * The content that needs to be allowed to enable this UI element.
 * All formats accepted by {@link CKEDITOR.filter#check} may be used.
 *
 * When all UI elements in a tab are disabled, this tab will be disabled automatically.
 *
 * @property {String/Object/CKEDITOR.style} requiredContent
 */

/**
 * CSS class names to append to the UI element.
 *
 * @property {String} className
 */

/**
 * Inline CSS classes to append to the UI element.
 *
 * @property {String} style
 */

/**
 * Horizontal alignment (in container) of the UI element.
 *
 * @property {String} align
 */

/**
 * Function to execute the first time the UI element is displayed.
 *
 * @property {Function} onLoad
 */

/**
 * Function to execute whenever the UI element's parent dialog is displayed.
 *
 * @property {Function} onShow
 */

/**
 * Function to execute whenever the UI element's parent dialog is closed.
 *
 * @property {Function} onHide
 */

/**
 * Function to execute whenever the UI element's parent
 * dialog's {@link CKEDITOR.dialog#setupContent} method is executed.
 * It usually takes care of the respective UI element as a standalone element.
 *
 * @property {Function} setup
 */

/**
 * Function to execute whenever the UI element's parent
 * dialog's {@link CKEDITOR.dialog#commitContent} method is executed.
 * It usually takes care of the respective UI element as a standalone element.
 *
 * @property {Function} commit
 */

// ----- hbox -----------------------------------------------------------------

/**
 * Horizontal layout box for dialog UI elements, auto-expends to available width of container.
 *
 * This class is not really part of the API. It just illustrates the properties
 * that developers can use to define and create horizontal layouts.
 *
 * Once the dialog is opened, the created element becomes a {@link CKEDITOR.ui.dialog.hbox} object and can be accessed with {@link CKEDITOR.dialog#getContentElement}.
 *
 *		// There is no constructor for this class, the user just has to define an
 *		// object with the appropriate properties.
 *
 *		// Example:
 *		{
 *			type: 'hbox',
 *			widths: [ '25%', '25%', '50%' ],
 *			children: [
 *				{
 *					type: 'text',
 *					id: 'id1',
 *					width: '40px',
 *				},
 *				{
 *					type: 'text',
 *					id: 'id2',
 *					width: '40px',
 *				},
 *				{
 *					type: 'text',
 *					id: 'id3'
 *				}
 *			]
 *		}
 *
 * @class CKEDITOR.dialog.definition.hbox
 * @extends CKEDITOR.dialog.definition.uiElement
 */

/**
 * Array of {@link CKEDITOR.ui.dialog.uiElement} objects inside this container.
 *
 * @property {Array} children
 */

/**
 * (Optional) The widths of child cells.
 *
 * @property {Array} widths
 */

/**
 * (Optional) The height of the layout.
 *
 * @property {Number} height
 */

/**
 * The CSS styles to apply to this element.
 *
 * @property {String} styles
 */

/**
 * (Optional) The padding width inside child cells. Example: 0, 1.
 *
 * @property {Number} padding
 */

/**
 * (Optional) The alignment of the whole layout. Example: center, top.
 *
 * @property {String} align
 */

// ----- vbox -----------------------------------------------------------------

/**
 * Vertical layout box for dialog UI elements.
 *
 * This class is not really part of the API. It just illustrates the properties
 * that developers can use to define and create vertical layouts.
 *
 * Once the dialog is opened, the created element becomes a {@link CKEDITOR.ui.dialog.vbox} object and can
 * be accessed with {@link CKEDITOR.dialog#getContentElement}.
 *
 *		// There is no constructor for this class, the user just has to define an
 *		// object with the appropriate properties.
 *
 *		// Example:
 *		{
 *			type: 'vbox',
 *			align: 'right',
 *			width: '200px',
 *			children: [
 *				{
 *					type: 'text',
 *					id: 'age',
 *					label: 'Age'
 *				},
 *				{
 *					type: 'text',
 *					id: 'sex',
 *					label: 'Sex'
 *				},
 *				{
 *					type: 'text',
 *					id: 'nationality',
 *					label: 'Nationality'
 *				}
 *			]
 *		}
 *
 * @class CKEDITOR.dialog.definition.vbox
 * @extends CKEDITOR.dialog.definition.uiElement
 */

/**
 * Array of {@link CKEDITOR.ui.dialog.uiElement} objects inside this container.
 *
 * @property {Array} children
 */

/**
 * (Optional) The width of the layout.
 *
 * @property {Array} width
 */

/**
 * (Optional) The heights of individual cells.
 *
 * @property {Number} heights
 */

/**
 * The CSS styles to apply to this element.
 *
 * @property {String} styles
 */

/**
 * (Optional) The padding width inside child cells. Example: 0, 1.
 *
 * @property {Number} padding
 */

/**
 * (Optional) The alignment of the whole layout. Example: center, top.
 *
 * @property {String} align
 */

/**
 * (Optional) Whether the layout should expand vertically to fill its container.
 *
 * @property {Boolean} expand
 */

// ----- labeled element ------------------------------------------------------

/**
 * The definition of labeled user interface element (textarea, textInput etc).
 *
 * This class is not really part of the API. It just illustrates the properties
 * that developers can use to define and create dialog UI elements.
 *
 * @class CKEDITOR.dialog.definition.labeledElement
 * @extends CKEDITOR.dialog.definition.uiElement
 * @see CKEDITOR.ui.dialog.labeledElement
 */

/**
 * The label of the UI element.
 *
 *		{
 *			type: 'text',
 *			label: 'My Label'
 *		}
 *
 * @property {String} label
 */

/**
 * (Optional) Specify the layout of the label. Set to `'horizontal'` for horizontal layout.
 * The default layout is vertical.
 *
 *		{
 *			type: 'text',
 *			label: 'My Label',
 *			labelLayout: 'horizontal'
 *		}
 *
 * @property {String} labelLayout
 */

/**
 * (Optional) Applies only to horizontal layouts: a two elements array of lengths to specify the widths of the
 * label and the content element. See also {@link CKEDITOR.dialog.definition.labeledElement#labelLayout}.
 *
 *		{
 *			type: 'text',
 *			label: 'My Label',
 *			labelLayout: 'horizontal',
 *			widths: [100, 200]
 *		}
 *
 * @property {Array} widths
 */

/**
 * Specify the inline style of the uiElement label.
 *
 *		{
 *			type: 'text',
 *			label: 'My Label',
 *			labelStyle: 'color: red'
 *		}
 *
 * @property {String} labelStyle
 */


/**
 * Specify the inline style of the input element.
 *
 *		{
 *			type: 'text',
 *			label: 'My Label',
 *			inputStyle: 'text-align: center'
 *		}
 *
 * @since 3.6.1
 * @property {String} inputStyle
 */

/**
 * Specify the inline style of the input element container.
 *
 *		{
 *			type: 'text',
 *			label: 'My Label',
 *			controlStyle: 'width: 3em'
 *		}
 *
 * @since 3.6.1
 * @property {String} controlStyle
 */

// ----- button ---------------------------------------------------------------

/**
 * The definition of a button.
 *
 * This class is not really part of the API. It just illustrates the properties
 * that developers can use to define and create buttons.
 *
 * Once the dialog is opened, the created element becomes a {@link CKEDITOR.ui.dialog.button} object
 * and can be accessed with {@link CKEDITOR.dialog#getContentElement}.
 *
 * For a complete example of dialog definition, please check {@link CKEDITOR.dialog#add}.
 *
 *		// There is no constructor for this class, the user just has to define an
 *		// object with the appropriate properties.
 *
 *		// Example:
 *		{
 *			type: 'button',
 *			id: 'buttonId',
 *			label: 'Click me',
 *			title: 'My title',
 *			onClick: function() {
 *				// this = CKEDITOR.ui.dialog.button
 *				alert( 'Clicked: ' + this.id );
 *			}
 *		}
 *
 * @class CKEDITOR.dialog.definition.button
 * @extends CKEDITOR.dialog.definition.uiElement
 */

/**
 * Whether the button is disabled.
 *
 * @property {Boolean} disabled
 */

/**
 * The label of the UI element.
 *
 * @property {String} label
 */

// ----- checkbox ------
/**
 * The definition of a checkbox element.
 *
 * This class is not really part of the API. It just illustrates the properties
 * that developers can use to define and create groups of checkbox buttons.
 *
 * Once the dialog is opened, the created element becomes a {@link CKEDITOR.ui.dialog.checkbox} object
 * and can be accessed with {@link CKEDITOR.dialog#getContentElement}.
 *
 * For a complete example of dialog definition, please check {@link CKEDITOR.dialog#add}.
 *
 *		// There is no constructor for this class, the user just has to define an
 *		// object with the appropriate properties.
 *
 *		// Example:
 *		{
 *			type: 'checkbox',
 *			id: 'agree',
 *			label: 'I agree',
 *			'default': 'checked',
 *			onClick: function() {
 *				// this = CKEDITOR.ui.dialog.checkbox
 *				alert( 'Checked: ' + this.getValue() );
 *			}
 *		}
 *
 * @class CKEDITOR.dialog.definition.checkbox
 * @extends CKEDITOR.dialog.definition.uiElement
 */

/**
 * (Optional) The validation function.
 *
 * @property {Function} validate
 */

/**
 * The label of the UI element.
 *
 * @property {String} label
 */

/**
 * The default state.
 *
 * @property {String} [default='' (unchecked)]
 */

// ----- file -----------------------------------------------------------------

/**
 * The definition of a file upload input.
 *
 * This class is not really part of the API. It just illustrates the properties
 * that developers can use to define and create file upload elements.
 *
 * Once the dialog is opened, the created element becomes a {@link CKEDITOR.ui.dialog.file} object
 * and can be accessed with {@link CKEDITOR.dialog#getContentElement}.
 *
 * For a complete example of dialog definition, please check {@link CKEDITOR.dialog#add}.
 *
 *		// There is no constructor for this class, the user just has to define an
 *		// object with the appropriate properties.
 *
 *		// Example:
 *		{
 *			type: 'file',
 *			id: 'upload',
 *			label: 'Select file from your computer',
 *			size: 38
 *		},
 *		{
 *			type: 'fileButton',
 *			id: 'fileId',
 *			label: 'Upload file',
 *			'for': [ 'tab1', 'upload' ],
 *			filebrowser: {
 *				onSelect: function( fileUrl, data ) {
 *					alert( 'Successfully uploaded: ' + fileUrl );
 *				}
 *			}
 *		}
 *
 * @class CKEDITOR.dialog.definition.file
 * @extends CKEDITOR.dialog.definition.labeledElement
 */

/**
 * (Optional) The validation function.
 *
 * @property {Function} validate
 */

/**
 * (Optional) The action attribute of the form element associated with this file upload input.
 * If empty, CKEditor will use path to server connector for currently opened folder.
 *
 * @property {String} action
 */

/**
 * The size of the UI element.
 *
 * @property {Number} size
 */

// ----- fileButton -----------------------------------------------------------

/**
 * The definition of a button for submitting the file in a file upload input.
 *
 * This class is not really part of the API. It just illustrates the properties
 * that developers can use to define and create a button for submitting the file in a file upload input.
 *
 * Once the dialog is opened, the created element becomes a {@link CKEDITOR.ui.dialog.fileButton} object
 * and can be accessed with {@link CKEDITOR.dialog#getContentElement}.
 *
 * For a complete example of dialog definition, please check {@link CKEDITOR.dialog#add}.
 *
 * @class CKEDITOR.dialog.definition.fileButton
 * @extends CKEDITOR.dialog.definition.uiElement
 */

/**
 * (Optional) The validation function.
 *
 * @property {Function} validate
 */

/**
 * The label of the UI element.
 *
 * @property {String} label
 */

/**
 * The instruction for CKEditor how to deal with file upload.
 * By default, the file and fileButton elements will not work "as expected" if this attribute is not set.
 *
 *		// Update field with id 'txtUrl' in the 'tab1' tab when file is uploaded.
 *		filebrowser: 'tab1:txtUrl'
 *
 *		// Call custom onSelect function when file is successfully uploaded.
 *		filebrowser: {
 *			onSelect: function( fileUrl, data ) {
 *				alert( 'Successfully uploaded: ' + fileUrl );
 *			}
 *		}
 *
 * @property {String} filebrowser/Object
 */

/**
 * An array that contains pageId and elementId of the file upload input element for which this button is created.
 *
 *		[ pageId, elementId ]
 *
 * @property {String} for
 */

// ----- html -----------------------------------------------------------------

/**
 * The definition of a raw HTML element.
 *
 * This class is not really part of the API. It just illustrates the properties
 * that developers can use to define and create elements made from raw HTML code.
 *
 * Once the dialog is opened, the created element becomes a {@link CKEDITOR.ui.dialog.html} object
 * and can be accessed with {@link CKEDITOR.dialog#getContentElement}.
 *
 * For a complete example of dialog definition, please check {@link CKEDITOR.dialog#add}.
 * To access HTML elements use {@link CKEDITOR.dom.document#getById}.
 *
 *		// There is no constructor for this class, the user just has to define an
 *		// object with the appropriate properties.
 *
 *		// Example 1:
 *		{
 *			type: 'html',
 *			html: '<h3>This is some sample HTML content.</h3>'
 *		}
 *
 *		// Example 2:
 *		// Complete sample with document.getById() call when the "Ok" button is clicked.
 *		var dialogDefinition = {
 *			title: 'Sample dialog',
 *			minWidth: 300,
 *			minHeight: 200,
 *			onOk: function() {
 *				// "this" is now a CKEDITOR.dialog object.
 *				var document = this.getElement().getDocument();
 *				// document = CKEDITOR.dom.document
 *				var element = <b>document.getById( 'myDiv' );</b>
 *				if ( element )
 *					alert( element.getHtml() );
 *			},
 *			contents: [
 *				{
 *					id: 'tab1',
 *					label: '',
 *					title: '',
 *					elements: [
 *						{
 *							type: 'html',
 *							html: '<div id="myDiv">Sample <b>text</b>.</div><div id="otherId">Another div.</div>'
 *						}
 *					]
 *				}
 *			],
 *			buttons: [ CKEDITOR.dialog.cancelButton, CKEDITOR.dialog.okButton ]
 *		};
 *
 * @class CKEDITOR.dialog.definition.html
 * @extends CKEDITOR.dialog.definition.uiElement
 */

/**
 * (Required) HTML code of this element.
 *
 * @property {String} html
 */

// ----- radio ----------------------------------------------------------------

/**
 * The definition of a radio group.
 *
 * This class is not really part of the API. It just illustrates the properties
 * that developers can use to define and create groups of radio buttons.
 *
 * Once the dialog is opened, the created element becomes a {@link CKEDITOR.ui.dialog.radio} object
 * and can be accessed with {@link CKEDITOR.dialog#getContentElement}.
 *
 * For a complete example of dialog definition, please check {@link CKEDITOR.dialog#add}.
 *
 *		// There is no constructor for this class, the user just has to define an
 *		// object with the appropriate properties.
 *
 *		// Example:
 *		{
 *			type: 'radio',
 *			id: 'country',
 *			label: 'Which country is bigger',
 *			items: [ [ 'France', 'FR' ], [ 'Germany', 'DE' ] ],
 *			style: 'color: green',
 *			'default': 'DE',
 *			onClick: function() {
 *				// this = CKEDITOR.ui.dialog.radio
 *				alert( 'Current value: ' + this.getValue() );
 *			}
 *		}
 *
 * @class CKEDITOR.dialog.definition.radio
 * @extends CKEDITOR.dialog.definition.labeledElement
 */

/**
 * The default value.
 *
 * @property {String} default
 */

/**
 * (Optional) The validation function.
 *
 * @property {Function} validate
 */

/**
 * An array of options. Each option is a 1- or 2-item array of format `[ 'Description', 'Value' ]`.
 * If `'Value'` is missing, then the value would be assumed to be the same as the description.
 *
 * @property {Array} items
 */

// ----- selectElement --------------------------------------------------------

/**
 * The definition of a select element.
 *
 * This class is not really part of the API. It just illustrates the properties
 * that developers can use to define and create select elements.
 *
 * Once the dialog is opened, the created element becomes a {@link CKEDITOR.ui.dialog.select} object
 * and can be accessed with {@link CKEDITOR.dialog#getContentElement}.
 *
 * For a complete example of dialog definition, please check {@link CKEDITOR.dialog#add}.
 *
 *		// There is no constructor for this class, the user just has to define an
 *		// object with the appropriate properties.
 *
 *		// Example:
 *		{
 *			type: 'select',
 *			id: 'sport',
 *			label: 'Select your favourite sport',
 *			items: [ [ 'Basketball' ], [ 'Baseball' ], [ 'Hockey' ], [ 'Football' ] ],
 *			'default': 'Football',
 *			onChange: function( api ) {
 *				// this = CKEDITOR.ui.dialog.select
 *				alert( 'Current value: ' + this.getValue() );
 *			}
 *		}
 *
 * @class CKEDITOR.dialog.definition.select
 * @extends CKEDITOR.dialog.definition.labeledElement
 */

/**
 * The default value.
 *
 * @property {String} default
 */

/**
 * (Optional) The validation function.
 *
 * @property {Function} validate
 */

/**
 * An array of options. Each option is a 1- or 2-item array of format `[ 'Description', 'Value' ]`.
 * If `'Value'` is missing, then the value would be assumed to be the same as the description.
 *
 * @property {Array} items
 */

/**
 * (Optional) Set this to true if you'd like to have a multiple-choice select box.
 *
 * @property {Boolean} [multiple=false]
 */

/**
 * (Optional) The number of items to display in the select box.
 *
 * @property {Number} size
 */

// ----- textInput ------------------------------------------------------------

/**
 * The definition of a text field (single line).
 *
 * This class is not really part of the API. It just illustrates the properties
 * that developers can use to define and create text fields.
 *
 * Once the dialog is opened, the created element becomes a {@link CKEDITOR.ui.dialog.textInput} object
 * and can be accessed with {@link CKEDITOR.dialog#getContentElement}.
 *
 * For a complete example of dialog definition, please check {@link CKEDITOR.dialog#add}.
 *
 *		// There is no constructor for this class, the user just has to define an
 *		// object with the appropriate properties.
 *
 *		{
 *			type: 'text',
 *			id: 'name',
 *			label: 'Your name',
 *			'default': '',
 *			validate: function() {
 *				if ( !this.getValue() ) {
 *					api.openMsgDialog( '', 'Name cannot be empty.' );
 *					return false;
 *				}
 *			}
 *		}
 *
 * @class CKEDITOR.dialog.definition.textInput
 * @extends CKEDITOR.dialog.definition.labeledElement
 */

/**
 * The default value.
 *
 * @property {String} default
 */

/**
 * (Optional) The maximum length.
 *
 * @property {Number} maxLength
 */

/**
 * (Optional) The size of the input field.
 *
 * @property {Number} size
 */

/**
 * (Optional) The validation function.
 *
 * @property {Function} validate
 */

// ----- textarea -------------------------------------------------------------

/**
 * The definition of a text field (multiple lines).
 *
 * This class is not really part of the API. It just illustrates the properties
 * that developers can use to define and create textarea.
 *
 * Once the dialog is opened, the created element becomes a {@link CKEDITOR.ui.dialog.textarea} object
 * and can be accessed with {@link CKEDITOR.dialog#getContentElement}.
 *
 * For a complete example of dialog definition, please check {@link CKEDITOR.dialog#add}.
 *
* 		// There is no constructor for this class, the user just has to define an
* 		// object with the appropriate properties.
*
* 		// Example:
* 		{
* 			type: 'textarea',
* 			id: 'message',
* 			label: 'Your comment',
* 			'default': '',
* 			validate: function() {
* 				if ( this.getValue().length < 5 ) {
* 					api.openMsgDialog( 'The comment is too short.' );
* 					return false;
* 				}
* 			}
* 		}
 *
 * @class CKEDITOR.dialog.definition.textarea
 * @extends CKEDITOR.dialog.definition.labeledElement
 */

/**
 * The number of rows.
 *
 * @property {Number} rows
 */

/**
 * The number of columns.
 *
 * @property {Number} cols
 */

/**
 * (Optional) The validation function.
 *
 * @property {Function} validate
 */

/**
 * The default value.
 *
 * @property {String} default
 */
