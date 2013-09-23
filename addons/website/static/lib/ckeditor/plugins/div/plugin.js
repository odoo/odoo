/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview The "div" plugin. It wraps the selected block level elements with a 'div' element with specified styles and attributes.
 *
 */

(function() {
	CKEDITOR.plugins.add( 'div', {
		requires: 'dialog',
		lang: 'af,ar,bg,bn,bs,ca,cs,cy,da,de,el,en,en-au,en-ca,en-gb,eo,es,et,eu,fa,fi,fo,fr,fr-ca,gl,gu,he,hi,hr,hu,id,is,it,ja,ka,km,ko,ku,lt,lv,mk,mn,ms,nb,nl,no,pl,pt,pt-br,ro,ru,si,sk,sl,sq,sr,sr-latn,sv,th,tr,ug,uk,vi,zh,zh-cn', // %REMOVE_LINE_CORE%
		icons: 'creatediv', // %REMOVE_LINE_CORE%
		hidpi: true, // %REMOVE_LINE_CORE%
		init: function( editor ) {
			if ( editor.blockless )
				return;

			var lang = editor.lang.div,
				allowed = 'div(*)';

			if ( CKEDITOR.dialog.isTabEnabled( editor, 'editdiv', 'advanced' ) )
				allowed += ';div[dir,id,lang,title]{*}';

			editor.addCommand( 'creatediv', new CKEDITOR.dialogCommand( 'creatediv', {
				allowedContent: allowed,
				requiredContent: 'div',
				contextSensitive: true,
				refresh: function( editor, path ) {
					var context = editor.config.div_wrapTable ? path.root : path.blockLimit;
					this.setState( 'div' in context.getDtd() ? CKEDITOR.TRISTATE_OFF : CKEDITOR.TRISTATE_DISABLED );
				}
			}));

			editor.addCommand( 'editdiv', new CKEDITOR.dialogCommand( 'editdiv', { requiredContent: 'div' } ) );
			editor.addCommand( 'removediv', {
				requiredContent: 'div',
				exec: function( editor ) {
					var selection = editor.getSelection(),
						ranges = selection && selection.getRanges(),
						range,
						bookmarks = selection.createBookmarks(),
						walker,
						toRemove = [];

					function findDiv( node ) {
						var div = CKEDITOR.plugins.div.getSurroundDiv( editor, node );
						if ( div && !div.data( 'cke-div-added' ) ) {
							toRemove.push( div );
							div.data( 'cke-div-added' );
						}
					}

					for ( var i = 0; i < ranges.length; i++ ) {
						range = ranges[ i ];
						if ( range.collapsed )
							findDiv( selection.getStartElement() );
						else {
							walker = new CKEDITOR.dom.walker( range );
							walker.evaluator = findDiv;
							walker.lastForward();
						}
					}

					for ( i = 0; i < toRemove.length; i++ )
						toRemove[ i ].remove( true );

					selection.selectBookmarks( bookmarks );
				}
			});

			editor.ui.addButton && editor.ui.addButton( 'CreateDiv', {
				label: lang.toolbar,
				command: 'creatediv',
				toolbar: 'blocks,50'
			});

			if ( editor.addMenuItems ) {
				editor.addMenuItems({
					editdiv: {
						label: lang.edit,
						command: 'editdiv',
						group: 'div',
						order: 1
					},

					removediv: {
						label: lang.remove,
						command: 'removediv',
						group: 'div',
						order: 5
					}
				});

				if ( editor.contextMenu ) {
					editor.contextMenu.addListener( function( element ) {
						if ( !element || element.isReadOnly() )
							return null;


						if ( CKEDITOR.plugins.div.getSurroundDiv( editor ) ) {
							return {
								editdiv: CKEDITOR.TRISTATE_OFF,
								removediv: CKEDITOR.TRISTATE_OFF
							};
						}

						return null;
					});
				}
			}

			CKEDITOR.dialog.add( 'creatediv', this.path + 'dialogs/div.js' );
			CKEDITOR.dialog.add( 'editdiv', this.path + 'dialogs/div.js' );
		}
	});

	CKEDITOR.plugins.div = {
		getSurroundDiv: function( editor, start ) {
			var path = editor.elementPath( start );
			return editor.elementPath( path.blockLimit ).contains( 'div', 1 );
		}
	};
})();
