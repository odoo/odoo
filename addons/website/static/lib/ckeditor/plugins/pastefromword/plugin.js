/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

(function() {
	CKEDITOR.plugins.add( 'pastefromword', {
		requires: 'clipboard',
		lang: 'af,ar,bg,bn,bs,ca,cs,cy,da,de,el,en,en-au,en-ca,en-gb,eo,es,et,eu,fa,fi,fo,fr,fr-ca,gl,gu,he,hi,hr,hu,id,is,it,ja,ka,km,ko,ku,lt,lv,mk,mn,ms,nb,nl,no,pl,pt,pt-br,ro,ru,si,sk,sl,sq,sr,sr-latn,sv,th,tr,ug,uk,vi,zh,zh-cn', // %REMOVE_LINE_CORE%
		icons: 'pastefromword,pastefromword-rtl', // %REMOVE_LINE_CORE%
		hidpi: true, // %REMOVE_LINE_CORE%
		init: function( editor ) {
			var commandName = 'pastefromword',
				// Flag indicate this command is actually been asked instead of a generic pasting.
				forceFromWord = 0,
				path = this.path;

			editor.addCommand( commandName, {
				// Snapshots are done manually by editable.insertXXX methods.
				canUndo: false,
				async: true,

				exec: function( editor ) {
					var cmd = this;

					forceFromWord = 1;
					// Force html mode for incomming paste events sequence.
					editor.once( 'beforePaste', forceHtmlMode );

					editor.getClipboardData({ title: editor.lang.pastefromword.title }, function( data ) {
						// Do not use editor#paste, because it would start from beforePaste event.
						data && editor.fire( 'paste', { type: 'html', dataValue: data.dataValue } );

						editor.fire( 'afterCommandExec', {
							name: commandName,
							command: cmd,
							returnValue: !!data
						});
					});
				}
			});

			// Register the toolbar button.
			editor.ui.addButton && editor.ui.addButton( 'PasteFromWord', {
				label: editor.lang.pastefromword.toolbar,
				command: commandName,
				toolbar: 'clipboard,50'
			});

			editor.on( 'pasteState', function( evt ) {
				editor.getCommand( commandName ).setState( evt.data );
			});

			// Features bring by this command beside the normal process:
			// 1. No more bothering of user about the clean-up.
			// 2. Perform the clean-up even if content is not from MS-Word.
			// (e.g. from a MS-Word similar application.)
			// 3. Listen with high priority (3), so clean up is done before content
			// type sniffing (priority = 6).
			editor.on( 'paste', function( evt ) {
				var data = evt.data,
					mswordHtml = data.dataValue;

				// MS-WORD format sniffing.
				if ( mswordHtml && ( forceFromWord || ( /(class=\"?Mso|style=\"[^\"]*\bmso\-|w:WordDocument)/ ).test( mswordHtml ) ) ) {
					// If filter rules aren't loaded then cancel 'paste' event,
					// load them and when they'll get loaded fire new paste event
					// for which data will be filtered in second execution of
					// this listener.
					var isLazyLoad = loadFilterRules( editor, path, function() {
						// Event continuation with the original data.
						if ( isLazyLoad )
							editor.fire( 'paste', data );
						else if ( !editor.config.pasteFromWordPromptCleanup || ( forceFromWord || confirm( editor.lang.pastefromword.confirmCleanup ) ) ) {
							data.dataValue = CKEDITOR.cleanWord( mswordHtml, editor );
						}
					});

					// The cleanup rules are to be loaded, we should just cancel
					// this event.
					isLazyLoad && evt.cancel();
				}
			}, null, null, 3 );

			function resetFromWord( evt ) {
				evt && evt.removeListener();
				editor.removeListener( 'beforePaste', forceHtmlMode );
				forceFromWord && setTimeout( function() {
					forceFromWord = 0;
				}, 0 );
			}
		}

	});

	function loadFilterRules( editor, path, callback ) {
		var isLoaded = CKEDITOR.cleanWord;

		if ( isLoaded )
			callback();
		else {
			var filterFilePath = CKEDITOR.getUrl( editor.config.pasteFromWordCleanupFile || ( path + 'filter/default.js' ) );

			// Load with busy indicator.
			CKEDITOR.scriptLoader.load( filterFilePath, callback, null, true );
		}

		return !isLoaded;
	}

	function forceHtmlMode( evt ) {
		evt.data.type = 'html';
	}
})();


/**
 * Whether to prompt the user about the clean up of content being pasted from MS Word.
 *
 *		config.pasteFromWordPromptCleanup = true;
 *
 * @since 3.1
 * @cfg {Boolean} [pasteFromWordPromptCleanup=false]
 * @member CKEDITOR.config
 */

/**
 * The file that provides the MS Word cleanup function for pasting operations.
 *
 * **Note:** This is a global configuration shared by all editor instances present
 * in the page.
 *
 *		// Load from 'pastefromword' plugin 'filter' sub folder (custom.js file) using path relative to CKEditor installation folder.
 *		CKEDITOR.config.pasteFromWordCleanupFile = 'plugins/pastefromword/filter/custom.js';
 *
 *		// Load from 'pastefromword' plugin 'filter' sub folder (custom.js file) using full path (including CKEditor installation folder).
 *		CKEDITOR.config.pasteFromWordCleanupFile = '/ckeditor/plugins/pastefromword/filter/custom.js';
 *
 *		// Load custom.js file from 'customFilerts' folder (located in server's root) using full URL.
 *		CKEDITOR.config.pasteFromWordCleanupFile = 'http://my.example.com/customFilerts/custom.js';
 *
 * @since 3.1
 * @cfg {String} [pasteFromWordCleanupFile=<plugin path> + 'filter/default.js']
 * @member CKEDITOR.config
 */
