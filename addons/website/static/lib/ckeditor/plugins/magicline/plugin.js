/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Allows accessing difficult focus spaces.
 */

'use strict';

(function() {
	CKEDITOR.plugins.add( 'magicline', {
		lang: 'ar,bg,ca,cs,cy,de,el,en,eo,es,et,eu,fa,fi,fr,fr-ca,gl,he,hr,hu,id,it,ja,ko,ku,lv,nb,nl,no,pl,pt,pt-br,ru,si,sk,sl,sq,sv,tr,ug,uk,vi,zh-cn', // %REMOVE_LINE_CORE%
		init: initPlugin
	});

	// Activates the box inside of an editor.
	function initPlugin( editor ) {

		var enterBehaviors = {};
		enterBehaviors[ CKEDITOR.ENTER_BR ] = 'br';
		enterBehaviors[ CKEDITOR.ENTER_P ] = 'p';
		enterBehaviors[ CKEDITOR.ENTER_DIV ] = 'div';

		// Configurables
		var config = editor.config,
			triggerOffset = config.magicline_triggerOffset || 30,
			enterMode = config.enterMode,
			that = {
				// Global stuff is being initialized here.
				editor: editor,
				enterBehavior: enterBehaviors[ enterMode ], 		// A tag which is to be inserted by the magicline.
				enterMode: enterMode,
				triggerOffset: triggerOffset,
				holdDistance: 0 | triggerOffset * ( config.magicline_holdDistance || 0.5 ),
				boxColor: config.magicline_color || '#ff0000',
				rtl: config.contentsLangDirection == 'rtl',
				tabuList: [ 'data-widget-wrapper' ].concat( config.magicline_tabuList || [] ),
				triggers: config.magicline_everywhere ? DTD_BLOCK : { table:1,hr:1,div:1,ul:1,ol:1,dl:1,form:1,blockquote:1 }
			},
			scrollTimeout, checkMouseTimeoutPending, checkMouseTimeout, checkMouseTimer;

		// %REMOVE_START%
		// Internal DEBUG uses tools located in the topmost window.

		// (#9701) Due to security limitations some browsers may throw
		// errors when accessing window.top object. Do it safely first then.
		try {
			that.debug = window.top.DEBUG;
		}
		catch ( e ) {}

		that.debug = that.debug || {
			groupEnd: function() {},
			groupStart: function() {},
			log: function() {},
			logElements: function() {},
			logElementsEnd: function() {},
			logEnd: function() {},
			mousePos: function() {},
			showHidden: function() {},
			showTrigger: function() {},
			startTimer: function() {},
			stopTimer: function() {}
		};
		// %REMOVE_END%

		// Simple irrelevant elements filter.
		that.isRelevant = function( node ) {
			return isHtml( node ) 			// 	-> Node must be an existing HTML element.
				&& !isLine( that, node ) 	// 	-> Node can be neither the box nor its child.
				&& !isFlowBreaker( node ); 	// 	-> Node can be neither floated nor positioned nor aligned.
		};

		editor.on( 'contentDom', addListeners, this );

		function addListeners() {
			var editable = editor.editable(),
				doc = editor.document,
				win = editor.window,
				listener;

			// Global stuff is being initialized here.
			extend( that, {
				editable: editable,
				inInlineMode: editable.isInline(),
				doc: doc,
				win: win
			}, true );

			// This is the boundary of the editor. For inline the boundary is editable itself.
			// For framed editor, the HTML element is a real boundary.
			that.boundary = that.inInlineMode ? that.editable : that.doc.getDocumentElement();

			// Enabling the box inside of inline editable is pointless.
			// There's no need to access spaces inside paragraphs, links, spans, etc.
			if ( editable.is( dtd.$inline ) )
				return;

			// Handle in-line editing by setting appropriate position.
			// If current position is static, make it relative and clear top/left coordinates.
			if ( that.inInlineMode && !isPositioned( editable ) ) {
				editable.setStyles({
					position: 'relative',
					top: null,
					left: null
				});
			}
			// Enable the box. Let it produce children elements, initialize
			// event handlers and own methods.
			initLine.call( this, that );

			// Get view dimensions and scroll positions.
			// At this stage (before any checkMouse call) it is used mostly
			// by tests. Nevertheless it a crucial thing.
			updateWindowSize( that );

			// Remove the box before an undo image is created.
			// This is important. If we didn't do that, the *undo thing* would revert the box into an editor.
			// Thanks to that, undo doesn't even know about the existence of the box.
			editable.attachListener( editor, 'beforeUndoImage', function() {
				that.line.detach();
			});

			// Removes the box HTML from editor data string if getData is called.
			// Thanks to that, an editor never yields data polluted by the box.
			// Listen with very high priority, so line will be removed before other
			// listeners will see it.
			editable.attachListener( editor, 'beforeGetData', function() {
				// If the box is in editable, remove it.
				if ( that.line.wrap.getParent() ) {
					that.line.detach();

					// Restore line in the last listener for 'getData'.
					editor.once( 'getData', function() {
						that.line.attach();
					}, null, null, 1000 );
				}
			}, null, null, 0 );

			// Hide the box on mouseout if mouse leaves document.
			editable.attachListener( that.inInlineMode ? doc : doc.getWindow().getFrame(), 'mouseout', function( event ) {
				if ( editor.mode != 'wysiwyg' )
					return;

				// Check for inline-mode editor. If so, check mouse position
				// and remove the box if mouse outside of an editor.
				if ( that.inInlineMode ) {
					var mouse = {
						x: event.data.$.clientX,
						y: event.data.$.clientY
					};

					updateWindowSize( that );
					updateEditableSize( that, true );

					var size = that.view.editable,
						scroll = that.view.scroll;

					// If outside of an editor...
					if ( !inBetween( mouse.x, size.left - scroll.x, size.right - scroll.x ) || !inBetween( mouse.y, size.top - scroll.y, size.bottom - scroll.y ) ) {
						clearTimeout( checkMouseTimer );
						checkMouseTimer = null;
						that.line.detach();
					}
				}

				else {
					clearTimeout( checkMouseTimer );
					checkMouseTimer = null;
					that.line.detach();
				}
			});

			// This one deactivates hidden mode of an editor which
			// prevents the box from being shown.
			editable.attachListener( editable, 'keyup', function( event ) {
				that.hiddenMode = 0;
				that.debug.showHidden( that.hiddenMode ); // %REMOVE_LINE%
			});

			editable.attachListener( editable, 'keydown', function( event ) {
				if ( editor.mode != 'wysiwyg' )
					return;

				var keyStroke = event.data.getKeystroke(),
					selection = editor.getSelection(),
					selected = selection.getStartElement();

				switch ( keyStroke ) {
					// Shift pressed
					case 2228240: // IE
					case 16:
						that.hiddenMode = 1;
						that.line.detach();
				}

				that.debug.showHidden( that.hiddenMode ); // %REMOVE_LINE%
			});

			// This method ensures that checkMouse aren't executed
			// in parallel and no more frequently than specified in timeout function.
			// In framed editor, document is used as a trigger, to provide magicline
			// functionality when mouse is below the body (short content, short body).
			editable.attachListener( that.inInlineMode ? editable : doc, 'mousemove', function( event ) {
				checkMouseTimeoutPending = true;

				if ( editor.mode != 'wysiwyg' || editor.readOnly || checkMouseTimer )
					return;

				// IE<9 requires this event-driven object to be created
				// outside of the setTimeout statement.
				// Otherwise it loses the event object with its properties.
				var mouse = {
					x: event.data.$.clientX,
					y: event.data.$.clientY
				};

				checkMouseTimer = setTimeout( function() {
					checkMouse( mouse );
				}, 30 ); // balances performance and accessibility
			});

			// This one removes box on scroll event.
			// It is to avoid box displacement.
			editable.attachListener( win, 'scroll', function( event ) {
				if ( editor.mode != 'wysiwyg' )
					return;

				that.line.detach();

				// To figure this out just look at the mouseup
				// event handler below.
				if ( env.webkit ) {
					that.hiddenMode = 1;

					clearTimeout( scrollTimeout );
					scrollTimeout = setTimeout( function() {
						that.hiddenMode = 0;
						that.debug.showHidden( that.hiddenMode ); // %REMOVE_LINE%
					}, 50 );

					that.debug.showHidden( that.hiddenMode ); // %REMOVE_LINE%
				}
			});

			// Those event handlers remove the box on mousedown
			// and don't reveal it until the mouse is released.
			// It is to prevent box insertion e.g. while scrolling
			// (w/ scrollbar), selecting and so on.
			editable.attachListener( win, 'mousedown', function( event ) {
				if ( editor.mode != 'wysiwyg' )
					return;

				that.line.detach();
				that.hiddenMode = 1;

				that.debug.showHidden( that.hiddenMode ); // %REMOVE_LINE%
			});

			// Google Chrome doesn't trigger this on the scrollbar (since 2009...)
			// so it is totally useless to check for scroll finish
			// see: http://code.google.com/p/chromium/issues/detail?id=14204
			editable.attachListener( win, 'mouseup', function( event ) {
				that.hiddenMode = 0;
				that.debug.showHidden( that.hiddenMode ); // %REMOVE_LINE%
			});

			// Editor commands for accessing difficult focus spaces.
			editor.addCommand( 'accessPreviousSpace', accessFocusSpaceCmd( that ) );
			editor.addCommand( 'accessNextSpace', accessFocusSpaceCmd( that, true ) );

			editor.setKeystroke( [
				[ config.magicline_keystrokePrevious, 'accessPreviousSpace' ],
				[ config.magicline_keystrokeNext, 'accessNextSpace' ]
			] );

			// Revert magicline hot node on undo/redo.
			editor.on( 'loadSnapshot', function( event ) {
				var elements = editor.document.getElementsByTag( that.enterBehavior ),
					element;

				for ( var i = elements.count(); i--; ) {
					if ( ( element = elements.getItem( i ) ).hasAttribute( 'data-cke-magicline-hot' ) ) {
						// Restore hotNode
						that.hotNode = element;
						// Restore last access direction
						that.lastCmdDirection = element.getAttribute( 'data-cke-magicline-dir' ) === 'true' ? true : false;
						break;
					}
				}
			} );

			// This method handles mousemove mouse for box toggling.
			// It uses mouse position to determine underlying element, then
			// it tries to use different trigger type in order to place the box
			// in correct place. The following procedure is executed periodically.
			function checkMouse( mouse ) {
				that.debug.groupStart( 'CheckMouse' ); // %REMOVE_LINE%
				that.debug.startTimer(); // %REMOVE_LINE%

				that.mouse = mouse;
				that.trigger = null;

				checkMouseTimer = null;
				updateWindowSize( that );

				if ( checkMouseTimeoutPending 								//	-> There must be an event pending.
					&& !that.hiddenMode 									// 	-> Can't be in hidden mode.
					&& editor.focusManager.hasFocus 						// 	-> Editor must have focus.
					&& !that.line.mouseNear() 								// 	-> Mouse pointer can't be close to the box.
					&& ( that.element = elementFromMouse( that, true ) ) ) 	// 	-> There must be valid element.
				{
					// If trigger exists, and trigger is correct -> show the box.
					// Don't show the line if trigger is a descendant of some tabu-list element.
					if ( ( that.trigger = triggerEditable( that ) || triggerEdge( that ) || triggerExpand( that ) ) &&
						!isInTabu( that, that.trigger.upper || that.trigger.lower ) ) {
						that.line.attach().place();
					}

					// Otherwise remove the box
					else {
						that.trigger = null;
						that.line.detach();
					}

					that.debug.showTrigger( that.trigger ); // %REMOVE_LINE%
					that.debug.mousePos( mouse.y, that.element ); // %REMOVE_LINE%

					checkMouseTimeoutPending = false;
				}

				that.debug.stopTimer(); // %REMOVE_LINE%
				that.debug.groupEnd(); // %REMOVE_LINE%
			}

			// This one allows testing and debugging. It reveals some
			// inner methods to the world.
			this.backdoor = {
				accessFocusSpace: accessFocusSpace,
				boxTrigger: boxTrigger,
				isLine: isLine,
				getAscendantTrigger: getAscendantTrigger,
				getNonEmptyNeighbour: getNonEmptyNeighbour,
				getSize: getSize,
				that: that,
				triggerEdge: triggerEdge,
				triggerEditable: triggerEditable,
				triggerExpand: triggerExpand
			};
		}
	}

	// Some shorthands for common methods to save bytes
	var extend = CKEDITOR.tools.extend,
		newElement = CKEDITOR.dom.element,
		newElementFromHtml = newElement.createFromHtml,
		env = CKEDITOR.env,
		dtd = CKEDITOR.dtd,

		// Constant values, types and so on.
		EDGE_TOP = 128,
		EDGE_BOTTOM = 64,
		EDGE_MIDDLE = 32,
		TYPE_EDGE = 16,
		TYPE_EXPAND = 8,
		LOOK_TOP = 4,
		LOOK_BOTTOM = 2,
		LOOK_NORMAL = 1,
		WHITE_SPACE = '\u00A0',
		DTD_LISTITEM = dtd.$listItem,
		DTD_TABLECONTENT = dtd.$tableContent,
		DTD_NONACCESSIBLE = extend( {}, dtd.$nonEditable, dtd.$empty ),
		DTD_BLOCK = dtd.$block,

		// Minimum time that must elapse between two update*Size calls.
		// It prevents constant getComuptedStyle calls and improves performance.
		CACHE_TIME = 100,

		// Shared CSS stuff for box elements
		CSS_COMMON = 'width:0px;height:0px;padding:0px;margin:0px;display:block;' + 'z-index:9999;color:#fff;position:absolute;font-size: 0px;line-height:0px;',
		CSS_TRIANGLE = CSS_COMMON + 'border-color:transparent;display:block;border-style:solid;',
		TRIANGLE_HTML = '<span>' + WHITE_SPACE + '</span>';

	function areSiblings( that, upper, lower ) {
		return isHtml( upper ) && isHtml( lower ) && lower.equals( upper.getNext( function( node ) {
			return !( isEmptyTextNode( node ) || isComment( node ) || isFlowBreaker( node ) );
		}) );
	}

	// boxTrigger is an abstract type which describes
	// the relationship between elements that may result
	// in showing the box.
	//
	// The following type is used by numerous methods
	// to share information about the hypothetical box placement
	// and look by referring to boxTrigger properties.
	function boxTrigger( triggerSetup ) {
		this.upper = triggerSetup[ 0 ];
		this.lower = triggerSetup[ 1 ];
		this.set.apply( this, triggerSetup.slice( 2 ) );
	}

	boxTrigger.prototype = {
		set: function( edge, type, look ) {
			this.properties = edge + type + ( look || LOOK_NORMAL );
			return this;
		},

		is: function( property ) {
			return ( this.properties & property ) == property;
		}
	};

	var elementFromMouse = ( function() {
		function elementFromPoint( doc, mouse ) {
			return new CKEDITOR.dom.element( doc.$.elementFromPoint( mouse.x, mouse.y ) );
		}

		return function( that, ignoreBox, forceMouse ) {
			if ( !that.mouse )
				return null;

			var doc = that.doc,
				lineWrap = that.line.wrap,
				mouse = forceMouse || that.mouse,
				element = elementFromPoint( doc, mouse );

			// If ignoreBox is set and element is the box, it means that we
			// need to hide the box for a while, repeat elementFromPoint
			// and show it again.
			if ( ignoreBox && isLine( that, element ) ) {
				lineWrap.hide();
				element = elementFromPoint( doc, mouse );
				lineWrap.show();
			}

			// Return nothing if:
			//	\-> Element is not HTML.
			if ( !( element && element.type == CKEDITOR.NODE_ELEMENT && element.$ ) ) {
				return null;
			}

			// Also return nothing if:
			//	\-> We're IE<9 and element is out of the top-level element (editable for inline and HTML for framed).
			//		This is due to the bug which allows IE<9 firing mouse events on element
			//		with contenteditable=true while doing selection out (far, away) of the element.
			//		Thus we must always be sure that we stay in editable or HTML.
			if ( env.ie && env.version < 9 ) {
				if ( !( that.boundary.equals( element ) || that.boundary.contains( element ) ) )
					return null;
			}

			return element;
		};
	})();

	// Gets the closest parent node that belongs to triggers group.
	function getAscendantTrigger( that ) {
		var node = that.element,
			trigger;

		if ( node && isHtml( node ) ) {
			return ( trigger = node.getAscendant( that.triggers, true ) ) &&
				!trigger.contains( that.editable ) &&
				!trigger.equals( that.editable ) ? trigger : null;
		}

		return null;
	}

	function getMidpoint( that, upper, lower ) {
		updateSize( that, upper );
		updateSize( that, lower );

		var upperSizeBottom = upper.size.bottom,
			lowerSizeTop = lower.size.top;

		return upperSizeBottom && lowerSizeTop ? 0 | ( upperSizeBottom + lowerSizeTop ) / 2 : upperSizeBottom || lowerSizeTop;
	}

	// Get nearest node (either text or HTML), but:
	//	\->	Omit all empty text nodes (containing white characters only).
	//	\-> Omit BR elements
	//	\-> Omit flow breakers.
	function getNonEmptyNeighbour( that, node, goBack ) {
		node = node[ goBack ? 'getPrevious' : 'getNext' ]( function( node ) {
			return ( isTextNode( node ) && !isEmptyTextNode( node ) ) ||
				( isHtml( node ) && !isFlowBreaker( node ) && !isLine( that, node ) );
		});

		return node;
	}

	function inBetween( val, lower, upper ) {
		return val > lower && val < upper;
	}

	// Access space line consists of a few elements (spans):
	// 	\-> Line wrapper.
	// 	\-> Line.
	// 	\-> Line triangles: left triangle (LT), right triangle (RT).
	// 	\-> Button handler (BTN).
	//
	//	+--------------------------------------------------- line.wrap (span) -----+
	//	| +---------------------------------------------------- line (span) -----+ |
	//	| | +- LT \                                           +- BTN -+  / RT -+ | |
	//	| | |      \                                          |     | | /      | | |
	//	| | |      /                                          |  <__| | \      | | |
	//	| | +-----/                                           +-------+  \-----+ | |
	//	| +----------------------------------------------------------------------+ |
	//  +--------------------------------------------------------------------------+
	//
	function initLine( that ) {
		var doc = that.doc,
			// This the main box element that holds triangles and the insertion button
			line = newElementFromHtml( '<span contenteditable="false" style="' + CSS_COMMON + 'position:absolute;border-top:1px dashed ' + that.boxColor + '"></span>', doc ),
			iconPath = this.path + 'images/' + ( env.hidpi ? 'hidpi/' : '' ) + 'icon.png';

		extend( line, {

			attach: function() {
				// Only if not already attached
				if ( !this.wrap.getParent() )
					this.wrap.appendTo( that.editable, true );

				return this;
			},

			// Looks are as follows: [ LOOK_TOP, LOOK_BOTTOM, LOOK_NORMAL ].
			lineChildren: [
				extend(
					newElementFromHtml( '<span title="' + that.editor.lang.magicline.title +
						'" contenteditable="false">&#8629;</span>', doc ), {
					base: CSS_COMMON + 'height:17px;width:17px;' + ( that.rtl ? 'left' : 'right' ) + ':17px;'
						+ 'background:url(' + iconPath + ') center no-repeat ' + that.boxColor + ';cursor:pointer;'
						+ ( env.hc ? 'font-size: 15px;line-height:14px;border:1px solid #fff;text-align:center;' : '' )
						+ ( env.hidpi ? 'background-size: 9px 10px;' : '' ),
					looks: [
						'top:-8px;' + CKEDITOR.tools.cssVendorPrefix( 'border-radius', '2px', 1 ),
						'top:-17px;' + CKEDITOR.tools.cssVendorPrefix( 'border-radius', '2px 2px 0px 0px', 1 ),
						'top:-1px;' + CKEDITOR.tools.cssVendorPrefix( 'border-radius', '0px 0px 2px 2px', 1 )
					]
				}),
				extend( newElementFromHtml( TRIANGLE_HTML, doc ), {
					base: CSS_TRIANGLE + 'left:0px;border-left-color:' + that.boxColor + ';',
					looks: [
						'border-width:8px 0 8px 8px;top:-8px',
						'border-width:8px 0 0 8px;top:-8px',
						'border-width:0 0 8px 8px;top:0px'
					]
				}),
				extend( newElementFromHtml( TRIANGLE_HTML, doc ), {
					base: CSS_TRIANGLE + 'right:0px;border-right-color:' + that.boxColor + ';',
					looks: [
						'border-width:8px 8px 8px 0;top:-8px',
						'border-width:8px 8px 0 0;top:-8px',
						'border-width:0 8px 8px 0;top:0px'
					]
				})
			],

			detach: function() {
				// Detach only if already attached.
				if ( this.wrap.getParent() )
					this.wrap.remove();

				return this;
			},

			// Checks whether mouseY is around an element by comparing boundaries and considering
			// an offset distance.
			mouseNear: function() {
				that.debug.groupStart( 'mouseNear' ); // %REMOVE_LINE%

				updateSize( that, this );
				var offset = that.holdDistance,
					size = this.size;

				// Determine neighborhood by element dimensions and offsets.
				if ( size && inBetween( that.mouse.y, size.top - offset, size.bottom + offset ) && inBetween( that.mouse.x, size.left - offset, size.right + offset ) ) {
					that.debug.logEnd( 'Mouse is near.' ); // %REMOVE_LINE%
					return true;
				}

				that.debug.logEnd( 'Mouse isn\'t near.' ); // %REMOVE_LINE%
				return false;
			},

			// Adjusts position of the box according to the trigger properties.
			// If also affects look of the box depending on the type of the trigger.
			place: function() {
				var view = that.view,
					editable = that.editable,
					trigger = that.trigger,
					upper = trigger.upper,
					lower = trigger.lower,
					any = upper || lower,
					parent = any.getParent(),
					styleSet = {};

				// Save recent trigger for further insertion.
				// It is necessary due to the fact, that that.trigger may
				// contain different boxTrigger at the moment of insertion
				// or may be even null.
				this.trigger = trigger;

				upper && updateSize( that, upper, true );
				lower && updateSize( that, lower, true );
				updateSize( that, parent, true );

				// Yeah, that's gonna be useful in inline-mode case.
				if ( that.inInlineMode )
					updateEditableSize( that, true );

				// Set X coordinate (left, right, width).
				if ( parent.equals( editable ) ) {
					styleSet.left = view.scroll.x;
					styleSet.right = -view.scroll.x;
					styleSet.width = '';
				} else {
					styleSet.left = any.size.left - any.size.margin.left + view.scroll.x - ( that.inInlineMode ? view.editable.left + view.editable.border.left : 0 );
					styleSet.width = any.size.outerWidth + any.size.margin.left + any.size.margin.right + view.scroll.x;
					styleSet.right = '';
				}

				// Set Y coordinate (top) for trigger consisting of two elements.
				if ( upper && lower ) {
					// No margins at all or they're equal. Place box right between.
					if ( upper.size.margin.bottom === lower.size.margin.top )
						styleSet.top = 0 | ( upper.size.bottom + upper.size.margin.bottom / 2 );
					else {
						// Upper margin < lower margin. Place at lower margin.
						if ( upper.size.margin.bottom < lower.size.margin.top )
							styleSet.top = upper.size.bottom + upper.size.margin.bottom;
						// Upper margin > lower margin. Place at upper margin - lower margin.
						else
							styleSet.top = upper.size.bottom + upper.size.margin.bottom - lower.size.margin.top;
					}
				}
				// Set Y coordinate (top) for single-edge trigger.
				else if ( !upper )
					styleSet.top = lower.size.top - lower.size.margin.top;
				else if ( !lower )
					styleSet.top = upper.size.bottom + upper.size.margin.bottom;

				// Set box button modes if close to the viewport horizontal edge
				// or look forced by the trigger.
				if ( trigger.is( LOOK_TOP ) || inBetween( styleSet.top, view.scroll.y - 15, view.scroll.y + 5 ) ) {
					styleSet.top = that.inInlineMode ? 0 : view.scroll.y;
					this.look( LOOK_TOP );
				} else if ( trigger.is( LOOK_BOTTOM ) || inBetween( styleSet.top, view.pane.bottom - 5, view.pane.bottom + 15 ) ) {
					styleSet.top = that.inInlineMode ?
							view.editable.height + view.editable.padding.top + view.editable.padding.bottom
						:
							view.pane.bottom - 1;

					this.look( LOOK_BOTTOM );
				} else {
					if ( that.inInlineMode )
						styleSet.top -= view.editable.top + view.editable.border.top;

					this.look( LOOK_NORMAL );
				}

				if ( that.inInlineMode ) {
					// 1px bug here...
					styleSet.top--;

					// Consider the editable to be an element with overflow:scroll
					// and non-zero scrollTop/scrollLeft value.
					// For example: divarea editable. (#9383)
					styleSet.top += view.editable.scroll.top;
					styleSet.left += view.editable.scroll.left;
				}

				// Append `px` prefixes.
				for ( var style in styleSet )
					styleSet[ style ] = CKEDITOR.tools.cssLength( styleSet[ style ] );

				this.setStyles( styleSet );
			},

			// Changes look of the box according to current needs.
			// Three different styles are available: [ LOOK_TOP, LOOK_BOTTOM, LOOK_NORMAL ].
			look: function( look ) {
				if ( this.oldLook == look )
					return;

				for ( var i = this.lineChildren.length, child; i--; )
					( child = this.lineChildren[ i ] ).setAttribute( 'style', child.base + child.looks[ 0 | look / 2 ] );

				this.oldLook = look;
			},

			wrap: new newElement( 'span', that.doc )

		});

		// Insert children into the box.
		for ( var i = line.lineChildren.length; i--; )
			line.lineChildren[ i ].appendTo( line );

		// Set default look of the box.
		line.look( LOOK_NORMAL );

		// Using that wrapper prevents IE (8,9) from resizing editable area at the moment
		// of box insertion. This works thanks to the fact, that positioned box is wrapped by
		// an inline element. So much tricky.
		line.appendTo( line.wrap );

		// Make the box unselectable.
		line.unselectable();

		// Handle accessSpace node insertion.
		line.lineChildren[ 0 ].on( 'mouseup', function( event ) {
			line.detach();

			accessFocusSpace( that, function( accessNode ) {
				// Use old trigger that was saved by 'place' method. Look: line.place
				var trigger = that.line.trigger;

				accessNode[ trigger.is( EDGE_TOP ) ? 'insertBefore' : 'insertAfter' ]
					( trigger.is( EDGE_TOP ) ? trigger.lower : trigger.upper );
			}, true );

			that.editor.focus();

			if ( !env.ie && that.enterMode != CKEDITOR.ENTER_BR )
				that.hotNode.scrollIntoView();

			event.data.preventDefault( true );
		});

		// Prevents IE9 from displaying the resize box and disables drag'n'drop functionality.
		line.on( 'mousedown', function( event ) {
			event.data.preventDefault( true );
		});

		that.line = line;
	}

	// This function allows accessing any focus space according to the insert function:
	// 	* For enterMode ENTER_P it creates P element filled with dummy white-space.
	// 	* For enterMode ENTER_DIV it creates DIV element filled with dummy white-space.
	// 	* For enterMode ENTER_BR it creates BR element or &nbsp; in IE.
	//
	// The node is being inserted according to insertFunction. Finally the method
	// selects the non-breaking space making the node ready for typing.
	function accessFocusSpace( that, insertFunction, doSave ) {
		var range = new CKEDITOR.dom.range( that.doc ),
			editor = that.editor,
			accessNode;

		// IE requires text node of &nbsp; in ENTER_BR mode.
		if ( env.ie && that.enterMode == CKEDITOR.ENTER_BR )
			accessNode = that.doc.createText( WHITE_SPACE );

		// In other cases a regular element is used.
		else {
			accessNode = new newElement( that.enterBehavior, that.doc );

			if ( that.enterMode != CKEDITOR.ENTER_BR ) {
				var dummy = that.doc.createText( WHITE_SPACE );
				dummy.appendTo( accessNode );
			}
		}

		doSave && editor.fire( 'saveSnapshot' );

		insertFunction( accessNode );
		//dummy.appendTo( accessNode );
		range.moveToPosition( accessNode, CKEDITOR.POSITION_AFTER_START );
		editor.getSelection().selectRanges( [ range ] );
		that.hotNode = accessNode;

		doSave && editor.fire( 'saveSnapshot' );
	}

	// Access focus space on demand by taking an element under the caret as a reference.
	// The space is accessed provided the element under the caret is trigger AND:
	//
	//  1. First/last-child of its parent:
	//		+----------------------- Parent element -+
	//		| +------------------------------ DIV -+ |	<-- Access before
	//		| | Foo^                               | |
	//		| |                                    | |
	//		| +------------------------------------+ |	<-- Access after
	//		+----------------------------------------+
	//
	//                       OR
	//
	//  2. It has a direct sibling element, which is also a trigger:
	//		+-------------------------------- DIV#1 -+
	//		| Foo^                                   |
	//		|                                        |
	//		+----------------------------------------+
	//                                                	<-- Access here
	//		+-------------------------------- DIV#2 -+
	//		| Bar                                    |
	//		|                                        |
	//		+----------------------------------------+
	//
	//                       OR
	//
	//  3. It has a direct sibling, which is a trigger and has a valid neighbour trigger,
	//     but belongs to dtd.$.empty/nonEditable:
	//		+------------------------------------ P -+
	//		| Foo^                                   |
	//		|                                        |
	//		+----------------------------------------+
	//		+----------------------------------- HR -+
	//                                                	<-- Access here
	//		+-------------------------------- DIV#2 -+
	//		| Bar                                    |
	//		|                                        |
	//		+----------------------------------------+
	//
	function accessFocusSpaceCmd( that, insertAfter ) {
		return {
			canUndo: true,
			modes: { wysiwyg: 1 },
			exec: ( function() {

				// Inserts line (accessNode) at the position by taking target node as a reference.
				function doAccess( target ) {
					// Remove old hotNode under certain circumstances.
					var hotNodeChar = ( env.ie && env.version < 9 ? ' ' : WHITE_SPACE ),
						removeOld = that.hotNode &&							// Old hotNode must exist.
							that.hotNode.getText() == hotNodeChar &&		// Old hotNode hasn't been changed.
							that.element.equals( that.hotNode ) &&			// Caret is inside old hotNode.
							that.lastCmdDirection === !!insertAfter;		// Command is executed in the same direction.

					accessFocusSpace( that, function( accessNode ) {
						if ( removeOld && that.hotNode )
							that.hotNode.remove();

						accessNode[ insertAfter ? 'insertAfter' : 'insertBefore' ]( target );

						// Make this element distinguishable. Also remember the direction
						// it's been inserted into document.
						accessNode.setAttributes( {
							'data-cke-magicline-hot': 1,
							'data-cke-magicline-dir': !!insertAfter
						} );

						// Save last direction of the command (is insertAfter?).
						that.lastCmdDirection = !!insertAfter;
					} );

					if( !env.ie && that.enterMode != CKEDITOR.ENTER_BR )
						that.hotNode.scrollIntoView();

					// Detach the line if was visible (previously triggered by mouse).
					that.line.detach();
				}

				return function( editor ) {
					var selected = editor.getSelection().getStartElement();

					// (#9833) Go down to the closest non-inline element in DOM structure
					// since inline elements don't participate in in magicline.
					selected = selected.getAscendant( DTD_BLOCK, 1 );

					// Stop if selected is a child of a tabu-list element.
					if ( isInTabu( that, selected ) )
						return;

					// Sometimes it may happen that there's no parent block below selected element
					// or, for example, getAscendant reaches editable or editable parent.
					// We must avoid such pathological cases.
					if ( !selected || selected.equals( that.editable ) || selected.contains( that.editable ) )
						return;

					// That holds element from mouse. Replace it with the
					// element under the caret.
					that.element = selected;

					// (3.) Handle the following cases where selected neighbour
					// is a trigger inaccessible for the caret AND:
					//	- Is first/last-child
					//	OR
					//	- Has a sibling, which is also a trigger.
					var neighbor = getNonEmptyNeighbour( that, selected, !insertAfter ),
						neighborSibling;

					// Check for a neighbour that belongs to triggers.
					// Consider only non-accessible elements (they cannot have any children)
					// since they cannot be given a caret inside, to run the command
					// the regular way (1. & 2.).
					if ( isHtml( neighbor ) && neighbor.is( that.triggers ) && neighbor.is( DTD_NONACCESSIBLE ) &&
							(
									// Check whether neighbor is first/last-child.
									!getNonEmptyNeighbour( that, neighbor, !insertAfter )
								||
									// Check for a sibling of a neighbour that also is a trigger.
									(
										( neighborSibling = getNonEmptyNeighbour( that, neighbor, !insertAfter ) ) &&
										isHtml( neighborSibling ) &&
										neighborSibling.is( that.triggers )
									)
							)
						) {
						doAccess( neighbor );
						return;
					}

					// Look for possible target element DOWN "selected" DOM branch (towards editable)
					// that belong to that.triggers
					var target = getAscendantTrigger( that, selected );

					// No HTML target -> no access.
					if ( !isHtml( target ) )
						return;

					// (1.) Target is first/last child -> access.
					if ( !getNonEmptyNeighbour( that, target, !insertAfter ) ) {
						doAccess( target );
						return;
					}

					var sibling = getNonEmptyNeighbour( that, target, !insertAfter );

					// (2.) Target has a sibling that belongs to that.triggers -> access.
					if ( sibling && isHtml( sibling ) && sibling.is( that.triggers ) ) {
						doAccess( target );
						return;
					}
				};
			})()
		};
	}

	function isLine( that, node ) {
		if ( !( node && node.type == CKEDITOR.NODE_ELEMENT && node.$ ) )
			return false;

		var line = that.line;

		return line.wrap.equals( node ) || line.wrap.contains( node );
	}

	// Is text node containing white-spaces only?
	var isEmptyTextNode = CKEDITOR.dom.walker.whitespaces();

	// Is fully visible HTML node?
	function isHtml( node ) {
		return node && node.type == CKEDITOR.NODE_ELEMENT && node.$;	// IE requires that
	}

	function isFloated( element ) {
		if ( !isHtml( element ) )
			return false;

		var options = { left:1,right:1,center:1 };

		return !!( options[ element.getComputedStyle( 'float' ) ] || options[ element.getAttribute( 'align' ) ] );
	}

	function isFlowBreaker( element ) {
		if ( !isHtml( element ) )
			return false;

		return isPositioned( element ) || isFloated( element );
	}

	// Isn't node of NODE_COMMENT type?
	var isComment = CKEDITOR.dom.walker.nodeType( CKEDITOR.NODE_COMMENT );

	function isPositioned( element ) {
		return !!{ absolute:1,fixed:1,relative:1 }[ element.getComputedStyle( 'position' ) ];
	}

	// Is text node?
	function isTextNode( node ) {
		return node && node.type == CKEDITOR.NODE_TEXT;
	}

	function isTrigger( that, element ) {
		return isHtml( element ) ? element.is( that.triggers ) : null;
	}

	function isInTabu( that, element ) {
		if ( !element )
			return false;

		var parents = element.getParents( 1 );

		for ( var i = parents.length ; i-- ; ) {
			for ( var j = that.tabuList.length ; j-- ; ) {
				if ( parents[ i ].hasAttribute( that.tabuList[ j ] ) )
					return true;
			}
		}

		return false;
	}

	// This function checks vertically is there's a relevant child between element's edge
	// and the pointer.
	//	\-> Table contents are omitted.
	function isChildBetweenPointerAndEdge( that, parent, edgeBottom ) {
		var edgeChild = parent[ edgeBottom ? 'getLast' : 'getFirst' ]( function( node ) {
			return that.isRelevant( node ) && !node.is( DTD_TABLECONTENT );
		});

		if ( !edgeChild )
			return false;

		updateSize( that, edgeChild );

		return edgeBottom ? edgeChild.size.top > that.mouse.y : edgeChild.size.bottom < that.mouse.y;
	}

	// This method handles edge cases:
	// 	\-> Mouse is around upper or lower edge of view pane.
	// 	\-> Also scroll position is either minimal or maximal.
	// 	\-> It's OK to show LOOK_TOP(BOTTOM) type line.
	//
	// This trigger doesn't need additional post-filtering.
	//
	//	+----------------------------- Editable -+  /--
	//	| +---------------------- First child -+ |  | <-- Top edge (first child)
	//	| |                                    | |  |
	//	| |                                    | |  |	 * Mouse activation area *
	//	| |                                    | |  |
	//	| |                 ...                | |	\-- Top edge + trigger offset
	//	| .                                    . |
	//	|                                        |
	//	| .                                    . |
	//	| |                 ...                | |  /-- Bottom edge - trigger offset
	//	| |                                    | |  |
	//	| |                                    | |  |	 * Mouse activation area *
	//	| |                                    | |  |
	//	| +----------------------- Last child -+ |  | <-- Bottom edge (last child)
	//	+----------------------------------------+  \--
	//
	function triggerEditable( that ) {
		that.debug.groupStart( 'triggerEditable' ); // %REMOVE_LINE%

		var editable = that.editable,
			mouse = that.mouse,
			view = that.view,
			triggerOffset = that.triggerOffset,
			triggerLook;

		// Update editable dimensions.
		updateEditableSize( that );

		// This flag determines whether checking bottom trigger.
		var bottomTrigger = mouse.y > ( that.inInlineMode ?
				view.editable.top + view.editable.height / 2
			:
				// This is to handle case when editable.height / 2 <<< pane.height.
				Math.min( view.editable.height, view.pane.height ) / 2 ),

		// Edge node according to bottomTrigger.
		edgeNode = editable[ bottomTrigger ? 'getLast' : 'getFirst' ]( function( node ) {
			return !( isEmptyTextNode( node ) || isComment( node ) );
		});

		// There's no edge node. Abort.
		if ( !edgeNode ) {
			that.debug.logEnd( 'ABORT. No edge node found.' ); // %REMOVE_LINE%
			return null;
		}

		// If the edgeNode in editable is ML, get the next one.
		if ( isLine( that, edgeNode ) ) {
			edgeNode = that.line.wrap[ bottomTrigger ? 'getPrevious' : 'getNext' ]( function( node ) {
				return !( isEmptyTextNode( node ) || isComment( node ) );
			});
		}

		// Exclude bad nodes (no ML needed then):
		//	\-> Edge node is text.
		//	\-> Edge node is floated, etc.
		//
		// Edge node *must be* a valid trigger at this stage as well.
		if ( !isHtml( edgeNode ) || isFlowBreaker( edgeNode ) || !isTrigger( that, edgeNode ) ) {
			that.debug.logEnd( 'ABORT. Invalid edge node.' ); // %REMOVE_LINE%
			return null;
		}

		// Update size of edge node. Dimensions will be necessary.
		updateSize( that, edgeNode );

		// Return appropriate trigger according to bottomTrigger.
		// \->	Top edge trigger case first.
		if ( !bottomTrigger &&													// Top trigger case.
			edgeNode.size.top >= 0 &&											// Check if the first element is fully visible.
			inBetween( mouse.y, 0, edgeNode.size.top + triggerOffset ) ) {		// Check if mouse in [0, edgeNode.top + triggerOffset].

			// Determine trigger look.
			triggerLook = that.inInlineMode || view.scroll.y === 0 ?
				LOOK_TOP : LOOK_NORMAL;

			that.debug.logEnd( 'SUCCESS. Created box trigger. EDGE_TOP.' ); // %REMOVE_LINE%

			return new boxTrigger( [ null, edgeNode,
				EDGE_TOP,
				TYPE_EDGE,
				triggerLook
			] );
		}

		// \->	Bottom case.
		else if ( bottomTrigger &&
			edgeNode.size.bottom <= view.pane.height &&							// Check if the last element is fully visible
			inBetween( mouse.y,													// Check if mouse in...
				edgeNode.size.bottom - triggerOffset, view.pane.height ) ) {	// [ edgeNode.bottom - triggerOffset, paneHeight ]

			// Determine trigger look.
			triggerLook = that.inInlineMode ||
				inBetween( edgeNode.size.bottom, view.pane.height - triggerOffset, view.pane.height ) ?
					LOOK_BOTTOM : LOOK_NORMAL;

			that.debug.logEnd( 'SUCCESS. Created box trigger. EDGE_BOTTOM.' ); // %REMOVE_LINE%

			return new boxTrigger( [ edgeNode, null,
				EDGE_BOTTOM,
				TYPE_EDGE,
				triggerLook
			] );
		}

		that.debug.logEnd( 'ABORT. No trigger created.' ); // %REMOVE_LINE%
		return null;
	}

	// This method covers cases *inside* of an element:
	// 	\->	The pointer is in the top (bottom) area of an element and there's
	//		HTML node before (after) this element.
	// 	\-> An element being the first or last child of its parent.
	//
	//	+----------------------- Parent element -+
	//	| +----------------------- Element #1 -+ |  /--
	//	| |                                    | |  |	 * Mouse activation area (as first child) *
	//	| |                                    | |  \--
	//	| |                                    | |  /--
	//	| |                                    | |  |	 * Mouse activation area (Element #2) *
	//	| +------------------------------------+ |  \--
	//	|                                        |
	//	| +----------------------- Element #2 -+ |  /--
	//	| |                                    | |  |	 * Mouse activation area (Element #1) *
	//	| |                                    | |  \--
	//	| |                                    | |
	//	| +------------------------------------+ |
	//	|                                        |
	//	|            Text node is here.          |
	//	|                                        |
	//	| +----------------------- Element #3 -+ |
	//	| |                                    | |
	//	| |                                    | |
	//	| |                                    | |  /--
	//	| |                                    | |  |	 * Mouse activation area (as last child) *
	//	| +------------------------------------+ |  \--
	//	+----------------------------------------+
	//
	function triggerEdge( that ) {
		that.debug.groupStart( 'triggerEdge' ); // %REMOVE_LINE%

		var mouse = that.mouse,
			view = that.view,
			triggerOffset = that.triggerOffset;

		// Get the ascendant trigger basing on elementFromMouse.
		var element = getAscendantTrigger( that );

		that.debug.logElements( [ element ], [ 'Ascendant trigger' ], 'First stage' ); // %REMOVE_LINE%

		// Abort if there's no appropriate element.
		if ( !element ) {
			that.debug.logEnd( 'ABORT. No element, element is editable or element contains editable.' ); // %REMOVE_LINE%
			return null;
		}

		// Dimensions will be necessary.
		updateSize( that, element );

		// If triggerOffset is larger than a half of element's height,
		// use an offset of 1/2 of element's height. If the offset wasn't reduced,
		// top area would cover most (all) cases.
		var fixedOffset = Math.min( triggerOffset,
				0 | ( element.size.outerHeight / 2 ) ),

		// This variable will hold the trigger to be returned.
			triggerSetup = [],
			triggerLook,

		// This flag determines whether dealing with a bottom trigger.
			bottomTrigger;

		//	\-> Top trigger.
		if ( inBetween( mouse.y, element.size.top - 1, element.size.top + fixedOffset ) )
			bottomTrigger = false;
		//	\-> Bottom trigger.
		else if ( inBetween( mouse.y, element.size.bottom - fixedOffset, element.size.bottom + 1 ) )
			bottomTrigger = true;
		//	\-> Abort. Not in a valid trigger space.
		else {
			that.debug.logEnd( 'ABORT. Not around of any edge.' ); // %REMOVE_LINE%
			return null;
		}

		// Reject wrong elements.
		// 	\-> Reject an element which is a flow breaker.
		// 	\-> Reject an element which has a child above/below the mouse pointer.
		//	\-> Reject an element which belongs to list items.
		if( isFlowBreaker( element ) ||
			isChildBetweenPointerAndEdge( that, element, bottomTrigger ) ||
			element.getParent().is( DTD_LISTITEM ) ) {
				that.debug.logEnd( 'ABORT. element is wrong', element ); // %REMOVE_LINE%
				return null;
		}

		// Get sibling according to bottomTrigger.
		var elementSibling = getNonEmptyNeighbour( that, element, !bottomTrigger );

		// No sibling element.
		// This is a first or last child case.
		if ( !elementSibling ) {
			// No need to reject the element as it has already been done before.
			// Prepare a trigger.

			// Determine trigger look.
			if ( element.equals( that.editable[ bottomTrigger ? 'getLast' : 'getFirst' ]( that.isRelevant ) ) ) {
				updateEditableSize( that );

				if ( bottomTrigger && inBetween( mouse.y,
					element.size.bottom - fixedOffset, view.pane.height ) &&
					inBetween( element.size.bottom, view.pane.height - fixedOffset, view.pane.height ) ) {
						triggerLook = LOOK_BOTTOM;
				}
				else if ( inBetween( mouse.y, 0, element.size.top + fixedOffset ) ) {
					triggerLook = LOOK_TOP;
				}
			}
			else
				triggerLook = LOOK_NORMAL;

			triggerSetup = [ null, element ][ bottomTrigger ? 'reverse' : 'concat' ]().concat( [
					bottomTrigger ? EDGE_BOTTOM : EDGE_TOP,
					TYPE_EDGE,
					triggerLook,
					element.equals( that.editable[ bottomTrigger ? 'getLast' : 'getFirst' ]( that.isRelevant ) ) ?
						( bottomTrigger ? LOOK_BOTTOM : LOOK_TOP ) : LOOK_NORMAL
				] );

			that.debug.log( 'Configured edge trigger of ' + ( bottomTrigger ? 'EDGE_BOTTOM' : 'EDGE_TOP' ) ); // %REMOVE_LINE%
		}

		// Abort. Sibling is a text element.
		else if ( isTextNode( elementSibling ) ) {
			that.debug.logEnd( 'ABORT. Sibling is non-empty text element' ); // %REMOVE_LINE%
			return null;
		}

		// Check if the sibling is a HTML element.
		// If so, create an TYPE_EDGE, EDGE_MIDDLE trigger.
		else if ( isHtml( elementSibling ) ) {
			// Reject wrong elementSiblings.
			// 	\-> Reject an elementSibling which is a flow breaker.
			//	\-> Reject an elementSibling which isn't a trigger.
			//	\-> Reject an elementSibling which belongs to list items.
			if( isFlowBreaker( elementSibling ) ||
				!isTrigger( that, elementSibling ) ||
				elementSibling.getParent().is( DTD_LISTITEM ) ) {
					that.debug.logEnd( 'ABORT. elementSibling is wrong', elementSibling ); // %REMOVE_LINE%
					return null;
			}

			// Prepare a trigger.
			triggerSetup = [ elementSibling, element ][ bottomTrigger ? 'reverse' : 'concat' ]().concat( [
					EDGE_MIDDLE,
					TYPE_EDGE
				] );

			that.debug.log( 'Configured edge trigger of EDGE_MIDDLE' ); // %REMOVE_LINE%
		}

		if ( 0 in triggerSetup ) {
			that.debug.logEnd( 'SUCCESS. Returning a trigger.' ); // %REMOVE_LINE%
			return new boxTrigger( triggerSetup );
		}

		that.debug.logEnd( 'ABORT. No trigger generated.' ); // %REMOVE_LINE%
		return null;
	}

	// Checks iteratively up and down in search for elements using elementFromMouse method.
	// Useful if between two triggers.
	//
	//	+----------------------- Parent element -+
	//	| +----------------------- Element #1 -+ |
	//	| |                                    | |
	//	| |                                    | |
	//	| |                                    | |
	//	| +------------------------------------+ |
	//	|                                        |  /--
	//	|                  .                     |  |
	//	|                  .      +-- Floated -+ |  |
	//	|                  |      |            | |  |	* Mouse activation area *
	//	|                  |      |   IGNORE   | |  |
	//	|                  X      |            | |  |	Method searches vertically for sibling elements.
	//	|                  |      +------------+ |  |	Start point is X (mouse-y coordinate).
	//	|                  |                     |  |	Floated elements, comments and empty text nodes are omitted.
	//	|                  .                     |  |
	//	|                  .                     |  |
	//	|                                        |  \--
	//	| +----------------------- Element #2 -+ |
	//	| |                                    | |
	//	| |                                    | |
	//	| |                                    | |
	//	| |                                    | |
	//	| +------------------------------------+ |
	//	+----------------------------------------+
	//
	var triggerExpand = ( function() {
		// The heart of the procedure. This method creates triggers that are
		// filtered by expandFilter method.
		function expandEngine( that ) {
			that.debug.groupStart( 'expandEngine' ); // %REMOVE_LINE%

			var startElement = that.element,
				upper, lower, trigger;

			if ( !isHtml( startElement ) || startElement.contains( that.editable ) ) {
				that.debug.logEnd( 'ABORT. No start element, or start element contains editable.' ); // %REMOVE_LINE%
				return null;
			}

			trigger = verticalSearch( that,
				function( current, startElement ) {
					return !startElement.equals( current );	// stop when start element and the current one differ
				}, function( that, mouse ) {
					return elementFromMouse( that, true, mouse );
				}, startElement ),

			upper = trigger.upper,
			lower = trigger.lower;

			that.debug.logElements( [ upper, lower ], [ 'Upper', 'Lower' ], 'Pair found' ); // %REMOVE_LINE%

			// Success: two siblings have been found
			if ( areSiblings( that, upper, lower ) ) {
				that.debug.logEnd( 'SUCCESS. Expand trigger created.' ); // %REMOVE_LINE%
				return trigger.set( EDGE_MIDDLE, TYPE_EXPAND );
			}

			that.debug.logElements( [ startElement, upper, lower ], // %REMOVE_LINE%
				[ 'Start', 'Upper', 'Lower' ], 'Post-processing' ); // %REMOVE_LINE%

			// Danger. Dragons ahead.
			// No siblings have been found during previous phase, post-processing may be necessary.
			// We can traverse DOM until a valid pair of elements around the pointer is found.

			// Prepare for post-processing:
			// 	1. Determine if upper and lower are children of startElement.
			// 		1.1. If so, find their ascendants that are closest to startElement (one level deeper than startElement).
			// 		1.2. Otherwise use first/last-child of the startElement as upper/lower. Why?:
			// 			a) 	upper/lower belongs to another branch of the DOM tree.
			// 			b) 	verticalSearch encountered an edge of the viewport and failed.
			// 		1.3. Make sure upper and lower still exist. Why?:
			// 			a) 	Upper and lower may be not belong to the branch of the startElement (may not exist at all) and
			// 				startElement has no children.
			// 	2. Perform the post-processing.
			// 		2.1. Gather dimensions of an upper element.
			// 		2.2. Abort if lower edge of upper is already under the mouse pointer. Why?:
			// 			a) 	We expect upper to be above and lower below the mouse pointer.
			// 	3. Perform iterative search while upper != lower.
			// 		3.1. Find the upper-next element. If there's no such element, break current search. Why?:
			// 			a)	There's no point in further search if there are only text nodes ahead.
			// 		3.2. Calculate the distance between the middle point of ( upper, upperNext ) and mouse-y.
			// 		3.3. If the distance is shorter than the previous best, save it (save upper, upperNext as well).
			// 		3.4. If the optimal pair is found, assign it back to the trigger.

			// 1.1., 1.2.
			if ( upper && startElement.contains( upper ) ) {
				while ( !upper.getParent().equals( startElement ) )
					upper = upper.getParent();
			} else {
				upper = startElement.getFirst( function( node ) {
					return expandSelector( that, node );
				});
			}

			if ( lower && startElement.contains( lower ) ) {
				while ( !lower.getParent().equals( startElement ) )
					lower = lower.getParent();
			} else {
				lower = startElement.getLast( function( node ) {
					return expandSelector( that, node );
				});
			}

			// 1.3.
			if ( !upper || !lower ) {
				that.debug.logEnd( 'ABORT. There is no upper or no lower element.' ); // %REMOVE_LINE%
				return null;
			}

			// 2.1.
			updateSize( that, upper );
			updateSize( that, lower );

			if ( !checkMouseBetweenElements( that, upper, lower ) ) {
				that.debug.logEnd( 'ABORT. Mouse is already above upper or below lower.' ); // %REMOVE_LINE%
				return null;
			}

			var minDistance = Number.MAX_VALUE,
				currentDistance, upperNext, minElement, minElementNext;

			while ( lower && !lower.equals( upper ) ) {
				// 3.1.
				if ( !( upperNext = upper.getNext( that.isRelevant ) ) )
					break;

				// 3.2.
				currentDistance = Math.abs( getMidpoint( that, upper, upperNext ) - that.mouse.y );

				// 3.3.
				if ( currentDistance < minDistance ) {
					minDistance = currentDistance;
					minElement = upper;
					minElementNext = upperNext;
				}

				upper = upperNext;
				updateSize( that, upper );
			}

			that.debug.logElements( [ minElement, minElementNext ], // %REMOVE_LINE%
				[ 'Min', 'MinNext' ], 'Post-processing results' ); // %REMOVE_LINE%

			// 3.4.
			if ( !minElement || !minElementNext ) {
				that.debug.logEnd( 'ABORT. No Min or MinNext' ); // %REMOVE_LINE%
				return null;
			}

			if ( !checkMouseBetweenElements( that, minElement, minElementNext ) ) {
				that.debug.logEnd( 'ABORT. Mouse is already above minElement or below minElementNext.' ); // %REMOVE_LINE%
				return null;
			}

			// An element of minimal distance has been found. Assign it to the trigger.
			trigger.upper = minElement;
			trigger.lower = minElementNext;

			// Success: post-processing revealed a pair of elements.
			that.debug.logEnd( 'SUCCESSFUL post-processing. Trigger created.' ); // %REMOVE_LINE%
			return trigger.set( EDGE_MIDDLE, TYPE_EXPAND );
		}

		// This is default element selector used by the engine.
		function expandSelector( that, node ) {
			return !( isTextNode( node )
				|| isComment( node )
				|| isFlowBreaker( node )
				|| isLine( that, node )
				|| ( node.type == CKEDITOR.NODE_ELEMENT && node.$ && node.is( 'br' ) ) );
		}

		// This method checks whether mouse-y is between the top edge of upper
		// and bottom edge of lower.
		//
		// NOTE: This method assumes that updateSize has already been called
		// for the elements and is up-to-date.
		//
		//	+---------------------------- Upper -+  /--
		//	|                                    |  |
		//	+------------------------------------+  |
		//                                          |
		//                     ...                  |
		//                                          |
		//						X                   |	* Return true for mouse-y in this range *
		//                                          |
		//                     ...                  |
		//                                          |
		//	+---------------------------- Lower -+  |
		//	|                                    |  |
		//	+------------------------------------+  \--
		//
		function checkMouseBetweenElements( that, upper, lower ) {
			return inBetween( that.mouse.y, upper.size.top, lower.size.bottom );
		}

		// A method for trigger filtering. Accepts or rejects trigger pairs
		// by their location in DOM etc.
		function expandFilter( that, trigger ) {
			that.debug.groupStart( 'expandFilter' ); // %REMOVE_LINE%

			var upper = trigger.upper,
				lower = trigger.lower;

			if ( !upper || !lower 											// NOT: EDGE_MIDDLE trigger ALWAYS has two elements.
				|| isFlowBreaker( lower ) || isFlowBreaker( upper )			// NOT: one of the elements is floated or positioned
				|| lower.equals( upper ) || upper.equals( lower ) 			// NOT: two trigger elements, one equals another.
				|| lower.contains( upper ) || upper.contains( lower ) ) { 	// NOT: two trigger elements, one contains another.
				that.debug.logEnd( 'REJECTED. No upper or no lower or they contain each other.' ); // %REMOVE_LINE%

				return false;
			}

			// YES: two trigger elements, pure siblings.
			else if ( isTrigger( that, upper ) && isTrigger( that, lower ) && areSiblings( that, upper, lower ) ) {
				that.debug.logElementsEnd( [ upper, lower ], // %REMOVE_LINE%
					[ 'upper', 'lower' ], 'APPROVED EDGE_MIDDLE' ); // %REMOVE_LINE%

				return true;
			}

			that.debug.logElementsEnd( [ upper, lower ], // %REMOVE_LINE%
				[ 'upper', 'lower' ], 'Rejected unknown pair' ); // %REMOVE_LINE%

			return false;
		}

		// Simple wrapper for expandEngine and expandFilter.
		return function( that ) {
			that.debug.groupStart( 'triggerExpand' ); // %REMOVE_LINE%

			var trigger = expandEngine( that );

			that.debug.groupEnd(); // %REMOVE_LINE%
			return trigger && expandFilter( that, trigger ) ? trigger : null;
		};
	})();

	// Collects dimensions of an element.
	var sizePrefixes = [ 'top', 'left', 'right', 'bottom' ];

	function getSize( that, element, ignoreScroll, force ) {
		var getStyle = (function() {
			// Better "cache and reuse" than "call again and again".
			var computed = env.ie ? element.$.currentStyle : that.win.$.getComputedStyle( element.$, '' );

				return env.ie ?
					function( propertyName ) {
						return computed[ CKEDITOR.tools.cssStyleToDomStyle( propertyName ) ];
					} : function( propertyName ) {
						return computed.getPropertyValue( propertyName );
					};
			})(),
			docPosition = element.getDocumentPosition(),
			border = {},
			margin = {},
			padding = {},
			box = {};

		for ( var i = sizePrefixes.length; i--; ) {
			border[ sizePrefixes[ i ] ] = parseInt( getStyle( 'border-' + sizePrefixes[ i ] + '-width' ), 10 ) || 0;
			padding[ sizePrefixes[ i ] ] = parseInt( getStyle( 'padding-' + sizePrefixes[ i ] ), 10 ) || 0;
			margin[ sizePrefixes[ i ] ] = parseInt( getStyle( 'margin-' + sizePrefixes[ i ] ), 10 ) || 0;
		}

		// updateWindowSize if forced to do so OR NOT ignoring scroll.
		if ( !ignoreScroll || force )
			updateWindowSize( that, force );

		box.top = docPosition.y - ( ignoreScroll ? 0 : that.view.scroll.y ), box.left = docPosition.x - ( ignoreScroll ? 0 : that.view.scroll.x ),

		// w/ borders and paddings.
		box.outerWidth = element.$.offsetWidth, box.outerHeight = element.$.offsetHeight,

		// w/o borders and paddings.
		box.height = box.outerHeight - ( padding.top + padding.bottom + border.top + border.bottom ), box.width = box.outerWidth - ( padding.left + padding.right + border.left + border.right ),

		box.bottom = box.top + box.outerHeight, box.right = box.left + box.outerWidth;

		if ( that.inInlineMode ) {
			box.scroll = {
				top: element.$.scrollTop,
				left: element.$.scrollLeft
			};
		}

		return extend({
			border: border,
			padding: padding,
			margin: margin,
			ignoreScroll: ignoreScroll
		}, box, true );
	}

	function updateSize( that, element, ignoreScroll ) {
		if ( !isHtml( element ) ) // i.e. an element is hidden
			return ( element.size = null ); //	-> reset size to make it useless for other methods

		if ( !element.size )
			element.size = {};

		// Abort if there was a similar query performed recently.
		// This kind of caching provides great performance improvement.
		else if ( element.size.ignoreScroll == ignoreScroll && element.size.date > new Date() - CACHE_TIME ) {
			that.debug.log( 'element.size: get from cache' ); // %REMOVE_LINE%
			return null;
		}

		that.debug.log( 'element.size: capture' ); // %REMOVE_LINE%

		return extend( element.size, getSize( that, element, ignoreScroll ), {
			date: +new Date()
		}, true );
	}

	// Updates that.view.editable object.
	// This one must be called separately outside of updateWindowSize
	// to prevent cyclic dependency getSize<->updateWindowSize.
	// It calls getSize with force flag to avoid getWindowSize cache (look: getSize).
	function updateEditableSize( that, ignoreScroll ) {
		that.view.editable = getSize( that, that.editable, ignoreScroll, true );
	}

	function updateWindowSize( that, force ) {
		if ( !that.view )
			that.view = {};

		var view = that.view;

		if ( !force && view && view.date > new Date() - CACHE_TIME ) {
			that.debug.log( 'win.size: get from cache' ); // %REMOVE_LINE%
			return;
		}

		that.debug.log( 'win.size: capturing' ); // %REMOVE_LINE%

		var win = that.win,
			scroll = win.getScrollPosition(),
			paneSize = win.getViewPaneSize();

		extend( that.view, {
			scroll: {
				x: scroll.x,
				y: scroll.y,
				width: that.doc.$.documentElement.scrollWidth - paneSize.width,
				height: that.doc.$.documentElement.scrollHeight - paneSize.height
			},
			pane: {
				width: paneSize.width,
				height: paneSize.height,
				bottom: paneSize.height + scroll.y
			},
			date: +new Date()
		}, true );
	}

	// This method searches document vertically using given
	// select criterion until stop criterion is fulfilled.
	function verticalSearch( that, stopCondition, selectCriterion, startElement ) {
		var upper = startElement,
			lower = startElement,
			mouseStep = 0,
			upperFound = false,
			lowerFound = false,
			viewPaneHeight = that.view.pane.height,
			mouse = that.mouse;

		while ( mouse.y + mouseStep < viewPaneHeight && mouse.y - mouseStep > 0 ) {
			if ( !upperFound )
				upperFound = stopCondition( upper, startElement );

			if ( !lowerFound )
				lowerFound = stopCondition( lower, startElement );

			// Still not found...
			if ( !upperFound && mouse.y - mouseStep > 0 )
				upper = selectCriterion( that, { x: mouse.x, y: mouse.y - mouseStep } );

			if ( !lowerFound && mouse.y + mouseStep < viewPaneHeight )
				lower = selectCriterion( that, { x: mouse.x, y: mouse.y + mouseStep } );

			if ( upperFound && lowerFound )
				break;

			// Instead of ++ to reduce the number of invocations by half.
			// It's trades off accuracy in some edge cases for improved performance.
			mouseStep += 2;
		}

		return new boxTrigger( [ upper, lower, null, null ] );
	}

})();

