/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

CKEDITOR.dialog.add( 'uicolor', function( editor ) {
	var dialog, picker, pickerContents,
	// Actual UI color value.
	uiColor = editor.getUiColor(),
		pickerId = 'cke_uicolor_picker' + CKEDITOR.tools.getNextNumber();

	function setNewPickerColor( color ) {
		// Convert HEX representation to RGB, stripping # char.
		if ( /^#/.test( color ) )
			color = window.YAHOO.util.Color.hex2rgb( color.substr( 1 ) );
		picker.setValue( color, true );
		// Refresh picker UI.
		picker.refresh( pickerId );
	}

	function setNewUiColor( color ) {
		editor.setUiColor( color );
		// Write new config string into textbox.
		dialog._.contents.tab1.configBox.setValue( 'config.uiColor = "#' + picker.get( "hex" ) + '"' );
	}

	pickerContents = {
		id: 'yuiColorPicker',
		type: 'html',
		html: "<div id='" + pickerId + "' class='cke_uicolor_picker' style='width: 360px; height: 200px; position: relative;'></div>",
		onLoad: function( event ) {
			var url = CKEDITOR.getUrl( 'plugins/uicolor/yui/' );

			// Create new color picker widget.
			picker = new window.YAHOO.widget.ColorPicker( pickerId, {
				showhsvcontrols: true,
				showhexcontrols: true,
				images: {
					PICKER_THUMB: url + "assets/picker_thumb.png",
					HUE_THUMB: url + "assets/hue_thumb.png"
				}
			});

			// Make Yahoo widget available to public.
			this.picker = picker;

			// Set actual UI color to the picker.
			if ( uiColor )
				setNewPickerColor( uiColor );

			// Subscribe to the rgbChange event.
			picker.on( "rgbChange", function() {
				// Reset predefined box.
				dialog._.contents.tab1.predefined.setValue( '' );
				setNewUiColor( '#' + picker.get( 'hex' ) );
			});

			// Fix input class names.
			var inputs = new CKEDITOR.dom.nodeList( picker.getElementsByTagName( 'input' ) );
			for ( var i = 0; i < inputs.count(); i++ )
				inputs.getItem( i ).addClass( 'cke_dialog_ui_input_text' );
		}
	};

	return {
		title: editor.lang.uicolor.title,
		minWidth: 360,
		minHeight: 320,
		onLoad: function() {
			dialog = this;
			this.setupContent();

			// #3808
			if ( CKEDITOR.env.ie7Compat )
				dialog.parts.contents.setStyle( 'overflow', 'hidden' );
		},
		contents: [
			{
			id: 'tab1',
			label: '',
			title: '',
			expand: true,
			padding: 0,
			elements: [
				pickerContents,
			{
				id: 'tab1',
				type: 'vbox',
				children: [
					{
					type: 'hbox',
					children: [
						{
						id: 'predefined',
						type: 'select',
						'default': '',
						label: editor.lang.uicolor.predefined,
						items: [
							[ '' ],
							[ 'Light blue', '#9AB8F3' ],
							[ 'Sand', '#D2B48C' ],
							[ 'Metallic', '#949AAA' ],
							[ 'Purple', '#C2A3C7' ],
							[ 'Olive', '#A2C980' ],
							[ 'Happy green', '#9BD446' ],
							[ 'Jezebel Blue', '#14B8C4' ],
							[ 'Burn', '#FF893A' ],
							[ 'Easy red', '#FF6969' ],
							[ 'Pisces 3', '#48B4F2' ],
							[ 'Aquarius 5', '#487ED4' ],
							[ 'Absinthe', '#A8CF76' ],
							[ 'Scrambled Egg', '#C7A622' ],
							[ 'Hello monday', '#8E8D80' ],
							[ 'Lovely sunshine', '#F1E8B1' ],
							[ 'Recycled air', '#B3C593' ],
							[ 'Down', '#BCBCA4' ],
							[ 'Mark Twain', '#CFE91D' ],
							[ 'Specks of dust', '#D1B596' ],
							[ 'Lollipop', '#F6CE23' ]
							],
						onChange: function() {
							var color = this.getValue();
							if ( color ) {
								setNewPickerColor( color );
								setNewUiColor( color );
								// Refresh predefined preview box.
								CKEDITOR.document.getById( 'predefinedPreview' ).setStyle( 'background', color );
							} else
								CKEDITOR.document.getById( 'predefinedPreview' ).setStyle( 'background', '' );
						},
						onShow: function() {
							var color = editor.getUiColor();
							if ( color )
								this.setValue( color );
						}
					},
						{
						id: 'predefinedPreview',
						type: 'html',
						html: '<div id="cke_uicolor_preview" style="border: 1px solid black; padding: 3px; width: 30px;">' +
							'<div id="predefinedPreview" style="width: 30px; height: 30px;">&nbsp;</div>' +
							'</div>'
					}
					]
				},
					{
					id: 'configBox',
					type: 'text',
					label: editor.lang.uicolor.config,
					onShow: function() {
						var color = editor.getUiColor();
						if ( color )
							this.setValue( 'config.uiColor = "' + color + '"' );
					}
				}
				]
			}
			]
		}
		],
		buttons: [ CKEDITOR.dialog.okButton ]
	};
});
