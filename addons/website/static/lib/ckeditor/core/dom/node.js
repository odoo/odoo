/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the {@link CKEDITOR.dom.node} class which is the base
 *		class for classes that represent DOM nodes.
 */

/**
 * Base class for classes representing DOM nodes. This constructor may return
 * an instance of a class that inherits from this class, like
 * {@link CKEDITOR.dom.element} or {@link CKEDITOR.dom.text}.
 *
 * @class
 * @extends CKEDITOR.dom.domObject
 * @constructor Creates a node class instance.
 * @param {Object} domNode A native DOM node.
 * @see CKEDITOR.dom.element
 * @see CKEDITOR.dom.text
 */
CKEDITOR.dom.node = function( domNode ) {
	if ( domNode ) {
		var type = domNode.nodeType == CKEDITOR.NODE_DOCUMENT ? 'document' : domNode.nodeType == CKEDITOR.NODE_ELEMENT ? 'element' : domNode.nodeType == CKEDITOR.NODE_TEXT ? 'text' : domNode.nodeType == CKEDITOR.NODE_COMMENT ? 'comment' : domNode.nodeType == CKEDITOR.NODE_DOCUMENT_FRAGMENT ? 'documentFragment' : 'domObject'; // Call the base constructor otherwise.

		return new CKEDITOR.dom[ type ]( domNode );
	}

	return this;
};

CKEDITOR.dom.node.prototype = new CKEDITOR.dom.domObject();

/**
 * Element node type.
 *
 * @readonly
 * @property {Number} [=1]
 * @member CKEDITOR
 */
CKEDITOR.NODE_ELEMENT = 1;

/**
 * Document node type.
 *
 * @readonly
 * @property {Number} [=9]
 * @member CKEDITOR
 */
CKEDITOR.NODE_DOCUMENT = 9;

/**
 * Text node type.
 *
 * @readonly
 * @property {Number} [=3]
 * @member CKEDITOR
 */
CKEDITOR.NODE_TEXT = 3;

/**
 * Comment node type.
 *
 * @readonly
 * @property {Number} [=8]
 * @member CKEDITOR
 */
CKEDITOR.NODE_COMMENT = 8;

/**
 * Document fragment node type.
 *
 * @readonly
 * @property {Number} [=11]
 * @member CKEDITOR
 */
CKEDITOR.NODE_DOCUMENT_FRAGMENT = 11;

CKEDITOR.POSITION_IDENTICAL = 0;
CKEDITOR.POSITION_DISCONNECTED = 1;
CKEDITOR.POSITION_FOLLOWING = 2;
CKEDITOR.POSITION_PRECEDING = 4;
CKEDITOR.POSITION_IS_CONTAINED = 8;
CKEDITOR.POSITION_CONTAINS = 16;

