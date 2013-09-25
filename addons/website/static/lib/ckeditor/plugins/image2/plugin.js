/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.html or http://ckeditor.com/license
 */

'use strict';

(function() {

	var template =
			'<figure class="caption">' +
				'<img alt="" src="" />' +
				'<figcaption>Caption</figcaption>' +
			'</figure>',
		templateInline = '<img alt="" src="" />';

	CKEDITOR.plugins.add( 'image2', {
		lang: 'en', // %REMOVE_LINE_CORE%
		requires: 'widget,dialog',
		icons: 'image2',
		hidpi: true,

		onLoad: function( editor ) {
			CKEDITOR.addCss( '.cke_image2_resizer{' +
				'display:none;' +
				'position:absolute;' +
				'bottom:2px;' +
				'width: 0px;' +
				'height: 0px;' +
				'border-style:solid;' +
				// Bottom-right corner style of the resizer.
				'right:2px;' +
				'border-width:0 0 10px 10px;' +
				'border-color:transparent transparent #ccc transparent;' +
				CKEDITOR.tools.cssVendorPrefix( 'box-shadow', '1px 1px 0px #777', true ) + ';' +
				'cursor:se-resize;' +
			'}' +
			'.cke_image2_resizer_wrapper{' +
				'position:relative;' +
				'display:inline-block;' +
				'line-height:0;' +
			'}' +
			// Bottom-left corner style of the resizer.
			'.cke_image2_resizer.cke_image2_resizer_left{' +
				'right:auto;' +
				'left:2px;' +
				'border-width:10px 0 0 10px;' +
				'border-color:transparent transparent transparent #ccc;' +
				CKEDITOR.tools.cssVendorPrefix( 'box-shadow', '-1px 1px 0px #777', true ) + ';' +
				'cursor:sw-resize;' +
			'}' +
			'.cke_widget_wrapper:hover .cke_image2_resizer{display:block;}' );
		},

		init: function( editor ) {
			// Register the inline widget.
			editor.widgets.add( 'image2inline', image2inline );

			// Register the block widget.
			editor.widgets.add( 'image2block', image2block );

			// Add the command for this plugin.
			editor.addCommand( 'image2', {
				exec: function() {
					var focused = getFocusedWidget( editor );

					if ( focused )
						focused.edit();
					else
						editor.execCommand( 'image2inline' );
				}
			} );

			// Add toolbar button for this plugin.
			editor.ui.addButton && editor.ui.addButton( 'image2', {
				label: editor.lang.common.image,
				command: 'image2',
				toolbar: 'insert,10'
			} );

			// Integrate the plugin with context menus.
			if ( editor.contextMenu ) {
				editor.addMenuGroup( 'image2', 10 );

				// Define a menu item for the plguin.
				editor.addMenuItem( 'image2', {
					label: editor.lang.image2.menu,
					command: 'image2',
					group: 'image2'
				} );

				// Show the menu item in the context menu when a widget
				// is focused.
				editor.contextMenu.addListener( function() {
					var focused = getFocusedWidget( editor );

					if ( focused )
						return { image2: CKEDITOR.TRISTATE_OFF };

					return null;
				} );
			}

			// Add the dialog associated with both widgets.
			CKEDITOR.dialog.add( 'image2', this.path + 'dialogs/image2.js' );
		},

		afterInit: function( editor ) {
			var align = { left:1,right:1,center:1,block:1 },
				integrate = alignCommandIntegrator( editor );

			for ( var value in align )
				integrate( value );
		}
	} );

	// Default definition shared across widgets.
	var image2 = {
			// This widget converts style-driven dimensions to attributes.
			contentTransformations: [
				[ 'img[width]: sizeToAttribute' ]
			],

			data: function() {
				var widget = this,
					editor = widget.editor,
					oldState = widget.oldData,
					newState = widget.data;

				// Convert the internal form of the widget
				// from the old state to the new one.
				widget.shiftState( {
					element: widget.element,
					oldState: oldState,
					newState: newState,

					// Destroy the widget.
					destroy: function() {
						if ( this.destroyed )
							return;

						editor.widgets.destroy( widget );

						// Mark widget was destroyed.
						this.destroyed = true;
					},

					init: function( element ) {
						// Create a new widget. This widget will be either captioned
						// non-captioned, block or inline according to what is the
						// new state of the widget.
						if ( this.destroyed ) {
							var name = 'image2' + ( newState.hasCaption || newState.align == 'center' ? 'block' : 'inline' );
							widget = editor.widgets.initOn( element, name, widget.data );
						}

						// If now widget was destroyed just update wrapper's alignment.
						// According to the new state.
						else
							setWrapperAlign( widget );
					}
				} );

				// Get the <img> from the widget. As widget may have been
				// re-initialized, this may be a totally different <img>.
				var image = widget.parts.image;

				image.setAttributes( {
					src: widget.data.src,

					// This internal is required by the editor.
					'data-cke-saved-src': widget.data.src,

					alt: widget.data.alt
				} );

				// Set dimensions of the image according to gathered data.
				setDimensions( widget );

				// Cache current data.
				widget.oldData = CKEDITOR.tools.extend( {}, widget.data );
			},

			// The name of this widget's dialog.
			dialog: 'image2',

			// Initialization of this widget.
			init: function() {
				var image = this.parts.image,
					data = {
						// Check whether widget has caption.
						hasCaption: !!this.parts.caption,

						// Read initial image SRC attribute.
						src: image.getAttribute( 'src' ),

						// Read initial image ALT attribute.
						alt: image.getAttribute( 'alt' ) || '',

						// Read initial width from either attribute or style.
						width: image.getAttribute( 'width' ) || '',

						// Read initial height from either attribute or style.
						height: image.getAttribute( 'height' ) || ''
					};

				// If element was marked as centered when upcasting, update
				// the alignment both visually and in widget data.
				if ( this.element.data( 'cke-centered' ) ) {
					this.element.data( 'cke-centered', false );
					data.align = 'center';
				}

				// Otherwise, read initial float style from figure/image and
				// then remove it. This style will be set on wrapper in #data listener.
				else {
					data.align = this.element.getStyle( 'float' ) || image.getStyle( 'float' ) || 'none';
					this.element.removeStyle( 'float' );
					image.removeStyle( 'float' );
				}

				// Get rid of extra vertical space when there's no caption.
				// It will improve the look of the resizer.
				if ( !data.hasCaption )
					this.wrapper.setStyle( 'line-height', '0' );

				// Set collected data.
				this.setData( data );

				// Setup dynamic image resizing with mouse.
				setupResizer( this );

				// Create shift stater for this widget.
				this.shiftState = CKEDITOR.plugins.image2.stateShifter( this.editor );
			},

			// Widget downcasting.
			downcast: downcastWidgetElement
		},

		image2inline = CKEDITOR.tools.extend( {
			// Widget-specific rules for Allowed Content Filter.
			allowedContent: {
				// This widget needs <img>.
				img: {
					attributes: '!src,alt,width,height',
					styles: 'float'
				}
			},

			// This widget is inline.
			inline: true,

			// Parts of this widget.
			parts: { image: 'img' },

			// Template of the widget: plain image.
			template: templateInline,

			// Widget upcasting.
			upcast: createUpcastFunction()
		}, image2 ),

		image2block = CKEDITOR.tools.extend( {
			// Widget-specific rules for Allowed Content Filter.
			allowedContent: {
				// This widget needs <figcaption>.
				figcaption: true,

				// This widget needs <figure>.
				figure: {
					classes: '!caption',
					styles: 'float,display'
				},

				// This widget needs <img>.
				img: {
					attributes: '!src,alt,width,height'
				},

				// This widget may need <div> centering wrapper.
				div: {
					match: isCenterWrapper,
					styles: 'text-align'
				},

				// This widget may need <p> centering wrapper.
				p: {
					match: isCenterWrapper,
					styles: 'text-align'
				}
			},

			// This widget has an editable caption.
			editables: {
				caption: {
					selector: 'figcaption',
					allowedContent: 'br em strong sub sup u; a[!href]'
				}
			},

			// Parts of this widget: image and caption.
			parts: {
				image: 'img',
				caption: 'figcaption'
			},

			// Template of the widget: figure with image and caption.
			template: template,

			// Widget upcasting.
			upcast: createUpcastFunction( true )
		}, image2 );

	CKEDITOR.plugins.image2 = {
		stateShifter: function( editor ) {
			// Tag name used for centering non-captioned widgets.
			var centerElement = editor.config.enterMode == CKEDITOR.ENTER_P ? 'p' : 'div',

				// The order that stateActions get executed. It matters!
				shiftables = [ 'hasCaption', 'align' ],

				editable = editor.editable(),

				// Atomic procedures, one per state variable.
				stateActions = {
					align: function( data, oldValue, newValue ) {
						var hasCaptionAfter = data.newState.hasCaption,
							element = data.element;

						// Alignment changed.
						if ( changed( data, 'align' ) ) {
							// No caption in the new state.
							if ( !hasCaptionAfter ) {
								// Changed to "center" (non-captioned).
								if ( newValue == 'center' ) {
									data.destroy();
									data.element = wrapInCentering( element );
								}

								// Changed to "non-center" from "center" while caption removed.
								if ( !changed( data, 'hasCaption' ) && oldValue == 'center' && newValue != 'center' ) {
									data.destroy();
									data.element = unwrapFromCentering( element );
								}
							}
						}

						// Alignment remains and "center" removed caption.
						else if ( newValue == 'center' && changed( data, 'hasCaption' ) && !hasCaptionAfter ) {
							data.destroy();
							data.element = wrapInCentering( element );
						}

						// Finally set display for figure.
						if ( element.is( 'figure' ) ) {
							if ( newValue == 'center' )
								element.setStyle( 'display', 'inline-block' );
							else
								element.removeStyle( 'display' );
						}
					},
					hasCaption:	function( data, oldValue, newValue ) {
						// This action is for real state change only.
						if ( !changed( data, 'hasCaption' ) )
							return;

						var element = data.element,
							oldState = data.oldState,
							newState = data.newState,
							img;

						// Switching hasCaption always destroys the widget.
						data.destroy();

						// There was no caption, but the caption is to be added.
						if ( newValue ) {
							// Get <img> from element. As element may be either
							// <img> or centering <p>, consider it now.
							img = element.findOne( 'img' ) || element;

							// Create new <figure> from widget template.
							var figure = CKEDITOR.dom.element.createFromHtml( template, editor.document );

							// Replace element with <figure>.
							replaceSafely( figure, element );

							// Use old <img> instead of the one from the template,
							// so we won't lose additional attributes.
							img.replace( figure.findOne( 'img' ) );

							// Update widget's element.
							data.element = figure;
						}

						// The caption was present, but now it's to be removed.
						else {
							// Unwrap <img> from figure.
							img = element.findOne( 'img' );

							// Replace <figure> with <img>.
							img.replace( element );

							// Update widget's element.
							data.element = img;
						}
					}
				};

			function getValue( state, name ) {
				return state && state[ name ] !== undefined ? state[ name ] : null;
			}

			function changed( data, name ) {
				if ( !data.oldState )
					return false;
				else
					return data.oldState[ name ] !== data.newState[ name ];
			}

			function wrapInCentering( element ) {
				// When widget gets centered. Wrapper must be created.
				// Create new <p|div> with text-align:center.
				var center = editor.document.createElement( centerElement, {
					// Centering wrapper is.. centering.
					styles: { 'text-align': 'center' }
				} );

				// Replace element with centering wrapper.
				replaceSafely( center, element );

				// Append element into centering wrapper.
				element.move( center );

				return center;
			}

			function unwrapFromCentering( element ) {
				var img = element.findOne( 'img' );

				img.replace( element );

				return img;
			}

			function replaceSafely( replacing, replaced ) {
				if ( replaced.getParent() ) {
					// Create a range that corresponds with old element's position.
					var range = editor.createRange();

					// Move the range before old element.
					range.moveToPosition( replaced, CKEDITOR.POSITION_BEFORE_START );

					// Insert element at range position.
					editable.insertElementIntoRange( replacing, range );

					// Remove old element.
					replaced.remove();
				}
				else
					replacing.replace( replaced );
			}

			return function( data ) {
				var oldState = data.oldState,
					newState = data.newState,
					name;

				// Iterate over possible state variables.
				for ( var i = 0; i < shiftables.length; i++ ) {
					name = shiftables[ i ];

					stateActions[ name ]( data,
						oldState ? oldState[ name ] : null,
						newState[ name ] );
				}

				data.init( data.element );
			};
		}
	};

	function setWrapperAlign( widget ) {
		var wrapper = widget.wrapper,
			align = widget.data.align;

		if ( align == 'center' ) {
			if ( !widget.inline )
				wrapper.setStyle( 'text-align', 'center' );

			wrapper.removeStyle( 'float' );
		} else {
			if ( !widget.inline )
				wrapper.removeStyle( 'text-align' );

			if ( align == 'none' )
				wrapper.removeStyle( 'float' );
			else
				wrapper.setStyle( 'float', align );
		}
	}

	// Creates widgets from all <img> and <figure class="caption">.
	//
	// @param {CKEDITOR.htmlParser.element} el
	function createUpcastFunction( isBlock ) {
		var regexPercent = /^\s*(\d+\%)\s*$/i,
			dimensions = { width:1,height:1 };

		function upcastElement( el, isBlock, isCenter ) {
			var name = el.name,
				image;

			// Block widget to be upcasted.
			if ( isBlock ) {
				// If a center wrapper is found.
				if ( isCenter ) {
					// So the element is:
					// 		<div style="text-align:center"><figure></figure></div>.
					// Centering is done by widget.wrapper in such case. Hence, replace
					// centering wrapper with figure.
					// The other case is:
					// 		<p style="text-align:center"><img></p>.
					// Then <p> takes charge of <figure> and nothing is to be changed.
					if ( name == 'div' ) {
						var figure = el.getFirst( 'figure' );
						el.replaceWith( figure );
						el = figure;
					}

					// Mark the element as centered, so widget.data.align
					// can be correctly filled on init.
					el.attributes[ 'data-cke-centered' ] = true;

					image = el.getFirst( 'img' );
				}

				// No center wrapper has been found.
				else if ( name == 'figure' && el.hasClass( 'caption' ) )
					image = el.getFirst( 'img' );
			}

			// Inline widget from plain img.
			else if ( name == 'img' )
				image = el;

			if ( !image )
				return;

			// If there's an image, then cool, we got a widget.
			// Now just remove dimension attributes expressed with %.
			for ( var d in dimensions ) {
				var dimension = image.attributes[ d ];

				if ( dimension && dimension.match( regexPercent ) )
					delete image.attributes[ d ];
			}

			return el;
		}

		return isBlock ?
				function( el ) {
					return upcastElement( el, true, isCenterWrapper( el ) );
				}
			:
				function( el ) {
					// Basically upcast the element if there is no special
					// wrapper around.
					return upcastElement( el );
				};
	}

	// Transforms the widget to the external format according to
	// the current configuration.
	//
	// @param {CKEDITOR.htmlParser.element} el
	function downcastWidgetElement( el ) {
		var attrs = el.attributes,
			align = this.data.align;

		// De-wrap the image from resize handle wrapper.
		// Only block widgets have one.
		if ( !this.inline ) {
			var resizeWrapper = el.getFirst( 'span' ),
				img = resizeWrapper.getFirst( 'img' );

			resizeWrapper.replaceWith( img );
		}

		if ( align && align != 'none' ) {
			// Parse element styles. Styles will be extended.
			var styles = CKEDITOR.tools.parseCssText( attrs.style || '' );

			// If centering, wrap downcasted element.
			// Wrappers for <img> and <figure> are <p> and <div>, respectively.
			if ( align == 'center' && el.name != 'p' ) {
				var name = el.name == 'img' ? 'p' : 'div';

				el = el.wrapWith( new CKEDITOR.htmlParser.element( name, {
					'style': 'text-align:center'
				} ) );
			}

			// If left/right, add float style to the downcasted element.
			else if ( align in { left:1,right:1 } )
				styles[ 'float' ] = align;

			// Update element styles.
			if ( !CKEDITOR.tools.isEmpty( styles ) )
				attrs.style = CKEDITOR.tools.writeCssText( styles );
		}

		return el;
	}

	function isCenterWrapper( el ) {
		// Wrapper must be either <div> or <p>.
		if ( !( el.name in { div:1,p:1 } ) )
			return false;

		var children = el.children;

		// Centering wrapper can have only one child.
		if ( children.length !== 1 )
			return false;

		var styles = CKEDITOR.tools.parseCssText( el.attributes.style || '' );

		// Centering wrapper got to be... centering.
		if ( !styles[ 'text-align' ] || styles[ 'text-align' ] != 'center' )
			return false;

		var child = children[ 0 ],
			childName = child.name;

		// The only child of centering wrapper can be <figure> with
		// class="caption" or plain <img>.
		if ( childName == 'img' || ( childName == 'figure' && child.hasClass( 'caption' ) ) )
			return true;

		return false;
	}

	// Sets width and height of the widget image according to
	// current widget data.
	//
	// @param {CKEDITOR.plugins.widget} widget
	function setDimensions( widget ) {
		var dimensions = CKEDITOR.tools.extend( {}, widget.data, false, { width:1,height:1 } ),
			image = widget.parts.image;

		for ( var d in dimensions ) {
			if ( dimensions[ d ] )
				image.setAttribute( d, dimensions[ d ] );
			else
				image.removeAttribute( d );
		}
	}

	// Defines all features related to drag-driven image resizing.
	// @param {CKEDITOR.plugins.widget} widget
	function setupResizer( widget ) {
		var editor = widget.editor,
			doc = editor.document,
			resizer = doc.createElement( 'span' );

		resizer.addClass( 'cke_image2_resizer' );
		resizer.setAttribute( 'title', editor.lang.image2.resizer );
		resizer.append( new CKEDITOR.dom.text( '\u200b', doc ) );

		// Inline widgets don't need a resizer wrapper as an image spans the entire widget.
		if ( !widget.inline ) {
			var oldResizeWrapper = widget.element.getFirst(),
				resizeWrapper = doc.createElement( 'span' );

			resizeWrapper.addClass( 'cke_image2_resizer_wrapper' );
			resizeWrapper.append( widget.parts.image );
			resizeWrapper.append( resizer );
			widget.element.append( resizeWrapper, true );

			// Remove the old wrapper which could came from e.g. pasted HTML
			// and which could be corrupted (e.g. resizer span has been lost).
			if ( oldResizeWrapper.is( 'span' ) )
				oldResizeWrapper.remove();
		} else
			widget.wrapper.append( resizer );

		// Calculate values of size variables and mouse offsets.
		// Start observing mousemove.
		resizer.on( 'mousedown', function( evt ) {
			var image = widget.parts.image,

				// "factor" can be either 1 or -1. I.e.: For right-aligned images, we need to
				// subtract the difference to get proper width, etc. Without "factor",
				// resizer starts working the opposite way.
				factor = widget.data.align == 'right' ? -1 : 1,

				// The x-coordinate of the mouse relative to the screen
				// when button gets pressed.
				startX = evt.data.$.screenX,
				startY = evt.data.$.screenY,

				// The initial dimensions and aspect ratio of the image.
				startWidth = image.$.clientWidth,
				startHeight = image.$.clientHeight,
				ratio = startWidth / startHeight,

				moveListeners = [],

				nativeEvt, newWidth, newHeight, updateData,
				moveDiffX, moveDiffY, moveRatio;

			// Save the undo snapshot first: before resizing.
			editor.fire( 'saveSnapshot' );

			// Mousemove listeners are removed on mouseup.
			attachToDocuments( 'mousemove', onMouseMove, moveListeners );

			// Clean up the mousemove listener. Update widget data if valid.
			attachToDocuments( 'mouseup', onMouseUp );

			// Attaches an event to a global document if inline editor.
			// Additionally, if framed, also attaches the same event to iframe's document.
			function attachToDocuments( name, callback, collection ) {
				var globalDoc = CKEDITOR.document,
					listeners = [];

				if ( !doc.equals( globalDoc ) )
					listeners.push( globalDoc.on( name, callback ) );

				listeners.push( doc.on( name, callback ) );

				if ( collection ) {
					for ( var i = listeners.length; i--; )
						collection.push( listeners.pop() );
				}
			}

			// Calculate with first, and then adjust height, preserving ratio.
			function adjustToX() {
				newWidth = startWidth + factor * moveDiffX;
				newHeight = 0 | newWidth / ratio;
			}

			// Calculate height first, and then adjust width, preserving ratio.
			function adjustToY() {
				newHeight = startHeight - moveDiffY;
				newWidth = 0 | newHeight * ratio;
			}

			// This is how variables refer to the geometry.
			// Note: x corresponds to moveOffset, this is the position of mouse
			// Note: o corresponds to [startX, startY].
			//
			// 	+--------------+--------------+
			// 	|              |              |
			// 	|      I       |      II      |
			// 	|              |              |
			// 	+------------- o -------------+ _ _ _
			// 	|              |              |      ^
			// 	|      VI      |     III      |      | moveDiffY
			// 	|              |         x _ _ _ _ _ v
			// 	+--------------+---------|----+
			// 	               |         |
			// 	                <------->
			// 	                moveDiffX
			function onMouseMove( evt ) {
				nativeEvt = evt.data.$;

				// This is how far the mouse is from the point the button was pressed.
				moveDiffX = nativeEvt.screenX - startX;
				moveDiffY = startY - nativeEvt.screenY;

				// This is the aspect ratio of the move difference.
				moveRatio = Math.abs( moveDiffX / moveDiffY );

				// Left, center or none-aligned widget.
				if ( factor == 1 ) {
					if ( moveDiffX <= 0 ) {
						// Case: IV.
						if ( moveDiffY <= 0 )
							adjustToX();

						// Case: I.
						else {
							if ( moveRatio >= ratio )
								adjustToX();
							else
								adjustToY();
						}
					} else {
						// Case: III.
						if ( moveDiffY <= 0 ) {
							if ( moveRatio >= ratio )
								adjustToY();
							else
								adjustToX();
						}

						// Case: II.
						else
							adjustToY();
					}
				}

				// Right-aligned widget. It mirrors behaviours, so I becomes II,
				// IV becomes III and vice-versa.
				else {
					if ( moveDiffX <= 0 ) {
						// Case: IV.
						if ( moveDiffY <= 0 ) {
							if ( moveRatio >= ratio )
								adjustToY();
							else
								adjustToX();
						}

						// Case: I.
						else
							adjustToY();
					} else {
						// Case: III.
						if ( moveDiffY <= 0 )
							adjustToX();

						// Case: II.
						else {
							if ( moveRatio >= ratio )
								adjustToX();
							else
								adjustToY();
						}
					}
				}

				// Don't update attributes if less than 10.
				// This is to prevent images to visually disappear.
				if ( newWidth >= 15 && newHeight >= 15 ) {
					image.setAttributes( { width: newWidth, height: newHeight } );
					updateData = true;
				} else
					updateData = false;
			}

			function onMouseUp( evt ) {
				var l;

				while ( ( l = moveListeners.pop() ) )
					l.removeListener();

				if ( updateData ) {
					widget.setData( { width: newWidth, height: newHeight } );

					// Save another undo snapshot: after resizing.
					editor.fire( 'saveSnapshot' );
				}

				// Don't update data twice or more.
				updateData = false;
			}
		} );

		// Change the position of the widget resizer when data changes.
		widget.on( 'data', function() {
			resizer[ widget.data.align == 'right' ? 'addClass' : 'removeClass' ]( 'cke_image2_resizer_left' );
		} );
	}

	// Integrates widget alignment setting with justify
	// plugin's commands (execution and refreshment).
	// @param {CKEDITOR.editor} editor
	// @param {String} value 'left', 'right', 'center' or 'block'
	function alignCommandIntegrator( editor ) {
		var execCallbacks = [];

		return function( value ) {
			var command = editor.getCommand( 'justify' + value );

			// Most likely, the justify plugin isn't loaded.
			if ( !command )
				return;

			// This command will be manually refreshed along with
			// other commands after exec.
			execCallbacks.push( function() {
				command.refresh( editor, editor.elementPath() );
			} );

			if ( value in { right:1,left:1,center:1 } ) {
				command.on( 'exec', function( evt ) {
					var widget = getFocusedWidget( editor );

					if ( widget ) {
						widget.setData( 'align', value );

						// Once the widget changed its align, all the align commands
						// must be refreshed: the event is to be cancelled.
						for ( var i = execCallbacks.length; i--; )
							execCallbacks[ i ]();

						evt.cancel();
					}
				} );
			}

			command.on( 'refresh', function( evt ) {
				var widget = getFocusedWidget( editor ),
					allowed = { right:1,left:1,center:1 };

				if ( !widget )
					return;

				this.setState(
					( widget.data.align == value ) ?
							CKEDITOR.TRISTATE_ON
						:
							( value in allowed ) ?
									CKEDITOR.TRISTATE_OFF
								:
									CKEDITOR.TRISTATE_DISABLED );

				evt.cancel();
			} );
		};
	}

	// Returns the focused widget, if of the type specific for this plugin.
	// If no widget is focused, `null` is returned.
	// @param {CKEDITOR.editor}
	// @returns {CKEDITOR.plugins.widget}
	function getFocusedWidget( editor ) {
		var widget = editor.widgets.focused;

		if ( widget && widget.name in { image2inline:1,image2block:1 } )
			return widget;

		return null;
	}
})();