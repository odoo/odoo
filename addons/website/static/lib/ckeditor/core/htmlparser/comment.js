/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

 'use strict';

/**
 * A lightweight representation of an HTML comment.
 *
 * @class
 * @extends CKEDITOR.htmlParser.node
 * @constructor Creates a comment class instance.
 * @param {String} value The comment text value.
 */
CKEDITOR.htmlParser.comment = function( value ) {
	/**
	 * The comment text.
	 *
	 * @property {String}
	 */
	this.value = value;

	/** @private */
	this._ = {
		isBlockLike: false
	};
};

CKEDITOR.htmlParser.comment.prototype = CKEDITOR.tools.extend( new CKEDITOR.htmlParser.node(), {
	/**
	 * The node type. This is a constant value set to {@link CKEDITOR#NODE_COMMENT}.
	 *
	 * @readonly
	 * @property {Number} [=CKEDITOR.NODE_COMMENT]
	 */
	type: CKEDITOR.NODE_COMMENT,

	/**
	 * Filter this comment with given filter.
	 *
	 * @since 4.1
	 * @param {CKEDITOR.htmlParser.filter} filter
	 * @returns {Boolean} Method returns `false` when this comment has
	 * been removed or replaced with other node. This is an information for
	 * {@link CKEDITOR.htmlParser.element#filterChildren} that it has
	 * to repeat filter on current position in parent's children array.
	 */
	filter: function( filter, context ) {
		var comment = this.value;

		if ( !( comment = filter.onComment( context, comment, this ) ) ) {
			this.remove();
			return false;
		}

		if ( typeof comment != 'string' ) {
			this.replaceWith( comment );
			return false;
		}

		this.value = comment;

		return true;
	},

	/**
	 * Writes the HTML representation of this comment to a CKEDITOR.htmlWriter.
	 *
	 * @param {CKEDITOR.htmlParser.basicWriter} writer The writer to which write the HTML.
	 * @param {CKEDITOR.htmlParser.filter} [filter] The filter to be applied to this node.
	 * **Note:** it's unsafe to filter offline (not appended) node.
	 */
	writeHtml: function( writer, filter ) {
		if ( filter )
			this.filter( filter );

		writer.comment( this.value );
	}
} );
