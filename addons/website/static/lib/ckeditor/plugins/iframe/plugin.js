/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

(function() {
	CKEDITOR.plugins.add( 'iframe', {
		requires: 'dialog,fakeobjects',
		lang: 'af,ar,bg,bn,bs,ca,cs,cy,da,de,el,en,en-au,en-ca,en-gb,eo,es,et,eu,fa,fi,fo,fr,fr-ca,gl,gu,he,hi,hr,hu,id,is,it,ja,ka,km,ko,ku,lt,lv,mk,mn,ms,nb,nl,no,pl,pt,pt-br,ro,ru,si,sk,sl,sq,sr,sr-latn,sv,th,tr,ug,uk,vi,zh,zh-cn', // %REMOVE_LINE_CORE%
		icons: 'iframe', // %REMOVE_LINE_CORE%
		hidpi: true, // %REMOVE_LINE_CORE%
		onLoad: function() {
			CKEDITOR.addCss( 'img.cke_iframe' +
				'{' +
					'background-image: url(' + CKEDITOR.getUrl( this.path + 'images/placeholder.png' ) + ');' +
					'background-position: center center;' +
					'background-repeat: no-repeat;' +
					'border: 1px solid #a9a9a9;' +
					'width: 80px;' +
					'height: 80px;' +
				'}'
				);
		},
		init: function( editor ) {
			var pluginName = 'iframe',
				lang = editor.lang.iframe,
				allowed = 'iframe[align,longdesc,frameborder,height,name,scrolling,src,title,width]';

			if ( editor.plugins.dialogadvtab )
				allowed += ';iframe' + editor.plugins.dialogadvtab.allowedContent( { id:1,classes:1,styles:1 } );

			CKEDITOR.dialog.add( pluginName, this.path + 'dialogs/iframe.js' );
			editor.addCommand( pluginName, new CKEDITOR.dialogCommand( pluginName, {
				allowedContent: allowed,
				requiredContent: 'iframe'
			} ) );

			editor.ui.addButton && editor.ui.addButton( 'Iframe', {
				label: lang.toolbar,
				command: pluginName,
				toolbar: 'insert,80'
			});

			editor.on( 'doubleclick', function( evt ) {
				var element = evt.data.element;
				if ( element.is( 'img' ) && element.data( 'cke-real-element-type' ) == 'iframe' )
					evt.data.dialog = 'iframe';
			});

			if ( editor.addMenuItems ) {
				editor.addMenuItems({
					iframe: {
						label: lang.title,
						command: 'iframe',
						group: 'image'
					}
				});
			}

			// If the "contextmenu" plugin is loaded, register the listeners.
			if ( editor.contextMenu ) {
				editor.contextMenu.addListener( function( element, selection ) {
					if ( element && element.is( 'img' ) && element.data( 'cke-real-element-type' ) == 'iframe' )
						return { iframe: CKEDITOR.TRISTATE_OFF };
				});
			}
		},
		afterInit: function( editor ) {
			var dataProcessor = editor.dataProcessor,
				dataFilter = dataProcessor && dataProcessor.dataFilter;

			if ( dataFilter ) {
				dataFilter.addRules({
					elements: {
						iframe: function( element ) {
							return editor.createFakeParserElement( element, 'cke_iframe', 'iframe', true );
						}
					}
				});
			}
		}
	});
})();
