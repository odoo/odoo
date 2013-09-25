/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview The "divarea" plugin. It registers the "wysiwyg" editing
 *		mode using a DIV element.
 */

CKEDITOR.plugins.add( 'divarea', {
	afterInit: function( editor ) {
		// Add the "wysiwyg" mode.
		// Do that in the afterInit function, so it'll eventually overwrite
		// the mode defined by the wysiwygarea plugin.
		editor.addMode( 'wysiwyg', function( callback ) {
			var editingBlock = CKEDITOR.dom.element.createFromHtml( '<div class="cke_wysiwyg_div cke_reset" hidefocus="true"></div>' );

			var contentSpace = editor.ui.space( 'contents' );
			contentSpace.append( editingBlock );

			editingBlock = editor.editable( editingBlock );

			editingBlock.detach = CKEDITOR.tools.override( editingBlock.detach,
				function( org ) {
					return function() {
						org.apply( this, arguments );
						this.remove();
					};
				});

			editor.setData( editor.getData( 1 ), callback );
			editor.fire( 'contentDom' );
		});
	}
});
