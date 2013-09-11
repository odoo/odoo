/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

CKEDITOR.plugins.add( 'removeformat', {
	lang: 'af,ar,bg,bn,bs,ca,cs,cy,da,de,el,en,en-au,en-ca,en-gb,eo,es,et,eu,fa,fi,fo,fr,fr-ca,gl,gu,he,hi,hr,hu,id,is,it,ja,ka,km,ko,ku,lt,lv,mk,mn,ms,nb,nl,no,pl,pt,pt-br,ro,ru,si,sk,sl,sq,sr,sr-latn,sv,th,tr,ug,uk,vi,zh,zh-cn', // %REMOVE_LINE_CORE%
	icons: 'removeformat', // %REMOVE_LINE_CORE%
	hidpi: true, // %REMOVE_LINE_CORE%
	init: function( editor ) {
		editor.addCommand( 'removeFormat', CKEDITOR.plugins.removeformat.commands.removeformat );
		editor.ui.addButton && editor.ui.addButton( 'RemoveFormat', {
			label: editor.lang.removeformat.toolbar,
			command: 'removeFormat',
			toolbar: 'cleanup,10'
		});
	}
});

CKEDITOR.plugins.removeformat = {
	commands: {
		removeformat: {
			exec: function( editor ) {
				var tagsRegex = editor._.removeFormatRegex || ( editor._.removeFormatRegex = new RegExp( '^(?:' + editor.config.removeFormatTags.replace( /,/g, '|' ) + ')$', 'i' ) );

				var removeAttributes = editor._.removeAttributes || ( editor._.removeAttributes = editor.config.removeFormatAttributes.split( ',' ) );

				var filter = CKEDITOR.plugins.removeformat.filter;
				var ranges = editor.getSelection().getRanges( 1 ),
					iterator = ranges.createIterator(),
					range;

				while ( ( range = iterator.getNextRange() ) ) {
					if ( !range.collapsed )
						range.enlarge( CKEDITOR.ENLARGE_ELEMENT );

					// Bookmark the range so we can re-select it after processing.
					var bookmark = range.createBookmark(),
						// The style will be applied within the bookmark boundaries.
						startNode = bookmark.startNode,
						endNode = bookmark.endNode,
						currentNode;

					// We need to check the selection boundaries (bookmark spans) to break
					// the code in a way that we can properly remove partially selected nodes.
					// For example, removing a <b> style from
					//		<b>This is [some text</b> to show <b>the] problem</b>
					// ... where [ and ] represent the selection, must result:
					//		<b>This is </b>[some text to show the]<b> problem</b>
					// The strategy is simple, we just break the partial nodes before the
					// removal logic, having something that could be represented this way:
					//		<b>This is </b>[<b>some text</b> to show <b>the</b>]<b> problem</b>

					var breakParent = function( node ) {
							// Let's start checking the start boundary.
							var path = editor.elementPath( node ),
								pathElements = path.elements;

							for ( var i = 1, pathElement; pathElement = pathElements[ i ]; i++ ) {
								if ( pathElement.equals( path.block ) || pathElement.equals( path.blockLimit ) )
									break;

								// If this element can be removed (even partially).
								if ( tagsRegex.test( pathElement.getName() ) && filter( editor, pathElement ) )
									node.breakParent( pathElement );
							}
						};

					breakParent( startNode );
					if ( endNode ) {
						breakParent( endNode );

						// Navigate through all nodes between the bookmarks.
						currentNode = startNode.getNextSourceNode( true, CKEDITOR.NODE_ELEMENT );

						while ( currentNode ) {
							// If we have reached the end of the selection, stop looping.
							if ( currentNode.equals( endNode ) )
								break;

							// Cache the next node to be processed. Do it now, because
							// currentNode may be removed.
							var nextNode = currentNode.getNextSourceNode( false, CKEDITOR.NODE_ELEMENT );

							// This node must not be a fake element.
							if ( !( currentNode.getName() == 'img' && currentNode.data( 'cke-realelement' ) ) && filter( editor, currentNode ) ) {
								// Remove elements nodes that match with this style rules.
								if ( tagsRegex.test( currentNode.getName() ) )
									currentNode.remove( 1 );
								else {
									currentNode.removeAttributes( removeAttributes );
									editor.fire( 'removeFormatCleanup', currentNode );
								}
							}

							currentNode = nextNode;
						}
					}

					range.moveToBookmark( bookmark );
				}

				// The selection path may not changed, but we should force a selection
				// change event to refresh command states, due to the above attribution change. (#9238)
				editor.forceNextSelectionCheck();
				editor.getSelection().selectRanges( ranges );
			}
		}
	},

	// Perform the remove format filters on the passed element.
	// @param {CKEDITOR.editor} editor
	// @param {CKEDITOR.dom.element} element
	filter: function( editor, element ) {
		// If editor#addRemoveFotmatFilter hasn't been executed yet value is not initialized.
		var filters = editor._.removeFormatFilters || [];
		for ( var i = 0; i < filters.length; i++ ) {
			if ( filters[ i ]( element ) === false )
				return false;
		}
		return true;
	}
};

/**
 * Add to a collection of functions to decide whether a specific
 * element should be considered as formatting element and thus
 * could be removed during `removeFormat` command.
 *
 * **Note:** Only available with the existence of `removeformat` plugin.
 *
 *		// Don't remove empty span.
 *		editor.addRemoveFormatFilter( function( element ) {
 *			return !( element.is( 'span' ) && CKEDITOR.tools.isEmpty( element.getAttributes() ) );
 *		} );
 *
 * @since 3.3
 * @member CKEDITOR.editor
 * @param {Function} func The function to be called, which will be passed a {CKEDITOR.dom.element} element to test.
 */
CKEDITOR.editor.prototype.addRemoveFormatFilter = function( func ) {
	if ( !this._.removeFormatFilters )
		this._.removeFormatFilters = [];

	this._.removeFormatFilters.push( func );
};

/**
 * A comma separated list of elements to be removed when executing the `remove
 * format` command. Note that only inline elements are allowed.
 *
 * @cfg
 * @member CKEDITOR.config
 */
CKEDITOR.config.removeFormatTags = 'b,big,code,del,dfn,em,font,i,ins,kbd,q,s,samp,small,span,strike,strong,sub,sup,tt,u,var';

/**
 * A comma separated list of elements attributes to be removed when executing
 * the `remove format` command.
 *
 * @cfg
 * @member CKEDITOR.config
 */
CKEDITOR.config.removeFormatAttributes = 'class,style,lang,width,height,align,hspace,valign';

/**
 * Fired after an element was cleaned by the removeFormat plugin.
 *
 * @event removeFormatCleanup
 * @member CKEDITOR.editor
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param data
 * @param {CKEDITOR.dom.element} data.element The element that was cleaned up.
 */
