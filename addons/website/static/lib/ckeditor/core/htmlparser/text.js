/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

 'use strict';

(function() {
	/**
	 * A lightweight representation of HTML text.
	 *
	 * @class
	 * @extends CKEDITOR.htmlParser.node
	 * @constructor Creates a text class instance.
	 * @param {String} value The text node value.
	 */
	CKEDITOR.htmlParser.text = function( value ) {
		/**
		 * The text value.
		 *
		 * @property {String}
		 */
		this.value = value;

		/** @private */
		this._ = {
			isBlockLike: false
		};
	};

	CKEDITOR.htmlParser.text.prototype = CKEDITOR.tools.extend( new CKEDITOR.htmlParser.node(), {
		/**
		 * The node type. This is a constant value set to {@link CKEDITOR#NODE_TEXT}.
		 *
		 * @readonly
		 * @property {Number} [=CKEDITOR.NODE_TEXT]
		 */
		type: CKEDITOR.NODE_TEXT,

		/**
		 * Filter this text node with given filter.
		 *
		 * @since 4.1
		 * @param {CKEDITOR.htmlParser.filter} filter
		 * @returns {Boolean} Method returns `false` when this text node has
		 * been removed. This is an information for {@link CKEDITOR.htmlParser.element#filterChildren}
		 * that it has to repeat filter on current position in parent's children array.
		 */
		filter: function( filter, context ) {
			if ( !( this.value = filter.onText( context, this.value, this ) ) ) {
				this.remove();
				return false;
			}
		},

		/**
		 * Writes the HTML representation of this text to a {CKEDITOR.htmlParser.basicWriter}.
		 *
		 * @param {CKEDITOR.htmlParser.basicWriter} writer The writer to which write the HTML.
		 * @param {CKEDITOR.htmlParser.filter} [filter] The filter to be applied to this node.
		 * **Note:** it's unsafe to filter offline (not appended) node.
		 */
		writeHtml: function( writer, filter ) {
			if ( filter )
				this.filter( filter );

			writer.text( this.value );
		}
	} );
})();
