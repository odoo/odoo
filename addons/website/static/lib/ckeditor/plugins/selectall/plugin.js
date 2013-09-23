/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview The "selectall" plugin provides an editor command that
 *               allows selecting the entire content of editable area.
 *               This plugin also enables a toolbar button for the feature.
 */

(function() {
	CKEDITOR.plugins.add( 'selectall', {
		lang: 'af,ar,bg,bn,bs,ca,cs,cy,da,de,el,en,en-au,en-ca,en-gb,eo,es,et,eu,fa,fi,fo,fr,fr-ca,gl,gu,he,hi,hr,hu,id,is,it,ja,ka,km,ko,ku,lt,lv,mk,mn,ms,nb,nl,no,pl,pt,pt-br,ro,ru,si,sk,sl,sq,sr,sr-latn,sv,th,tr,ug,uk,vi,zh,zh-cn', // %REMOVE_LINE_CORE%
		icons: 'selectall', // %REMOVE_LINE_CORE%
		hidpi: true, // %REMOVE_LINE_CORE%
		init: function( editor ) {
			editor.addCommand( 'selectAll', { modes:{wysiwyg:1,source:1 },
				exec: function( editor ) {
					var editable = editor.editable();

					if ( editable.is( 'textarea' ) ) {
						var textarea = editable.$;

						if ( CKEDITOR.env.ie )
							textarea.createTextRange().execCommand( 'SelectAll' );
						else {
							textarea.selectionStart = 0;
							textarea.selectionEnd = textarea.value.length;
						}

						textarea.focus();
					} else {
						if ( editable.is( 'body' ) )
							editor.document.$.execCommand( 'SelectAll', false, null );
						else {
							var range = editor.createRange();
							range.selectNodeContents( editable );
							range.select();
						}

						// Force triggering selectionChange (#7008)
						editor.forceNextSelectionCheck();
						editor.selectionChange();
					}

				},
				canUndo: false
			});

			editor.ui.addButton && editor.ui.addButton( 'SelectAll', {
				label: editor.lang.selectall.toolbar,
				command: 'selectAll',
				toolbar: 'selection,10'
			});
		}
	});
})();