CKEDITOR.tools.extend( CKEDITOR.dom.node.prototype, {
	/**
	 * Makes this node a child of another element.
	 *
	 *		var p = new CKEDITOR.dom.element( 'p' );
	 *		var strong = new CKEDITOR.dom.element( 'strong' );
	 *		strong.appendTo( p );
	 *
	 *		// Result: '<p><strong></strong></p>'.
	 *
	 * @param {CKEDITOR.dom.element} element The target element to which this node will be appended.
	 * @returns {CKEDITOR.dom.element} The target element.
	 */
	appendTo: function( element, toStart ) {
		element.append( this, toStart );
		return element;
	},

	/**
	 * Clone this node.
	 *
	 * **Note**: Values set by {#setCustomData} won't be available in the clone.
	 *
	 * @param {Boolean} [includeChildren=false] If `true` then all node's
	 * children will be cloned recursively.
	 * @param {Boolean} [cloneId=false] Whether ID attributes should be cloned too.
	 * @returns {CKEDITOR.dom.node} Clone of this node.
	 */
	clone: function( includeChildren, cloneId ) {
		var $clone = this.$.cloneNode( includeChildren );

		var removeIds = function( node ) {
				// Reset data-cke-expando only when has been cloned (IE and only for some types of objects).
				if ( node['data-cke-expando'] )
					node['data-cke-expando'] = false;

				if ( node.nodeType != CKEDITOR.NODE_ELEMENT )
					return;
				if ( !cloneId )
					node.removeAttribute( 'id', false );

				if ( includeChildren ) {
					var childs = node.childNodes;
					for ( var i = 0; i < childs.length; i++ )
						removeIds( childs[ i ] );
				}
			};

		// The "id" attribute should never be cloned to avoid duplication.
		removeIds( $clone );

		return new CKEDITOR.dom.node( $clone );
	},

	/**
	 * Check if node is preceded by any sibling.
	 *
	 * @returns {Boolean}
	 */
	hasPrevious: function() {
		return !!this.$.previousSibling;
	},

	/**
	 * Check if node is succeeded by any sibling.
	 *
	 * @returns {Boolean}
	 */
	hasNext: function() {
		return !!this.$.nextSibling;
	},

	/**
	 * Inserts this element after a node.
	 *
	 *		var em = new CKEDITOR.dom.element( 'em' );
	 *		var strong = new CKEDITOR.dom.element( 'strong' );
	 *		strong.insertAfter( em );
	 *
	 *		// Result: '<em></em><strong></strong>'
	 *
	 * @param {CKEDITOR.dom.node} node The node that will precede this element.
	 * @returns {CKEDITOR.dom.node} The node preceding this one after insertion.
	 */
	insertAfter: function( node ) {
		node.$.parentNode.insertBefore( this.$, node.$.nextSibling );
		return node;
	},

	/**
	 * Inserts this element before a node.
	 *
	 *		var em = new CKEDITOR.dom.element( 'em' );
	 *		var strong = new CKEDITOR.dom.element( 'strong' );
	 *		strong.insertBefore( em );
	 *
	 *		// result: '<strong></strong><em></em>'
	 *
	 * @param {CKEDITOR.dom.node} node The node that will succeed this element.
	 * @returns {CKEDITOR.dom.node} The node being inserted.
	 */
	insertBefore: function( node ) {
		node.$.parentNode.insertBefore( this.$, node.$ );
		return node;
	},

	/**
	 * Inserts node before this node.
	 *
	 *		var em = new CKEDITOR.dom.element( 'em' );
	 *		var strong = new CKEDITOR.dom.element( 'strong' );
	 *		strong.insertBeforeMe( em );
	 *
	 *		// result: '<em></em><strong></strong>'
	 *
	 * @param {CKEDITOR.dom.node} node The node that will preceed this element.
	 * @returns {CKEDITOR.dom.node} The node being inserted.
	 */
	insertBeforeMe: function( node ) {
		this.$.parentNode.insertBefore( node.$, this.$ );
		return node;
	},

	/**
	 * Retrieves a uniquely identifiable tree address for this node.
	 * The tree address returned is an array of integers, with each integer
	 * indicating a child index of a DOM node, starting from
	 * `document.documentElement`.
	 *
	 * For example, assuming `<body>` is the second child
	 * of `<html>` (`<head>` being the first),
	 * and we would like to address the third child under the
	 * fourth child of `<body>`, the tree address returned would be:
	 * `[1, 3, 2]`.
	 *
	 * The tree address cannot be used for finding back the DOM tree node once
	 * the DOM tree structure has been modified.
	 *
	 * @param {Boolean} [normalized=false] See {@link #getIndex}.
	 * @returns {Array} The address.
	 */
	getAddress: function( normalized ) {
		var address = [];
		var $documentElement = this.getDocument().$.documentElement;
		var node = this.$;

		while ( node && node != $documentElement ) {
			var parentNode = node.parentNode;

			if ( parentNode ) {
				// Get the node index. For performance, call getIndex
				// directly, instead of creating a new node object.
				address.unshift( this.getIndex.call({ $: node }, normalized ) );
			}

			node = parentNode;
		}

		return address;
	},

	/**
	 * Gets the document containing this element.
	 *
	 *		var element = CKEDITOR.document.getById( 'example' );
	 *		alert( element.getDocument().equals( CKEDITOR.document ) ); // true
	 *
	 * @returns {CKEDITOR.dom.document} The document.
	 */
	getDocument: function() {
		return new CKEDITOR.dom.document( this.$.ownerDocument || this.$.parentNode.ownerDocument );
	},

	/**
	 * Get index of a node in an array of its parent.childNodes.
	 *
	 * Let's assume having childNodes array:
	 *
	 *		[ emptyText, element1, text, text, element2 ]
	 *		element1.getIndex();		// 1
	 *		element1.getIndex( true );	// 0
	 *		element2.getIndex();		// 4
	 *		element2.getIndex( true );	// 2
	 *
	 * @param {Boolean} normalized When `true` empty text nodes and one followed
	 * by another one text node are not counted in.
	 * @returns {Number} Index of a node.
	 */
	getIndex: function( normalized ) {
		// Attention: getAddress depends on this.$
		// getIndex is called on a plain object: { $ : node }

		var current = this.$,
			index = -1,
			isNormalizing;

		if ( !this.$.parentNode )
			return index;

		do {
			// Bypass blank node and adjacent text nodes.
			if ( normalized && current != this.$ && current.nodeType == CKEDITOR.NODE_TEXT && ( isNormalizing || !current.nodeValue ) ) {
				continue;
			}

			index++;
			isNormalizing = current.nodeType == CKEDITOR.NODE_TEXT;
		}
		while ( ( current = current.previousSibling ) )

		return index;
	},

	/**
	 * @todo
	 */
	getNextSourceNode: function( startFromSibling, nodeType, guard ) {
		// If "guard" is a node, transform it in a function.
		if ( guard && !guard.call ) {
			var guardNode = guard;
			guard = function( node ) {
				return !node.equals( guardNode );
			};
		}

		var node = ( !startFromSibling && this.getFirst && this.getFirst() ),
			parent;

		// Guarding when we're skipping the current element( no children or 'startFromSibling' ).
		// send the 'moving out' signal even we don't actually dive into.
		if ( !node ) {
			if ( this.type == CKEDITOR.NODE_ELEMENT && guard && guard( this, true ) === false )
				return null;
			node = this.getNext();
		}

		while ( !node && ( parent = ( parent || this ).getParent() ) ) {
			// The guard check sends the "true" paramenter to indicate that
			// we are moving "out" of the element.
			if ( guard && guard( parent, true ) === false )
				return null;

			node = parent.getNext();
		}

		if ( !node )
			return null;

		if ( guard && guard( node ) === false )
			return null;

		if ( nodeType && nodeType != node.type )
			return node.getNextSourceNode( false, nodeType, guard );

		return node;
	},

	/**
	 * @todo
	 */
	getPreviousSourceNode: function( startFromSibling, nodeType, guard ) {
		if ( guard && !guard.call ) {
			var guardNode = guard;
			guard = function( node ) {
				return !node.equals( guardNode );
			};
		}

		var node = ( !startFromSibling && this.getLast && this.getLast() ),
			parent;

		// Guarding when we're skipping the current element( no children or 'startFromSibling' ).
		// send the 'moving out' signal even we don't actually dive into.
		if ( !node ) {
			if ( this.type == CKEDITOR.NODE_ELEMENT && guard && guard( this, true ) === false )
				return null;
			node = this.getPrevious();
		}

		while ( !node && ( parent = ( parent || this ).getParent() ) ) {
			// The guard check sends the "true" paramenter to indicate that
			// we are moving "out" of the element.
			if ( guard && guard( parent, true ) === false )
				return null;

			node = parent.getPrevious();
		}

		if ( !node )
			return null;

		if ( guard && guard( node ) === false )
			return null;

		if ( nodeType && node.type != nodeType )
			return node.getPreviousSourceNode( false, nodeType, guard );

		return node;
	},

	/**
	 * Gets the node that preceed this element in its parent's child list.
	 *
	 *		var element = CKEDITOR.dom.element.createFromHtml( '<div><i>prev</i><b>Example</b></div>' );
	 *		var first = element.getLast().getPrev();
	 *		alert( first.getName() ); // 'i'
	 *
	 * @param {Function} [evaluator] Filtering the result node.
	 * @returns {CKEDITOR.dom.node} The previous node or null if not available.
	 */
	getPrevious: function( evaluator ) {
		var previous = this.$,
			retval;
		do {
			previous = previous.previousSibling;

			// Avoid returning the doc type node.
			// http://www.w3.org/TR/REC-DOM-Level-1/level-one-core.html#ID-412266927
			retval = previous && previous.nodeType != 10 && new CKEDITOR.dom.node( previous );
		}
		while ( retval && evaluator && !evaluator( retval ) )
		return retval;
	},

	/**
	 * Gets the node that follows this element in its parent's child list.
	 *
	 *		var element = CKEDITOR.dom.element.createFromHtml( '<div><b>Example</b><i>next</i></div>' );
	 *		var last = element.getFirst().getNext();
	 *		alert( last.getName() ); // 'i'
	 *
	 * @param {Function} [evaluator] Filtering the result node.
	 * @returns {CKEDITOR.dom.node} The next node or null if not available.
	 */
	getNext: function( evaluator ) {
		var next = this.$,
			retval;
		do {
			next = next.nextSibling;
			retval = next && new CKEDITOR.dom.node( next );
		}
		while ( retval && evaluator && !evaluator( retval ) )
		return retval;
	},

	/**
	 * Gets the parent element for this node.
	 *
	 *		var node = editor.document.getBody().getFirst();
	 *		var parent = node.getParent();
	 *		alert( node.getName() ); // 'body'
	 *
	 * @param {Boolean} [allowFragmentParent=false] Consider also parent node that is of
	 * fragment type {@link CKEDITOR#NODE_DOCUMENT_FRAGMENT}.
	 * @returns {CKEDITOR.dom.element} The parent element.
	 */
	getParent: function( allowFragmentParent ) {
		var parent = this.$.parentNode;
		return ( parent && ( parent.nodeType == CKEDITOR.NODE_ELEMENT || allowFragmentParent && parent.nodeType == CKEDITOR.NODE_DOCUMENT_FRAGMENT ) ) ? new CKEDITOR.dom.node( parent ) : null;
	},

	/**
	 * @todo
	 */
	getParents: function( closerFirst ) {
		var node = this;
		var parents = [];

		do {
			parents[ closerFirst ? 'push' : 'unshift' ]( node );
		}
		while ( ( node = node.getParent() ) )

		return parents;
	},

	/**
	 * @todo
	 */
	getCommonAncestor: function( node ) {
		if ( node.equals( this ) )
			return this;

		if ( node.contains && node.contains( this ) )
			return node;

		var start = this.contains ? this : this.getParent();

		do {
			if ( start.contains( node ) ) return start;
		}
		while ( ( start = start.getParent() ) );

		return null;
	},

	/**
	 * @todo
	 */
	getPosition: function( otherNode ) {
		var $ = this.$;
		var $other = otherNode.$;

		if ( $.compareDocumentPosition )
			return $.compareDocumentPosition( $other );

		// IE and Safari have no support for compareDocumentPosition.

		if ( $ == $other )
			return CKEDITOR.POSITION_IDENTICAL;

		// Only element nodes support contains and sourceIndex.
		if ( this.type == CKEDITOR.NODE_ELEMENT && otherNode.type == CKEDITOR.NODE_ELEMENT ) {
			if ( $.contains ) {
				if ( $.contains( $other ) )
					return CKEDITOR.POSITION_CONTAINS + CKEDITOR.POSITION_PRECEDING;

				if ( $other.contains( $ ) )
					return CKEDITOR.POSITION_IS_CONTAINED + CKEDITOR.POSITION_FOLLOWING;
			}

			if ( 'sourceIndex' in $ ) {
				return ( $.sourceIndex < 0 || $other.sourceIndex < 0 ) ? CKEDITOR.POSITION_DISCONNECTED : ( $.sourceIndex < $other.sourceIndex ) ? CKEDITOR.POSITION_PRECEDING : CKEDITOR.POSITION_FOLLOWING;
			}
		}

		// For nodes that don't support compareDocumentPosition, contains
		// or sourceIndex, their "address" is compared.

		var addressOfThis = this.getAddress(),
			addressOfOther = otherNode.getAddress(),
			minLevel = Math.min( addressOfThis.length, addressOfOther.length );

		// Determinate preceed/follow relationship.
		for ( var i = 0; i <= minLevel - 1; i++ ) {
			if ( addressOfThis[ i ] != addressOfOther[ i ] ) {
				if ( i < minLevel ) {
					return addressOfThis[ i ] < addressOfOther[ i ] ? CKEDITOR.POSITION_PRECEDING : CKEDITOR.POSITION_FOLLOWING;
				}
				break;
			}
		}

		// Determinate contains/contained relationship.
		return ( addressOfThis.length < addressOfOther.length ) ? CKEDITOR.POSITION_CONTAINS + CKEDITOR.POSITION_PRECEDING : CKEDITOR.POSITION_IS_CONTAINED + CKEDITOR.POSITION_FOLLOWING;
	},

	/**
	 * Gets the closest ancestor node of this node, specified by its name.
	 *
	 *		// Suppose we have the following HTML structure:
	 *		// <div id="outer"><div id="inner"><p><b>Some text</b></p></div></div>
	 *		// If node == <b>
	 *		ascendant = node.getAscendant( 'div' );				// ascendant == <div id="inner">
	 *		ascendant = node.getAscendant( 'b' );				// ascendant == null
	 *		ascendant = node.getAscendant( 'b', true );			// ascendant == <b>
	 *		ascendant = node.getAscendant( { div:1,p:1 } );		// Searches for the first 'div' or 'p': ascendant == <div id="inner">
	 *
	 * @since 3.6.1
	 * @param {String} reference The name of the ancestor node to search or
	 * an object with the node names to search for.
	 * @param {Boolean} [includeSelf] Whether to include the current
	 * node in the search.
	 * @returns {CKEDITOR.dom.node} The located ancestor node or null if not found.
	 */
	getAscendant: function( reference, includeSelf ) {
		var $ = this.$,
			name;

		if ( !includeSelf )
			$ = $.parentNode;

		while ( $ ) {
			if ( $.nodeName && ( name = $.nodeName.toLowerCase(), ( typeof reference == 'string' ? name == reference : name in reference ) ) )
				return new CKEDITOR.dom.node( $ );

			try {
				$ = $.parentNode;
			} catch( e ) {
				$ = null;
			}
		}
		return null;
	},

	/**
	 * @todo
	 */
	hasAscendant: function( name, includeSelf ) {
		var $ = this.$;

		if ( !includeSelf )
			$ = $.parentNode;

		while ( $ ) {
			if ( $.nodeName && $.nodeName.toLowerCase() == name )
				return true;

			$ = $.parentNode;
		}
		return false;
	},

	/**
	 * @todo
	 */
	move: function( target, toStart ) {
		target.append( this.remove(), toStart );
	},

	/**
	 * Removes this node from the document DOM.
	 *
	 *		var element = CKEDITOR.document.getById( 'MyElement' );
	 *		element.remove();
	 *
	 * @param {Boolean} [preserveChildren=false] Indicates that the children
	 * elements must remain in the document, removing only the outer tags.
	 */
	remove: function( preserveChildren ) {
		var $ = this.$;
		var parent = $.parentNode;

		if ( parent ) {
			if ( preserveChildren ) {
				// Move all children before the node.
				for ( var child;
				( child = $.firstChild ); ) {
					parent.insertBefore( $.removeChild( child ), $ );
				}
			}

			parent.removeChild( $ );
		}

		return this;
	},

	/**
	 * @todo
	 */
	replace: function( nodeToReplace ) {
		this.insertBefore( nodeToReplace );
		nodeToReplace.remove();
	},

	/**
	 * @todo
	 */
	trim: function() {
		this.ltrim();
		this.rtrim();
	},

	/**
	 * @todo
	 */
	ltrim: function() {
		var child;
		while ( this.getFirst && ( child = this.getFirst() ) ) {
			if ( child.type == CKEDITOR.NODE_TEXT ) {
				var trimmed = CKEDITOR.tools.ltrim( child.getText() ),
					originalLength = child.getLength();

				if ( !trimmed ) {
					child.remove();
					continue;
				} else if ( trimmed.length < originalLength ) {
					child.split( originalLength - trimmed.length );

					// IE BUG: child.remove() may raise JavaScript errors here. (#81)
					this.$.removeChild( this.$.firstChild );
				}
			}
			break;
		}
	},

	/**
	 * @todo
	 */
	rtrim: function() {
		var child;
		while ( this.getLast && ( child = this.getLast() ) ) {
			if ( child.type == CKEDITOR.NODE_TEXT ) {
				var trimmed = CKEDITOR.tools.rtrim( child.getText() ),
					originalLength = child.getLength();

				if ( !trimmed ) {
					child.remove();
					continue;
				} else if ( trimmed.length < originalLength ) {
					child.split( trimmed.length );

					// IE BUG: child.getNext().remove() may raise JavaScript errors here.
					// (#81)
					this.$.lastChild.parentNode.removeChild( this.$.lastChild );
				}
			}
			break;
		}

		if ( !CKEDITOR.env.ie && !CKEDITOR.env.opera ) {
			child = this.$.lastChild;

			if ( child && child.type == 1 && child.nodeName.toLowerCase() == 'br' ) {
				// Use "eChildNode.parentNode" instead of "node" to avoid IE bug (#324).
				child.parentNode.removeChild( child );
			}
		}
	},

	/**
	 * Checks if this node is read-only (should not be changed).
	 *
	 * **Note:** When `attributeCheck` is not used, this method only work for elements
	 * that are already presented in the document, otherwise the result
	 * is not guaranteed, it's mainly for performance consideration.
	 *
	 *		// For the following HTML:
	 *		// <div contenteditable="false">Some <b>text</b></div>
	 *
	 *		// If "ele" is the above <div>
	 *		element.isReadOnly(); // true
	 *
	 * @since 3.5
	 * @returns {Boolean}
	 */
	isReadOnly: function() {
		var element = this;
		if ( this.type != CKEDITOR.NODE_ELEMENT )
			element = this.getParent();

		if ( element && typeof element.$.isContentEditable != 'undefined' )
			return !( element.$.isContentEditable || element.data( 'cke-editable' ) );
		else {
			// Degrade for old browsers which don't support "isContentEditable", e.g. FF3

			while ( element ) {
				if ( element.data( 'cke-editable' ) )
					break;

				if ( element.getAttribute( 'contentEditable' ) == 'false' )
					return true;
				else if ( element.getAttribute( 'contentEditable' ) == 'true' )
					break;

				element = element.getParent();
			}

			// Reached the root of DOM tree, no editable found.
			return !element;
		}
	}
});
