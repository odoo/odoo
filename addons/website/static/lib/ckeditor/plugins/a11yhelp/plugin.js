/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Plugin definition for the a11yhelp, which provides a dialog
 * with accessibility related help.
 */

(function() {
	var pluginName = 'a11yhelp',
		commandName = 'a11yHelp';

	CKEDITOR.plugins.add( pluginName, {
		requires: 'dialog',

		// List of available localizations.
		availableLangs: { ar:1,bg:1,ca:1,cs:1,cy:1,da:1,de:1,el:1,en:1,eo:1,es:1,et:1,fa:1,fi:1,fr:1,'fr-ca':1,gl:1,gu:1,he:1,hi:1,hr:1,hu:1,id:1,it:1,ja:1,km:1,ku:1,lt:1,lv:1,mk:1,mn:1,nb:1,nl:1,no:1,pl:1,pt:1,'pt-br':1,ro:1,ru:1,si:1,sk:1,sl:1,sq:1,sr:1,'sr-latn':1,sv:1,th:1,tr:1,ug:1,uk:1,vi:1,'zh-cn':1 },

		init: function( editor ) {
			var plugin = this;
			editor.addCommand( commandName, {
				exec: function() {
					var langCode = editor.langCode;
					langCode =
						plugin.availableLangs[ langCode ] ? langCode :
						plugin.availableLangs[ langCode.replace( /-.*/, '' ) ] ? langCode.replace( /-.*/, '' ) :
						'en';

					CKEDITOR.scriptLoader.load( CKEDITOR.getUrl( plugin.path + 'dialogs/lang/' + langCode + '.js' ), function() {
						editor.lang.a11yhelp = plugin.langEntries[ langCode ];
						editor.openDialog( commandName );
					});
				},
				modes: { wysiwyg:1,source:1 },
				readOnly: 1,
				canUndo: false
			});

			editor.setKeystroke( CKEDITOR.ALT + 48 /*0*/, 'a11yHelp' );
			CKEDITOR.dialog.add( commandName, this.path + 'dialogs/a11yhelp.js' );
		}
	});
})();
