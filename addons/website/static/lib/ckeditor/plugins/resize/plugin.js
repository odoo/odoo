/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

CKEDITOR.plugins.add( 'resize', {
	init: function( editor ) {
		var config = editor.config;
		var spaceId = editor.ui.spaceId( 'resizer' );

		// Resize in the same direction of chrome,
		// which is identical to dir of editor element. (#6614)
		var resizeDir = editor.element ? editor.element.getDirection( 1 ) : 'ltr';

		!config.resize_dir && ( config.resize_dir = 'vertical' );
		( config.resize_maxWidth == undefined ) && ( config.resize_maxWidth = 3000 );
		( config.resize_maxHeight == undefined ) && ( config.resize_maxHeight = 3000 );
		( config.resize_minWidth == undefined ) && ( config.resize_minWidth = 750 );
		( config.resize_minHeight == undefined ) && ( config.resize_minHeight = 250 );

		if ( config.resize_enabled !== false ) {
			var container = null,
				origin, startSize,
				resizeHorizontal = ( config.resize_dir == 'both' || config.resize_dir == 'horizontal' ) && ( config.resize_minWidth != config.resize_maxWidth ),
				resizeVertical = ( config.resize_dir == 'both' || config.resize_dir == 'vertical' ) && ( config.resize_minHeight != config.resize_maxHeight );

			function dragHandler( evt ) {
				var dx = evt.data.$.screenX - origin.x,
					dy = evt.data.$.screenY - origin.y,
					width = startSize.width,
					height = startSize.height,
					internalWidth = width + dx * ( resizeDir == 'rtl' ? -1 : 1 ),
					internalHeight = height + dy;

				if ( resizeHorizontal )
					width = Math.max( config.resize_minWidth, Math.min( internalWidth, config.resize_maxWidth ) );

				if ( resizeVertical )
					height = Math.max( config.resize_minHeight, Math.min( internalHeight, config.resize_maxHeight ) );

				// DO NOT impose fixed size with single direction resize. (#6308)
				editor.resize( resizeHorizontal ? width : null, height );
			}

			function dragEndHandler( evt ) {
				CKEDITOR.document.removeListener( 'mousemove', dragHandler );
				CKEDITOR.document.removeListener( 'mouseup', dragEndHandler );

				if ( editor.document ) {
					editor.document.removeListener( 'mousemove', dragHandler );
					editor.document.removeListener( 'mouseup', dragEndHandler );
				}
			}

			var mouseDownFn = CKEDITOR.tools.addFunction( function( $event ) {
				if ( !container )
					container = editor.getResizable();

				startSize = { width: container.$.offsetWidth || 0, height: container.$.offsetHeight || 0 };
				origin = { x: $event.screenX, y: $event.screenY };

				config.resize_minWidth > startSize.width && ( config.resize_minWidth = startSize.width );
				config.resize_minHeight > startSize.height && ( config.resize_minHeight = startSize.height );

				CKEDITOR.document.on( 'mousemove', dragHandler );
				CKEDITOR.document.on( 'mouseup', dragEndHandler );

				if ( editor.document ) {
					editor.document.on( 'mousemove', dragHandler );
					editor.document.on( 'mouseup', dragEndHandler );
				}

				$event.preventDefault && $event.preventDefault();
			});

			editor.on( 'destroy', function() {
				CKEDITOR.tools.removeFunction( mouseDownFn );
			});

			editor.on( 'uiSpace', function( event ) {
				if ( event.data.space == 'bottom' ) {
					var direction = '';
					if ( resizeHorizontal && !resizeVertical )
						direction = ' cke_resizer_horizontal';
					if ( !resizeHorizontal && resizeVertical )
						direction = ' cke_resizer_vertical';

					var resizerHtml =
						'<span' +
						' id="' + spaceId + '"' +
						' class="cke_resizer' + direction + ' cke_resizer_' + resizeDir + '"' +
						' title="' + CKEDITOR.tools.htmlEncode( editor.lang.common.resize ) + '"' +
						' onmousedown="CKEDITOR.tools.callFunction(' + mouseDownFn + ', event)"' +
						'>' +
						// BLACK LOWER RIGHT TRIANGLE (ltr)
						// BLACK LOWER LEFT TRIANGLE (rtl)
						( resizeDir == 'ltr' ? '\u25E2' : '\u25E3' ) +
						'</span>';

					// Always sticks the corner of botttom space.
					resizeDir == 'ltr' && direction == 'ltr' ? event.data.html += resizerHtml : event.data.html = resizerHtml + event.data.html;
				}
			}, editor, null, 100 );

			// Toggle the visibility of the resizer when an editor is being maximized or minimized.
			editor.on( 'maximize', function( event ) {
				editor.ui.space( 'resizer' )[ event.data == CKEDITOR.TRISTATE_ON ? 'hide' : 'show' ]();
			});
		}
	}
});

/**
 * The minimum editor width, in pixels, when resizing the editor interface by using the resize handle.
 * Note: It falls back to editor's actual width if it is smaller than the default value.
 *
 *		config.resize_minWidth = 500;
 *
 * @cfg {Number} [resize_minWidth=750]
 * @member CKEDITOR.config
 */

/**
 * The minimum editor height, in pixels, when resizing the editor interface by using the resize handle.
 * Note: It falls back to editor's actual height if it is smaller than the default value.
 *
 *		config.resize_minHeight = 600;
 *
 * @cfg {Number} [resize_minHeight=250]
 * @member CKEDITOR.config
 */

/**
 * The maximum editor width, in pixels, when resizing the editor interface by using the resize handle.
 *
 *		config.resize_maxWidth = 750;
 *
 * @cfg {Number} [resize_maxWidth=3000]
 * @member CKEDITOR.config
 */

/**
 * The maximum editor height, in pixels, when resizing the editor interface by using the resize handle.
 *
 *		config.resize_maxHeight = 600;
 *
 * @cfg {Number} [resize_maxHeight=3000]
 * @member CKEDITOR.config
 */

/**
 * Whether to enable the resizing feature. If this feature is disabled, the resize handle will not be visible.
 *
 *		config.resize_enabled = false;
 *
 * @cfg {Boolean} [resize_enabled=true]
 * @member CKEDITOR.config
 */

/**
 * The dimensions for which the editor resizing is enabled. Possible values
 * are `both`, `vertical`, and `horizontal`.
 *
 *		config.resize_dir = 'both';
 *
 * @since 3.3
 * @cfg {String} [resize_dir='vertical']
 * @member CKEDITOR.config
 */
