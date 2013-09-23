/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the {@link CKEDITOR.dom.comment} class, which represents
 *		a DOM comment node.
 */

/**
 * Represents a DOM comment node.
 *
 *		var nativeNode = document.createComment( 'Example' );
 *		var comment = new CKEDITOR.dom.comment( nativeNode );
 *
 *		var comment = new CKEDITOR.dom.comment( 'Example' );
 *
 * @class
 * @extends CKEDITOR.dom.node
 * @constructor Creates a comment class instance.
 * @param {Object/String} comment A native DOM comment node or a string containing
 * the text to use to create a new comment node.
 * @param {CKEDITOR.dom.document} [ownerDocument] The document that will contain
 * the node in case of new node creation. Defaults to the current document.
 */
CKEDITOR.dom.comment = function( comment, ownerDocument ) {
	if ( typeof comment == 'string' )
		comment = ( ownerDocument ? ownerDocument.$ : document ).createComment( comment );

	CKEDITOR.dom.domObject.call( this, comment );
};

CKEDITOR.dom.comment.prototype = new CKEDITOR.dom.node();

CKEDITOR.tools.extend( CKEDITOR.dom.comment.prototype, {
	/**
	 * The node type. This is a constant value set to {@link CKEDITOR#NODE_COMMENT}.
	 *
	 * @readonly
	 * @property {Number} [=CKEDITOR.NODE_COMMENT]
	 */
	type: CKEDITOR.NODE_COMMENT,

	/**
	 * Gets the outer HTML of this comment.
	 *
	 * @returns {String} The HTML `<!-- comment value -->`.
	 */
	getOuterHtml: function() {
		return '<!--' + this.$.nodeValue + '-->';
	}
});
