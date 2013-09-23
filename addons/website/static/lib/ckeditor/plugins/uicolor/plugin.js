/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

CKEDITOR.plugins.add( 'uicolor', {
	requires: 'dialog',
	lang: 'bg,cs,cy,da,de,el,en,eo,et,fa,fi,fr,he,hr,it,ku,mk,nb,nl,no,pl,tr,ug,uk,vi,zh-cn', // %REMOVE_LINE_CORE%
	icons: 'uicolor', // %REMOVE_LINE_CORE%
	hidpi: true, // %REMOVE_LINE_CORE%
	init: function( editor ) {
		if ( CKEDITOR.env.ie6Compat )
			return;

		editor.addCommand( 'uicolor', new CKEDITOR.dialogCommand( 'uicolor' ) );
		editor.ui.addButton && editor.ui.addButton( 'UIColor', {
			label: editor.lang.uicolor.title,
			command: 'uicolor',
			toolbar: 'tools,1'
		});
		CKEDITOR.dialog.add( 'uicolor', this.path + 'dialogs/uicolor.js' );

		// Load YUI js files.
		CKEDITOR.scriptLoader.load( CKEDITOR.getUrl( 'plugins/uicolor/yui/yui.js' ) );

		// Load YUI css files.
		CKEDITOR.document.appendStyleSheet( CKEDITOR.getUrl( 'plugins/uicolor/yui/assets/yui.css' ) );
	}
});
