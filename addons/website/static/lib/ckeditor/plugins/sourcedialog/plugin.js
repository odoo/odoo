/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

CKEDITOR.plugins.add( 'sourcedialog', {
	lang: 'af,ar,bg,bn,bs,ca,cs,cy,da,de,el,en,en-au,en-ca,en-gb,eo,es,et,eu,fa,fi,fo,fr,fr-ca,gl,gu,he,hi,hr,hu,id,is,it,ja,ka,km,ko,ku,lt,lv,mn,ms,nb,nl,no,pl,pt,pt-br,ro,ru,si,sk,sl,sq,sr,sr-latn,sv,th,tr,ug,uk,vi,zh,zh-cn', // %REMOVE_LINE_CORE%
	icons: 'sourcedialog,sourcedialog-rtl', // %REMOVE_LINE_CORE%
	hidpi: true, // %REMOVE_LINE_CORE%

	init: function( editor ) {
		// Register the "source" command, which simply opens the "source" dialog.
		editor.addCommand( 'sourcedialog', new CKEDITOR.dialogCommand( 'sourcedialog' ) );

		// Register the "source" dialog.
		CKEDITOR.dialog.add( 'sourcedialog', this.path + 'dialogs/sourcedialog.js' );

		// If the toolbar is available, create the "Source" button.
		if ( editor.ui.addButton ) {
			editor.ui.addButton( 'Sourcedialog', {
				label: editor.lang.sourcedialog.toolbar,
				command: 'sourcedialog',
				toolbar: 'mode,10'
			});
		}
	}
});
