/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

'use strict';

(function() {

	var pathBlockLimitElements = {},
		pathBlockElements = {},
		tag;

	// Elements that are considered the "Block limit" in an element path.
	for ( tag in CKEDITOR.dtd.$blockLimit ) {
		// Exclude from list roots.
		if ( !( tag in CKEDITOR.dtd.$list ) )
			pathBlockLimitElements[ tag ] = 1;
	}

	// Elements that are considered the "End level Block" in an element path.
	for ( tag in CKEDITOR.dtd.$block ) {
		// Exclude block limits, and empty block element, e.g. hr.
		if ( !( tag in CKEDITOR.dtd.$blockLimit || tag in CKEDITOR.dtd.$empty ) )
			pathBlockElements[ tag ] = 1;
	}

	// Check if an element contains any block element.
	function checkHasBlock( element ) {
		var childNodes = element.getChildren();

		for ( var i = 0, count = childNodes.count(); i < count; i++ ) {
			var child = childNodes.getItem( i );

			if ( child.type == CKEDITOR.NODE_ELEMENT && CKEDITOR.dtd.$block[ child.getName() ] )
				return true;
		}

		return false;
	}

	/**
	 * Retrieve the list of nodes walked from the start node up to the editable element of the editor.
	 *
	 * @class
	 * @constructor Creates an element path class instance.
	 * @param {CKEDITOR.dom.element} startNode From which the path should start.
	 * @param {CKEDITOR.dom.element} root To which element the path should stop, defaults to the `body` element.
	 */
	CKEDITOR.dom.elementPath = function( startNode, root ) {
		var block = null,
			blockLimit = null,
			elements = [],
			e = startNode,
			elementName;

		// Backward compact.
		root = root || startNode.getDocument().getBody();

		do {
			if ( e.type == CKEDITOR.NODE_ELEMENT ) {
				elements.push( e );

				if ( !this.lastElement ) {
					this.lastElement = e;

					// If a table is fully selected at the end of the element path,
					// it must not become the block limit.
					if ( e.is( CKEDITOR.dtd.$object ) )
						continue;
				}

				if ( e.equals( root ) )
					break;

				if ( !blockLimit ) {
					elementName = e.getName();

					// First editable element becomes a block limit, because it cannot be split.
					if ( e.getAttribute( 'contenteditable' ) == 'true' )
						blockLimit = e;
					// "Else" because element cannot be both - block and block levelimit.
					else if ( !block && pathBlockElements[ elementName ] )
						block = e;

					if ( pathBlockLimitElements[ elementName ] ) {
						// End level DIV is considered as the block, if no block is available. (#525)
						// But it must NOT be the root element (checked above).
						if ( !block && elementName == 'div' && !checkHasBlock( e ) )
							block = e;
						else
							blockLimit = e;
					}
				}
			}
		}
		while ( ( e = e.getParent() ) );

		// Block limit defaults to root.
		if ( !blockLimit )
			blockLimit = root;

		/**
		 * First non-empty block element which:
		 *
		 * * is not a {@link CKEDITOR.dtd#$blockLimit},
		 * * or is a `div` which does not contain block elements and is not a `root`.
		 *
		 * This means a first, splittable block in elements path.
		 *
		 * @readonly
		 * @property {CKEDITOR.dom.element}
		 */
		this.block = block;

		/**
		 * See the {@link CKEDITOR.dtd#$blockLimit} description.
		 *
		 * @readonly
		 * @property {CKEDITOR.dom.element}
		 */
		this.blockLimit = blockLimit;

		/**
		 * The root of the elements path - `root` argument passed to class constructor or a `body` element.
		 *
		 * @readonly
		 * @property {CKEDITOR.dom.element}
		 */
		this.root = root;

		/**
		 * An array of elements (from `startNode` to `root`) in the path.
		 *
		 * @readonly
		 * @property {CKEDITOR.dom.element[]}
		 */
		this.elements = elements;

		/**
		 * The last element of the elements path - `startNode` or its parent.
		 *
		 * @readonly
		 * @property {CKEDITOR.dom.element} lastElement
		 */
	};

})();

CKEDITOR.dom.elementPath.prototype = {
	/**
	 * Compares this element path with another one.
	 *
	 * @param {CKEDITOR.dom.elementPath} otherPath The elementPath object to be
	 * compared with this one.
	 * @returns {Boolean} `true` if the paths are equal, containing the same
	 * number of elements and the same elements in the same order.
	 */
	compare: function( otherPath ) {
		var thisElements = this.elements;
		var otherElements = otherPath && otherPath.elements;

		if ( !otherElements || thisElements.length != otherElements.length )
			return false;

		for ( var i = 0; i < thisElements.length; i++ ) {
			if ( !thisElements[ i ].equals( otherElements[ i ] ) )
				return false;
		}

		return true;
	},

	/**
	 * Search the path elements that meets the specified criteria.
	 *
	 * @param {String/Array/Function/Object/CKEDITOR.dom.element} query The criteria that can be
	 * either a tag name, list (array and object) of tag names, element or an node evaluator function.
	 * @param {Boolean} [excludeRoot] Not taking path root element into consideration.
	 * @param {Boolean} [fromTop] Search start from the topmost element instead of bottom.
	 * @returns {CKEDITOR.dom.element} The first matched dom element or `null`.
	 */
	contains: function( query, excludeRoot, fromTop ) {
		var evaluator;
		if ( typeof query == 'string' )
			evaluator = function( node ) {
				return node.getName() == query;
			};
		if ( query instanceof CKEDITOR.dom.element )
			evaluator = function( node ) {
				return node.equals( query );
			};
		else if ( CKEDITOR.tools.isArray( query ) )
			evaluator = function( node ) {
				return CKEDITOR.tools.indexOf( query, node.getName() ) > -1;
			};
		else if ( typeof query == 'function' )
			evaluator = query;
		else if ( typeof query == 'object' )
			evaluator = function( node ) {
				return node.getName() in query;
			};

		var elements = this.elements,
			length = elements.length;
		excludeRoot && length--;

		if ( fromTop ) {
			elements = Array.prototype.slice.call( elements, 0 );
			elements.reverse();
		}

		for ( var i = 0; i < length; i++ ) {
			if ( evaluator( elements[ i ] ) )
				return elements[ i ];
		}

		return null;
	},

	/**
	 * Check whether the elements path is the proper context for the specified
	 * tag name in the DTD.
	 *
	 * @param {String} tag The tag name.
	 * @returns {Boolean}
	 */
	isContextFor: function( tag ) {
		var holder;

		// Check for block context.
		if ( tag in CKEDITOR.dtd.$block ) {
			// Indeterminate elements which are not subjected to be splitted or surrounded must be checked first.
			var inter = this.contains( CKEDITOR.dtd.$intermediate );
			holder = inter || ( this.root.equals( this.block ) && this.block ) || this.blockLimit;
			return !!holder.getDtd()[ tag ];
		}

		return true;
	},

	/**
	 * Retrieve the text direction for this elements path.
	 *
	 * @returns {'ltr'/'rtl'}
	 */
	direction: function() {
		var directionNode = this.block || this.blockLimit || this.root;
		return directionNode.getDirection( 1 );
	}
};