/**
 * Sets the default vertical distance between element edge and mouse pointer that
 * causes the box to appear. The distance is expressed in pixels (px).
 *
 *		// Changes the offset to 15px.
 *		CKEDITOR.config.magicline_triggerOffset = 15;
 *
 * @cfg {Number} [magicline_triggerOffset=30]
 * @member CKEDITOR.config
 * @see CKEDITOR.config#magicline_holdDistance
 */

/**
 * Defines the distance between mouse pointer and the box, within
 * which the box stays revealed and no other focus space is offered to be accessed.
 * The value is relative to {@link #magicline_triggerOffset}.
 *
 *		// Increases the distance to 80% of CKEDITOR.config.magicline_triggerOffset.
 *		CKEDITOR.config.magicline_holdDistance = .8;
 *
 * @cfg {Number} [magicline_holdDistance=0.5]
 * @member CKEDITOR.config
 * @see CKEDITOR.config#magicline_triggerOffset
 */

/**
 * Defines default keystroke that access the closest unreachable focus space **before**
 * the caret (start of the selection). If there's no any focus space, selection remains.
 *
 *		// Changes keystroke to CTRL + ,
 *		CKEDITOR.config.magicline_keystrokePrevious = CKEDITOR.CTRL + 188;
 *
 * @cfg {Number} [magicline_keystrokePrevious=CKEDITOR.CTRL + CKEDITOR.SHIFT + 219 (CTRL + SHIFT + [)]
 * @member CKEDITOR.config
 */
