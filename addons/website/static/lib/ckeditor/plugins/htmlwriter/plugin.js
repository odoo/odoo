/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

CKEDITOR.plugins.add( 'htmlwriter', {
	init: function( editor ) {
		var writer = new CKEDITOR.htmlWriter();

		writer.forceSimpleAmpersand = editor.config.forceSimpleAmpersand;
		writer.indentationChars = editor.config.dataIndentationChars || '\t';

		// Overwrite default basicWriter initialized in hmtlDataProcessor constructor.
		editor.dataProcessor.writer = writer;
	}
});

/**
 * Class used to write HTML data.
 *
 *		var writer = new CKEDITOR.htmlWriter();
 *		writer.openTag( 'p' );
 *		writer.attribute( 'class', 'MyClass' );
 *		writer.openTagClose( 'p' );
 *		writer.text( 'Hello' );
 *		writer.closeTag( 'p' );
 *		alert( writer.getHtml() ); // '<p class="MyClass">Hello</p>'
 *
 * @class
 * @extends CKEDITOR.htmlParser.basicWriter
 */
CKEDITOR.htmlWriter = CKEDITOR.tools.createClass({
	base: CKEDITOR.htmlParser.basicWriter,

	/**
	 * Creates a htmlWriter class instance.
	 *
	 * @constructor
	 */
	$: function() {
		// Call the base contructor.
		this.base();

		/**
		 * The characters to be used for each identation step.
		 *
		 *		// Use tab for indentation.
		 *		editorInstance.dataProcessor.writer.indentationChars = '\t';
		 */
		this.indentationChars = '\t';

		/**
		 * The characters to be used to close "self-closing" elements, like `<br>` or `<img>`.
		 *
		 *		// Use HTML4 notation for self-closing elements.
		 *		editorInstance.dataProcessor.writer.selfClosingEnd = '>';
		 */
		this.selfClosingEnd = ' />';

		/**
		 * The characters to be used for line breaks.
		 *
		 *		// Use CRLF for line breaks.
		 *		editorInstance.dataProcessor.writer.lineBreakChars = '\r\n';
		 */
		this.lineBreakChars = '\n';

		this.sortAttributes = 1;

		this._.indent = 0;
		this._.indentation = '';
		// Indicate preformatted block context status. (#5789)
		this._.inPre = 0;
		this._.rules = {};

		var dtd = CKEDITOR.dtd;

		for ( var e in CKEDITOR.tools.extend( {}, dtd.$nonBodyContent, dtd.$block, dtd.$listItem, dtd.$tableContent ) ) {
			this.setRules( e, {
				indent: !dtd[ e ][ '#' ],
				breakBeforeOpen: 1,
				breakBeforeClose: !dtd[ e ][ '#' ],
				breakAfterClose: 1,
				needsSpace: ( e in dtd.$block ) && !( e in { li:1,dt:1,dd:1 } )
			});
		}

		this.setRules( 'br', { breakAfterOpen:1 } );

		this.setRules( 'title', {
			indent: 0,
			breakAfterOpen: 0
		});

		this.setRules( 'style', {
			indent: 0,
			breakBeforeClose: 1
		});

		this.setRules( 'pre', {
			breakAfterOpen: 1, // Keep line break after the opening tag
			indent: 0 // Disable indentation on <pre>.
		});
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
			var rules = this._.rules[ tagName ];

			if ( this._.afterCloser && rules && rules.needsSpace && this._.needsSpace )
				this._.output.push( '\n' );

			if ( this._.indent )
				this.indentation();
			// Do not break if indenting.
			else if ( rules && rules.breakBeforeOpen ) {
				this.lineBreak();
				this.indentation();
			}

			this._.output.push( '<', tagName );

			this._.afterCloser = 0;
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
			var rules = this._.rules[ tagName ];

			if ( isSelfClose ) {
				this._.output.push( this.selfClosingEnd );

				if ( rules && rules.breakAfterClose )
					this._.needsSpace = rules.needsSpace;
			} else {
				this._.output.push( '>' );

				if ( rules && rules.indent )
					this._.indentation += this.indentationChars;
			}

			if ( rules && rules.breakAfterOpen )
				this.lineBreak();
			tagName == 'pre' && ( this._.inPre = 1 );
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

			if ( typeof attValue == 'string' ) {
				this.forceSimpleAmpersand && ( attValue = attValue.replace( /&amp;/g, '&' ) );
				// Browsers don't always escape special character in attribute values. (#4683, #4719).
				attValue = CKEDITOR.tools.htmlEncodeAttr( attValue );
			}

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
			var rules = this._.rules[ tagName ];

			if ( rules && rules.indent )
				this._.indentation = this._.indentation.substr( this.indentationChars.length );

			if ( this._.indent )
				this.indentation();
			// Do not break if indenting.
			else if ( rules && rules.breakBeforeClose ) {
				this.lineBreak();
				this.indentation();
			}

			this._.output.push( '</', tagName, '>' );
			tagName == 'pre' && ( this._.inPre = 0 );

			if ( rules && rules.breakAfterClose ) {
				this.lineBreak();
				this._.needsSpace = rules.needsSpace;
			}

			this._.afterCloser = 1;
		},

		/**
		 * Writes text.
		 *
		 *		// Writes 'Hello Word'.
		 *		writer.text( 'Hello Word' );
		 *
		 * @param {String} text The text value
		 */
		text: function( text ) {
			if ( this._.indent ) {
				this.indentation();
				!this._.inPre && ( text = CKEDITOR.tools.ltrim( text ) );
			}

			this._.output.push( text );
		},

		/**
		 * Writes a comment.
		 *
		 *		// Writes "<!-- My comment -->".
		 *		writer.comment( ' My comment ' );
		 *
		 * @param {String} comment The comment text.
		 */
		comment: function( comment ) {
			if ( this._.indent )
				this.indentation();

			this._.output.push( '<!--', comment, '-->' );
		},

		/**
		 * Writes a line break. It uses the {@link #lineBreakChars} property for it.
		 *
		 *		// Writes '\n' (e.g.).
		 *		writer.lineBreak();
		 */
		lineBreak: function() {
			if ( !this._.inPre && this._.output.length > 0 )
				this._.output.push( this.lineBreakChars );
			this._.indent = 1;
		},

		/**
		 * Writes the current indentation chars. It uses the {@link #indentationChars}
		 * property, repeating it for the current indentation steps.
		 *
		 *		// Writes '\t' (e.g.).
		 *		writer.indentation();
		 */
		indentation: function() {
			if ( !this._.inPre && this._.indentation )
				this._.output.push( this._.indentation );
			this._.indent = 0;
		},

		/**
		 * Empties the current output buffer. It also brings back the default
		 * values of the writer flags.
		 *
		 *		writer.reset();
		 */
		reset: function() {
			this._.output = [];
			this._.indent = 0;
			this._.indentation = '';
			this._.afterCloser = 0;
			this._.inPre = 0;
		},

		/**
		 * Sets formatting rules for a give element. The possible rules are:
		 *
		 * * `indent`: indent the element contents.
		 * * `breakBeforeOpen`: break line before the opener tag for this element.
		 * * `breakAfterOpen`: break line after the opener tag for this element.
		 * * `breakBeforeClose`: break line before the closer tag for this element.
		 * * `breakAfterClose`: break line after the closer tag for this element.
		 *
		 * All rules default to `false`. Each call to the function overrides
		 * already present rules, leaving the undefined untouched.
		 *
		 * By default, all elements available in the {@link CKEDITOR.dtd#$block},
		 * {@link CKEDITOR.dtd#$listItem} and {@link CKEDITOR.dtd#$tableContent}
		 * lists have all the above rules set to `true`. Additionaly, the `<br>`
		 * element has the `breakAfterOpen` set to `true`.
		 *
		 *		// Break line before and after "img" tags.
		 *		writer.setRules( 'img', {
		 *			breakBeforeOpen: true
		 *			breakAfterOpen: true
		 *		} );
		 *
		 *		// Reset the rules for the "h1" tag.
		 *		writer.setRules( 'h1', {} );
		 *
		 * @param {String} tagName The element name to which set the rules.
		 * @param {Object} rules An object containing the element rules.
		 */
		setRules: function( tagName, rules ) {
			var currentRules = this._.rules[ tagName ];

			if ( currentRules )
				CKEDITOR.tools.extend( currentRules, rules, true );
			else
				this._.rules[ tagName ] = rules;
		}
	}
});

/**
 * Whether to force using `'&'` instead of `'&amp;'` in elements attributes
 * values, it's not recommended to change this setting for compliance with the
 * W3C XHTML 1.0 standards ([C.12, XHTML 1.0](http://www.w3.org/TR/xhtml1/#C_12)).
 *
 *		// Use `'&'` instead of `'&amp;'`
 *		CKEDITOR.config.forceSimpleAmpersand = true;
 *
 * @cfg {Boolean} [forceSimpleAmpersand=false]
 * @member CKEDITOR.config
 */

/**
 * The characters to be used for indenting the HTML produced by the editor.
 * Using characters different than `' '` (space) and `'\t'` (tab) is definitely
 * a bad idea as it'll mess the code.
 *
 *		// No indentation.
 *		CKEDITOR.config.dataIndentationChars = '';
 *
 *		// Use two spaces for indentation.
 *		CKEDITOR.config.dataIndentationChars = '  ';
 *
 * @cfg {String} [dataIndentationChars='\t']
 * @member CKEDITOR.config
 */
