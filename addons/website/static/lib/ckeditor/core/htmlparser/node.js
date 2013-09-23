/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

'use strict';

(function() {
	/**
	 * A lightweight representation of HTML node.
	 *
	 * @since 4.1
	 * @class
	 * @constructor Creates a node class instance.
	 */
	CKEDITOR.htmlParser.node = function() {};

	CKEDITOR.htmlParser.node.prototype = {
		/**
		 * Remove this node from a tree.
		 *
		 * @since 4.1
		 */
		remove: function() {
			var children = this.parent.children,
				index = CKEDITOR.tools.indexOf( children, this ),
				previous = this.previous,
				next = this.next;

			previous && ( previous.next = next );
			next && ( next.previous = previous );
			children.splice( index, 1 );
			this.parent = null;
		},

		/**
		 * Replace this node with given one.
		 *
		 * @since 4.1
		 * @param {CKEDITOR.htmlParser.node} node The node that will replace this one.
		 */
		replaceWith: function( node ) {
			var children = this.parent.children,
				index = CKEDITOR.tools.indexOf( children, this ),
				previous = node.previous = this.previous,
				next = node.next = this.next;

			previous && ( previous.next = node );
			next && ( next.previous = node );

			children[ index ] = node;

			node.parent = this.parent;
			this.parent = null;
		},

		/**
		 * Insert this node after given one.
		 *
		 * @since 4.1
		 * @param {CKEDITOR.htmlParser.node} node The node that will precede this element.
		 */
		insertAfter: function( node ) {
			var children = node.parent.children,
				index = CKEDITOR.tools.indexOf( children, node ),
				next = node.next;

			children.splice( index + 1, 0, this );

			this.next = node.next;
			this.previous = node;
			node.next = this;
			next && ( next.previous = this );

			this.parent = node.parent;
		},

		/**
		 * Insert this node before given one.
		 *
		 * @since 4.1
		 * @param {CKEDITOR.htmlParser.node} node The node that will follow this element.
		 */
		insertBefore: function( node ) {
			var children = node.parent.children,
				index = CKEDITOR.tools.indexOf( children, node );

			children.splice( index, 0, this );

			this.next = node;
			this.previous = node.previous;
			node.previous && ( node.previous.next = this );
			node.previous = this;

			this.parent = node.parent;
		},

		/**
		 * Gets the closest ancestor element of this element which satisfies given condition
		 *
		 * @since 4.3
		 * @param {String/Object/Function} condition Name of an ancestor, hash of names or validator function.
		 * @returns {CKEDITOR.htmlParser.element} The closest ancestor which satisfies given condition or `null`.
		 */
		getAscendant: function( condition ) {
			var checkFn =
				typeof condition == 'function' ?	condition :
				typeof condition == 'string' ?		function( el ) { return el.name == condition; } :
													function( el ) { return el.name in condition; };

			var parent = this.parent;

			// Parent has to be an element - don't check doc fragment.
			while ( parent && parent.type == CKEDITOR.NODE_ELEMENT ) {
				if ( checkFn( parent ) )
					return parent;
				parent = parent.parent;
			}

			return null;
		},

		/**
		 * Wraps this element with given `wrapper`.
		 *
		 * @since 4.3
		 * @param {CKEDITOR.htmlParser.element} wrapper The element which will be this element's new parent.
		 * @returns {CKEDITOR.htmlParser.element} Wrapper.
		 */
		wrapWith: function( wrapper ) {
			this.replaceWith( wrapper );
			wrapper.add( this );
			return wrapper;
		},

		/**
		 * Gets this node's index in its parent's children array.
		 *
		 * @since 4.3
		 * @returns {Number}
		 */
		getIndex: function() {
			return CKEDITOR.tools.indexOf( this.parent.children, this );
		},

		getFilterContext: function( context ) {
			return context || {};
		}
	};
})();
