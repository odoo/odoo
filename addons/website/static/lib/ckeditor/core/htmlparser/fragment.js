/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

'use strict';

/**
 * A lightweight representation of an HTML DOM structure.
 *
 * @class
 * @constructor Creates a fragment class instance.
 */
CKEDITOR.htmlParser.fragment = function() {
	/**
	 * The nodes contained in the root of this fragment.
	 *
	 *		var fragment = CKEDITOR.htmlParser.fragment.fromHtml( '<b>Sample</b> Text' );
	 *		alert( fragment.children.length ); // 2
	 */
	this.children = [];

	/**
	 * Get the fragment parent. Should always be null.
	 *
	 * @property {Object} [=null]
	 */
	this.parent = null;

	/** @private */
	this._ = {
		isBlockLike: true,
		hasInlineStarted: false
	};
};

(function() {
	// Block-level elements whose internal structure should be respected during
	// parser fixing.
	var nonBreakingBlocks = CKEDITOR.tools.extend( { table:1,ul:1,ol:1,dl:1 }, CKEDITOR.dtd.table, CKEDITOR.dtd.ul, CKEDITOR.dtd.ol, CKEDITOR.dtd.dl );

	var listBlocks = { ol:1,ul:1 };

	// Dtd of the fragment element, basically it accept anything except for intermediate structure, e.g. orphan <li>.
	var rootDtd = CKEDITOR.tools.extend( {}, { html:1 }, CKEDITOR.dtd.html, CKEDITOR.dtd.body, CKEDITOR.dtd.head, { style:1,script:1 } );

	function isRemoveEmpty( node ) {
		// Empty link is to be removed when empty but not anchor. (#7894)
		return node.name == 'a' && node.attributes.href || CKEDITOR.dtd.$removeEmpty[ node.name ];
	}

	/**
	 * Creates a {@link CKEDITOR.htmlParser.fragment} from an HTML string.
	 *
	 *		var fragment = CKEDITOR.htmlParser.fragment.fromHtml( '<b>Sample</b> Text' );
	 *		alert( fragment.children[ 0 ].name );		// 'b'
	 *		alert( fragment.children[ 1 ].value );	// ' Text'
	 *
	 * @static
	 * @param {String} fragmentHtml The HTML to be parsed, filling the fragment.
	 * @param {CKEDITOR.htmlParser.element/String} [parent] Optional contextual
	 * element which makes the content been parsed as the content of this element and fix
	 * to match it.
	 * If not provided, then {@link CKEDITOR.htmlParser.fragment} will be used
	 * as the parent and it will be returned.
	 * @param {String/Boolean} [fixingBlock] When `parent` is a block limit element,
	 * and the param is a string value other than `false`, it is to
	 * avoid having block-less content as the direct children of parent by wrapping
	 * the content with a block element of the specified tag, e.g.
	 * when `fixingBlock` specified as `p`, the content `<body><i>foo</i></body>`
	 * will be fixed into `<body><p><i>foo</i></p></body>`.
	 * @returns {CKEDITOR.htmlParser.fragment/CKEDITOR.htmlParser.element} The created fragment or passed `parent`.
	 */
	CKEDITOR.htmlParser.fragment.fromHtml = function( fragmentHtml, parent, fixingBlock ) {
		var parser = new CKEDITOR.htmlParser();

		var root = parent instanceof CKEDITOR.htmlParser.element ? parent : typeof parent == 'string' ? new CKEDITOR.htmlParser.element( parent ) : new CKEDITOR.htmlParser.fragment();

		var pendingInline = [],
			pendingBRs = [],
			currentNode = root,
			// Indicate we're inside a <textarea> element, spaces should be touched differently.
			inTextarea = root.name == 'textarea',
			// Indicate we're inside a <pre> element, spaces should be touched differently.
			inPre = root.name == 'pre';

		function checkPending( newTagName ) {
			var pendingBRsSent;

			if ( pendingInline.length > 0 ) {
				for ( var i = 0; i < pendingInline.length; i++ ) {
					var pendingElement = pendingInline[ i ],
						pendingName = pendingElement.name,
						pendingDtd = CKEDITOR.dtd[ pendingName ],
						currentDtd = currentNode.name && CKEDITOR.dtd[ currentNode.name ];

					if ( ( !currentDtd || currentDtd[ pendingName ] ) && ( !newTagName || !pendingDtd || pendingDtd[ newTagName ] || !CKEDITOR.dtd[ newTagName ] ) ) {
						if ( !pendingBRsSent ) {
							sendPendingBRs();
							pendingBRsSent = 1;
						}

						// Get a clone for the pending element.
						pendingElement = pendingElement.clone();

						// Add it to the current node and make it the current,
						// so the new element will be added inside of it.
						pendingElement.parent = currentNode;
						currentNode = pendingElement;

						// Remove the pending element (back the index by one
						// to properly process the next entry).
						pendingInline.splice( i, 1 );
						i--;
					} else {
						// Some element of the same type cannot be nested, flat them,
						// e.g. <a href="#">foo<a href="#">bar</a></a>. (#7894)
						if ( pendingName == currentNode.name )
							addElement( currentNode, currentNode.parent, 1 ), i--;
					}
				}
			}
		}

		function sendPendingBRs() {
			while ( pendingBRs.length )
				addElement( pendingBRs.shift(), currentNode );
		}

		// Rtrim empty spaces on block end boundary. (#3585)
		function removeTailWhitespace( element ) {
			if ( element._.isBlockLike && element.name != 'pre' && element.name != 'textarea' ) {

				var length = element.children.length,
					lastChild = element.children[ length - 1 ],
					text;
				if ( lastChild && lastChild.type == CKEDITOR.NODE_TEXT ) {
					if ( !( text = CKEDITOR.tools.rtrim( lastChild.value ) ) )
						element.children.length = length - 1;
					else
						lastChild.value = text;
				}
			}
		}

		// Beside of simply append specified element to target, this function also takes
		// care of other dirty lifts like forcing block in body, trimming spaces at
		// the block boundaries etc.
		//
		// @param {Element} element  The element to be added as the last child of {@link target}.
		// @param {Element} target The parent element to relieve the new node.
		// @param {Boolean} [moveCurrent=false] Don't change the "currentNode" global unless
		// there's a return point node specified on the element, otherwise move current onto {@link target} node.
		//
		function addElement( element, target, moveCurrent ) {
			target = target || currentNode || root;

			// Current element might be mangled by fix body below,
			// save it for restore later.
			var savedCurrent = currentNode;

			// Ignore any element that has already been added.
			if ( element.previous === undefined ) {
				if ( checkAutoParagraphing( target, element ) ) {
					// Create a <p> in the fragment.
					currentNode = target;
					parser.onTagOpen( fixingBlock, {} );

					// The new target now is the <p>.
					element.returnPoint = target = currentNode;
				}

				removeTailWhitespace( element );

				// Avoid adding empty inline.
				if ( !( isRemoveEmpty( element ) && !element.children.length ) )
					target.add( element );

				if ( element.name == 'pre' )
					inPre = false;

				if ( element.name == 'textarea' )
					inTextarea = false;
			}

			if ( element.returnPoint ) {
				currentNode = element.returnPoint;
				delete element.returnPoint;
			} else
				currentNode = moveCurrent ? target : savedCurrent;
		}

		// Auto paragraphing should happen when inline content enters the root element.
		function checkAutoParagraphing( parent, node ) {

			// Check for parent that can contain block.
			if ( ( parent == root || parent.name == 'body' ) && fixingBlock &&
					 ( !parent.name || CKEDITOR.dtd[ parent.name ][ fixingBlock ] ) )
			{
				var name, realName;
				if ( node.attributes && ( realName = node.attributes[ 'data-cke-real-element-type' ] ) )
					name = realName;
				else
					name = node.name;

				// Text node, inline elements are subjected, except for <script>/<style>.
				return name && name in CKEDITOR.dtd.$inline &&
				       !( name in CKEDITOR.dtd.head ) &&
				       !node.isOrphan ||
				       node.type == CKEDITOR.NODE_TEXT;
			}
		}

		// Judge whether two element tag names are likely the siblings from the same
		// structural element.
		function possiblySibling( tag1, tag2 ) {

			if ( tag1 in CKEDITOR.dtd.$listItem || tag1 in CKEDITOR.dtd.$tableContent )
				return tag1 == tag2 || tag1 == 'dt' && tag2 == 'dd' || tag1 == 'dd' && tag2 == 'dt';

			return false;
		}

		parser.onTagOpen = function( tagName, attributes, selfClosing, optionalClose ) {
			var element = new CKEDITOR.htmlParser.element( tagName, attributes );

			// "isEmpty" will be always "false" for unknown elements, so we
			// must force it if the parser has identified it as a selfClosing tag.
			if ( element.isUnknown && selfClosing )
				element.isEmpty = true;

			// Check for optional closed elements, including browser quirks and manually opened blocks.
			element.isOptionalClose = optionalClose;

			// This is a tag to be removed if empty, so do not add it immediately.
			if ( isRemoveEmpty( element ) ) {
				pendingInline.push( element );
				return;
			} else if ( tagName == 'pre' )
				inPre = true;
			else if ( tagName == 'br' && inPre ) {
				currentNode.add( new CKEDITOR.htmlParser.text( '\n' ) );
				return;
			} else if ( tagName == 'textarea' )
				inTextarea = true;

			if ( tagName == 'br' ) {
				pendingBRs.push( element );
				return;
			}

			while ( 1 ) {
				var currentName = currentNode.name;

				var currentDtd = currentName ? ( CKEDITOR.dtd[ currentName ] || ( currentNode._.isBlockLike ? CKEDITOR.dtd.div : CKEDITOR.dtd.span ) ) : rootDtd;

				// If the element cannot be child of the current element.
				if ( !element.isUnknown && !currentNode.isUnknown && !currentDtd[ tagName ] ) {
					// Current node doesn't have a close tag, time for a close
					// as this element isn't fit in. (#7497)
					if ( currentNode.isOptionalClose )
						parser.onTagClose( currentName );
					// Fixing malformed nested lists by moving it into a previous list item. (#3828)
					else if ( tagName in listBlocks && currentName in listBlocks ) {
						var children = currentNode.children,
							lastChild = children[ children.length - 1 ];

						// Establish the list item if it's not existed.
						if ( !( lastChild && lastChild.name == 'li' ) )
							addElement( ( lastChild = new CKEDITOR.htmlParser.element( 'li' ) ), currentNode );

						!element.returnPoint && ( element.returnPoint = currentNode );
						currentNode = lastChild;
					}
					// Establish new list root for orphan list items, but NOT to create
					// new list for the following ones, fix them instead. (#6975)
					// <dl><dt>foo<dd>bar</dl>
					// <ul><li>foo<li>bar</ul>
					else if ( tagName in CKEDITOR.dtd.$listItem &&
							!possiblySibling( tagName, currentName ) ) {
						parser.onTagOpen( tagName == 'li' ? 'ul' : 'dl', {}, 0, 1 );
					}
					// We're inside a structural block like table and list, AND the incoming element
					// is not of the same type (e.g. <td>td1<td>td2</td>), we simply add this new one before it,
					// and most importantly, return back to here once this element is added,
					// e.g. <table><tr><td>td1</td><p>p1</p><td>td2</td></tr></table>
					else if ( currentName in nonBreakingBlocks &&
							!possiblySibling( tagName, currentName ) ) {
						!element.returnPoint && ( element.returnPoint = currentNode );
						currentNode = currentNode.parent;
					} else {
						// The current element is an inline element, which
						// need to be continued even after the close, so put
						// it in the pending list.
						if ( currentName in CKEDITOR.dtd.$inline )
							pendingInline.unshift( currentNode );

						// The most common case where we just need to close the
						// current one and append the new one to the parent.
						if ( currentNode.parent )
							addElement( currentNode, currentNode.parent, 1 );
						// We've tried our best to fix the embarrassment here, while
						// this element still doesn't find it's parent, mark it as
						// orphan and show our tolerance to it.
						else {
							element.isOrphan = 1;
							break;
						}
					}
				} else
					break;
			}

			checkPending( tagName );
			sendPendingBRs();

			element.parent = currentNode;

			if ( element.isEmpty )
				addElement( element );
			else
				currentNode = element;
		};

		parser.onTagClose = function( tagName ) {
			// Check if there is any pending tag to be closed.
			for ( var i = pendingInline.length - 1; i >= 0; i-- ) {
				// If found, just remove it from the list.
				if ( tagName == pendingInline[ i ].name ) {
					pendingInline.splice( i, 1 );
					return;
				}
			}

			var pendingAdd = [],
				newPendingInline = [],
				candidate = currentNode;

			while ( candidate != root && candidate.name != tagName ) {
				// If this is an inline element, add it to the pending list, if we're
				// really closing one of the parents element later, they will continue
				// after it.
				if ( !candidate._.isBlockLike )
					newPendingInline.unshift( candidate );

				// This node should be added to it's parent at this point. But,
				// it should happen only if the closing tag is really closing
				// one of the nodes. So, for now, we just cache it.
				pendingAdd.push( candidate );

				// Make sure return point is properly restored.
				candidate = candidate.returnPoint || candidate.parent;
			}

			if ( candidate != root ) {
				// Add all elements that have been found in the above loop.
				for ( i = 0; i < pendingAdd.length; i++ ) {
					var node = pendingAdd[ i ];
					addElement( node, node.parent );
				}

				currentNode = candidate;

				if ( candidate._.isBlockLike )
					sendPendingBRs();

				addElement( candidate, candidate.parent );

				// The parent should start receiving new nodes now, except if
				// addElement changed the currentNode.
				if ( candidate == currentNode )
					currentNode = currentNode.parent;

				pendingInline = pendingInline.concat( newPendingInline );
			}

			if ( tagName == 'body' )
				fixingBlock = false;
		};

		parser.onText = function( text ) {
			// Trim empty spaces at beginning of text contents except <pre> and <textarea>.
			if ( ( !currentNode._.hasInlineStarted || pendingBRs.length ) && !inPre && !inTextarea ) {
				text = CKEDITOR.tools.ltrim( text );

				if ( text.length === 0 )
					return;
			}

			var currentName = currentNode.name,
				currentDtd = currentName ? ( CKEDITOR.dtd[ currentName ] || ( currentNode._.isBlockLike ? CKEDITOR.dtd.div : CKEDITOR.dtd.span ) ) : rootDtd;

			// Fix orphan text in list/table. (#8540) (#8870)
			if ( !inTextarea && !currentDtd[ '#' ] && currentName in nonBreakingBlocks ) {
				parser.onTagOpen( currentName in listBlocks ? 'li' : currentName == 'dl' ? 'dd' : currentName == 'table' ? 'tr' : currentName == 'tr' ? 'td' : '' );
				parser.onText( text );
				return;
			}

			sendPendingBRs();
			checkPending();

			// Shrinking consequential spaces into one single for all elements
			// text contents.
			if ( !inPre && !inTextarea )
				text = text.replace( /[\t\r\n ]{2,}|[\t\r\n]/g, ' ' );

			text = new CKEDITOR.htmlParser.text( text );


			if ( checkAutoParagraphing( currentNode, text ) )
				this.onTagOpen( fixingBlock, {}, 0, 1 );

			currentNode.add( text );
		};

		parser.onCDATA = function( cdata ) {
			currentNode.add( new CKEDITOR.htmlParser.cdata( cdata ) );
		};

		parser.onComment = function( comment ) {
			sendPendingBRs();
			checkPending();
			currentNode.add( new CKEDITOR.htmlParser.comment( comment ) );
		};

		// Parse it.
		parser.parse( fragmentHtml );

		// Send all pending BRs except one, which we consider a unwanted bogus. (#5293)
		sendPendingBRs( !CKEDITOR.env.ie && 1 );

		// Close all pending nodes, make sure return point is properly restored.
		while ( currentNode != root )
			addElement( currentNode, currentNode.parent, 1 );

		removeTailWhitespace( root );

		return root;
	};

	CKEDITOR.htmlParser.fragment.prototype = {

		/**
		 * The node type. This is a constant value set to {@link CKEDITOR#NODE_DOCUMENT_FRAGMENT}.
		 *
		 * @readonly
		 * @property {Number} [=CKEDITOR.NODE_DOCUMENT_FRAGMENT]
		 */
		type: CKEDITOR.NODE_DOCUMENT_FRAGMENT,

		/**
		 * Adds a node to this fragment.
		 *
		 * @param {CKEDITOR.htmlParser.node} node The node to be added.
		 * @param {Number} [index] From where the insertion happens.
		 */
		add: function( node, index ) {
			isNaN( index ) && ( index = this.children.length );

			var previous = index > 0 ? this.children[ index - 1 ] : null;
			if ( previous ) {
				// If the block to be appended is following text, trim spaces at
				// the right of it.
				if ( node._.isBlockLike && previous.type == CKEDITOR.NODE_TEXT ) {
					previous.value = CKEDITOR.tools.rtrim( previous.value );

					// If we have completely cleared the previous node.
					if ( previous.value.length === 0 ) {
						// Remove it from the list and add the node again.
						this.children.pop();
						this.add( node );
						return;
					}
				}

				previous.next = node;
			}

			node.previous = previous;
			node.parent = this;

			this.children.splice( index, 0, node );

			if ( !this._.hasInlineStarted )
				this._.hasInlineStarted = node.type == CKEDITOR.NODE_TEXT || ( node.type == CKEDITOR.NODE_ELEMENT && !node._.isBlockLike );
		},

		/**
		 * Filter this fragment's content with given filter.
		 *
		 * @since 4.1
		 * @param {CKEDITOR.htmlParser.filter} filter
		 */
		filter: function( filter, context ) {
			context = this.getFilterContext( context );

			// Apply the root filter.
			filter.onRoot( context, this );

			this.filterChildren( filter, false, context );
		},

		/**
		 * Filter this fragment's children with given filter.
		 *
		 * Element's children may only be filtered once by one
		 * instance of filter.
		 *
		 * @since 4.1
		 * @param {CKEDITOR.htmlParser.filter} filter
		 * @param {Boolean} [filterRoot] Whether to apply the "root" filter rule specified in the `filter`.
		 */
		filterChildren: function( filter, filterRoot, context ) {
			// If this element's children were already filtered
			// by current filter, don't filter them 2nd time.
			// This situation may occur when filtering bottom-up
			// (filterChildren() called manually in element's filter),
			// or in unpredictable edge cases when filter
			// is manipulating DOM structure.
			if ( this.childrenFilteredBy == filter.id )
				return;

			context = this.getFilterContext( context );

			// Filtering root if enforced.
			if ( filterRoot && !this.parent )
				filter.onRoot( context, this );

			this.childrenFilteredBy = filter.id;

			// Don't cache anything, children array may be modified by filter rule.
			for ( var i = 0; i < this.children.length; i++ ) {
				// Stay in place if filter returned false, what means
				// that node has been removed.
				if ( this.children[ i ].filter( filter, context ) === false )
					i--;
			}
		},

		/**
		 * Writes the fragment HTML to a {@link CKEDITOR.htmlParser.basicWriter}.
		 *
		 *		var writer = new CKEDITOR.htmlWriter();
		 *		var fragment = CKEDITOR.htmlParser.fragment.fromHtml( '<P><B>Example' );
		 *		fragment.writeHtml( writer );
		 *		alert( writer.getHtml() ); // '<p><b>Example</b></p>'
		 *
		 * @param {CKEDITOR.htmlParser.basicWriter} writer The writer to which write the HTML.
		 * @param {CKEDITOR.htmlParser.filter} [filter] The filter to use when writing the HTML.
		 */
		writeHtml: function( writer, filter ) {
			if ( filter )
				this.filter( filter );

			this.writeChildrenHtml( writer );
		},

		/**
		 * Write and filtering the child nodes of this fragment.
		 *
		 * @param {CKEDITOR.htmlParser.basicWriter} writer The writer to which write the HTML.
		 * @param {CKEDITOR.htmlParser.filter} [filter] The filter to use when writing the HTML.
		 * @param {Boolean} [filterRoot] Whether to apply the "root" filter rule specified in the `filter`.
		 */
		writeChildrenHtml: function( writer, filter, filterRoot ) {
			var context = this.getFilterContext();

			// Filtering root if enforced.
			if ( filterRoot && !this.parent && filter )
				filter.onRoot( context, this );

			if ( filter )
				this.filterChildren( filter, false, context );

			for ( var i = 0, children = this.children, l = children.length; i < l; i++ )
				children[ i ].writeHtml( writer );
		},

		/**
		 * Execute callback on each node (of given type) in this document fragment.
		 *
		 *		var fragment = CKEDITOR.htmlParser.fragment.fromHtml( '<p>foo<b>bar</b>bom</p>' );
		 *		fragment.forEach( function( node ) {
		 *			console.log( node );
		 *		} );
		 *		// Will log:
		 *		// 1. document fragment,
		 *		// 2. <p> element,
		 *		// 3. "foo" text node,
		 *		// 4. <b> element,
		 *		// 5. "bar" text node,
		 *		// 6. "bom" text node.
		 *
		 * @since 4.1
		 * @param {Function} callback Function to be executed on every node.
		 * **Since 4.3** if `callback` returned `false` descendants of current node will be ignored.
		 * @param {CKEDITOR.htmlParser.node} callback.node Node passed as argument.
		 * @param {Number} [type] If specified `callback` will be executed only on nodes of this type.
		 * @param {Boolean} [skipRoot] Don't execute `callback` on this fragment.
		 */
		forEach: function( callback, type, skipRoot ) {
			if ( !skipRoot && ( !type || this.type == type ) )
				var ret = callback( this );

			// Do not filter children if callback returned false.
			if ( ret === false )
				return;

			var children = this.children,
				node,
				i = 0,
				l = children.length;

			for ( ; i < l; i++ ) {
				node = children[ i ];
				if ( node.type == CKEDITOR.NODE_ELEMENT )
					node.forEach( callback, type );
				else if ( !type || node.type == type )
					callback( node );
			}
		},

		getFilterContext: function( context ) {
			return context || {};
		}
	};
})();
