/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * Represents a delimited piece of content in a DOM Document.
 * It is contiguous in the sense that it can be characterized as selecting all
 * of the content between a pair of boundary-points.
 *
 * This class shares much of the W3C
 * [Document Object Model Range](http://www.w3.org/TR/DOM-Level-2-Traversal-Range/ranges.html)
 * ideas and features, adding several range manipulation tools to it, but it's
 * not intended to be compatible with it.
 *
 *		// Create a range for the entire contents of the editor document body.
 *		var range = new CKEDITOR.dom.range( editor.document );
 *		range.selectNodeContents( editor.document.getBody() );
 *		// Delete the contents.
 *		range.deleteContents();
 *
 * @class
 * @constructor Creates a {@link CKEDITOR.dom.range} instance that can be used inside a specific DOM Document.
 * @param {CKEDITOR.dom.document/CKEDITOR.dom.element} root The document or element
 * within which the range will be scoped.
 * @todo global "TODO" - precise algorithms descriptions needed for the most complex methods like #enlarge.
 */
CKEDITOR.dom.range = function( root ) {
	/**
	 * Node within which the range begins.
	 *
	 *		var range = new CKEDITOR.dom.range( editor.document );
	 *		range.selectNodeContents( editor.document.getBody() );
	 *		alert( range.startContainer.getName() ); // 'body'
	 *
	 * @readonly
	 * @property {CKEDITOR.dom.element/CKEDITOR.dom.text}
	 */
	this.startContainer = null;

	/**
	 * Offset within the starting node of the range.
	 *
	 *		var range = new CKEDITOR.dom.range( editor.document );
	 *		range.selectNodeContents( editor.document.getBody() );
	 *		alert( range.startOffset ); // 0
	 *
	 * @readonly
	 * @property {Number}
	 */
	this.startOffset = null;

	/**
	 * Node within which the range ends.
	 *
	 *		var range = new CKEDITOR.dom.range( editor.document );
	 *		range.selectNodeContents( editor.document.getBody() );
	 *		alert( range.endContainer.getName() ); // 'body'
	 *
	 * @readonly
	 * @property {CKEDITOR.dom.element/CKEDITOR.dom.text}
	 */
	this.endContainer = null;

	/**
	 * Offset within the ending node of the range.
	 *
	 *		var range = new CKEDITOR.dom.range( editor.document );
	 *		range.selectNodeContents( editor.document.getBody() );
	 *		alert( range.endOffset ); // == editor.document.getBody().getChildCount()
	 *
	 * @readonly
	 * @property {Number}
	 */
	this.endOffset = null;

	/**
	 * Indicates that this is a collapsed range. A collapsed range has its
	 * start and end boundaries at the very same point so nothing is contained
	 * in it.
	 *
	 *		var range = new CKEDITOR.dom.range( editor.document );
	 *		range.selectNodeContents( editor.document.getBody() );
	 *		alert( range.collapsed ); // false
	 *		range.collapse();
	 *		alert( range.collapsed ); // true
	 *
	 * @readonly
	 */
	this.collapsed = true;

	var isDocRoot = root instanceof CKEDITOR.dom.document;
	/**
	 * The document within which the range can be used.
	 *
	 *		// Selects the body contents of the range document.
	 *		range.selectNodeContents( range.document.getBody() );
	 *
	 * @readonly
	 * @property {CKEDITOR.dom.document}
	 */
	this.document = isDocRoot ? root : root.getDocument();

	/**
	 * The ancestor DOM element within which the range manipulation are limited.
	 *
	 * @readonly
	 * @property {CKEDITOR.dom.element}
	 */
	this.root = isDocRoot ? root.getBody() : root;
};

(function() {
	// Updates the "collapsed" property for the given range object.
	var updateCollapsed = function( range ) {
			range.collapsed = ( range.startContainer && range.endContainer && range.startContainer.equals( range.endContainer ) && range.startOffset == range.endOffset );
		};

	// This is a shared function used to delete, extract and clone the range
	// contents.
	// V2
	var execContentsAction = function( range, action, docFrag, mergeThen ) {
			range.optimizeBookmark();

			var startNode = range.startContainer;
			var endNode = range.endContainer;

			var startOffset = range.startOffset;
			var endOffset = range.endOffset;

			var removeStartNode;
			var removeEndNode;

			// For text containers, we must simply split the node and point to the
			// second part. The removal will be handled by the rest of the code .
			if ( endNode.type == CKEDITOR.NODE_TEXT )
				endNode = endNode.split( endOffset );
			else {
				// If the end container has children and the offset is pointing
				// to a child, then we should start from it.
				if ( endNode.getChildCount() > 0 ) {
					// If the offset points after the last node.
					if ( endOffset >= endNode.getChildCount() ) {
						// Let's create a temporary node and mark it for removal.
						endNode = endNode.append( range.document.createText( '' ) );
						removeEndNode = true;
					} else
						endNode = endNode.getChild( endOffset );
				}
			}

			// For text containers, we must simply split the node. The removal will
			// be handled by the rest of the code .
			if ( startNode.type == CKEDITOR.NODE_TEXT ) {
				startNode.split( startOffset );

				// In cases the end node is the same as the start node, the above
				// splitting will also split the end, so me must move the end to
				// the second part of the split.
				if ( startNode.equals( endNode ) )
					endNode = startNode.getNext();
			} else {
				// If the start container has children and the offset is pointing
				// to a child, then we should start from its previous sibling.

				// If the offset points to the first node, we don't have a
				// sibling, so let's use the first one, but mark it for removal.
				if ( !startOffset ) {
					// Let's create a temporary node and mark it for removal.
					startNode = startNode.append( range.document.createText( '' ), 1 );
					removeStartNode = true;
				} else if ( startOffset >= startNode.getChildCount() ) {
					// Let's create a temporary node and mark it for removal.
					startNode = startNode.append( range.document.createText( '' ) );
					removeStartNode = true;
				} else
					startNode = startNode.getChild( startOffset ).getPrevious();
			}

			// Get the parent nodes tree for the start and end boundaries.
			var startParents = startNode.getParents();
			var endParents = endNode.getParents();

			// Compare them, to find the top most siblings.
			var i, topStart, topEnd;

			for ( i = 0; i < startParents.length; i++ ) {
				topStart = startParents[ i ];
				topEnd = endParents[ i ];

				// The compared nodes will match until we find the top most
				// siblings (different nodes that have the same parent).
				// "i" will hold the index in the parents array for the top
				// most element.
				if ( !topStart.equals( topEnd ) )
					break;
			}

			var clone = docFrag,
				levelStartNode, levelClone, currentNode, currentSibling;

			// Remove all successive sibling nodes for every node in the
			// startParents tree.
			for ( var j = i; j < startParents.length; j++ ) {
				levelStartNode = startParents[ j ];

				// For Extract and Clone, we must clone this level.
				if ( clone && !levelStartNode.equals( startNode ) ) // action = 0 = Delete
				levelClone = clone.append( levelStartNode.clone() );

				currentNode = levelStartNode.getNext();

				while ( currentNode ) {
					// Stop processing when the current node matches a node in the
					// endParents tree or if it is the endNode.
					if ( currentNode.equals( endParents[ j ] ) || currentNode.equals( endNode ) )
						break;

					// Cache the next sibling.
					currentSibling = currentNode.getNext();

					// If cloning, just clone it.
					if ( action == 2 ) // 2 = Clone
					clone.append( currentNode.clone( true ) );
					else {
						// Both Delete and Extract will remove the node.
						currentNode.remove();

						// When Extracting, move the removed node to the docFrag.
						if ( action == 1 ) // 1 = Extract
						clone.append( currentNode );
					}

					currentNode = currentSibling;
				}

				if ( clone )
					clone = levelClone;
			}

			clone = docFrag;

			// Remove all previous sibling nodes for every node in the
			// endParents tree.
			for ( var k = i; k < endParents.length; k++ ) {
				levelStartNode = endParents[ k ];

				// For Extract and Clone, we must clone this level.
				if ( action > 0 && !levelStartNode.equals( endNode ) ) // action = 0 = Delete
				levelClone = clone.append( levelStartNode.clone() );

				// The processing of siblings may have already been done by the parent.
				if ( !startParents[ k ] || levelStartNode.$.parentNode != startParents[ k ].$.parentNode ) {
					currentNode = levelStartNode.getPrevious();

					while ( currentNode ) {
						// Stop processing when the current node matches a node in the
						// startParents tree or if it is the startNode.
						if ( currentNode.equals( startParents[ k ] ) || currentNode.equals( startNode ) )
							break;

						// Cache the next sibling.
						currentSibling = currentNode.getPrevious();

						// If cloning, just clone it.
						if ( action == 2 ) // 2 = Clone
						clone.$.insertBefore( currentNode.$.cloneNode( true ), clone.$.firstChild );
						else {
							// Both Delete and Extract will remove the node.
							currentNode.remove();

							// When Extracting, mode the removed node to the docFrag.
							if ( action == 1 ) // 1 = Extract
							clone.$.insertBefore( currentNode.$, clone.$.firstChild );
						}

						currentNode = currentSibling;
					}
				}

				if ( clone )
					clone = levelClone;
			}

			if ( action == 2 ) // 2 = Clone.
			{
				// No changes in the DOM should be done, so fix the split text (if any).

				var startTextNode = range.startContainer;
				if ( startTextNode.type == CKEDITOR.NODE_TEXT ) {
					startTextNode.$.data += startTextNode.$.nextSibling.data;
					startTextNode.$.parentNode.removeChild( startTextNode.$.nextSibling );
				}

				var endTextNode = range.endContainer;
				if ( endTextNode.type == CKEDITOR.NODE_TEXT && endTextNode.$.nextSibling ) {
					endTextNode.$.data += endTextNode.$.nextSibling.data;
					endTextNode.$.parentNode.removeChild( endTextNode.$.nextSibling );
				}
			} else {
				// Collapse the range.

				// If a node has been partially selected, collapse the range between
				// topStart and topEnd. Otherwise, simply collapse it to the start. (W3C specs).
				if ( topStart && topEnd && ( startNode.$.parentNode != topStart.$.parentNode || endNode.$.parentNode != topEnd.$.parentNode ) ) {
					var endIndex = topEnd.getIndex();

					// If the start node is to be removed, we must correct the
					// index to reflect the removal.
					if ( removeStartNode && topEnd.$.parentNode == startNode.$.parentNode )
						endIndex--;

					// Merge splitted parents.
					if ( mergeThen && topStart.type == CKEDITOR.NODE_ELEMENT ) {
						var span = CKEDITOR.dom.element.createFromHtml( '<span ' +
							'data-cke-bookmark="1" style="display:none">&nbsp;</span>', range.document );
						span.insertAfter( topStart );
						topStart.mergeSiblings( false );
						range.moveToBookmark({ startNode: span } );
					} else
						range.setStart( topEnd.getParent(), endIndex );
				}

				// Collapse it to the start.
				range.collapse( true );
			}

			// Cleanup any marked node.
			if ( removeStartNode )
				startNode.remove();

			if ( removeEndNode && endNode.$.parentNode )
				endNode.remove();
		};

	var inlineChildReqElements = { abbr:1,acronym:1,b:1,bdo:1,big:1,cite:1,code:1,del:1,dfn:1,em:1,font:1,i:1,ins:1,label:1,kbd:1,q:1,samp:1,small:1,span:1,strike:1,strong:1,sub:1,sup:1,tt:1,u:1,'var':1 };

	// Creates the appropriate node evaluator for the dom walker used inside
	// check(Start|End)OfBlock.
	function getCheckStartEndBlockEvalFunction() {
		var skipBogus = false,
			whitespaces = CKEDITOR.dom.walker.whitespaces(),
			bookmarkEvaluator = CKEDITOR.dom.walker.bookmark( true ),
			isBogus = CKEDITOR.dom.walker.bogus();

		return function( node ) {
			// First skip empty nodes
			if ( bookmarkEvaluator( node ) || whitespaces( node ) )
				return true;

			// Skip the bogus node at the end of block.
			if ( isBogus( node ) && !skipBogus ) {
				skipBogus = true;
				return true;
			}

			// If there's any visible text, then we're not at the start.
			if ( node.type == CKEDITOR.NODE_TEXT &&
					 ( node.hasAscendant( 'pre' ) ||
						 CKEDITOR.tools.trim( node.getText() ).length ) )
				return false;

			// If there are non-empty inline elements (e.g. <img />), then we're not
			// at the start.
			if ( node.type == CKEDITOR.NODE_ELEMENT && !node.is( inlineChildReqElements ) )
				return false;

			return true;
		};
	}


	var isBogus = CKEDITOR.dom.walker.bogus(),
		nbspRegExp = /^[\t\r\n ]*(?:&nbsp;|\xa0)$/,
		editableEval = CKEDITOR.dom.walker.editable(),
		notIgnoredEval = CKEDITOR.dom.walker.ignored( true );

	// Evaluator for CKEDITOR.dom.element::checkBoundaryOfElement, reject any
	// text node and non-empty elements unless it's being bookmark text.
	function elementBoundaryEval( checkStart ) {
		var whitespaces = CKEDITOR.dom.walker.whitespaces(),
			bookmark = CKEDITOR.dom.walker.bookmark( 1 );

		return function( node ) {
			// First skip empty nodes.
			if ( bookmark( node ) || whitespaces( node ) )
				return true;

			// Tolerant bogus br when checking at the end of block.
			// Reject any text node unless it's being bookmark
			// OR it's spaces.
			// Reject any element unless it's being invisible empty. (#3883)
			return !checkStart && isBogus( node ) ||
						 node.type == CKEDITOR.NODE_ELEMENT &&
						 node.is( CKEDITOR.dtd.$removeEmpty );
		};
	}

	function getNextEditableNode( isPrevious ) {
		return function() {
			var first;

			return this[ isPrevious ? 'getPreviousNode' : 'getNextNode' ]( function( node ) {
				// Cache first not ignorable node.
				if ( !first && notIgnoredEval( node ) )
					first = node;

				// Return true if found editable node, but not a bogus next to start of our lookup (first != bogus).
				return editableEval( node ) && !( isBogus( node ) && node.equals( first ) );
			} );
		};
	}

	CKEDITOR.dom.range.prototype = {
		/**
		 * Clones this range.
		 *
		 * @returns {CKEDITOR.dom.range}
		 */
		clone: function() {
			var clone = new CKEDITOR.dom.range( this.root );

			clone.startContainer = this.startContainer;
			clone.startOffset = this.startOffset;
			clone.endContainer = this.endContainer;
			clone.endOffset = this.endOffset;
			clone.collapsed = this.collapsed;

			return clone;
		},

		/**
		 * Makes range collapsed by moving its start point (or end point if `toStart==true`)
		 * to the second end.
		 *
		 * @param {Boolean} toStart Collapse range "to start".
		 */
		collapse: function( toStart ) {
			if ( toStart ) {
				this.endContainer = this.startContainer;
				this.endOffset = this.startOffset;
			} else {
				this.startContainer = this.endContainer;
				this.startOffset = this.endOffset;
			}

			this.collapsed = true;
		},

		/**
		 * The content nodes of the range are cloned and added to a document fragment, which is returned.
		 *
		 * **Note:** Text selection may lost after invoking this method (caused by text node splitting).
		 *
		 * @returns {CKEDITOR.dom.documentFragment} Document fragment containing clone of range's content.
		 */
		cloneContents: function() {
			var docFrag = new CKEDITOR.dom.documentFragment( this.document );

			if ( !this.collapsed )
				execContentsAction( this, 2, docFrag );

			return docFrag;
		},

		/**
		 * Deletes the content nodes of the range permanently from the DOM tree.
		 *
		 * @param {Boolean} [mergeThen] Merge any splitted elements result in DOM true due to partial selection.
		 */
		deleteContents: function( mergeThen ) {
			if ( this.collapsed )
				return;

			execContentsAction( this, 0, null, mergeThen );
		},

		/**
		 * The content nodes of the range are cloned and added to a document fragment,
		 * meanwhile they are removed permanently from the DOM tree.
		 *
		 * @param {Boolean} [mergeThen] Merge any splitted elements result in DOM true due to partial selection.
		 * @returns {CKEDITOR.dom.documentFragment} Document fragment containing extracted content.
		 */
		extractContents: function( mergeThen ) {
			var docFrag = new CKEDITOR.dom.documentFragment( this.document );

			if ( !this.collapsed )
				execContentsAction( this, 1, docFrag, mergeThen );

			return docFrag;
		},

		/**
		 * Creates a bookmark object, which can be later used to restore the
		 * range by using the {@link #moveToBookmark} function.
		 *
		 * This is an "intrusive" way to create a bookmark. It includes `<span>` tags
		 * in the range boundaries. The advantage of it is that it is possible to
		 * handle DOM mutations when moving back to the bookmark.
		 *
		 * **Note:** The inclusion of nodes in the DOM is a design choice and
		 * should not be changed as there are other points in the code that may be
		 * using those nodes to perform operations.
		 *
		 * @param {Boolean} [serializable] Indicates that the bookmark nodes
		 * must contain IDs, which can be used to restore the range even
		 * when these nodes suffer mutations (like cloning or `innerHTML` change).
		 * @returns {Object} And object representing a bookmark.
		 * @returns {CKEDITOR.dom.node/String} return.startNode Node or element ID.
		 * @returns {CKEDITOR.dom.node/String} return.endNode Node or element ID.
		 * @returns {Boolean} return.serializable
		 * @returns {Boolean} return.collapsed
		 */
		createBookmark: function( serializable ) {
			var startNode, endNode;
			var baseId;
			var clone;
			var collapsed = this.collapsed;

			startNode = this.document.createElement( 'span' );
			startNode.data( 'cke-bookmark', 1 );
			startNode.setStyle( 'display', 'none' );

			// For IE, it must have something inside, otherwise it may be
			// removed during DOM operations.
			startNode.setHtml( '&nbsp;' );

			if ( serializable ) {
				baseId = 'cke_bm_' + CKEDITOR.tools.getNextNumber();
				startNode.setAttribute( 'id', baseId + ( collapsed ? 'C' : 'S' ) );
			}

			// If collapsed, the endNode will not be created.
			if ( !collapsed ) {
				endNode = startNode.clone();
				endNode.setHtml( '&nbsp;' );

				if ( serializable )
					endNode.setAttribute( 'id', baseId + 'E' );

				clone = this.clone();
				clone.collapse();
				clone.insertNode( endNode );
			}

			clone = this.clone();
			clone.collapse( true );
			clone.insertNode( startNode );

			// Update the range position.
			if ( endNode ) {
				this.setStartAfter( startNode );
				this.setEndBefore( endNode );
			} else
				this.moveToPosition( startNode, CKEDITOR.POSITION_AFTER_END );

			return {
				startNode: serializable ? baseId + ( collapsed ? 'C' : 'S' ) : startNode,
				endNode: serializable ? baseId + 'E' : endNode,
				serializable: serializable,
				collapsed: collapsed
			};
		},

		/**
		 * Creates a "non intrusive" and "mutation sensible" bookmark. This
		 * kind of bookmark should be used only when the DOM is supposed to
		 * remain stable after its creation.
		 *
		 * @param {Boolean} [normalized] Indicates that the bookmark must
		 * be normalized. When normalized, the successive text nodes are
		 * considered a single node. To successfully load a normalized
		 * bookmark, the DOM tree must also be normalized before calling
		 * {@link #moveToBookmark}.
		 * @returns {Object} An object representing the bookmark.
		 * @returns {Array} return.start Start container's address (see {@link CKEDITOR.dom.node#getAddress}).
		 * @returns {Array} return.end Start container's address.
		 * @returns {Number} return.startOffset
		 * @returns {Number} return.endOffset
		 * @returns {Boolean} return.collapsed
		 * @returns {Boolean} return.normalized
		 * @returns {Boolean} return.is2 This is "bookmark2".
		 */
		createBookmark2: (function() {
			function isPreviousText( node, offset ) {
				return offset > 0 && node && node.type == CKEDITOR.NODE_TEXT && node.getPrevious() && node.getPrevious().type == CKEDITOR.NODE_TEXT;
			}

			// Normalize the range. The limit is either start or end of the range.
			// If there are several text nodes in a row, this function moves range boundary from the
			// element to a text node and updates the offset. As a result, it looks like text nodes
			// were glued together into a bigger one, and the range refers to it.
			function normalize( limit ) {
				var child, previous,
					container = limit.container,
					offset = limit.offset;

				// Find out if the limit is pointing to a text node that will be normalized.
				if ( container.type == CKEDITOR.NODE_ELEMENT ) {
					child = container.getChild( offset );

					// If the limit of the range is after last child, offset will be equal
					// the number of children so getChild( offset ) becomes null.
					// In such case, move the limit to the end of the child.
					// Before:
					//		            ____ <p> is the container. Offset is 2.
					//		           |
					//		<p>        |</p>
					//		   Foo, Bar         // Two text-node children.
					//
					// After:
					//		            ____ "Bar" becomes the container. Offset is 3.
					//		           |
					//		<p>        |</p>
					//		   Foo, Bar|
					//
					if ( !child ) {
						child = container.getLast();

						if ( isPreviousText( child, offset ) ) {
							container = child;
							offset = child.getLength();
						}
					}

					// In this case, move the limit information to the beginning of
					// that text node.
					// Before:
					//		         ____ <p> is the container. Offset is 1.
					//		        |
					//		<p>     |   </p>
					//		   Foo, Bar         // Two text-node children.
					//
					// After:
					//		         ____ "Bar" becomes the container. Offset is 0.
					//		        |
					//		<p>     |   </p>
					//		   Foo, |Bar
					//
					else if ( isPreviousText( child, offset ) ) {
						container = child;
						offset = 0;
					}

					// Get the normalized offset.
					if ( child && child.type == CKEDITOR.NODE_ELEMENT )
						offset = child.getIndex( 1 );
				}

				// Normalize.
				while ( container.type == CKEDITOR.NODE_TEXT && ( previous = container.getPrevious() ) && previous.type == CKEDITOR.NODE_TEXT ) {
					container = previous;
					offset += previous.getLength();
				}

				limit.container = container;
				limit.offset = offset;
			}

			return function( normalized ) {
				var collapsed = this.collapsed,
					bmStart = {
						container: this.startContainer,
						offset: this.startOffset
					},
					bmEnd = {
						container: this.endContainer,
						offset: this.endOffset
					};

				// If there is no range then get out of here.
				// It happens on initial load in Safari #962 and if the editor it's
				// hidden also in Firefox
				if ( !bmStart.container || !bmEnd.container )
					return { start: 0, end: 0 };

				// Normalize range.
				if ( normalized ) {
					normalize( bmStart );

					if ( !collapsed )
						normalize( bmEnd );
				}

				return {
					start: bmStart.container.getAddress( normalized ),
					end: collapsed ? null : bmEnd.container.getAddress( normalized ),
					startOffset: bmStart.offset,
					endOffset: bmEnd.offset,
					normalized: normalized,
					collapsed: collapsed,
					is2: true // It's a createBookmark2 bookmark.
				};
			};
		})(),

		/**
		 * Moves this range to the given bookmark. See {@link #createBookmark} and {@link #createBookmark2}.
		 *
		 * If serializable bookmark passed, then its `<span>` markers will be removed.
		 *
		 * @param {Object} bookmark
		 */
		moveToBookmark: function( bookmark ) {
			if ( bookmark.is2 ) // Created with createBookmark2().
			{
				// Get the start information.
				var startContainer = this.document.getByAddress( bookmark.start, bookmark.normalized ),
					startOffset = bookmark.startOffset;

				// Get the end information.
				var endContainer = bookmark.end && this.document.getByAddress( bookmark.end, bookmark.normalized ),
					endOffset = bookmark.endOffset;

				// Set the start boundary.
				this.setStart( startContainer, startOffset );

				// Set the end boundary. If not available, collapse it.
				if ( endContainer )
					this.setEnd( endContainer, endOffset );
				else
					this.collapse( true );
			} else // Created with createBookmark().
			{
				var serializable = bookmark.serializable,
					startNode = serializable ? this.document.getById( bookmark.startNode ) : bookmark.startNode,
					endNode = serializable ? this.document.getById( bookmark.endNode ) : bookmark.endNode;

				// Set the range start at the bookmark start node position.
				this.setStartBefore( startNode );

				// Remove it, because it may interfere in the setEndBefore call.
				startNode.remove();

				// Set the range end at the bookmark end node position, or simply
				// collapse it if it is not available.
				if ( endNode ) {
					this.setEndBefore( endNode );
					endNode.remove();
				} else
					this.collapse( true );
			}
		},

		/**
		 * Returns two nodes which are on the boundaries of this range.
		 *
		 * @returns {Object}
		 * @returns {CKEDITOR.dom.node} return.startNode
		 * @returns {CKEDITOR.dom.node} return.endNode
		 * @todo precise desc/algorithm
		 */
		getBoundaryNodes: function() {
			var startNode = this.startContainer,
				endNode = this.endContainer,
				startOffset = this.startOffset,
				endOffset = this.endOffset,
				childCount;

			if ( startNode.type == CKEDITOR.NODE_ELEMENT ) {
				childCount = startNode.getChildCount();
				if ( childCount > startOffset )
					startNode = startNode.getChild( startOffset );
				else if ( childCount < 1 )
					startNode = startNode.getPreviousSourceNode();
				else // startOffset > childCount but childCount is not 0
				{
					// Try to take the node just after the current position.
					startNode = startNode.$;
					while ( startNode.lastChild )
						startNode = startNode.lastChild;
					startNode = new CKEDITOR.dom.node( startNode );

					// Normally we should take the next node in DFS order. But it
					// is also possible that we've already reached the end of
					// document.
					startNode = startNode.getNextSourceNode() || startNode;
				}
			}
			if ( endNode.type == CKEDITOR.NODE_ELEMENT ) {
				childCount = endNode.getChildCount();
				if ( childCount > endOffset )
					endNode = endNode.getChild( endOffset ).getPreviousSourceNode( true );
				else if ( childCount < 1 )
					endNode = endNode.getPreviousSourceNode();
				else // endOffset > childCount but childCount is not 0
				{
					// Try to take the node just before the current position.
					endNode = endNode.$;
					while ( endNode.lastChild )
						endNode = endNode.lastChild;
					endNode = new CKEDITOR.dom.node( endNode );
				}
			}

			// Sometimes the endNode will come right before startNode for collapsed
			// ranges. Fix it. (#3780)
			if ( startNode.getPosition( endNode ) & CKEDITOR.POSITION_FOLLOWING )
				startNode = endNode;

			return { startNode: startNode, endNode: endNode };
		},

		/**
		 * Find the node which fully contains the range.
		 *
		 * @param {Boolean} [includeSelf=false]
		 * @param {Boolean} [ignoreTextNode=false] Whether ignore {@link CKEDITOR#NODE_TEXT} type.
		 * @returns {CKEDITOR.dom.element}
		 */
		getCommonAncestor: function( includeSelf, ignoreTextNode ) {
			var start = this.startContainer,
				end = this.endContainer,
				ancestor;

			if ( start.equals( end ) ) {
				if ( includeSelf && start.type == CKEDITOR.NODE_ELEMENT && this.startOffset == this.endOffset - 1 )
					ancestor = start.getChild( this.startOffset );
				else
					ancestor = start;
			} else
				ancestor = start.getCommonAncestor( end );

			return ignoreTextNode && !ancestor.is ? ancestor.getParent() : ancestor;
		},

		/**
		 * Transforms the {@link #startContainer} and {@link #endContainer} properties from text
		 * nodes to element nodes, whenever possible. This is actually possible
		 * if either of the boundary containers point to a text node, and its
		 * offset is set to zero, or after the last char in the node.
		 */
		optimize: function() {
			var container = this.startContainer;
			var offset = this.startOffset;

			if ( container.type != CKEDITOR.NODE_ELEMENT ) {
				if ( !offset )
					this.setStartBefore( container );
				else if ( offset >= container.getLength() )
					this.setStartAfter( container );
			}

			container = this.endContainer;
			offset = this.endOffset;

			if ( container.type != CKEDITOR.NODE_ELEMENT ) {
				if ( !offset )
					this.setEndBefore( container );
				else if ( offset >= container.getLength() )
					this.setEndAfter( container );
			}
		},

		/**
		 * Move the range out of bookmark nodes if they'd been the container.
		 */
		optimizeBookmark: function() {
			var startNode = this.startContainer,
				endNode = this.endContainer;

			if ( startNode.is && startNode.is( 'span' ) && startNode.data( 'cke-bookmark' ) )
				this.setStartAt( startNode, CKEDITOR.POSITION_BEFORE_START );
			if ( endNode && endNode.is && endNode.is( 'span' ) && endNode.data( 'cke-bookmark' ) )
				this.setEndAt( endNode, CKEDITOR.POSITION_AFTER_END );
		},

		/**
		 * @param {Boolean} [ignoreStart=false]
		 * @param {Boolean} [ignoreEnd=false]
		 * @todo precise desc/algorithm
		 */
		trim: function( ignoreStart, ignoreEnd ) {
			var startContainer = this.startContainer,
				startOffset = this.startOffset,
				collapsed = this.collapsed;
			if ( ( !ignoreStart || collapsed ) && startContainer && startContainer.type == CKEDITOR.NODE_TEXT ) {
				// If the offset is zero, we just insert the new node before
				// the start.
				if ( !startOffset ) {
					startOffset = startContainer.getIndex();
					startContainer = startContainer.getParent();
				}
				// If the offset is at the end, we'll insert it after the text
				// node.
				else if ( startOffset >= startContainer.getLength() ) {
					startOffset = startContainer.getIndex() + 1;
					startContainer = startContainer.getParent();
				}
				// In other case, we split the text node and insert the new
				// node at the split point.
				else {
					var nextText = startContainer.split( startOffset );

					startOffset = startContainer.getIndex() + 1;
					startContainer = startContainer.getParent();

					// Check all necessity of updating the end boundary.
					if ( this.startContainer.equals( this.endContainer ) )
						this.setEnd( nextText, this.endOffset - this.startOffset );
					else if ( startContainer.equals( this.endContainer ) )
						this.endOffset += 1;
				}

				this.setStart( startContainer, startOffset );

				if ( collapsed ) {
					this.collapse( true );
					return;
				}
			}

			var endContainer = this.endContainer;
			var endOffset = this.endOffset;

			if ( !( ignoreEnd || collapsed ) && endContainer && endContainer.type == CKEDITOR.NODE_TEXT ) {
				// If the offset is zero, we just insert the new node before
				// the start.
				if ( !endOffset ) {
					endOffset = endContainer.getIndex();
					endContainer = endContainer.getParent();
				}
				// If the offset is at the end, we'll insert it after the text
				// node.
				else if ( endOffset >= endContainer.getLength() ) {
					endOffset = endContainer.getIndex() + 1;
					endContainer = endContainer.getParent();
				}
				// In other case, we split the text node and insert the new
				// node at the split point.
				else {
					endContainer.split( endOffset );

					endOffset = endContainer.getIndex() + 1;
					endContainer = endContainer.getParent();
				}

				this.setEnd( endContainer, endOffset );
			}
		},

		/**
		 * Expands the range so that partial units are completely contained.
		 *
		 * @param unit {Number} The unit type to expand with.
		 * @param {Boolean} [excludeBrs=false] Whether include line-breaks when expanding.
		 */
		enlarge: function( unit, excludeBrs ) {
			switch ( unit ) {
				case CKEDITOR.ENLARGE_INLINE:
					var enlargeInlineOnly = 1;
					/*jsl:fallthru*/
				case CKEDITOR.ENLARGE_ELEMENT:

					if ( this.collapsed )
						return;

					// Get the common ancestor.
					var commonAncestor = this.getCommonAncestor();

					var boundary = this.root;

					// For each boundary
					//		a. Depending on its position, find out the first node to be checked (a sibling) or, if not available, to be enlarge.
					//		b. Go ahead checking siblings and enlarging the boundary as much as possible until the common ancestor is not reached. After reaching the common ancestor, just save the enlargeable node to be used later.

					var startTop, endTop;

					var enlargeable, sibling, commonReached;

					// Indicates that the node can be added only if whitespace
					// is available before it.
					var needsWhiteSpace = false;
					var isWhiteSpace;
					var siblingText;

					// Process the start boundary.

					var container = this.startContainer;
					var offset = this.startOffset;

					if ( container.type == CKEDITOR.NODE_TEXT ) {
						if ( offset ) {
							// Check if there is any non-space text before the
							// offset. Otherwise, container is null.
							container = !CKEDITOR.tools.trim( container.substring( 0, offset ) ).length && container;

							// If we found only whitespace in the node, it
							// means that we'll need more whitespace to be able
							// to expand. For example, <i> can be expanded in
							// "A <i> [B]</i>", but not in "A<i> [B]</i>".
							needsWhiteSpace = !!container;
						}

						if ( container ) {
							if ( !( sibling = container.getPrevious() ) )
								enlargeable = container.getParent();
						}
					} else {
						// If we have offset, get the node preceeding it as the
						// first sibling to be checked.
						if ( offset )
							sibling = container.getChild( offset - 1 ) || container.getLast();

						// If there is no sibling, mark the container to be
						// enlarged.
						if ( !sibling )
							enlargeable = container;
					}

					while ( enlargeable || sibling ) {
						if ( enlargeable && !sibling ) {
							// If we reached the common ancestor, mark the flag
							// for it.
							if ( !commonReached && enlargeable.equals( commonAncestor ) )
								commonReached = true;

							if ( enlargeInlineOnly ? enlargeable.isBlockBoundary() : !boundary.contains( enlargeable ) )
								break;

							// If we don't need space or this element breaks
							// the line, then enlarge it.
							if ( !needsWhiteSpace || enlargeable.getComputedStyle( 'display' ) != 'inline' ) {
								needsWhiteSpace = false;

								// If the common ancestor has been reached,
								// we'll not enlarge it immediately, but just
								// mark it to be enlarged later if the end
								// boundary also enlarges it.
								if ( commonReached )
									startTop = enlargeable;
								else
									this.setStartBefore( enlargeable );
							}

							sibling = enlargeable.getPrevious();
						}

						// Check all sibling nodes preceeding the enlargeable
						// node. The node wil lbe enlarged only if none of them
						// blocks it.
						while ( sibling ) {
							// This flag indicates that this node has
							// whitespaces at the end.
							isWhiteSpace = false;

							if ( sibling.type == CKEDITOR.NODE_COMMENT ) {
								sibling = sibling.getPrevious();
								continue;
							} else if ( sibling.type == CKEDITOR.NODE_TEXT ) {
								siblingText = sibling.getText();

								if ( /[^\s\ufeff]/.test( siblingText ) )
									sibling = null;

								isWhiteSpace = /[\s\ufeff]$/.test( siblingText );
							} else {
								// If this is a visible element.
								// We need to check for the bookmark attribute because IE insists on
								// rendering the display:none nodes we use for bookmarks. (#3363)
								// Line-breaks (br) are rendered with zero width, which we don't want to include. (#7041)
								if ( ( sibling.$.offsetWidth > 0 || excludeBrs && sibling.is( 'br' ) ) && !sibling.data( 'cke-bookmark' ) ) {
									// We'll accept it only if we need
									// whitespace, and this is an inline
									// element with whitespace only.
									if ( needsWhiteSpace && CKEDITOR.dtd.$removeEmpty[ sibling.getName() ] ) {
										// It must contains spaces and inline elements only.

										siblingText = sibling.getText();

										if ( ( /[^\s\ufeff]/ ).test( siblingText ) ) // Spaces + Zero Width No-Break Space (U+FEFF)
										sibling = null;
										else {
											var allChildren = sibling.$.getElementsByTagName( '*' );
											for ( var i = 0, child; child = allChildren[ i++ ]; ) {
												if ( !CKEDITOR.dtd.$removeEmpty[ child.nodeName.toLowerCase() ] ) {
													sibling = null;
													break;
												}
											}
										}

										if ( sibling )
											isWhiteSpace = !!siblingText.length;
									} else
										sibling = null;
								}
							}

							// A node with whitespaces has been found.
							if ( isWhiteSpace ) {
								// Enlarge the last enlargeable node, if we
								// were waiting for spaces.
								if ( needsWhiteSpace ) {
									if ( commonReached )
										startTop = enlargeable;
									else if ( enlargeable )
										this.setStartBefore( enlargeable );
								} else
									needsWhiteSpace = true;
							}

							if ( sibling ) {
								var next = sibling.getPrevious();

								if ( !enlargeable && !next ) {
									// Set the sibling as enlargeable, so it's
									// parent will be get later outside this while.
									enlargeable = sibling;
									sibling = null;
									break;
								}

								sibling = next;
							} else {
								// If sibling has been set to null, then we
								// need to stop enlarging.
								enlargeable = null;
							}
						}

						if ( enlargeable )
							enlargeable = enlargeable.getParent();
					}

					// Process the end boundary. This is basically the same
					// code used for the start boundary, with small changes to
					// make it work in the oposite side (to the right). This
					// makes it difficult to reuse the code here. So, fixes to
					// the above code are likely to be replicated here.

					container = this.endContainer;
					offset = this.endOffset;

					// Reset the common variables.
					enlargeable = sibling = null;
					commonReached = needsWhiteSpace = false;

					if ( container.type == CKEDITOR.NODE_TEXT ) {
						// Check if there is any non-space text after the
						// offset. Otherwise, container is null.
						container = !CKEDITOR.tools.trim( container.substring( offset ) ).length && container;

						// If we found only whitespace in the node, it
						// means that we'll need more whitespace to be able
						// to expand. For example, <i> can be expanded in
						// "A <i> [B]</i>", but not in "A<i> [B]</i>".
						needsWhiteSpace = !( container && container.getLength() );

						if ( container ) {
							if ( !( sibling = container.getNext() ) )
								enlargeable = container.getParent();
						}
					} else {
						// Get the node right after the boudary to be checked
						// first.
						sibling = container.getChild( offset );

						if ( !sibling )
							enlargeable = container;
					}

					while ( enlargeable || sibling ) {
						if ( enlargeable && !sibling ) {
							if ( !commonReached && enlargeable.equals( commonAncestor ) )
								commonReached = true;

							if ( enlargeInlineOnly ? enlargeable.isBlockBoundary() : !boundary.contains( enlargeable ) )
								break;

							if ( !needsWhiteSpace || enlargeable.getComputedStyle( 'display' ) != 'inline' ) {
								needsWhiteSpace = false;

								if ( commonReached )
									endTop = enlargeable;
								else if ( enlargeable )
									this.setEndAfter( enlargeable );
							}

							sibling = enlargeable.getNext();
						}

						while ( sibling ) {
							isWhiteSpace = false;

							if ( sibling.type == CKEDITOR.NODE_TEXT ) {
								siblingText = sibling.getText();

								if ( /[^\s\ufeff]/.test( siblingText ) )
									sibling = null;

								isWhiteSpace = /^[\s\ufeff]/.test( siblingText );
							} else if ( sibling.type == CKEDITOR.NODE_ELEMENT ) {
								// If this is a visible element.
								// We need to check for the bookmark attribute because IE insists on
								// rendering the display:none nodes we use for bookmarks. (#3363)
								// Line-breaks (br) are rendered with zero width, which we don't want to include. (#7041)
								if ( ( sibling.$.offsetWidth > 0 || excludeBrs && sibling.is( 'br' ) ) && !sibling.data( 'cke-bookmark' ) ) {
									// We'll accept it only if we need
									// whitespace, and this is an inline
									// element with whitespace only.
									if ( needsWhiteSpace && CKEDITOR.dtd.$removeEmpty[ sibling.getName() ] ) {
										// It must contains spaces and inline elements only.

										siblingText = sibling.getText();

										if ( ( /[^\s\ufeff]/ ).test( siblingText ) )
											sibling = null;
										else {
											allChildren = sibling.$.getElementsByTagName( '*' );
											for ( i = 0; child = allChildren[ i++ ]; ) {
												if ( !CKEDITOR.dtd.$removeEmpty[ child.nodeName.toLowerCase() ] ) {
													sibling = null;
													break;
												}
											}
										}

										if ( sibling )
											isWhiteSpace = !!siblingText.length;
									} else
										sibling = null;
								}
							} else
								isWhiteSpace = 1;

							if ( isWhiteSpace ) {
								if ( needsWhiteSpace ) {
									if ( commonReached )
										endTop = enlargeable;
									else
										this.setEndAfter( enlargeable );
								}
							}

							if ( sibling ) {
								next = sibling.getNext();

								if ( !enlargeable && !next ) {
									enlargeable = sibling;
									sibling = null;
									break;
								}

								sibling = next;
							} else {
								// If sibling has been set to null, then we
								// need to stop enlarging.
								enlargeable = null;
							}
						}

						if ( enlargeable )
							enlargeable = enlargeable.getParent();
					}

					// If the common ancestor can be enlarged by both boundaries, then include it also.
					if ( startTop && endTop ) {
						commonAncestor = startTop.contains( endTop ) ? endTop : startTop;

						this.setStartBefore( commonAncestor );
						this.setEndAfter( commonAncestor );
					}
					break;

				case CKEDITOR.ENLARGE_BLOCK_CONTENTS:
				case CKEDITOR.ENLARGE_LIST_ITEM_CONTENTS:

					// Enlarging the start boundary.
					var walkerRange = new CKEDITOR.dom.range( this.root );

					boundary = this.root;

					walkerRange.setStartAt( boundary, CKEDITOR.POSITION_AFTER_START );
					walkerRange.setEnd( this.startContainer, this.startOffset );

					var walker = new CKEDITOR.dom.walker( walkerRange ),
						blockBoundary, // The node on which the enlarging should stop.
						tailBr, // In case BR as block boundary.
						notBlockBoundary = CKEDITOR.dom.walker.blockBoundary(
						( unit == CKEDITOR.ENLARGE_LIST_ITEM_CONTENTS ) ? { br:1 } : null ),
						// Record the encountered 'blockBoundary' for later use.
						boundaryGuard = function( node ) {
							var retval = notBlockBoundary( node );
							if ( !retval )
								blockBoundary = node;
							return retval;
						},
						// Record the encounted 'tailBr' for later use.
						tailBrGuard = function( node ) {
							var retval = boundaryGuard( node );
							if ( !retval && node.is && node.is( 'br' ) )
								tailBr = node;
							return retval;
						};

					walker.guard = boundaryGuard;

					enlargeable = walker.lastBackward();

					// It's the body which stop the enlarging if no block boundary found.
					blockBoundary = blockBoundary || boundary;

					// Start the range either after the end of found block (<p>...</p>[text)
					// or at the start of block (<p>[text...), by comparing the document position
					// with 'enlargeable' node.
					this.setStartAt( blockBoundary, !blockBoundary.is( 'br' ) && ( !enlargeable && this.checkStartOfBlock() || enlargeable && blockBoundary.contains( enlargeable ) ) ? CKEDITOR.POSITION_AFTER_START : CKEDITOR.POSITION_AFTER_END );

					// Avoid enlarging the range further when end boundary spans right after the BR. (#7490)
					if ( unit == CKEDITOR.ENLARGE_LIST_ITEM_CONTENTS ) {
						var theRange = this.clone();
						walker = new CKEDITOR.dom.walker( theRange );

						var whitespaces = CKEDITOR.dom.walker.whitespaces(),
							bookmark = CKEDITOR.dom.walker.bookmark();

						walker.evaluator = function( node ) {
							return !whitespaces( node ) && !bookmark( node );
						};
						var previous = walker.previous();
						if ( previous && previous.type == CKEDITOR.NODE_ELEMENT && previous.is( 'br' ) )
							return;
					}


					// Enlarging the end boundary.
					walkerRange = this.clone();
					walkerRange.collapse();
					walkerRange.setEndAt( boundary, CKEDITOR.POSITION_BEFORE_END );
					walker = new CKEDITOR.dom.walker( walkerRange );

					// tailBrGuard only used for on range end.
					walker.guard = ( unit == CKEDITOR.ENLARGE_LIST_ITEM_CONTENTS ) ? tailBrGuard : boundaryGuard;
					blockBoundary = null;
					// End the range right before the block boundary node.

					enlargeable = walker.lastForward();

					// It's the body which stop the enlarging if no block boundary found.
					blockBoundary = blockBoundary || boundary;

					// Close the range either before the found block start (text]<p>...</p>) or at the block end (...text]</p>)
					// by comparing the document position with 'enlargeable' node.
					this.setEndAt( blockBoundary, ( !enlargeable && this.checkEndOfBlock() || enlargeable && blockBoundary.contains( enlargeable ) ) ? CKEDITOR.POSITION_BEFORE_END : CKEDITOR.POSITION_BEFORE_START );
					// We must include the <br> at the end of range if there's
					// one and we're expanding list item contents
					if ( tailBr )
						this.setEndAfter( tailBr );
			}
		},

		/**
		 * Descrease the range to make sure that boundaries
		 * always anchor beside text nodes or innermost element.
		 *
		 * @param {Number} mode The shrinking mode ({@link CKEDITOR#SHRINK_ELEMENT} or {@link CKEDITOR#SHRINK_TEXT}).
		 *
		 * * {@link CKEDITOR#SHRINK_ELEMENT} - Shrink the range boundaries to the edge of the innermost element.
		 * * {@link CKEDITOR#SHRINK_TEXT} - Shrink the range boudaries to anchor by the side of enclosed text
		 *     node, range remains if there's no text nodes on boundaries at all.
		 *
		 * @param {Boolean} selectContents Whether result range anchors at the inner OR outer boundary of the node.
		 */
		shrink: function( mode, selectContents, shrinkOnBlockBoundary ) {
			// Unable to shrink a collapsed range.
			if ( !this.collapsed ) {
				mode = mode || CKEDITOR.SHRINK_TEXT;

				var walkerRange = this.clone();

				var startContainer = this.startContainer,
					endContainer = this.endContainer,
					startOffset = this.startOffset,
					endOffset = this.endOffset,
					collapsed = this.collapsed;

				// Whether the start/end boundary is moveable.
				var moveStart = 1,
					moveEnd = 1;

				if ( startContainer && startContainer.type == CKEDITOR.NODE_TEXT ) {
					if ( !startOffset )
						walkerRange.setStartBefore( startContainer );
					else if ( startOffset >= startContainer.getLength() )
						walkerRange.setStartAfter( startContainer );
					else {
						// Enlarge the range properly to avoid walker making
						// DOM changes caused by triming the text nodes later.
						walkerRange.setStartBefore( startContainer );
						moveStart = 0;
					}
				}

				if ( endContainer && endContainer.type == CKEDITOR.NODE_TEXT ) {
					if ( !endOffset )
						walkerRange.setEndBefore( endContainer );
					else if ( endOffset >= endContainer.getLength() )
						walkerRange.setEndAfter( endContainer );
					else {
						walkerRange.setEndAfter( endContainer );
						moveEnd = 0;
					}
				}

				var walker = new CKEDITOR.dom.walker( walkerRange ),
					isBookmark = CKEDITOR.dom.walker.bookmark();

				walker.evaluator = function( node ) {
					return node.type == ( mode == CKEDITOR.SHRINK_ELEMENT ? CKEDITOR.NODE_ELEMENT : CKEDITOR.NODE_TEXT );
				};

				var currentElement;
				walker.guard = function( node, movingOut ) {
					if ( isBookmark( node ) )
						return true;

					// Stop when we're shrink in element mode while encountering a text node.
					if ( mode == CKEDITOR.SHRINK_ELEMENT && node.type == CKEDITOR.NODE_TEXT )
						return false;

					// Stop when we've already walked "through" an element.
					if ( movingOut && node.equals( currentElement ) )
						return false;

					if ( shrinkOnBlockBoundary === false && node.type == CKEDITOR.NODE_ELEMENT && node.isBlockBoundary() )
						return false;

					if ( !movingOut && node.type == CKEDITOR.NODE_ELEMENT )
						currentElement = node;

					return true;
				};

				if ( moveStart ) {
					var textStart = walker[ mode == CKEDITOR.SHRINK_ELEMENT ? 'lastForward' : 'next' ]();
					textStart && this.setStartAt( textStart, selectContents ? CKEDITOR.POSITION_AFTER_START : CKEDITOR.POSITION_BEFORE_START );
				}

				if ( moveEnd ) {
					walker.reset();
					var textEnd = walker[ mode == CKEDITOR.SHRINK_ELEMENT ? 'lastBackward' : 'previous' ]();
					textEnd && this.setEndAt( textEnd, selectContents ? CKEDITOR.POSITION_BEFORE_END : CKEDITOR.POSITION_AFTER_END );
				}

				return !!( moveStart || moveEnd );
			}
		},

		/**
		 * Inserts a node at the start of the range. The range will be expanded
		 * the contain the node.
		 *
		 * @param {CKEDITOR.dom.node} node
		 */
		insertNode: function( node ) {
			this.optimizeBookmark();
			this.trim( false, true );

			var startContainer = this.startContainer;
			var startOffset = this.startOffset;

			var nextNode = startContainer.getChild( startOffset );

			if ( nextNode )
				node.insertBefore( nextNode );
			else
				startContainer.append( node );

			// Check if we need to update the end boundary.
			if ( node.getParent() && node.getParent().equals( this.endContainer ) )
				this.endOffset++;

			// Expand the range to embrace the new node.
			this.setStartBefore( node );
		},

		/**
		 * @todo
		 */
		moveToPosition: function( node, position ) {
			this.setStartAt( node, position );
			this.collapse( true );
		},

		/**
		 * @todo
		 */
		moveToRange: function( range ) {
			this.setStart( range.startContainer, range.startOffset );
			this.setEnd( range.endContainer, range.endOffset );
		},

		/**
		 * Select nodes content. Range will start and end inside this node.
		 *
		 * @param {CKEDITOR.dom.node} node
		 */
		selectNodeContents: function( node ) {
			this.setStart( node, 0 );
			this.setEnd( node, node.type == CKEDITOR.NODE_TEXT ? node.getLength() : node.getChildCount() );
		},

		/**
		 * Sets the start position of a range.
		 *
		 * @param {CKEDITOR.dom.node} startNode The node to start the range.
		 * @param {Number} startOffset An integer greater than or equal to zero
		 * representing the offset for the start of the range from the start
		 * of `startNode`.
		 */
		setStart: function( startNode, startOffset ) {
			// W3C requires a check for the new position. If it is after the end
			// boundary, the range should be collapsed to the new start. It seams
			// we will not need this check for our use of this class so we can
			// ignore it for now.

			// Fixing invalid range start inside dtd empty elements.
			if ( startNode.type == CKEDITOR.NODE_ELEMENT && CKEDITOR.dtd.$empty[ startNode.getName() ] )
				startOffset = startNode.getIndex(), startNode = startNode.getParent();

			this.startContainer = startNode;
			this.startOffset = startOffset;

			if ( !this.endContainer ) {
				this.endContainer = startNode;
				this.endOffset = startOffset;
			}

			updateCollapsed( this );
		},

		/**
		 * Sets the end position of a Range.
		 *
		 * @param {CKEDITOR.dom.node} endNode The node to end the range.
		 * @param {Number} endOffset An integer greater than or equal to zero
		 * representing the offset for the end of the range from the start
		 * of `endNode`.
		 */
		setEnd: function( endNode, endOffset ) {
			// W3C requires a check for the new position. If it is before the start
			// boundary, the range should be collapsed to the new end. It seams we
			// will not need this check for our use of this class so we can ignore
			// it for now.

			// Fixing invalid range end inside dtd empty elements.
			if ( endNode.type == CKEDITOR.NODE_ELEMENT && CKEDITOR.dtd.$empty[ endNode.getName() ] )
				endOffset = endNode.getIndex() + 1, endNode = endNode.getParent();

			this.endContainer = endNode;
			this.endOffset = endOffset;

			if ( !this.startContainer ) {
				this.startContainer = endNode;
				this.startOffset = endOffset;
			}

			updateCollapsed( this );
		},

		/**
		 * @todo
		 */
		setStartAfter: function( node ) {
			this.setStart( node.getParent(), node.getIndex() + 1 );
		},

		/**
		 * @todo
		 */
		setStartBefore: function( node ) {
			this.setStart( node.getParent(), node.getIndex() );
		},

		/**
		 * @todo
		 */
		setEndAfter: function( node ) {
			this.setEnd( node.getParent(), node.getIndex() + 1 );
		},

		/**
		 * @todo
		 */
		setEndBefore: function( node ) {
			this.setEnd( node.getParent(), node.getIndex() );
		},

		/**
		 * @todo
		 */
		setStartAt: function( node, position ) {
			switch ( position ) {
				case CKEDITOR.POSITION_AFTER_START:
					this.setStart( node, 0 );
					break;

				case CKEDITOR.POSITION_BEFORE_END:
					if ( node.type == CKEDITOR.NODE_TEXT )
						this.setStart( node, node.getLength() );
					else
						this.setStart( node, node.getChildCount() );
					break;

				case CKEDITOR.POSITION_BEFORE_START:
					this.setStartBefore( node );
					break;

				case CKEDITOR.POSITION_AFTER_END:
					this.setStartAfter( node );
			}

			updateCollapsed( this );
		},

		/**
		 * @todo
		 */
		setEndAt: function( node, position ) {
			switch ( position ) {
				case CKEDITOR.POSITION_AFTER_START:
					this.setEnd( node, 0 );
					break;

				case CKEDITOR.POSITION_BEFORE_END:
					if ( node.type == CKEDITOR.NODE_TEXT )
						this.setEnd( node, node.getLength() );
					else
						this.setEnd( node, node.getChildCount() );
					break;

				case CKEDITOR.POSITION_BEFORE_START:
					this.setEndBefore( node );
					break;

				case CKEDITOR.POSITION_AFTER_END:
					this.setEndAfter( node );
			}

			updateCollapsed( this );
		},

		/**
		 * @todo
		 */
		fixBlock: function( isStart, blockTag ) {
			var bookmark = this.createBookmark(),
				fixedBlock = this.document.createElement( blockTag );

			this.collapse( isStart );

			this.enlarge( CKEDITOR.ENLARGE_BLOCK_CONTENTS );

			this.extractContents().appendTo( fixedBlock );
			fixedBlock.trim();

			if ( !CKEDITOR.env.ie )
				fixedBlock.appendBogus();

			this.insertNode( fixedBlock );

			this.moveToBookmark( bookmark );

			return fixedBlock;
		},

		/**
		 * @todo
		 */
		splitBlock: function( blockTag ) {
			var startPath = new CKEDITOR.dom.elementPath( this.startContainer, this.root ),
				endPath = new CKEDITOR.dom.elementPath( this.endContainer, this.root );

			var startBlockLimit = startPath.blockLimit,
				endBlockLimit = endPath.blockLimit;

			var startBlock = startPath.block,
				endBlock = endPath.block;

			var elementPath = null;
			// Do nothing if the boundaries are in different block limits.
			if ( !startBlockLimit.equals( endBlockLimit ) )
				return null;

			// Get or fix current blocks.
			if ( blockTag != 'br' ) {
				if ( !startBlock ) {
					startBlock = this.fixBlock( true, blockTag );
					endBlock = new CKEDITOR.dom.elementPath( this.endContainer, this.root ).block;
				}

				if ( !endBlock )
					endBlock = this.fixBlock( false, blockTag );
			}

			// Get the range position.
			var isStartOfBlock = startBlock && this.checkStartOfBlock(),
				isEndOfBlock = endBlock && this.checkEndOfBlock();

			// Delete the current contents.
			// TODO: Why is 2.x doing CheckIsEmpty()?
			this.deleteContents();

			if ( startBlock && startBlock.equals( endBlock ) ) {
				if ( isEndOfBlock ) {
					elementPath = new CKEDITOR.dom.elementPath( this.startContainer, this.root );
					this.moveToPosition( endBlock, CKEDITOR.POSITION_AFTER_END );
					endBlock = null;
				} else if ( isStartOfBlock ) {
					elementPath = new CKEDITOR.dom.elementPath( this.startContainer, this.root );
					this.moveToPosition( startBlock, CKEDITOR.POSITION_BEFORE_START );
					startBlock = null;
				} else {
					endBlock = this.splitElement( startBlock );

					// In Gecko, the last child node must be a bogus <br>.
					// Note: bogus <br> added under <ul> or <ol> would cause
					// lists to be incorrectly rendered.
					if ( !CKEDITOR.env.ie && !startBlock.is( 'ul', 'ol' ) )
						startBlock.appendBogus();
				}
			}

			return {
				previousBlock: startBlock,
				nextBlock: endBlock,
				wasStartOfBlock: isStartOfBlock,
				wasEndOfBlock: isEndOfBlock,
				elementPath: elementPath
			};
		},

		/**
		 * Branch the specified element from the collapsed range position and
		 * place the caret between the two result branches.
		 *
		 * **Note:** The range must be collapsed and been enclosed by this element.
		 *
		 * @param {CKEDITOR.dom.element} element
		 * @returns {CKEDITOR.dom.element} Root element of the new branch after the split.
		 */
		splitElement: function( toSplit ) {
			if ( !this.collapsed )
				return null;

			// Extract the contents of the block from the selection point to the end
			// of its contents.
			this.setEndAt( toSplit, CKEDITOR.POSITION_BEFORE_END );
			var documentFragment = this.extractContents();

			// Duplicate the element after it.
			var clone = toSplit.clone( false );

			// Place the extracted contents into the duplicated element.
			documentFragment.appendTo( clone );
			clone.insertAfter( toSplit );
			this.moveToPosition( toSplit, CKEDITOR.POSITION_AFTER_END );
			return clone;
		},

		/**
		 * Recursively remove any empty path blocks at the range boundary.
		 *
		 * @method
		 * @param {Boolean} atEnd Removal to perform at the end boundary,
		 * otherwise to perform at the start.
		 */
		removeEmptyBlocksAtEnd: (function() {

			var whitespace = CKEDITOR.dom.walker.whitespaces(),
					bookmark = CKEDITOR.dom.walker.bookmark( false );

			function childEval( parent ) {
				return function( node ) {

					// whitespace, bookmarks, empty inlines.
					if ( whitespace( node ) || bookmark( node ) ||
					     node.type == CKEDITOR.NODE_ELEMENT &&
					     node.isEmptyInlineRemoveable() )
						return false;
					else if ( parent.is( 'table' ) && node.is( 'caption' ) )
						return false;

					return true;
				};
			}

			return function( atEnd ) {

				var bm = this.createBookmark();
				var path = this[ atEnd ? 'endPath' : 'startPath' ]();
				var block = path.block || path.blockLimit, parent;

				// Remove any childless block, including list and table.
				while ( block && !block.equals( path.root ) &&
				        !block.getFirst( childEval( block ) ) )
				{
					parent = block.getParent();
					this[ atEnd ? 'setEndAt' : 'setStartAt' ]( block, CKEDITOR.POSITION_AFTER_END );
					block.remove( 1 );
					block = parent;
				}

				this.moveToBookmark( bm );
			};

		})(),

		/**
		 * Gets {@link CKEDITOR.dom.elementPath} for the {@link #startContainer}.
		 *
		 * @returns {CKEDITOR.dom.elementPath}
		 */
		startPath: function() {
			return new CKEDITOR.dom.elementPath( this.startContainer, this.root );
		},

		/**
		 * Gets {@link CKEDITOR.dom.elementPath} for the {@link #endContainer}.
		 *
		 * @returns {CKEDITOR.dom.elementPath}
		 */
		endPath: function() {
			return new CKEDITOR.dom.elementPath( this.endContainer, this.root );
		},

		/**
		 * Check whether a range boundary is at the inner boundary of a given
		 * element.
		 *
		 * @param {CKEDITOR.dom.element} element The target element to check.
		 * @param {Number} checkType The boundary to check for both the range
		 * and the element. It can be {@link CKEDITOR#START} or {@link CKEDITOR#END}.
		 * @returns {Boolean} `true` if the range boundary is at the inner
		 * boundary of the element.
		 */
		checkBoundaryOfElement: function( element, checkType ) {
			var checkStart = ( checkType == CKEDITOR.START );

			// Create a copy of this range, so we can manipulate it for our checks.
			var walkerRange = this.clone();

			// Collapse the range at the proper size.
			walkerRange.collapse( checkStart );

			// Expand the range to element boundary.
			walkerRange[ checkStart ? 'setStartAt' : 'setEndAt' ]
			( element, checkStart ? CKEDITOR.POSITION_AFTER_START : CKEDITOR.POSITION_BEFORE_END );

			// Create the walker, which will check if we have anything useful
			// in the range.
			var walker = new CKEDITOR.dom.walker( walkerRange );
			walker.evaluator = elementBoundaryEval( checkStart );

			return walker[ checkStart ? 'checkBackward' : 'checkForward' ]();
		},

		/**
		 * **Note:** Calls to this function may produce changes to the DOM. The range may
		 * be updated to reflect such changes.
		 *
		 * @returns {Boolean}
		 * @todo
		 */
		checkStartOfBlock: function() {
			var startContainer = this.startContainer,
				startOffset = this.startOffset;

			// [IE] Special handling for range start in text with a leading NBSP,
			// we it to be isolated, for bogus check.
			if ( CKEDITOR.env.ie && startOffset && startContainer.type == CKEDITOR.NODE_TEXT )
			{
				var textBefore = CKEDITOR.tools.ltrim( startContainer.substring( 0, startOffset ) );
				if ( nbspRegExp.test( textBefore ) )
					this.trim( 0, 1 );
			}

			// Antecipate the trim() call here, so the walker will not make
			// changes to the DOM, which would not get reflected into this
			// range otherwise.
			this.trim();

			// We need to grab the block element holding the start boundary, so
			// let's use an element path for it.
			var path = new CKEDITOR.dom.elementPath( this.startContainer, this.root );

			// Creates a range starting at the block start until the range start.
			var walkerRange = this.clone();
			walkerRange.collapse( true );
			walkerRange.setStartAt( path.block || path.blockLimit, CKEDITOR.POSITION_AFTER_START );

			var walker = new CKEDITOR.dom.walker( walkerRange );
			walker.evaluator = getCheckStartEndBlockEvalFunction();

			return walker.checkBackward();
		},

		/**
		 * **Note:** Calls to this function may produce changes to the DOM. The range may
		 * be updated to reflect such changes.
		 *
		 * @returns {Boolean}
		 * @todo
		 */
		checkEndOfBlock: function() {
			var endContainer = this.endContainer,
				endOffset = this.endOffset;

			// [IE] Special handling for range end in text with a following NBSP,
			// we it to be isolated, for bogus check.
			if ( CKEDITOR.env.ie && endContainer.type == CKEDITOR.NODE_TEXT )
			{
				var textAfter = CKEDITOR.tools.rtrim( endContainer.substring( endOffset ) );
				if ( nbspRegExp.test( textAfter ) )
					this.trim( 1, 0 );
			}

			// Antecipate the trim() call here, so the walker will not make
			// changes to the DOM, which would not get reflected into this
			// range otherwise.
			this.trim();

			// We need to grab the block element holding the start boundary, so
			// let's use an element path for it.
			var path = new CKEDITOR.dom.elementPath( this.endContainer, this.root );

			// Creates a range starting at the block start until the range start.
			var walkerRange = this.clone();
			walkerRange.collapse( false );
			walkerRange.setEndAt( path.block || path.blockLimit, CKEDITOR.POSITION_BEFORE_END );

			var walker = new CKEDITOR.dom.walker( walkerRange );
			walker.evaluator = getCheckStartEndBlockEvalFunction();

			return walker.checkForward();
		},

		/**
		 * Traverse with {@link CKEDITOR.dom.walker} to retrieve the previous element before the range start.
		 *
		 * @param {Function} evaluator Function used as the walker's evaluator.
		 * @param {Function} [guard] Function used as the walker's guard.
		 * @param {CKEDITOR.dom.element} [boundary] A range ancestor element in which the traversal is limited,
		 * default to the root editable if not defined.
		 * @returns {CKEDITOR.dom.element/null} The returned node from the traversal.
		 */
		getPreviousNode : function( evaluator, guard, boundary ) {
			var walkerRange = this.clone();
			walkerRange.collapse( 1 );
			walkerRange.setStartAt( boundary || this.root, CKEDITOR.POSITION_AFTER_START );

			var walker = new CKEDITOR.dom.walker( walkerRange );
			walker.evaluator = evaluator;
			walker.guard = guard;
			return walker.previous();
		},

		/**
		 * Traverse with {@link CKEDITOR.dom.walker} to retrieve the next element before the range start.
		 *
		 * @param {Function} evaluator Function used as the walker's evaluator.
		 * @param {Function} [guard] Function used as the walker's guard.
		 * @param {CKEDITOR.dom.element} [boundary] A range ancestor element in which the traversal is limited,
		 * default to the root editable if not defined.
		 * @returns {CKEDITOR.dom.element/null} The returned node from the traversal.
		 */
		getNextNode: function( evaluator, guard, boundary ) {
			var walkerRange = this.clone();
			walkerRange.collapse();
			walkerRange.setEndAt( boundary || this.root, CKEDITOR.POSITION_BEFORE_END );

			var walker = new CKEDITOR.dom.walker( walkerRange );
			walker.evaluator = evaluator;
			walker.guard = guard;
			return walker.next();
		},

		/**
		 * Check if elements at which the range boundaries anchor are read-only,
		 * with respect to `contenteditable` attribute.
		 *
		 * @returns {Boolean}
		 */
		checkReadOnly: (function() {
			function checkNodesEditable( node, anotherEnd ) {
				while ( node ) {
					if ( node.type == CKEDITOR.NODE_ELEMENT ) {
						if ( node.getAttribute( 'contentEditable' ) == 'false' && !node.data( 'cke-editable' ) ) {
							return 0;
						}
						// Range enclosed entirely in an editable element.
						else if ( node.is( 'html' ) || node.getAttribute( 'contentEditable' ) == 'true' && ( node.contains( anotherEnd ) || node.equals( anotherEnd ) ) ) {
							break;
						}
					}
					node = node.getParent();
				}

				return 1;
			}

			return function() {
				var startNode = this.startContainer,
					endNode = this.endContainer;

				// Check if elements path at both boundaries are editable.
				return !( checkNodesEditable( startNode, endNode ) && checkNodesEditable( endNode, startNode ) );
			};
		})(),

		/**
		 * Moves the range boundaries to the first/end editing point inside an
		 * element.
		 *
		 * For example, in an element tree like
		 * `<p><b><i></i></b> Text</p>`, the start editing point is
		 * `<p><b><i>^</i></b> Text</p>` (inside `<i>`).
		 *
		 * @param {CKEDITOR.dom.element} el The element into which look for the
		 * editing spot.
		 * @param {Boolean} isMoveToEnd Whether move to the end editable position.
		 * @returns {Boolean} Whether range was moved.
		 */
		moveToElementEditablePosition: function( el, isMoveToEnd ) {

			function nextDFS( node, childOnly ) {
				var next;

				if ( node.type == CKEDITOR.NODE_ELEMENT && node.isEditable( false ) )
					next = node[ isMoveToEnd ? 'getLast' : 'getFirst' ]( notIgnoredEval );

				if ( !childOnly && !next )
					next = node[ isMoveToEnd ? 'getPrevious' : 'getNext' ]( notIgnoredEval );

				return next;
			}

			// Handle non-editable element e.g. HR.
			if ( el.type == CKEDITOR.NODE_ELEMENT && !el.isEditable( false ) ) {
				this.moveToPosition( el, isMoveToEnd ? CKEDITOR.POSITION_AFTER_END : CKEDITOR.POSITION_BEFORE_START );
				return true;
			}

			var found = 0;

			while ( el ) {
				// Stop immediately if we've found a text node.
				if ( el.type == CKEDITOR.NODE_TEXT ) {
					// Put cursor before block filler.
					if ( isMoveToEnd && this.endContainer && this.checkEndOfBlock() && nbspRegExp.test( el.getText() ) )
						this.moveToPosition( el, CKEDITOR.POSITION_BEFORE_START );
					else
						this.moveToPosition( el, isMoveToEnd ? CKEDITOR.POSITION_AFTER_END : CKEDITOR.POSITION_BEFORE_START );
					found = 1;
					break;
				}

				// If an editable element is found, move inside it, but not stop the searching.
				if ( el.type == CKEDITOR.NODE_ELEMENT ) {
					if ( el.isEditable() ) {
						this.moveToPosition( el, isMoveToEnd ? CKEDITOR.POSITION_BEFORE_END : CKEDITOR.POSITION_AFTER_START );
						found = 1;
					}
					// Put cursor before padding block br.
					else if ( isMoveToEnd && el.is( 'br' ) && this.endContainer && this.checkEndOfBlock() )
						this.moveToPosition( el, CKEDITOR.POSITION_BEFORE_START );
					// Special case - non-editable block. Select entire element, because it does not make sense
					// to place collapsed selection next to it, because browsers can't handle that.
					else if ( el.getAttribute( 'contenteditable' ) == 'false' && el.is( CKEDITOR.dtd.$block ) ) {
						this.setStartBefore( el );
						this.setEndAfter( el );
						return true;
					}
				}

				el = nextDFS( el, found );
			}

			return !!found;
		},

		/**
		 * Moves the range boundaries to the closest editing point after/before an
		 * element.
		 *
		 * For example, if the start element has `id="start"`,
		 * `<p><b>foo</b><span id="start">start</start></p>`, the closest previous editing point is
		 * `<p><b>foo</b>^<span id="start">start</start></p>` (between `<b>` and `<span>`).
		 *
		 * See also: {@link #moveToElementEditablePosition}.
		 *
		 * @since 4.3
		 * @param {CKEDITOR.dom.element} element The starting element.
		 * @param {Boolean} isMoveToEnd Whether move to the end of editable. Otherwise, look back.
		 * @returns {Boolean} Whether the range was moved.
		 */
		moveToClosestEditablePosition: function( element, isMoveToEnd ) {
			// We don't want to modify original range if there's no editable position.
			var range = new CKEDITOR.dom.range( this.root ),
				found = 0,
				sibling,
				positions = [ CKEDITOR.POSITION_AFTER_END, CKEDITOR.POSITION_BEFORE_START ];

			// Set collapsed range at one of ends of element.
			range.moveToPosition( element, positions[ isMoveToEnd ? 0 : 1 ] );

			// Start element isn't a block, so we can automatically place range
			// next to it.
			if ( !element.is( CKEDITOR.dtd.$block ) )
				found = 1;
			else {
				// Look for first node that fulfills eval function and place range next to it.
				sibling = range[ isMoveToEnd ? 'getNextEditableNode' : 'getPreviousEditableNode' ]();
				if ( sibling ) {
					found = 1;

					// Special case - eval accepts block element only if it's a non-editable block,
					// which we want to select, not place collapsed selection next to it (which browsers
					// can't handle).
					if ( sibling.type == CKEDITOR.NODE_ELEMENT && sibling.is( CKEDITOR.dtd.$block ) && sibling.getAttribute( 'contenteditable' ) == 'false' ) {
						range.setStartAt( sibling, CKEDITOR.POSITION_BEFORE_START );
						range.setEndAt( sibling, CKEDITOR.POSITION_AFTER_END );
					}
					else
						range.moveToPosition( sibling, positions[ isMoveToEnd ? 1 : 0 ] );
				}
			}

			if ( found )
				this.moveToRange( range );

			return !!found;
		},

		/**
		 * See {@link #moveToElementEditablePosition}.
		 *
		 * @returns {Boolean} Whether range was moved.
		 */
		moveToElementEditStart: function( target ) {
			return this.moveToElementEditablePosition( target );
		},

		/**
		 * See {@link #moveToElementEditablePosition}.
		 *
		 * @returns {Boolean} Whether range was moved.
		 */
		moveToElementEditEnd: function( target ) {
			return this.moveToElementEditablePosition( target, true );
		},

		/**
		 * Get the single node enclosed within the range if there's one.
		 *
		 * @returns {CKEDITOR.dom.node}
		 */
		getEnclosedNode: function() {
			var walkerRange = this.clone();

			// Optimize and analyze the range to avoid DOM destructive nature of walker. (#5780)
			walkerRange.optimize();
			if ( walkerRange.startContainer.type != CKEDITOR.NODE_ELEMENT || walkerRange.endContainer.type != CKEDITOR.NODE_ELEMENT )
				return null;

			var walker = new CKEDITOR.dom.walker( walkerRange ),
				isNotBookmarks = CKEDITOR.dom.walker.bookmark( false, true ),
				isNotWhitespaces = CKEDITOR.dom.walker.whitespaces( true );

			walker.evaluator = function( node ) {
				return isNotWhitespaces( node ) && isNotBookmarks( node );
			};
			var node = walker.next();
			walker.reset();
			return node && node.equals( walker.previous() ) ? node : null;
		},

		/**
		 * Get the node adjacent to the range start or {@link #startContainer}.
		 *
		 * @returns {CKEDITOR.dom.node}
		 */
		getTouchedStartNode: function() {
			var container = this.startContainer;

			if ( this.collapsed || container.type != CKEDITOR.NODE_ELEMENT )
				return container;

			return container.getChild( this.startOffset ) || container;
		},

		/**
		 * Get the node adjacent to the range end or {@link #endContainer}.
		 *
		 * @returns {CKEDITOR.dom.node}
		 */
		getTouchedEndNode: function() {
			var container = this.endContainer;

			if ( this.collapsed || container.type != CKEDITOR.NODE_ELEMENT )
				return container;

			return container.getChild( this.endOffset - 1 ) || container;
		},

		/**
		 * Gets next node which can be a container of a selection.
		 * This methods mimics a behavior of right/left arrow keys in case of
		 * collapsed selection. It does not return an exact position (with offset) though,
		 * but just a selection's container.
		 *
		 * Note: use this method on a collapsed range.
		 *
		 * @returns {CKEDITOR.node.element/CKEDITOR.node.text}
		 */
		getNextEditableNode: getNextEditableNode(),

		/**
		 * See {@link #getNextEditableNode}.
		 *
		 * @returns {CKEDITOR.node.element/CKEDITOR.node.text}
		 */
		getPreviousEditableNode: getNextEditableNode( 1 ),

		/**
		 * Scrolls the start of current range into view.
		 */
		scrollIntoView: function() {

			// The reference element contains a zero-width space to avoid
			// a premature removal. The view is to be scrolled with respect
			// to this element.
			var reference = new CKEDITOR.dom.element.createFromHtml( '<span>&nbsp;</span>', this.document ),
				afterCaretNode, startContainerText, isStartText;

			var range = this.clone();

			// Work with the range to obtain a proper caret position.
			range.optimize();

			// Currently in a text node, so we need to split it into two
			// halves and put the reference between.
			if ( isStartText = range.startContainer.type == CKEDITOR.NODE_TEXT ) {
				// Keep the original content. It will be restored.
				startContainerText = range.startContainer.getText();

				// Split the startContainer at the this position.
				afterCaretNode = range.startContainer.split( range.startOffset );

				// Insert the reference between two text nodes.
				reference.insertAfter( range.startContainer );
			}

			// If not in a text node, simply insert the reference into the range.
			else
				range.insertNode( reference );

			// Scroll with respect to the reference element.
			reference.scrollIntoView();

			// Get rid of split parts if "in a text node" case.
			// Revert the original text of the startContainer.
			if ( isStartText ) {
				range.startContainer.setText( startContainerText );
				afterCaretNode.remove();
			}

			// Get rid of the reference node. It is no longer necessary.
			reference.remove();
		}
	};
})();

CKEDITOR.POSITION_AFTER_START = 1; // <element>^contents</element>		"^text"
CKEDITOR.POSITION_BEFORE_END = 2; // <element>contents^</element>		"text^"
CKEDITOR.POSITION_BEFORE_START = 3; // ^<element>contents</element>		^"text"
CKEDITOR.POSITION_AFTER_END = 4; // <element>contents</element>^		"text"

CKEDITOR.ENLARGE_ELEMENT = 1;
CKEDITOR.ENLARGE_BLOCK_CONTENTS = 2;
CKEDITOR.ENLARGE_LIST_ITEM_CONTENTS = 3;
CKEDITOR.ENLARGE_INLINE = 4;

// Check boundary types.

/**
 * See {@link CKEDITOR.dom.range#checkBoundaryOfElement}.
 *
 * @readonly
 * @member CKEDITOR
 * @property {Number} [=1]
 */
CKEDITOR.START = 1;

/**
 * See {@link CKEDITOR.dom.range#checkBoundaryOfElement}.
 *
 * @readonly
 * @member CKEDITOR
 * @property {Number} [=2]
 */
CKEDITOR.END = 2;

// Shrink range types.

/**
 * See {@link CKEDITOR.dom.range#shrink}.
 *
 * @readonly
 * @member CKEDITOR
 * @property {Number} [=1]
 */
CKEDITOR.SHRINK_ELEMENT = 1;

/**
 * See {@link CKEDITOR.dom.range#shrink}.
 *
 * @readonly
 * @member CKEDITOR
 * @property {Number} [=2]
 */
CKEDITOR.SHRINK_TEXT = 2;
