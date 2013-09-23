/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the {@link CKEDITOR.dom.text} class, which represents
 *		a DOM text node.
 */

/**
 * Represents a DOM text node.
 *
 *		var nativeNode = document.createTextNode( 'Example' );
 *		var text = CKEDITOR.dom.text( nativeNode );
 *
 *		var text = CKEDITOR.dom.text( 'Example' );
 *
 * @class
 * @extends CKEDITOR.dom.node
 * @constructor Creates a text class instance.
 * @param {Object/String} text A native DOM text node or a string containing
 * the text to use to create a new text node.
 * @param {CKEDITOR.dom.document} [ownerDocument] The document that will contain
 * the node in case of new node creation. Defaults to the current document.
 */
CKEDITOR.dom.text = function( text, ownerDocument ) {
	if ( typeof text == 'string' )
		text = ( ownerDocument ? ownerDocument.$ : document ).createTextNode( text );

	// Theoretically, we should call the base constructor here
	// (not CKEDITOR.dom.node though). But, IE doesn't support expando
	// properties on text node, so the features provided by domObject will not
	// work for text nodes (which is not a big issue for us).
	//
	// CKEDITOR.dom.domObject.call( this, element );

	this.$ = text;
};

CKEDITOR.dom.text.prototype = new CKEDITOR.dom.node();

CKEDITOR.tools.extend( CKEDITOR.dom.text.prototype, {
	/**
	 * The node type. This is a constant value set to {@link CKEDITOR#NODE_TEXT}.
	 *
	 * @readonly
	 * @property {Number} [=CKEDITOR.NODE_TEXT]
	 */
	type: CKEDITOR.NODE_TEXT,

	/**
	 * Gets length of node's value.
	 *
	 * @returns {Number}
	 */
	getLength: function() {
		return this.$.nodeValue.length;
	},

	/**
	 * Gets node's value.
	 *
	 * @returns {String}
	 */
	getText: function() {
		return this.$.nodeValue;
	},

	/**
	 * Sets node's value.
	 *
	 * @param {String} text
	 */
	setText: function( text ) {
		this.$.nodeValue = text;
	},

	/**
	 * Breaks this text node into two nodes at the specified offset,
	 * keeping both in the tree as siblings. This node then only contains
	 * all the content up to the offset point. A new text node, which is
	 * inserted as the next sibling of this node, contains all the content
	 * at and after the offset point. When the offset is equal to the
	 * length of this node, the new node has no data.
	 *
	 * @param {Number} The position at which to split, starting from zero.
	 * @returns {CKEDITOR.dom.text} The new text node.
	 */
	split: function( offset ) {

		// Saved the children count and text length beforehand.
		var parent = this.$.parentNode,
			count = parent.childNodes.length,
			length = this.getLength();

		var doc = this.getDocument();
		var retval = new CKEDITOR.dom.text( this.$.splitText( offset ), doc );

		if ( parent.childNodes.length == count )
		{
			// If the offset is after the last char, IE creates the text node
			// on split, but don't include it into the DOM. So, we have to do
			// that manually here.
			if ( offset >= length )
			{
				retval = doc.createText( '' );
				retval.insertAfter( this );
			}
			else
			{
				// IE BUG: IE8+ does not update the childNodes array in DOM after splitText(),
				// we need to make some DOM changes to make it update. (#3436)
				var workaround = doc.createText( '' );
				workaround.insertAfter( retval );
				workaround.remove();
			}
		}

		return retval;
	},

	/**
	 * Extracts characters from indexA up to but not including `indexB`.
	 *
	 * @param {Number} indexA An integer between `0` and one less than the
	 * length of the text.
	 * @param {Number} [indexB] An integer between `0` and the length of the
	 * string. If omitted, extracts characters to the end of the text.
	 */
	substring: function( indexA, indexB ) {
		// We need the following check due to a Firefox bug
		// https://bugzilla.mozilla.org/show_bug.cgi?id=458886
		if ( typeof indexB != 'number' )
			return this.$.nodeValue.substr( indexA );
		else
			return this.$.nodeValue.substring( indexA, indexB );
	}
});
