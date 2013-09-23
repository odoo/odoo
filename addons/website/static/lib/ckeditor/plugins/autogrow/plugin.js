/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview AutoGrow plugin.
 */

(function() {

	// Actual content height, figured out by appending check the last element's document position.
	function contentHeight( scrollable ) {
		var overflowY = scrollable.getStyle( 'overflow-y' );

		var doc = scrollable.getDocument();
		// Create a temporary marker element.
		var marker = CKEDITOR.dom.element.createFromHtml( '<span style="margin:0;padding:0;border:0;clear:both;width:1px;height:1px;display:block;">' + ( CKEDITOR.env.webkit ? '&nbsp;' : '' ) + '</span>', doc );
		doc[ CKEDITOR.env.ie ? 'getBody' : 'getDocumentElement' ]().append( marker );

		var height = marker.getDocumentPosition( doc ).y + marker.$.offsetHeight;
		marker.remove();
		scrollable.setStyle( 'overflow-y', overflowY );
		return height;
	}

	function getScrollable( editor ) {
		var doc = editor.document,
			body = doc.getBody(),
			htmlElement = doc.getDocumentElement();

		// Quirks mode overflows body, standards overflows document element
		return doc.$.compatMode == 'BackCompat' ? body : htmlElement;
	}

	// @param editor
	// @param {Number} lastHeight The last height set by autogrow.
	// @returns {Number} New height if has been changed, or the passed `lastHeight`.
	var resizeEditor = function( editor, lastHeight ) {
		if ( !editor.window )
			return null;

		var maximize = editor.getCommand( 'maximize' );
			// Disable autogrow when the editor is maximized .(#6339)
		if( maximize && maximize.state == CKEDITOR.TRISTATE_ON )
			return null;

		var scrollable = getScrollable( editor ),
			currentHeight = editor.window.getViewPaneSize().height,
			newHeight = contentHeight( scrollable );

		// Additional space specified by user.
		newHeight += ( editor.config.autoGrow_bottomSpace || 0 );

		var min = editor.config.autoGrow_minHeight != undefined ? editor.config.autoGrow_minHeight : 200,
			max = editor.config.autoGrow_maxHeight || Infinity;

		newHeight = Math.max( newHeight, min );
		newHeight = Math.min( newHeight, max );

		// #10196 Do not resize editor if new height is equal
		// to the one set by previous resizeEditor() call.
		if ( newHeight != currentHeight && lastHeight != newHeight ) {
			newHeight = editor.fire( 'autoGrow', { currentHeight: currentHeight, newHeight: newHeight } ).newHeight;
			editor.resize( editor.container.getStyle( 'width' ), newHeight, true );
			lastHeight = newHeight;
		}

		if ( scrollable.$.scrollHeight > scrollable.$.clientHeight && newHeight < max )
			scrollable.setStyle( 'overflow-y', 'hidden' );
		else
			scrollable.removeStyle( 'overflow-y' );

		return lastHeight;
	};

	CKEDITOR.plugins.add( 'autogrow', {
		init: function( editor ) {

			// This feature is available only for themed ui instance.
			if ( editor.elementMode == CKEDITOR.ELEMENT_MODE_INLINE )
				return;

			editor.on( 'instanceReady', function() {

				var editable = editor.editable(),
					lastHeight;

				// Simply set auto height with div wysiwyg.
				if ( editable.isInline() )
					editor.ui.space( 'contents' ).setStyle( 'height', 'auto' );
				// For framed wysiwyg we need to resize the editor.
				else
				{
					editor.addCommand( 'autogrow', {
						exec: function( editor ) {
							lastHeight = resizeEditor( editor, lastHeight );
						},
						modes:{ wysiwyg:1 },
						readOnly: 1,
						canUndo: false,
						editorFocus: false
					} );

					var eventsList = { contentDom:1,key:1,selectionChange:1,insertElement:1,mode:1 };
					for ( var eventName in eventsList ) {
						editor.on( eventName, function( evt ) {
							// Some time is required for insertHtml, and it gives other events better performance as well.
							if ( evt.editor.mode == 'wysiwyg'  ) {
								setTimeout( function() {
									lastHeight = resizeEditor( evt.editor, lastHeight );
									// Second pass to make correction upon
									// the first resize, e.g. scrollbar.
									lastHeight = resizeEditor( evt.editor, lastHeight );
								}, 100 );
							}
						});
					}

					// Coordinate with the "maximize" plugin. (#9311)
					editor.on( 'afterCommandExec', function( evt ) {
						if ( evt.data.name == 'maximize' && evt.editor.mode == 'wysiwyg' ) {
							if ( evt.data.command.state == CKEDITOR.TRISTATE_ON ) {
								var scrollable = getScrollable( editor );
								scrollable.removeStyle( 'overflow' );
							}
 							else
								lastHeight = resizeEditor( editor, lastHeight );
						}
					});

					editor.config.autoGrow_onStartup && editor.execCommand( 'autogrow' );
				}
			});
		}
	});
})();

/**
 * The minimum height that the editor can reach using the AutoGrow feature.
 *
 *		config.autoGrow_minHeight = 300;
 *
 * @since 3.4
 * @cfg {Number} [autoGrow_minHeight=200]
 * @member CKEDITOR.config
 */

/**
 * The maximum height that the editor can reach using the AutoGrow feature. Zero means unlimited.
 *
 *		config.autoGrow_maxHeight = 400;
 *
 * @since 3.4
 * @cfg {Number} [autoGrow_maxHeight=0]
 * @member CKEDITOR.config
 */

/**
 * Whether to have the auto grow happen on editor creation.
 *
 *		config.autoGrow_onStartup = true;
 *
 * @since 3.6.2
 * @cfg {Boolean} [autoGrow_onStartup=false]
 * @member CKEDITOR.config
 */

/**
 * Extra height in pixel to leave between the bottom boundary of content with document size when auto resizing.
 *
 * @since 3.6.2
 * @cfg {Number} [autoGrow_bottomSpace=0]
 * @member CKEDITOR.config
 */

/**
 * Fired when the AutoGrow plugin is about to change the size of the editor.
 *
 * @event autogrow
 * @member CKEDITOR.editor
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param data
 * @param {Number} data.currentHeight The current height of the editor (before resizing).
 * @param {Number} data.newHeight The new height of the editor (after resizing). It can be changed
 * to determine a different height value to be used instead.
 */
