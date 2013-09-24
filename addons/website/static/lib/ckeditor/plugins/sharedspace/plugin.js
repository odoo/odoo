/**
 * @license Copyright (c) 2003-2012, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

(function() {

	'use strict';

	var containerTpl = CKEDITOR.addTemplate( 'sharedcontainer', '<div' +
		' id="cke_{name}"' +
		' class="cke {id} cke_reset_all cke_chrome cke_editor_{name} cke_shared cke_detached cke_{langDir} ' + CKEDITOR.env.cssClass + '"' +
		' dir="{langDir}"' +
		' title="' + ( CKEDITOR.env.gecko ? ' ' : '' ) + '"' +
		' lang="{langCode}"' +
		' role="presentation"' +
		'>' +
			'<div class="cke_inner">' +
				'<div id="{spaceId}" class="cke_{space}" role="presentation">{content}</div>' +
			'</div>' +
		'</div>' );

	CKEDITOR.plugins.add( 'sharedspace', {
		init: function( editor ) {
			// Create toolbars on #loaded (like themed creator), but do that
			// with higher priority to block the default scenario.
			editor.on( 'loaded', function() {
				var spaces = editor.config.sharedSpaces;

				if ( spaces ) {
					for ( var spaceName in spaces )
						create( editor, spaceName, spaces[ spaceName ] );
				}
			}, null, null, 9 );
		}
	});

	function create( editor, spaceName, targetId ) {
		var target = CKEDITOR.document.getById( targetId ),
			innerHtml, space;

		if ( target ) {
			// Have other plugins filling the space.
			innerHtml = editor.fire( 'uiSpace', { space: spaceName, html: '' } ).html;

			if ( innerHtml ) {
				// Block the uiSpace handling by others (e.g. themed-ui).
				editor.on( 'uiSpace', function( ev ) {
					if ( ev.data.space == spaceName )
						ev.cancel();
				}, null, null, 1 );  // Hi-priority

				// Inject the space into the target.
				space = target.append( CKEDITOR.dom.element.createFromHtml( containerTpl.output({
					id: editor.id,
					name: editor.name,
					langDir: editor.lang.dir,
					langCode: editor.langCode,
					space: spaceName,
					spaceId: editor.ui.spaceId( spaceName ),
					content: innerHtml
				})));

				// Only the first container starts visible. Others get hidden.
				if ( target.getCustomData( 'cke_hasshared' ) )
					space.hide();
				else
					target.setCustomData( 'cke_hasshared', 1 );

				// There's no need for the space to be selectable.
				space.unselectable();

				// Prevent clicking on non-buttons area of the space from blurring editor.
				space.on( 'mousedown', function( evt ) {
					evt = evt.data;
					if ( !evt.getTarget().hasAscendant( 'a', 1 ) )
						evt.preventDefault();
				});

				// Register this UI space to the focus manager.
				editor.focusManager.add( space, 1 );

				// When the editor gets focus, show the space container, hiding others.
				editor.on( 'focus', function() {
					for ( var i = 0, sibling, children = target.getChildren(); ( sibling = children.getItem( i ) ); i++ ) {
						if ( sibling.type == CKEDITOR.NODE_ELEMENT &&
							!sibling.equals( space ) &&
							sibling.hasClass( 'cke_shared' ) ) {
							sibling.hide();
						}
					}

					space.show();
				});

				editor.on( 'destroy', function() {
					space.remove();
				});
			}
		}
	}
})();

/**
 * Makes it possible to place some of the editor UI blocks, like the toolbar
 * and the elements path, into any element in the page.
 *
 * The elements used to hold the UI blocks can be shared among several editor
 * instances. In that case, only the blocks of the active editor instance will
 * display.
 *
 *		// Place the toolbar inside the element with ID "someElementId" and the
 *		// elements path into the element with ID "anotherId".
 *		config.sharedSpaces = {
 *			top: 'someElementId',
 *			bottom: 'anotherId'
 *		};
 *
 *		// Place the toolbar inside the element with ID "someElementId". The
 *		// elements path will remain attached to the editor UI.
 *		config.sharedSpaces = {
 *			top: 'someElementId'
 *		};
 *
 * @cfg {Object} [sharedSpaces]
 * @member CKEDITOR.config
 */
