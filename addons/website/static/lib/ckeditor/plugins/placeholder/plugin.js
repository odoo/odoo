/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview The "placeholder" plugin.
 *
 */

(function() {
	var placeholderReplaceRegex = /\[\[[^\]]+\]\]/g;
	CKEDITOR.plugins.add( 'placeholder', {
		requires: 'dialog',
		lang: 'en,bg,cs,cy,da,de,el,eo,et,fa,fi,fr,he,hr,it,ku,nb,nl,no,pl,tr,ug,uk,vi,zh-cn', // %REMOVE_LINE_CORE%
		icons: 'placeholder', // %REMOVE_LINE_CORE%
		hidpi: true, // %REMOVE_LINE_CORE%
		onLoad: function() {
			CKEDITOR.addCss( '.cke_placeholder' +
				'{' +
					'background-color: #ffff00;' +
					( CKEDITOR.env.gecko ? 'cursor: default;' : '' ) +
				'}'
				);
		},
		init: function( editor ) {
			var lang = editor.lang.placeholder;

			editor.addCommand( 'createplaceholder', new CKEDITOR.dialogCommand( 'createplaceholder' ) );
			editor.addCommand( 'editplaceholder', new CKEDITOR.dialogCommand( 'editplaceholder' ) );

			editor.ui.addButton && editor.ui.addButton( 'CreatePlaceholder', {
				label: lang.toolbar,
				command: 'createplaceholder',
				toolbar: 'insert,5',
				icon: 'placeholder'
			});

			if ( editor.addMenuItems ) {
				editor.addMenuGroup( 'placeholder', 20 );
				editor.addMenuItems({
					editplaceholder: {
						label: lang.edit,
						command: 'editplaceholder',
						group: 'placeholder',
						order: 1,
						icon: 'placeholder'
					}
				});

				if ( editor.contextMenu ) {
					editor.contextMenu.addListener( function( element, selection ) {
						if ( !element || !element.data( 'cke-placeholder' ) )
							return null;

						return { editplaceholder: CKEDITOR.TRISTATE_OFF };
					});
				}
			}

			editor.on( 'doubleclick', function( evt ) {
				if ( CKEDITOR.plugins.placeholder.getSelectedPlaceHolder( editor ) )
					evt.data.dialog = 'editplaceholder';
			});

			editor.on( 'contentDom', function() {
				editor.editable().on( 'resizestart', function( evt ) {
					if ( editor.getSelection().getSelectedElement().data( 'cke-placeholder' ) )
						evt.data.preventDefault();
				});
			});

			CKEDITOR.dialog.add( 'createplaceholder', this.path + 'dialogs/placeholder.js' );
			CKEDITOR.dialog.add( 'editplaceholder', this.path + 'dialogs/placeholder.js' );
		},
		afterInit: function( editor ) {
			var dataProcessor = editor.dataProcessor,
				dataFilter = dataProcessor && dataProcessor.dataFilter,
				htmlFilter = dataProcessor && dataProcessor.htmlFilter;

			if ( dataFilter ) {
				dataFilter.addRules({
					text: function( text ) {
						return text.replace( placeholderReplaceRegex, function( match ) {
							return CKEDITOR.plugins.placeholder.createPlaceholder( editor, null, match, 1 );
						});
					}
				});
			}

			if ( htmlFilter ) {
				htmlFilter.addRules({
					elements: {
						'span': function( element ) {
							if ( element.attributes && element.attributes[ 'data-cke-placeholder' ] )
								delete element.name;
						}
					}
				});
			}
		}
	});
})();

CKEDITOR.plugins.placeholder = {
	createPlaceholder: function( editor, oldElement, text, isGet ) {
		var element = new CKEDITOR.dom.element( 'span', editor.document );
		element.setAttributes({
			contentEditable: 'false',
			'data-cke-placeholder': 1,
			'class': 'cke_placeholder'
		});

		text && element.setText( text );

		if ( isGet )
			return element.getOuterHtml();

		if ( oldElement ) {
			if ( CKEDITOR.env.ie ) {
				element.insertAfter( oldElement );
				// Some time is required for IE before the element is removed.
				setTimeout( function() {
					oldElement.remove();
					element.focus();
				}, 10 );
			} else
				element.replace( oldElement );
		} else
			editor.insertElement( element );

		return null;
	},

	getSelectedPlaceHolder: function( editor ) {
		var range = editor.getSelection().getRanges()[ 0 ];
		range.shrink( CKEDITOR.SHRINK_TEXT );
		var node = range.startContainer;
		while ( node && !( node.type == CKEDITOR.NODE_ELEMENT && node.data( 'cke-placeholder' ) ) )
			node = node.getParent();
		return node;
	}
};
