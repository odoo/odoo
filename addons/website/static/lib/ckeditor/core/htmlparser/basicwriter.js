/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * TODO
 *
 * @class
 * @todo
 */
CKEDITOR.htmlParser.basicWriter = CKEDITOR.tools.createClass({
	/**
	 * Creates a basicWriter class instance.
	 *
	 * @constructor
	 */
	$: function() {
		this._ = {
			output: []
		};
	},

	proto: {
		/**
		 * Writes the tag opening part for a opener tag.
		 *
		 *		// Writes '<p'.
		 *		writer.openTag( 'p', { class : 'MyClass', id : 'MyId' } );
		 *
		 * @param {String} tagName The element name for this tag.
		 * @param {Object} attributes The attributes defined for this tag. The
		 * attributes could be used to inspect the tag.
		 */
		openTag: function( tagName, attributes ) {
			this._.output.push( '<', tagName );
		},

		/**
		 * Writes the tag closing part for a opener tag.
		 *
		 *		// Writes '>'.
		 *		writer.openTagClose( 'p', false );
		 *
		 *		// Writes ' />'.
		 *		writer.openTagClose( 'br', true );
		 *
		 * @param {String} tagName The element name for this tag.
		 * @param {Boolean} isSelfClose Indicates that this is a self-closing tag,
		 * like `<br>` or `<img>`.
		 */
		openTagClose: function( tagName, isSelfClose ) {
			if ( isSelfClose )
				this._.output.push( ' />' );
			else
				this._.output.push( '>' );
		},

		/**
		 * Writes an attribute. This function should be called after opening the
		 * tag with {@link #openTagClose}.
		 *
		 *		// Writes ' class="MyClass"'.
		 *		writer.attribute( 'class', 'MyClass' );
		 *
		 * @param {String} attName The attribute name.
		 * @param {String} attValue The attribute value.
		 */
		attribute: function( attName, attValue ) {
			// Browsers don't always escape special character in attribute values. (#4683, #4719).
			if ( typeof attValue == 'string' )
				attValue = CKEDITOR.tools.htmlEncodeAttr( attValue );

			this._.output.push( ' ', attName, '="', attValue, '"' );
		},

		/**
		 * Writes a closer tag.
		 *
		 *		// Writes '</p>'.
		 *		writer.closeTag( 'p' );
		 *
		 * @param {String} tagName The element name for this tag.
		 */
		closeTag: function( tagName ) {
			this._.output.push( '</', tagName, '>' );
		},

		/**
		 * Writes text.
		 *
		 *		// Writes 'Hello Word'.
		 *		writer.text( 'Hello Word' );
		 *
		 * @param {String} text The text value.
		 */
		text: function( text ) {
			this._.output.push( text );
		},

		/**
		 * Writes a comment.
		 *
		 *		// Writes '<!-- My comment -->'.
		 *		writer.comment( ' My comment ' );
		 *
		 * @param {String} comment The comment text.
		 */
		comment: function( comment ) {
			this._.output.push( '<!--', comment, '-->' );
		},

		/**
		 * Writes any kind of data to the ouput.
		 *
		 *		writer.write( 'This is an <b>example</b>.' );
		 *
		 * @param {String} data
		 */
		write: function( data ) {
			this._.output.push( data );
		},

		/**
		 * Empties the current output buffer.
		 *
		 *		writer.reset();
		 */
		reset: function() {
			this._.output = [];
			this._.indent = false;
		},

		/**
		 * Empties the current output buffer.
		 *
		 *		var html = writer.getHtml();
		 *
		 * @param {Boolean} reset Indicates that the {@link #reset} method is to
		 * be automatically called after retrieving the HTML.
		 * @returns {String} The HTML written to the writer so far.
		 */
		getHtml: function( reset ) {
			var html = this._.output.join( '' );

			if ( reset )
				this.reset();

			return html;
		}
	}
});
