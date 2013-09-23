/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * Registers a function to be called whenever the selection position changes in the
 * editing area. The current state is passed to the function. The possible
 * states are {@link CKEDITOR#TRISTATE_ON} and {@link CKEDITOR#TRISTATE_OFF}.
 *
 *		// Create a style object for the <b> element.
 *		var style = new CKEDITOR.style( { element: 'b' } );
 *		var editor = CKEDITOR.instances.editor1;
 *		editor.attachStyleStateChange( style, function( state ) {
 *			if ( state == CKEDITOR.TRISTATE_ON )
 *				alert( 'The current state for the B element is ON' );
 *			else
 *				alert( 'The current state for the B element is OFF' );
 *		} );
 *
 * @member CKEDITOR.editor
 * @param {CKEDITOR.style} style The style to be watched.
 * @param {Function} callback The function to be called.
 */
CKEDITOR.editor.prototype.attachStyleStateChange = function( style, callback ) {
	// Try to get the list of attached callbacks.
	var styleStateChangeCallbacks = this._.styleStateChangeCallbacks;

	// If it doesn't exist, it means this is the first call. So, let's create
	// all the structure to manage the style checks and the callback calls.
	if ( !styleStateChangeCallbacks ) {
		// Create the callbacks array.
		styleStateChangeCallbacks = this._.styleStateChangeCallbacks = [];

		// Attach to the selectionChange event, so we can check the styles at
		// that point.
		this.on( 'selectionChange', function( ev ) {
			// Loop throw all registered callbacks.
			for ( var i = 0; i < styleStateChangeCallbacks.length; i++ ) {
				var callback = styleStateChangeCallbacks[ i ];

				// Check the current state for the style defined for that
				// callback.
				var currentState = callback.style.checkActive( ev.data.path ) ? CKEDITOR.TRISTATE_ON : CKEDITOR.TRISTATE_OFF;

				// Call the callback function, passing the current
				// state to it.
				callback.fn.call( this, currentState );
			}
		});
	}

	// Save the callback info, so it can be checked on the next occurrence of
	// selectionChange.
	styleStateChangeCallbacks.push( { style: style, fn: callback } );
};

CKEDITOR.STYLE_BLOCK = 1;
CKEDITOR.STYLE_INLINE = 2;
CKEDITOR.STYLE_OBJECT = 3;

(function() {
	var blockElements = { address:1,div:1,h1:1,h2:1,h3:1,h4:1,h5:1,h6:1,p:1,pre:1,section:1,header:1,footer:1,nav:1,article:1,aside:1,figure:1,dialog:1,hgroup:1,time:1,meter:1,menu:1,command:1,keygen:1,output:1,progress:1,details:1,datagrid:1,datalist:1 },
		objectElements = { a:1,embed:1,hr:1,img:1,li:1,object:1,ol:1,table:1,td:1,tr:1,th:1,ul:1,dl:1,dt:1,dd:1,form:1,audio:1,video:1 };

	var semicolonFixRegex = /\s*(?:;\s*|$)/,
		varRegex = /#\((.+?)\)/g;

	var notBookmark = CKEDITOR.dom.walker.bookmark( 0, 1 ),
		nonWhitespaces = CKEDITOR.dom.walker.whitespaces( 1 );

	/**
	 * TODO...
	 *
	 * @class
	 * @constructor Creates a style class instance.
	 * @param styleDefinition
	 * @param variablesValues
	 * @todo
	 */
	CKEDITOR.style = function( styleDefinition, variablesValues ) {

		// Inline style text as attribute should be converted
		// to styles object.
		var attrs = styleDefinition.attributes;
		if ( attrs && attrs.style ) {
			styleDefinition.styles = CKEDITOR.tools.extend( {},
				styleDefinition.styles, CKEDITOR.tools.parseCssText( attrs.style ) );
			delete attrs.style;
		}

		if ( variablesValues ) {
			styleDefinition = CKEDITOR.tools.clone( styleDefinition );

			replaceVariables( styleDefinition.attributes, variablesValues );
			replaceVariables( styleDefinition.styles, variablesValues );
		}

		var element = this.element = styleDefinition.element ?
		                             (typeof styleDefinition.element == 'string' ?
		                              styleDefinition.element.toLowerCase() :
		                              styleDefinition.element ) : '*';

		this.type = styleDefinition.type ||
		            (blockElements[ element ] ? CKEDITOR.STYLE_BLOCK :
		             objectElements[ element ] ? CKEDITOR.STYLE_OBJECT :
		             CKEDITOR.STYLE_INLINE );

		// If the 'element' property is an object with a set of possible element, it will be applied like an object style: only to existing elements
		if ( typeof this.element == 'object' )
			this.type = CKEDITOR.STYLE_OBJECT;

		this._ = {
			definition: styleDefinition
		};
	};

	/**
	 * Apply the style upon the editor's current selection.
	 *
	 * @member CKEDITOR.editor
	 * @param {CKEDITOR.style} style
	 */
	CKEDITOR.editor.prototype.applyStyle = function( style ) {
		applyStyleOnSelection.call( style, this.getSelection() );
	};

	/**
	 * Remove the style from the editor's current selection.
	 *
	 * @member CKEDITOR.editor
	 * @param {CKEDITOR.style} style
	 */
	CKEDITOR.editor.prototype.removeStyle = function( style ) {
		applyStyleOnSelection.call( style, this.getSelection(), 1 );
	};

	CKEDITOR.style.prototype = {
		/**
		 * @param {CKEDITOR.dom.document} document
		 * @todo
		 */
		apply: function( document ) {
			applyStyleOnSelection.call( this, document.getSelection() );
		},

		/**
		 * @param {CKEDITOR.dom.document} document
		 * @todo
		 */
		remove: function( document ) {
			applyStyleOnSelection.call( this, document.getSelection(), 1 );
		},

		/**
		 * @param {CKEDITOR.dom.range} range
		 * @todo
		 */
		applyToRange: function( range ) {
			return ( this.applyToRange =
			         this.type == CKEDITOR.STYLE_INLINE ? applyInlineStyle :
			         this.type == CKEDITOR.STYLE_BLOCK ? applyBlockStyle :
			         this.type == CKEDITOR.STYLE_OBJECT ? applyObjectStyle :
			         null ).call( this, range );
		},

		/**
		 * @param {CKEDITOR.dom.range} range
		 * @todo
		 */
		removeFromRange: function( range ) {
			return ( this.removeFromRange =
			         this.type == CKEDITOR.STYLE_INLINE ? removeInlineStyle :
			         this.type == CKEDITOR.STYLE_BLOCK ? removeBlockStyle :
			         this.type == CKEDITOR.STYLE_OBJECT ? removeObjectStyle :
			         null ).call( this, range );
		},

		/**
		 * @param {CKEDITOR.dom.element} element
		 * @todo
		 */
		applyToObject: function( element ) {
			setupElement( element, this );
		},

		/**
		 * Get the style state inside an element path.
		 *
		 * @param {CKEDITOR.dom.elementPath} elementPath
		 * @returns {Boolean} `true` if the element is active in the path.
		 */
		checkActive: function( elementPath ) {
			switch ( this.type ) {
				case CKEDITOR.STYLE_BLOCK:
					return this.checkElementRemovable( elementPath.block || elementPath.blockLimit, true );

				case CKEDITOR.STYLE_OBJECT:
				case CKEDITOR.STYLE_INLINE:

					var elements = elementPath.elements;

					for ( var i = 0, element; i < elements.length; i++ ) {
						element = elements[ i ];

						if ( this.type == CKEDITOR.STYLE_INLINE && ( element == elementPath.block || element == elementPath.blockLimit ) )
							continue;

						if ( this.type == CKEDITOR.STYLE_OBJECT ) {
							var name = element.getName();
							if ( !( typeof this.element == 'string' ? name == this.element : name in this.element ) )
								continue;
						}

						if ( this.checkElementRemovable( element, true ) )
							return true;
					}
			}
			return false;
		},

		/**
		 * Whether this style can be applied at the element path.
		 *
		 * @param {CKEDITOR.dom.elementPath} elementPath
		 * @returns {Boolean} `true` if this style can be applied at the element path.
		 */
		checkApplicable: function( elementPath ) {
			switch ( this.type ) {
				case CKEDITOR.STYLE_INLINE:
				case CKEDITOR.STYLE_BLOCK:
					break;

				case CKEDITOR.STYLE_OBJECT:
					return elementPath.contains( this.element );
			}

			return true;
		},

		/**
		 * Check if the element matches the current style definition.
		 *
		 * @param {CKEDITOR.dom.element} element
		 * @param {Boolean} fullMatch
		 * @returns {Boolean}
		 * @todo
		 */
		checkElementMatch: function( element, fullMatch ) {
			var def = this._.definition;

			if ( !element || !def.ignoreReadonly && element.isReadOnly() )
				return false;

			var attribs,
				name = element.getName();

			// If the element name is the same as the style name.
			if ( typeof this.element == 'string' ? name == this.element : name in this.element ) {
				// If no attributes are defined in the element.
				if ( !fullMatch && !element.hasAttributes() )
					return true;

				attribs = getAttributesForComparison( def );

				if ( attribs._length ) {
					for ( var attName in attribs ) {
						if ( attName == '_length' )
							continue;

						var elementAttr = element.getAttribute( attName ) || '';

						// Special treatment for 'style' attribute is required.
						if ( attName == 'style' ?
						     compareCssText( attribs[ attName ], elementAttr ) :
						     attribs[ attName ] == elementAttr )
						{
							if ( !fullMatch )
								return true;
						} else if ( fullMatch )
							return false;
					}
					if ( fullMatch )
						return true;
				} else
					return true;
			}

			return false;
		},

		/**
		 * Checks if an element, or any of its attributes, is removable by the
		 * current style definition.
		 *
		 * @param {CKEDITOR.dom.element} element
		 * @param {Boolean} fullMatch
		 * @returns {Boolean}
		 * @todo
		 */
		checkElementRemovable: function( element, fullMatch ) {
			// Check element matches the style itself.
			if ( this.checkElementMatch( element, fullMatch ) )
				return true;

			// Check if the element matches the style overrides.
			var override = getOverrides( this )[ element.getName() ];
			if ( override ) {
				var attribs, attName;

				// If no attributes have been defined, remove the element.
				if ( !( attribs = override.attributes ) )
					return true;

				for ( var i = 0; i < attribs.length; i++ ) {
					attName = attribs[ i ][ 0 ];
					var actualAttrValue = element.getAttribute( attName );
					if ( actualAttrValue ) {
						var attValue = attribs[ i ][ 1 ];

						// Remove the attribute if:
						//    - The override definition value is null;
						//    - The override definition value is a string that
						//      matches the attribute value exactly.
						//    - The override definition value is a regex that
						//      has matches in the attribute value.
						if ( attValue === null ||
						     ( typeof attValue == 'string' &&
						       actualAttrValue == attValue ) ||
						     attValue.test( actualAttrValue ) )
							return true;
					}
				}
			}
			return false;
		},

		/**
		 * Builds the preview HTML based on the styles definition.
		 *
		 * @param label
		 * @todo
		 */
		buildPreview: function( label ) {
			var styleDefinition = this._.definition,
				html = [],
				elementName = styleDefinition.element;

			// Avoid <bdo> in the preview.
			if ( elementName == 'bdo' )
				elementName = 'span';

			html = [ '<', elementName ];

			// Assign all defined attributes.
			var attribs = styleDefinition.attributes;
			if ( attribs ) {
				for ( var att in attribs ) {
					html.push( ' ', att, '="', attribs[ att ], '"' );
				}
			}

			// Assign the style attribute.
			var cssStyle = CKEDITOR.style.getStyleText( styleDefinition );
			if ( cssStyle )
				html.push( ' style="', cssStyle, '"' );

			html.push( '>', ( label || styleDefinition.name ), '</', elementName, '>' );

			return html.join( '' );
		},

		getDefinition: function() {
			return this._.definition;
		}
	};

	/**
	 * Build the cssText based on the styles definition.
	 *
	 * @static
	 * @param styleDefinition
	 * @returns {String}
	 * @todo
	 */
	CKEDITOR.style.getStyleText = function( styleDefinition ) {
		// If we have already computed it, just return it.
		var stylesDef = styleDefinition._ST;
		if ( stylesDef )
			return stylesDef;

		stylesDef = styleDefinition.styles;

		// Builds the StyleText.
		var stylesText = ( styleDefinition.attributes && styleDefinition.attributes[ 'style' ] ) || '',
			specialStylesText = '';

		if ( stylesText.length )
			stylesText = stylesText.replace( semicolonFixRegex, ';' );

		for ( var style in stylesDef ) {
			var styleVal = stylesDef[ style ],
				text = ( style + ':' + styleVal ).replace( semicolonFixRegex, ';' );

			// Some browsers don't support 'inherit' property value, leave them intact. (#5242)
			if ( styleVal == 'inherit' )
				specialStylesText += text;
			else
				stylesText += text;
		}

		// Browsers make some changes to the style when applying them. So, here
		// we normalize it to the browser format.
		if ( stylesText.length )
			stylesText = CKEDITOR.tools.normalizeCssText( stylesText, true );

		stylesText += specialStylesText;

		// Return it, saving it to the next request.
		return ( styleDefinition._ST = stylesText );
	};

	// Gets the parent element which blocks the styling for an element. This
	// can be done through read-only elements (contenteditable=false) or
	// elements with the "data-nostyle" attribute.
	function getUnstylableParent( element, root ) {
		var unstylable, editable;

		while ( ( element = element.getParent() ) ) {
			if ( element.equals( root ) )
				break;

			if ( element.getAttribute( 'data-nostyle' ) )
				unstylable = element;
			else if ( !editable ) {
				var contentEditable = element.getAttribute( 'contentEditable' );

				if ( contentEditable == 'false' )
					unstylable = element;
				else if ( contentEditable == 'true' )
					editable = 1;
			}
		}

		return unstylable;
	}

	function applyInlineStyle( range ) {
		var document = range.document;

		if ( range.collapsed ) {
			// Create the element to be inserted in the DOM.
			var collapsedElement = getElement( this, document );

			// Insert the empty element into the DOM at the range position.
			range.insertNode( collapsedElement );

			// Place the selection right inside the empty element.
			range.moveToPosition( collapsedElement, CKEDITOR.POSITION_BEFORE_END );

			return;
		}

		var elementName = this.element;
		var def = this._.definition;
		var isUnknownElement;

		// Indicates that fully selected read-only elements are to be included in the styling range.
		var ignoreReadonly = def.ignoreReadonly,
			includeReadonly = ignoreReadonly || def.includeReadonly;

		// If the read-only inclusion is not available in the definition, try
		// to get it from the root data (most often it's the editable).
		if ( includeReadonly == undefined )
			includeReadonly = range.root.getCustomData( 'cke_includeReadonly' );

		// Get the DTD definition for the element. Defaults to "span".
		var dtd = CKEDITOR.dtd[ elementName ] || ( isUnknownElement = true, CKEDITOR.dtd.span );

		// Expand the range.
		range.enlarge( CKEDITOR.ENLARGE_INLINE, 1 );
		range.trim();

		// Get the first node to be processed and the last, which concludes the
		// processing.
		var boundaryNodes = range.createBookmark(),
			firstNode = boundaryNodes.startNode,
			lastNode = boundaryNodes.endNode;

		var currentNode = firstNode;

		var styleRange;

		if ( !ignoreReadonly ) {
			// Check if the boundaries are inside non stylable elements.
			var root = range.getCommonAncestor(),
				firstUnstylable = getUnstylableParent( firstNode, root ),
				lastUnstylable = getUnstylableParent( lastNode, root );

			// If the first element can't be styled, we'll start processing right
			// after its unstylable root.
			if ( firstUnstylable )
				currentNode = firstUnstylable.getNextSourceNode( true );

			// If the last element can't be styled, we'll stop processing on its
			// unstylable root.
			if ( lastUnstylable )
				lastNode = lastUnstylable;
		}

		// Do nothing if the current node now follows the last node to be processed.
		if ( currentNode.getPosition( lastNode ) == CKEDITOR.POSITION_FOLLOWING )
			currentNode = 0;

		while ( currentNode ) {
			var applyStyle = false;

			if ( currentNode.equals( lastNode ) ) {
				currentNode = null;
				applyStyle = true;
			} else {
				var nodeType = currentNode.type;
				var nodeName = nodeType == CKEDITOR.NODE_ELEMENT ? currentNode.getName() : null;
				var nodeIsReadonly = nodeName && ( currentNode.getAttribute( 'contentEditable' ) == 'false' );
				var nodeIsNoStyle = nodeName && currentNode.getAttribute( 'data-nostyle' );

				if ( nodeName && currentNode.data( 'cke-bookmark' ) ) {
					currentNode = currentNode.getNextSourceNode( true );
					continue;
				}

				// Check if the current node can be a child of the style element.
				if ( !nodeName ||
				     ( dtd[ nodeName ] && !nodeIsNoStyle &&
				       ( !nodeIsReadonly || includeReadonly ) &&
				       ( currentNode.getPosition( lastNode ) |
				         CKEDITOR.POSITION_PRECEDING | CKEDITOR.POSITION_IDENTICAL |
				         CKEDITOR.POSITION_IS_CONTAINED ) ==
				       ( CKEDITOR.POSITION_PRECEDING + CKEDITOR.POSITION_IDENTICAL +
				         CKEDITOR.POSITION_IS_CONTAINED ) &&
				       ( !def.childRule || def.childRule( currentNode ) ) ) ) {
					var currentParent = currentNode.getParent();

					// Check if the style element can be a child of the current
					// node parent or if the element is not defined in the DTD.
					if ( currentParent &&
					     ( ( currentParent.getDtd() ||
					         CKEDITOR.dtd.span )[ elementName ] || isUnknownElement ) &&
					     ( !def.parentRule || def.parentRule( currentParent ) ) ) {
						// This node will be part of our range, so if it has not
						// been started, place its start right before the node.
						// In the case of an element node, it will be included
						// only if it is entirely inside the range.
						if ( !styleRange &&
						     ( !nodeName || !CKEDITOR.dtd.$removeEmpty[ nodeName ] ||
						       ( currentNode.getPosition( lastNode ) |
						         CKEDITOR.POSITION_PRECEDING | CKEDITOR.POSITION_IDENTICAL |
						         CKEDITOR.POSITION_IS_CONTAINED ) ==
						       ( CKEDITOR.POSITION_PRECEDING + CKEDITOR.POSITION_IDENTICAL +
						         CKEDITOR.POSITION_IS_CONTAINED ) ) ) {
							styleRange = range.clone();
							styleRange.setStartBefore( currentNode );
						}

						// Non element nodes, readonly elements, or empty
						// elements can be added completely to the range.
						if ( nodeType == CKEDITOR.NODE_TEXT || nodeIsReadonly ||
						     ( nodeType == CKEDITOR.NODE_ELEMENT &&
						       !currentNode.getChildCount() ) ) {
							var includedNode = currentNode;
							var parentNode;

							// This node is about to be included completelly, but,
							// if this is the last node in its parent, we must also
							// check if the parent itself can be added completelly
							// to the range, otherwise apply the style immediately.
							while ( ( applyStyle = !includedNode.getNext( notBookmark ) ) &&
							        ( parentNode = includedNode.getParent(), dtd[ parentNode.getName() ] ) &&
							        ( parentNode.getPosition( firstNode ) |
							          CKEDITOR.POSITION_FOLLOWING |
							          CKEDITOR.POSITION_IDENTICAL |
							          CKEDITOR.POSITION_IS_CONTAINED ) ==
							        ( CKEDITOR.POSITION_FOLLOWING +
							          CKEDITOR.POSITION_IDENTICAL +
							          CKEDITOR.POSITION_IS_CONTAINED ) &&
							        ( !def.childRule || def.childRule( parentNode ) ) ) {
								includedNode = parentNode;
							}

							styleRange.setEndAfter( includedNode );

						}
					} else
						applyStyle = true;
				} else
					applyStyle = true;

				// Get the next node to be processed.
				currentNode = currentNode.getNextSourceNode( nodeIsNoStyle || nodeIsReadonly && !includeReadonly );
			}

			// Apply the style if we have something to which apply it.
			if ( applyStyle && styleRange && !styleRange.collapsed ) {
				// Build the style element, based on the style object definition.
				var styleNode = getElement( this, document ),
					styleHasAttrs = styleNode.hasAttributes();

				// Get the element that holds the entire range.
				var parent = styleRange.getCommonAncestor();

				var removeList = {
					styles: {},
					attrs: {},
					// Styles cannot be removed.
					blockedStyles: {},
					// Attrs cannot be removed.
					blockedAttrs: {}
				};

				var attName, styleName, value;

				// Loop through the parents, removing the redundant attributes
				// from the element to be applied.
				while ( styleNode && parent ) {
					if ( parent.getName() == elementName ) {
						for ( attName in def.attributes ) {
							if ( removeList.blockedAttrs[ attName ] || !( value = parent.getAttribute( styleName ) ) )
								continue;

							if ( styleNode.getAttribute( attName ) == value )
								removeList.attrs[ attName ] = 1;
							else
								removeList.blockedAttrs[ attName ] = 1;
						}

						for ( styleName in def.styles ) {
							if ( removeList.blockedStyles[ styleName ] || !( value = parent.getStyle( styleName ) ) )
								continue;

							if ( styleNode.getStyle( styleName ) == value )
								removeList.styles[ styleName ] = 1;
							else
								removeList.blockedStyles[ styleName ] = 1;
						}
					}

					parent = parent.getParent();
				}

				for ( attName in removeList.attrs )
					styleNode.removeAttribute( attName );

				for ( styleName in removeList.styles )
					styleNode.removeStyle( styleName );

				if ( styleHasAttrs && !styleNode.hasAttributes() )
					styleNode = null;

				if ( styleNode ) {
					// Move the contents of the range to the style element.
					styleRange.extractContents().appendTo( styleNode );

					// Here we do some cleanup, removing all duplicated
					// elements from the style element.
					removeFromInsideElement.call( this, styleNode );

					// Insert it into the range position (it is collapsed after
					// extractContents.
					styleRange.insertNode( styleNode );

					// Let's merge our new style with its neighbors, if possible.
					styleNode.mergeSiblings();

					// As the style system breaks text nodes constantly, let's normalize
					// things for performance.
					// With IE, some paragraphs get broken when calling normalize()
					// repeatedly. Also, for IE, we must normalize body, not documentElement.
					// IE is also known for having a "crash effect" with normalize().
					// We should try to normalize with IE too in some way, somewhere.
					if ( !CKEDITOR.env.ie )
						styleNode.$.normalize();
				}
				// Style already inherit from parents, left just to clear up any internal overrides. (#5931)
				else {
					styleNode = new CKEDITOR.dom.element( 'span' );
					styleRange.extractContents().appendTo( styleNode );
					styleRange.insertNode( styleNode );
					removeFromInsideElement.call( this, styleNode );
					styleNode.remove( true );
				}

				// Style applied, let's release the range, so it gets
				// re-initialization in the next loop.
				styleRange = null;
			}
		}

		// Remove the bookmark nodes.
		range.moveToBookmark( boundaryNodes );

		// Minimize the result range to exclude empty text nodes. (#5374)
		range.shrink( CKEDITOR.SHRINK_TEXT );
	}

	function removeInlineStyle( range ) {
		// Make sure our range has included all "collpased" parent inline nodes so
		// that our operation logic can be simpler.
		range.enlarge( CKEDITOR.ENLARGE_INLINE, 1 );

		var bookmark = range.createBookmark(),
			startNode = bookmark.startNode;

		if ( range.collapsed ) {
			var startPath = new CKEDITOR.dom.elementPath( startNode.getParent(), range.root ),
				// The topmost element in elementspatch which we should jump out of.
				boundaryElement;


			for ( var i = 0, element; i < startPath.elements.length && ( element = startPath.elements[ i ] ); i++ ) {
				// 1. If it's collaped inside text nodes, try to remove the style from the whole element.
				//
				// 2. Otherwise if it's collapsed on element boundaries, moving the selection
				//  outside the styles instead of removing the whole tag,
				//  also make sure other inner styles were well preserverd.(#3309)
				if ( element == startPath.block || element == startPath.blockLimit )
					break;

				if ( this.checkElementRemovable( element ) ) {
					var isStart;

					if ( range.collapsed && ( range.checkBoundaryOfElement( element, CKEDITOR.END ) || ( isStart = range.checkBoundaryOfElement( element, CKEDITOR.START ) ) ) ) {
						boundaryElement = element;
						boundaryElement.match = isStart ? 'start' : 'end';
					} else {
						/*
						 * Before removing the style node, there may be a sibling to the style node
						 * that's exactly the same to the one to be removed. To the user, it makes
						 * no difference that they're separate entities in the DOM tree. So, merge
						 * them before removal.
						 */
						element.mergeSiblings();
						if ( element.getName() == this.element )
							removeFromElement.call( this, element );
						else
							removeOverrides( element, getOverrides( this )[ element.getName() ] );
					}
				}
			}

			// Re-create the style tree after/before the boundary element,
			// the replication start from bookmark start node to define the
			// new range.
			if ( boundaryElement ) {
				var clonedElement = startNode;
				for ( i = 0;; i++ ) {
					var newElement = startPath.elements[ i ];
					if ( newElement.equals( boundaryElement ) )
						break;
					// Avoid copying any matched element.
					else if ( newElement.match )
						continue;
					else
						newElement = newElement.clone();
					newElement.append( clonedElement );
					clonedElement = newElement;
				}
				clonedElement[ boundaryElement.match == 'start' ? 'insertBefore' : 'insertAfter' ]( boundaryElement );
			}
		} else {
			// Now our range isn't collapsed. Lets walk from the start node to the end
			// node via DFS and remove the styles one-by-one.
			var endNode = bookmark.endNode,
				me = this;

			// Find out the style ancestor that needs to be broken down at startNode
			// and endNode.
			function breakNodes() {
				var startPath = new CKEDITOR.dom.elementPath( startNode.getParent() ),
					endPath = new CKEDITOR.dom.elementPath( endNode.getParent() ),
					breakStart = null,
					breakEnd = null;
				for ( var i = 0; i < startPath.elements.length; i++ ) {
					var element = startPath.elements[ i ];

					if ( element == startPath.block || element == startPath.blockLimit )
						break;

					if ( me.checkElementRemovable( element ) )
						breakStart = element;
				}
				for ( i = 0; i < endPath.elements.length; i++ ) {
					element = endPath.elements[ i ];

					if ( element == endPath.block || element == endPath.blockLimit )
						break;

					if ( me.checkElementRemovable( element ) )
						breakEnd = element;
				}

				if ( breakEnd )
					endNode.breakParent( breakEnd );
				if ( breakStart )
					startNode.breakParent( breakStart );
			}
			breakNodes();

			// Now, do the DFS walk.
			var currentNode = startNode;
			while ( !currentNode.equals( endNode ) ) {
				// Need to get the next node first because removeFromElement() can remove
				// the current node from DOM tree.
				var nextNode = currentNode.getNextSourceNode();
				if ( currentNode.type == CKEDITOR.NODE_ELEMENT && this.checkElementRemovable( currentNode ) ) {
					// Remove style from element or overriding element.
					if ( currentNode.getName() == this.element )
						removeFromElement.call( this, currentNode );
					else
						removeOverrides( currentNode, getOverrides( this )[ currentNode.getName() ] );

					// removeFromElement() may have merged the next node with something before
					// the startNode via mergeSiblings(). In that case, the nextNode would
					// contain startNode and we'll have to call breakNodes() again and also
					// reassign the nextNode to something after startNode.
					if ( nextNode.type == CKEDITOR.NODE_ELEMENT && nextNode.contains( startNode ) ) {
						breakNodes();
						nextNode = startNode.getNext();
					}
				}
				currentNode = nextNode;
			}
		}

		range.moveToBookmark( bookmark );
	}

	function applyObjectStyle( range ) {
		// Selected or parent element. (#9651)
		var start = range.getEnclosedNode() || range.getCommonAncestor( false, true ),
			element = new CKEDITOR.dom.elementPath( start, range.root ).contains( this.element, 1 );

		element && !element.isReadOnly() && setupElement( element, this );
	}

	function removeObjectStyle( range ) {
		var parent = range.getCommonAncestor( true, true ),
			element = new CKEDITOR.dom.elementPath( parent, range.root ).contains( this.element, 1 );

		if ( !element )
			return;

		var style = this,
			def = style._.definition,
			attributes = def.attributes;

		// Remove all defined attributes.
		if ( attributes ) {
			for ( var att in attributes ) {
				element.removeAttribute( att, attributes[ att ] );
			}
		}

		// Assign all defined styles.
		if ( def.styles ) {
			for ( var i in def.styles ) {
				if ( !def.styles.hasOwnProperty( i ) )
					continue;

				element.removeStyle( i );
			}
		}
	}

	function applyBlockStyle( range ) {
		// Serializible bookmarks is needed here since
		// elements may be merged.
		var bookmark = range.createBookmark( true );

		var iterator = range.createIterator();
		iterator.enforceRealBlocks = true;

		// make recognize <br /> tag as a separator in ENTER_BR mode (#5121)
		if ( this._.enterMode )
			iterator.enlargeBr = ( this._.enterMode != CKEDITOR.ENTER_BR );

		var block;
		var doc = range.document;
		var previousPreBlock;

		while ( ( block = iterator.getNextParagraph() ) ) // Only one =
		{
			if ( !block.isReadOnly() ) {
				var newBlock = getElement( this, doc, block );
				replaceBlock( block, newBlock );
			}
		}

		range.moveToBookmark( bookmark );
	}

	function removeBlockStyle( range ) {
		// Serializible bookmarks is needed here since
		// elements may be merged.
		var bookmark = range.createBookmark( 1 );

		var iterator = range.createIterator();
		iterator.enforceRealBlocks = true;
		iterator.enlargeBr = this._.enterMode != CKEDITOR.ENTER_BR;

		var block;
		while ( ( block = iterator.getNextParagraph() ) ) {
			if ( this.checkElementRemovable( block ) ) {
				// <pre> get special treatment.
				if ( block.is( 'pre' ) ) {
					var newBlock = this._.enterMode == CKEDITOR.ENTER_BR ? null :
					               range.document.createElement( this._.enterMode == CKEDITOR.ENTER_P ? 'p' : 'div' );

					newBlock && block.copyAttributes( newBlock );
					replaceBlock( block, newBlock );
				} else
					removeFromElement.call( this, block );
			}
		}

		range.moveToBookmark( bookmark );
	}

	// Replace the original block with new one, with special treatment
	// for <pre> blocks to make sure content format is well preserved, and merging/splitting adjacent
	// when necessary. (#3188)
	function replaceBlock( block, newBlock ) {
		// Block is to be removed, create a temp element to
		// save contents.
		var removeBlock = !newBlock;
		if ( removeBlock ) {
			newBlock = block.getDocument().createElement( 'div' );
			block.copyAttributes( newBlock );
		}

		var newBlockIsPre = newBlock && newBlock.is( 'pre' );
		var blockIsPre = block.is( 'pre' );

		var isToPre = newBlockIsPre && !blockIsPre;
		var isFromPre = !newBlockIsPre && blockIsPre;

		if ( isToPre )
			newBlock = toPre( block, newBlock );
		else if ( isFromPre )
			// Split big <pre> into pieces before start to convert.
			newBlock = fromPres( removeBlock ? [ block.getHtml() ] : splitIntoPres( block ), newBlock );
		else
			block.moveChildren( newBlock );

		newBlock.replace( block );

		if ( newBlockIsPre ) {
			// Merge previous <pre> blocks.
			mergePre( newBlock );
		} else if ( removeBlock )
			removeNoAttribsElement( newBlock );
	}

	// Merge a <pre> block with a previous sibling if available.
	function mergePre( preBlock ) {
		var previousBlock;
		if ( !( ( previousBlock = preBlock.getPrevious( nonWhitespaces ) ) && previousBlock.is && previousBlock.is( 'pre' ) ) )
			return;

		// Merge the previous <pre> block contents into the current <pre>
		// block.
		//
		// Another thing to be careful here is that currentBlock might contain
		// a '\n' at the beginning, and previousBlock might contain a '\n'
		// towards the end. These new lines are not normally displayed but they
		// become visible after merging.
		var mergedHtml = replace( previousBlock.getHtml(), /\n$/, '' ) + '\n\n' +
			replace( preBlock.getHtml(), /^\n/, '' );

		// Krugle: IE normalizes innerHTML from <pre>, breaking whitespaces.
		if ( CKEDITOR.env.ie )
			preBlock.$.outerHTML = '<pre>' + mergedHtml + '</pre>';
		else
			preBlock.setHtml( mergedHtml );

		previousBlock.remove();
	}

	// Split into multiple <pre> blocks separated by double line-break.
	function splitIntoPres( preBlock ) {
		// Exclude the ones at header OR at tail,
		// and ignore bookmark content between them.
		var duoBrRegex = /(\S\s*)\n(?:\s|(<span[^>]+data-cke-bookmark.*?\/span>))*\n(?!$)/gi,
			blockName = preBlock.getName(),
			splitedHtml = replace( preBlock.getOuterHtml(), duoBrRegex, function( match, charBefore, bookmark ) {
				return charBefore + '</pre>' + bookmark + '<pre>';
			});

		var pres = [];
		splitedHtml.replace( /<pre\b.*?>([\s\S]*?)<\/pre>/gi, function( match, preContent ) {
			pres.push( preContent );
		});
		return pres;
	}

	// Wrapper function of String::replace without considering of head/tail bookmarks nodes.
	function replace( str, regexp, replacement ) {
		var headBookmark = '',
			tailBookmark = '';

		str = str.replace( /(^<span[^>]+data-cke-bookmark.*?\/span>)|(<span[^>]+data-cke-bookmark.*?\/span>$)/gi, function( str, m1, m2 ) {
			m1 && ( headBookmark = m1 );
			m2 && ( tailBookmark = m2 );
			return '';
		});
		return headBookmark + str.replace( regexp, replacement ) + tailBookmark;
	}

	// Converting a list of <pre> into blocks with format well preserved.
	function fromPres( preHtmls, newBlock ) {
		var docFrag;
		if ( preHtmls.length > 1 )
			docFrag = new CKEDITOR.dom.documentFragment( newBlock.getDocument() );

		for ( var i = 0; i < preHtmls.length; i++ ) {
			var blockHtml = preHtmls[ i ];

			// 1. Trim the first and last line-breaks immediately after and before <pre>,
			// they're not visible.
			blockHtml = blockHtml.replace( /(\r\n|\r)/g, '\n' );
			blockHtml = replace( blockHtml, /^[ \t]*\n/, '' );
			blockHtml = replace( blockHtml, /\n$/, '' );
			// 2. Convert spaces or tabs at the beginning or at the end to &nbsp;
			blockHtml = replace( blockHtml, /^[ \t]+|[ \t]+$/g, function( match, offset, s ) {
				if ( match.length == 1 ) // one space, preserve it
				return '&nbsp;';
				else if ( !offset ) // beginning of block
				return CKEDITOR.tools.repeat( '&nbsp;', match.length - 1 ) + ' ';
				else // end of block
				return ' ' + CKEDITOR.tools.repeat( '&nbsp;', match.length - 1 );
			});

			// 3. Convert \n to <BR>.
			// 4. Convert contiguous (i.e. non-singular) spaces or tabs to &nbsp;
			blockHtml = blockHtml.replace( /\n/g, '<br>' );
			blockHtml = blockHtml.replace( /[ \t]{2,}/g, function( match ) {
				return CKEDITOR.tools.repeat( '&nbsp;', match.length - 1 ) + ' ';
			});

			if ( docFrag ) {
				var newBlockClone = newBlock.clone();
				newBlockClone.setHtml( blockHtml );
				docFrag.append( newBlockClone );
			} else
				newBlock.setHtml( blockHtml );
		}

		return docFrag || newBlock;
	}

	// Converting from a non-PRE block to a PRE block in formatting operations.
	function toPre( block, newBlock ) {
		var bogus = block.getBogus();
		bogus && bogus.remove();

		// First trim the block content.
		var preHtml = block.getHtml();

		// 1. Trim head/tail spaces, they're not visible.
		preHtml = replace( preHtml, /(?:^[ \t\n\r]+)|(?:[ \t\n\r]+$)/g, '' );
		// 2. Delete ANSI whitespaces immediately before and after <BR> because
		//    they are not visible.
		preHtml = preHtml.replace( /[ \t\r\n]*(<br[^>]*>)[ \t\r\n]*/gi, '$1' );
		// 3. Compress other ANSI whitespaces since they're only visible as one
		//    single space previously.
		// 4. Convert &nbsp; to spaces since &nbsp; is no longer needed in <PRE>.
		preHtml = preHtml.replace( /([ \t\n\r]+|&nbsp;)/g, ' ' );
		// 5. Convert any <BR /> to \n. This must not be done earlier because
		//    the \n would then get compressed.
		preHtml = preHtml.replace( /<br\b[^>]*>/gi, '\n' );

		// Krugle: IE normalizes innerHTML to <pre>, breaking whitespaces.
		if ( CKEDITOR.env.ie ) {
			var temp = block.getDocument().createElement( 'div' );
			temp.append( newBlock );
			newBlock.$.outerHTML = '<pre>' + preHtml + '</pre>';
			newBlock.copyAttributes( temp.getFirst() );
			newBlock = temp.getFirst().remove();
		} else
			newBlock.setHtml( preHtml );

		return newBlock;
	}

	// Removes a style from an element itself, don't care about its subtree.
	function removeFromElement( element ) {
		var def = this._.definition,
			attributes = def.attributes,
			styles = def.styles,
			overrides = getOverrides( this )[ element.getName() ],
			// If the style is only about the element itself, we have to remove the element.
			removeEmpty = CKEDITOR.tools.isEmpty( attributes ) && CKEDITOR.tools.isEmpty( styles );

		// Remove definition attributes/style from the elemnt.
		for ( var attName in attributes ) {
			// The 'class' element value must match (#1318).
			if ( ( attName == 'class' || this._.definition.fullMatch ) && element.getAttribute( attName ) != normalizeProperty( attName, attributes[ attName ] ) )
				continue;
			removeEmpty = element.hasAttribute( attName );
			element.removeAttribute( attName );
		}

		for ( var styleName in styles ) {
			// Full match style insist on having fully equivalence. (#5018)
			if ( this._.definition.fullMatch && element.getStyle( styleName ) != normalizeProperty( styleName, styles[ styleName ], true ) )
				continue;

			removeEmpty = removeEmpty || !!element.getStyle( styleName );
			element.removeStyle( styleName );
		}

		// Remove overrides, but don't remove the element if it's a block element
		removeOverrides( element, overrides, blockElements[ element.getName() ] );

		if ( removeEmpty ) {
			if ( this._.definition.alwaysRemoveElement )
				removeNoAttribsElement( element, 1 );
			else {
				!CKEDITOR.dtd.$block[ element.getName() ] || this._.enterMode == CKEDITOR.ENTER_BR && !element.hasAttributes() ? removeNoAttribsElement( element ) : element.renameNode( this._.enterMode == CKEDITOR.ENTER_P ? 'p' : 'div' );
			}
		}
	}

	// Removes a style from inside an element.
	function removeFromInsideElement( element ) {
		var def = this._.definition,
			attribs = def.attributes,
			styles = def.styles,
			overrides = getOverrides( this ),
			innerElements = element.getElementsByTag( this.element );

		for ( var i = innerElements.count(); --i >= 0; )
			removeFromElement.call( this, innerElements.getItem( i ) );

		// Now remove any other element with different name that is
		// defined to be overriden.
		for ( var overrideElement in overrides ) {
			if ( overrideElement != this.element ) {
				innerElements = element.getElementsByTag( overrideElement );
				for ( i = innerElements.count() - 1; i >= 0; i-- ) {
					var innerElement = innerElements.getItem( i );
					removeOverrides( innerElement, overrides[ overrideElement ] );
				}
			}
		}
	}

	// Remove overriding styles/attributes from the specific element.
	// Note: Remove the element if no attributes remain.
	// @param {Object} element
	// @param {Object} overrides
	// @param {Boolean} Don't remove the element
	function removeOverrides( element, overrides, dontRemove ) {
		var attributes = overrides && overrides.attributes;

		if ( attributes ) {
			for ( var i = 0; i < attributes.length; i++ ) {
				var attName = attributes[ i ][ 0 ],
					actualAttrValue;

				if ( ( actualAttrValue = element.getAttribute( attName ) ) ) {
					var attValue = attributes[ i ][ 1 ];

					// Remove the attribute if:
					//    - The override definition value is null ;
					//    - The override definition valie is a string that
					//      matches the attribute value exactly.
					//    - The override definition value is a regex that
					//      has matches in the attribute value.
					if ( attValue === null || ( attValue.test && attValue.test( actualAttrValue ) ) || ( typeof attValue == 'string' && actualAttrValue == attValue ) )
						element.removeAttribute( attName );
				}
			}
		}

		if ( !dontRemove )
			removeNoAttribsElement( element );
	}

	// If the element has no more attributes, remove it.
	function removeNoAttribsElement( element, forceRemove ) {
		// If no more attributes remained in the element, remove it,
		// leaving its children.
		if ( !element.hasAttributes() || forceRemove ) {
			if ( CKEDITOR.dtd.$block[ element.getName() ] ) {
				var previous = element.getPrevious( nonWhitespaces ),
					next = element.getNext( nonWhitespaces );

				if ( previous && ( previous.type == CKEDITOR.NODE_TEXT || !previous.isBlockBoundary( { br:1 } ) ) )
					element.append( 'br', 1 );
				if ( next && ( next.type == CKEDITOR.NODE_TEXT || !next.isBlockBoundary( { br:1 } ) ) )
					element.append( 'br' );

				element.remove( true );
			} else {
				// Removing elements may open points where merging is possible,
				// so let's cache the first and last nodes for later checking.
				var firstChild = element.getFirst();
				var lastChild = element.getLast();

				element.remove( true );

				if ( firstChild ) {
					// Check the cached nodes for merging.
					firstChild.type == CKEDITOR.NODE_ELEMENT && firstChild.mergeSiblings();

					if ( lastChild && !firstChild.equals( lastChild ) && lastChild.type == CKEDITOR.NODE_ELEMENT )
						lastChild.mergeSiblings();
				}

			}
		}
	}

	function getElement( style, targetDocument, element ) {
		var el,
			def = style._.definition,
			elementName = style.element;

		// The "*" element name will always be a span for this function.
		if ( elementName == '*' )
			elementName = 'span';

		// Create the element.
		el = new CKEDITOR.dom.element( elementName, targetDocument );

		// #6226: attributes should be copied before the new ones are applied
		if ( element )
			element.copyAttributes( el );

		el = setupElement( el, style );

		// Avoid ID duplication.
		if ( targetDocument.getCustomData( 'doc_processing_style' ) && el.hasAttribute( 'id' ) )
			el.removeAttribute( 'id' );
		else
			targetDocument.setCustomData( 'doc_processing_style', 1 );

		return el;
	}

	function setupElement( el, style ) {
		var def = style._.definition,
			attributes = def.attributes,
			styles = CKEDITOR.style.getStyleText( def );

		// Assign all defined attributes.
		if ( attributes ) {
			for ( var att in attributes ) {
				el.setAttribute( att, attributes[ att ] );
			}
		}

		// Assign all defined styles.
		if ( styles )
			el.setAttribute( 'style', styles );

		return el;
	}

	function replaceVariables( list, variablesValues ) {
		for ( var item in list ) {
			list[ item ] = list[ item ].replace( varRegex, function( match, varName ) {
				return variablesValues[ varName ];
			});
		}
	}

	// Returns an object that can be used for style matching comparison.
	// Attributes names and values are all lowercased, and the styles get
	// merged with the style attribute.
	function getAttributesForComparison( styleDefinition ) {
		// If we have already computed it, just return it.
		var attribs = styleDefinition._AC;
		if ( attribs )
			return attribs;

		attribs = {};

		var length = 0;

		// Loop through all defined attributes.
		var styleAttribs = styleDefinition.attributes;
		if ( styleAttribs ) {
			for ( var styleAtt in styleAttribs ) {
				length++;
				attribs[ styleAtt ] = styleAttribs[ styleAtt ];
			}
		}

		// Includes the style definitions.
		var styleText = CKEDITOR.style.getStyleText( styleDefinition );
		if ( styleText ) {
			if ( !attribs[ 'style' ] )
				length++;
			attribs[ 'style' ] = styleText;
		}

		// Appends the "length" information to the object.
		attribs._length = length;

		// Return it, saving it to the next request.
		return ( styleDefinition._AC = attribs );
	}

	// Get the the collection used to compare the elements and attributes,
	// defined in this style overrides, with other element. All information in
	// it is lowercased.
	// @param {CKEDITOR.style} style
	function getOverrides( style ) {
		if ( style._.overrides )
			return style._.overrides;

		var overrides = ( style._.overrides = {} ),
			definition = style._.definition.overrides;

		if ( definition ) {
			// The override description can be a string, object or array.
			// Internally, well handle arrays only, so transform it if needed.
			if ( !CKEDITOR.tools.isArray( definition ) )
				definition = [ definition ];

			// Loop through all override definitions.
			for ( var i = 0; i < definition.length; i++ ) {
				var override = definition[ i ];
				var elementName;
				var overrideEl;
				var attrs;

				// If can be a string with the element name.
				if ( typeof override == 'string' )
					elementName = override.toLowerCase();
				// Or an object.
				else {
					elementName = override.element ? override.element.toLowerCase() : style.element;
					attrs = override.attributes;
				}

				// We can have more than one override definition for the same
				// element name, so we attempt to simply append information to
				// it if it already exists.
				overrideEl = overrides[ elementName ] || ( overrides[ elementName ] = {} );

				if ( attrs ) {
					// The returning attributes list is an array, because we
					// could have different override definitions for the same
					// attribute name.
					var overrideAttrs = ( overrideEl.attributes = overrideEl.attributes || new Array() );
					for ( var attName in attrs ) {
						// Each item in the attributes array is also an array,
						// where [0] is the attribute name and [1] is the
						// override value.
						overrideAttrs.push( [ attName.toLowerCase(), attrs[ attName ] ] );
					}
				}
			}
		}

		return overrides;
	}

	// Make the comparison of attribute value easier by standardizing it.
	function normalizeProperty( name, value, isStyle ) {
		var temp = new CKEDITOR.dom.element( 'span' );
		temp[ isStyle ? 'setStyle' : 'setAttribute' ]( name, value );
		return temp[ isStyle ? 'getStyle' : 'getAttribute' ]( name );
	}

	// Compare two bunch of styles, with the speciality that value 'inherit'
	// is treated as a wildcard which will match any value.
	// @param {Object/String} source
	// @param {Object/String} target
	function compareCssText( source, target ) {
		typeof source == 'string' && ( source = CKEDITOR.tools.parseCssText( source ) );
		typeof target == 'string' && ( target = CKEDITOR.tools.parseCssText( target, true ) );
		for ( var name in source ) {
			if ( !( name in target && ( target[ name ] == source[ name ] || source[ name ] == 'inherit' || target[ name ] == 'inherit' ) ) ) {
				return false;
			}
		}
		return true;
	}

	function applyStyleOnSelection( selection, remove ) {
		var doc = selection.document,
			ranges = selection.getRanges(),
			func = remove ? this.removeFromRange : this.applyToRange,
			range;

		var iterator = ranges.createIterator();
		while ( ( range = iterator.getNextRange() ) )
			func.call( this, range );

		selection.selectRanges( ranges );
		doc.removeCustomData( 'doc_processing_style' );
	}
})();

/**
 * Generic style command. It applies a specific style when executed.
 *
 *		var boldStyle = new CKEDITOR.style( { element: 'strong' } );
 *		// Register the "bold" command, which applies the bold style.
 *		editor.addCommand( 'bold', new CKEDITOR.dialogCommand( boldStyle ) );
 *
 * @class
 * @constructor Creates a styleCommand class instance.
 * @extends CKEDITOR.commandDefinition
 * @param {CKEDITOR.style} style The style to be applied when command is executed.
 * @param {Object} [ext] Additional command definition's properties.
 */
CKEDITOR.styleCommand = function( style, ext ) {
	this.style = style;
	this.allowedContent = style;
	this.requiredContent = style;

	CKEDITOR.tools.extend( this, ext, true );
};

/**
 * @param {CKEDITOR.editor} editor
 * @todo
 */
CKEDITOR.styleCommand.prototype.exec = function( editor ) {
	editor.focus();

	if ( this.state == CKEDITOR.TRISTATE_OFF )
		editor.applyStyle( this.style );
	else if ( this.state == CKEDITOR.TRISTATE_ON )
		editor.removeStyle( this.style );
};

/**
 * Manages styles registration and loading. See also {@link CKEDITOR.config#stylesSet}.
 *
 *		// The set of styles for the <b>Styles</b> combo.
 *		CKEDITOR.stylesSet.add( 'default', [
 *			// Block Styles
 *			{ name: 'Blue Title',		element: 'h3',		styles: { 'color': 'Blue' } },
 *			{ name: 'Red Title',		element: 'h3',		styles: { 'color': 'Red' } },
 *
 *			// Inline Styles
 *			{ name: 'Marker: Yellow',	element: 'span',	styles: { 'background-color': 'Yellow' } },
 *			{ name: 'Marker: Green',	element: 'span',	styles: { 'background-color': 'Lime' } },
 *
 *			// Object Styles
 *			{
 *				name: 'Image on Left',
 *				element: 'img',
 *				attributes: {
 *					style: 'padding: 5px; margin-right: 5px',
 *					border: '2',
 *					align: 'left'
 *				}
 *			}
 *		] );
 *
 * @since 3.2
 * @class
 * @singleton
 * @extends CKEDITOR.resourceManager
 */
CKEDITOR.stylesSet = new CKEDITOR.resourceManager( '', 'stylesSet' );

// Backward compatibility (#5025).
CKEDITOR.addStylesSet = CKEDITOR.tools.bind( CKEDITOR.stylesSet.add, CKEDITOR.stylesSet );
CKEDITOR.loadStylesSet = function( name, url, callback ) {
	CKEDITOR.stylesSet.addExternal( name, url, '' );
	CKEDITOR.stylesSet.load( name, callback );
};


/**
 * Gets the current styleSet for this instance.
 *
 *		editor.getStylesSet( function( stylesDefinitions ) {} );
 *
 * See also {@link CKEDITOR.editor#stylesSet} event.
 *
 * @param {Function} callback The function to be called with the styles data.
 * @member CKEDITOR.editor
 */
CKEDITOR.editor.prototype.getStylesSet = function( callback ) {
	if ( !this._.stylesDefinitions ) {
		var editor = this,
			// Respect the backwards compatible definition entry
			configStyleSet = editor.config.stylesCombo_stylesSet || editor.config.stylesSet;

		// The false value means that none styles should be loaded.
		if ( configStyleSet === false ) {
			callback( null );
			return;
		}

		// #5352 Allow to define the styles directly in the config object
		if ( configStyleSet instanceof Array ) {
			editor._.stylesDefinitions = configStyleSet;
			callback( configStyleSet );
			return;
		}

		// Default value is 'default'.
		if ( !configStyleSet )
			configStyleSet = 'default';

		var partsStylesSet = configStyleSet.split( ':' ),
			styleSetName = partsStylesSet[ 0 ],
			externalPath = partsStylesSet[ 1 ];

		CKEDITOR.stylesSet.addExternal( styleSetName, externalPath ? partsStylesSet.slice( 1 ).join( ':' ) : CKEDITOR.getUrl( 'styles.js' ), '' );

		CKEDITOR.stylesSet.load( styleSetName, function( stylesSet ) {
			editor._.stylesDefinitions = stylesSet[ styleSetName ];
			callback( editor._.stylesDefinitions );
		});
	} else
		callback( this._.stylesDefinitions );
};

/**
 * Indicates that fully selected read-only elements will be included when
 * applying the style (for inline styles only).
 *
 * @since 3.5
 * @property {Boolean} [includeReadonly=false]
 * @member CKEDITOR.style
 */

/**
 * Indicates that any matches element of this style will be eventually removed
 * when calling {@link CKEDITOR.editor#removeStyle}.
 *
 * @since 4.0
 * @property {Boolean} [alwaysRemoveElement=false]
 * @member CKEDITOR.style
 */

/**
 * Disables inline styling on read-only elements.
 *
 * @since 3.5
 * @cfg {Boolean} [disableReadonlyStyling=false]
 * @member CKEDITOR.config
 */

/**
 * The "styles definition set" to use in the editor. They will be used in the
 * styles combo and the style selector of the div container.
 *
 * The styles may be defined in the page containing the editor, or can be
 * loaded on demand from an external file. In the second case, if this setting
 * contains only a name, the `styles.js` file will be loaded from the
 * CKEditor root folder (what ensures backward compatibility with CKEditor 4.0).
 *
 * Otherwise, this setting has the `name:url` syntax, making it
 * possible to set the URL from which loading the styles file.
 * Note that the `name` has to be equal to the name used in
 * {@link CKEDITOR.stylesSet#add} while registering styles set.
 *
 * **Note**: Since 4.1 it is possible to set `stylesSet` to `false`
 * to prevent loading any styles set.
 *
 *		// Do not load any file. Styles set is empty.
 *		config.stylesSet = false;
 *
 *		// Load the 'mystyles' styles set from styles.js file.
 *		config.stylesSet = 'mystyles';
 *
 *		// Load the 'mystyles' styles set from a relative URL.
 *		config.stylesSet = 'mystyles:/editorstyles/styles.js';
 *
 *		// Load from a full URL.
 *		config.stylesSet = 'mystyles:http://www.example.com/editorstyles/styles.js';
 *
 *		// Load from a list of definitions.
 *		config.stylesSet = [
 *			{ name: 'Strong Emphasis', element: 'strong' },
 *			{ name: 'Emphasis', element: 'em' },
 *			...
 *		];
 *
 * @since 3.3
 * @cfg {String/Array/Boolean} [stylesSet='default']
 * @member CKEDITOR.config
 */
