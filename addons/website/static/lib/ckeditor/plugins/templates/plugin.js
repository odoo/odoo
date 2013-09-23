/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

(function() {
	CKEDITOR.plugins.add( 'templates', {
		requires: 'dialog',
		lang: 'af,ar,bg,bn,bs,ca,cs,cy,da,de,el,en,en-au,en-ca,en-gb,eo,es,et,eu,fa,fi,fo,fr,fr-ca,gl,gu,he,hi,hr,hu,id,is,it,ja,ka,km,ko,ku,lt,lv,mk,mn,ms,nb,nl,no,pl,pt,pt-br,ro,ru,si,sk,sl,sq,sr,sr-latn,sv,th,tr,ug,uk,vi,zh,zh-cn', // %REMOVE_LINE_CORE%
		icons: 'templates,templates-rtl', // %REMOVE_LINE_CORE%
		hidpi: true, // %REMOVE_LINE_CORE%
		init: function( editor ) {
			CKEDITOR.dialog.add( 'templates', CKEDITOR.getUrl( this.path + 'dialogs/templates.js' ) );

			editor.addCommand( 'templates', new CKEDITOR.dialogCommand( 'templates' ) );

			editor.ui.addButton && editor.ui.addButton( 'Templates', {
				label: editor.lang.templates.button,
				command: 'templates',
				toolbar: 'doctools,10'
			});
		}
	});

	var templates = {},
		loadedTemplatesFiles = {};

	CKEDITOR.addTemplates = function( name, definition ) {
		templates[ name ] = definition;
	};

	CKEDITOR.getTemplates = function( name ) {
		return templates[ name ];
	};

	CKEDITOR.loadTemplates = function( templateFiles, callback ) {
		// Holds the templates files to be loaded.
		var toLoad = [];

		// Look for pending template files to get loaded.
		for ( var i = 0, count = templateFiles.length; i < count; i++ ) {
			if ( !loadedTemplatesFiles[ templateFiles[ i ] ] ) {
				toLoad.push( templateFiles[ i ] );
				loadedTemplatesFiles[ templateFiles[ i ] ] = 1;
			}
		}

		if ( toLoad.length )
			CKEDITOR.scriptLoader.load( toLoad, callback );
		else
			setTimeout( callback, 0 );
	};
})();



/**
 * The templates definition set to use. It accepts a list of names separated by
 * comma. It must match definitions loaded with the {@link #templates_files} setting.
 *
 *		config.templates = 'my_templates';
 *
 * @cfg {String} [templates='default']
 * @member CKEDITOR.config
 */

/**
 * The list of templates definition files to load.
 *
 *		config.templates_files = [
 *			'/editor_templates/site_default.js',
 *			'http://www.example.com/user_templates.js
 *		];
 *
 * @cfg
 * @member CKEDITOR.config
 */
CKEDITOR.config.templates_files = [
	CKEDITOR.getUrl( 'plugins/templates/templates/default.js' )
	];

/**
 * Whether the "Replace actual contents" checkbox is checked by default in the
 * Templates dialog.
 *
 *		config.templates_replaceContent = false;
 *
 * @cfg
 * @member CKEDITOR.config
 */
CKEDITOR.config.templates_replaceContent = true;
