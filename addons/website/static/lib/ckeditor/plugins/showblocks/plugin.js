/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview The "showblocks" plugin. Enable it will make all block level
 *               elements being decorated with a border and the element name
 *               displayed on the left-right corner.
 */

(function() {
	var commandDefinition = {
		readOnly: 1,
		preserveState: true,
		editorFocus: false,

		exec: function( editor ) {
			this.toggleState();
			this.refresh( editor );
		},

		refresh: function( editor ) {
			if ( editor.document ) {
				// Show blocks turns inactive after editor loses focus when in inline.
				var showBlocks = this.state == CKEDITOR.TRISTATE_ON &&
				   ( editor.elementMode != CKEDITOR.ELEMENT_MODE_INLINE ||
					   editor.focusManager.hasFocus );

				var funcName = showBlocks ? 'attachClass' : 'removeClass';
				editor.editable()[ funcName ]( 'cke_show_blocks' );
			}
		}
	};

	CKEDITOR.plugins.add( 'showblocks', {
		lang: 'af,ar,bg,bn,bs,ca,cs,cy,da,de,el,en,en-au,en-ca,en-gb,eo,es,et,eu,fa,fi,fo,fr,fr-ca,gl,gu,he,hi,hr,hu,id,is,it,ja,ka,km,ko,ku,lt,lv,mk,mn,ms,nb,nl,no,pl,pt,pt-br,ro,ru,si,sk,sl,sq,sr,sr-latn,sv,th,tr,ug,uk,vi,zh,zh-cn', // %REMOVE_LINE_CORE%
		icons: 'showblocks,showblocks-rtl', // %REMOVE_LINE_CORE%
		hidpi: true, // %REMOVE_LINE_CORE%
		onLoad: function() {
			var cssTemplate = '.%2 p,' +
				'.%2 div,' +
				'.%2 pre,' +
				'.%2 address,' +
				'.%2 blockquote,' +
				'.%2 h1,' +
				'.%2 h2,' +
				'.%2 h3,' +
				'.%2 h4,' +
				'.%2 h5,' +
				'.%2 h6' +
				'{' +
					'background-repeat: no-repeat;' +
					'border: 1px dotted gray;' +
					'padding-top: 8px;' +
				'}' +

				'.%2 p' +
				'{' +
					'%1p.png);' +
				'}' +

				'.%2 div' +
				'{' +
					'%1div.png);' +
				'}' +

				'.%2 pre' +
				'{' +
					'%1pre.png);' +
				'}' +

				'.%2 address' +
				'{' +
					'%1address.png);' +
				'}' +

				'.%2 blockquote' +
				'{' +
					'%1blockquote.png);' +
				'}' +

				'.%2 h1' +
				'{' +
					'%1h1.png);' +
				'}' +

				'.%2 h2' +
				'{' +
					'%1h2.png);' +
				'}' +

				'.%2 h3' +
				'{' +
					'%1h3.png);' +
				'}' +

				'.%2 h4' +
				'{' +
					'%1h4.png);' +
				'}' +

				'.%2 h5' +
				'{' +
					'%1h5.png);' +
				'}' +

				'.%2 h6' +
				'{' +
					'%1h6.png);' +
				'}';

			// Styles with contents direction awareness.
			function cssWithDir( dir ) {
				var template = '.%1.%2 p,' +
					'.%1.%2 div,' +
					'.%1.%2 pre,' +
					'.%1.%2 address,' +
					'.%1.%2 blockquote,' +
					'.%1.%2 h1,' +
					'.%1.%2 h2,' +
					'.%1.%2 h3,' +
					'.%1.%2 h4,' +
					'.%1.%2 h5,' +
					'.%1.%2 h6' +
					'{' +
						'background-position: top %3;' +
						'padding-%3: 8px;' +
					'}';

				return template.replace( /%1/g, 'cke_show_blocks' ).replace( /%2/g, 'cke_contents_' + dir ).replace( /%3/g, dir == 'rtl' ? 'right' : 'left' );
			}

			CKEDITOR.addCss( cssTemplate.replace( /%1/g, 'background-image: url(' + CKEDITOR.getUrl( this.path ) + 'images/block_' ).replace( /%2/g, 'cke_show_blocks ' ) + cssWithDir( 'ltr' ) + cssWithDir( 'rtl' ) );
		},
		init: function( editor ) {
			if ( editor.blockless )
				return;

			var command = editor.addCommand( 'showblocks', commandDefinition );
			command.canUndo = false;

			if ( editor.config.startupOutlineBlocks )
				command.setState( CKEDITOR.TRISTATE_ON );

			editor.ui.addButton && editor.ui.addButton( 'ShowBlocks', {
				label: editor.lang.showblocks.toolbar,
				command: 'showblocks',
				toolbar: 'tools,20'
			});

			// Refresh the command on setData.
			editor.on( 'mode', function() {
				if ( command.state != CKEDITOR.TRISTATE_DISABLED )
					command.refresh( editor );
			});

			// Refresh the command on focus/blur in inline.
			if ( editor.elementMode == CKEDITOR.ELEMENT_MODE_INLINE ) {
				function onFocusBlur() {
					command.refresh( editor );
				}
				editor.on( 'focus', onFocusBlur );
				editor.on( 'blur', onFocusBlur );
			}

			// Refresh the command on setData.
			editor.on( 'contentDom', function() {
				if ( command.state != CKEDITOR.TRISTATE_DISABLED )
					command.refresh( editor );
			});
		}
	});
})();

/**
 * Whether to automaticaly enable the show block" command when the editor loads.
 *
 *		config.startupOutlineBlocks = true;
 *
 * @cfg {Boolean} [startupOutlineBlocks=false]
 * @member CKEDITOR.config
 */
