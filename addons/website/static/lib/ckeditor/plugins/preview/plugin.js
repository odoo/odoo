/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Preview plugin.
 */

(function() {
	var pluginPath;

	var previewCmd = { modes:{wysiwyg:1,source:1 },
		canUndo: false,
		readOnly: 1,
		exec: function( editor ) {
			var sHTML,
				config = editor.config,
				baseTag = config.baseHref ? '<base href="' + config.baseHref + '"/>' : '',
				eventData;

			if ( config.fullPage ) {
				sHTML = editor.getData().replace( /<head>/, '$&' + baseTag ).replace( /[^>]*(?=<\/title>)/, '$& &mdash; ' + editor.lang.preview.preview );
			} else {
				var bodyHtml = '<body ',
					body = editor.document && editor.document.getBody();

				if ( body ) {
					if ( body.getAttribute( 'id' ) )
						bodyHtml += 'id="' + body.getAttribute( 'id' ) + '" ';
					if ( body.getAttribute( 'class' ) )
						bodyHtml += 'class="' + body.getAttribute( 'class' ) + '" ';
				}

				bodyHtml += '>';

				sHTML = editor.config.docType + '<html dir="' + editor.config.contentsLangDirection + '">' +
					'<head>' +
						baseTag +
						'<title>' + editor.lang.preview.preview + '</title>' +
						CKEDITOR.tools.buildStyleHtml( editor.config.contentsCss ) +
					'</head>' + bodyHtml +
						editor.getData() +
					'</body></html>';
			}

			var iWidth = 640,
				// 800 * 0.8,
				iHeight = 420,
				// 600 * 0.7,
				iLeft = 80; // (800 - 0.8 * 800) /2 = 800 * 0.1.
			try {
				var screen = window.screen;
				iWidth = Math.round( screen.width * 0.8 );
				iHeight = Math.round( screen.height * 0.7 );
				iLeft = Math.round( screen.width * 0.1 );
			} catch ( e ) {}

			// (#9907) Allow data manipulation before preview is displayed.
			// Also don't open the preview window when event cancelled.
			if ( !editor.fire( 'contentPreview', eventData = { dataValue: sHTML } ) )
				return false;

			var sOpenUrl = '';
			if ( CKEDITOR.env.ie ) {
				window._cke_htmlToLoad = eventData.dataValue;
				sOpenUrl = 'javascript:void( (function(){' +
					'document.open();' +
					// Support for custom document.domain.
					// Strip comments and replace parent with window.opener in the function body.
					( '(' + CKEDITOR.tools.fixDomain + ')();' ).replace( /\/\/.*?\n/g, '' ).replace( /parent\./g, 'window.opener.' ) +
					'document.write( window.opener._cke_htmlToLoad );' +
					'document.close();' +
					'window.opener._cke_htmlToLoad = null;' +
				'})() )';
			}

			// With Firefox only, we need to open a special preview page, so
			// anchors will work properly on it. (#9047)
			if ( CKEDITOR.env.gecko ) {
				window._cke_htmlToLoad = eventData.dataValue;
				sOpenUrl = pluginPath + 'preview.html';
			}

			var oWindow = window.open( sOpenUrl, null, 'toolbar=yes,location=no,status=yes,menubar=yes,scrollbars=yes,resizable=yes,width=' +
				iWidth + ',height=' + iHeight + ',left=' + iLeft );

			if ( !CKEDITOR.env.ie && !CKEDITOR.env.gecko ) {
				var doc = oWindow.document;
				doc.open();
				doc.write( eventData.dataValue );
				doc.close();

				// Chrome will need this to show the embedded. (#8016)
				CKEDITOR.env.webkit && setTimeout( function() {
					doc.body.innerHTML += '';
				}, 0 );
			}

			return true;
		}
	};

	var pluginName = 'preview';

	// Register a plugin named "preview".
	CKEDITOR.plugins.add( pluginName, {
		lang: 'af,ar,bg,bn,bs,ca,cs,cy,da,de,el,en,en-au,en-ca,en-gb,eo,es,et,eu,fa,fi,fo,fr,fr-ca,gl,gu,he,hi,hr,hu,id,is,it,ja,ka,km,ko,ku,lt,lv,mk,mn,ms,nb,nl,no,pl,pt,pt-br,ro,ru,si,sk,sl,sq,sr,sr-latn,sv,th,tr,ug,uk,vi,zh,zh-cn', // %REMOVE_LINE_CORE%
		icons: 'preview,preview-rtl', // %REMOVE_LINE_CORE%
		hidpi: true, // %REMOVE_LINE_CORE%
		init: function( editor ) {

			// Preview is not used for the inline creator.
			if ( editor.elementMode == CKEDITOR.ELEMENT_MODE_INLINE )
				return;

			pluginPath = this.path;

			editor.addCommand( pluginName, previewCmd );
			editor.ui.addButton && editor.ui.addButton( 'Preview', {
				label: editor.lang.preview.preview,
				command: pluginName,
				toolbar: 'document,40'
			});
		}
	});
})();

/**
 * Event fired when executing `preview` command, which allows additional data manipulation.
 * With this event, the raw HTML content of the preview window to be displayed can be altered
 * or modified.
 *
 * @event contentPreview
 * @member CKEDITOR
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param data
 * @param {String} data.dataValue The data that will go to the preview.
 */