CKEDITOR.config.magicline_keystrokePrevious = CKEDITOR.CTRL + CKEDITOR.SHIFT + 219; // CTRL + SHIFT + [

/**
 * Defines default keystroke that access the closest unreachable focus space **after**
 * the caret (start of the selection). If there's no any focus space, selection remains.
 *
 *		// Changes keystroke to CTRL + .
 *		CKEDITOR.config.magicline_keystrokeNext = CKEDITOR.CTRL + 190;
 *
 * @cfg {Number} [magicline_keystrokeNext=CKEDITOR.CTRL + CKEDITOR.SHIFT + 221 (CTRL + SHIFT + ])]
 * @member CKEDITOR.config
 */
CKEDITOR.config.magicline_keystrokeNext = CKEDITOR.CTRL + CKEDITOR.SHIFT + 221; // CTRL + SHIFT + ]

/**
 * Defines a list of attributes that, if assigned to some elements, prevent magicline from being
 * used within these elements.
 *
 *		// Adds "data-tabu" attribute to magicline tabu list.
 *		CKEDITOR.config.magicline_tabuList = [ 'data-tabu' ];
 *
 * @cfg {Number} [magicline_tabuList=[ 'data-widget-wrapper' ]]
 * @member CKEDITOR.config
 */

/**
 * Defines box color. The color may be adjusted to enhance readability.
 *
 *		// Changes color to blue.
 *		CKEDITOR.config.magicline_color = '#0000FF';
 *
 * @cfg {String} [magicline_color='#FF0000']
 * @member CKEDITOR.config
 */

/**
 * Activates plugin mode that considers all focus spaces between
 * {@link CKEDITOR.dtd#$block} elements as accessible by the box.
 *
 *		// Enables "put everywhere" mode.
 *		CKEDITOR.config.magicline_putEverywhere = true;
 *
 * @cfg {Boolean} [magicline_putEverywhere=false]
 * @member CKEDITOR.config
 */
