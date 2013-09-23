/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the {@link CKEDITOR.dom.element} class, which
 *		represents a DOM element.
 */

/**
 * Represents a DOM element.
 *
 *		// Create a new <span> element.
 *		var element = new CKEDITOR.dom.element( 'span' );
 *
 *		// Create an element based on a native DOM element.
 *		var element = new CKEDITOR.dom.element( document.getElementById( 'myId' ) );
 *
 * @class
 * @extends CKEDITOR.dom.node
 * @constructor Creates an element class instance.
 * @param {Object/String} element A native DOM element or the element name for
 * new elements.
 * @param {CKEDITOR.dom.document} [ownerDocument] The document that will contain
 * the element in case of element creation.
 */
CKEDITOR.dom.element = function( element, ownerDocument ) {
	if ( typeof element == 'string' )
		element = ( ownerDocument ? ownerDocument.$ : document ).createElement( element );

	// Call the base constructor (we must not call CKEDITOR.dom.node).
	CKEDITOR.dom.domObject.call( this, element );
};

// PACKAGER_RENAME( CKEDITOR.dom.element )
/**
 * The the {@link CKEDITOR.dom.element} representing and element. If the
 * element is a native DOM element, it will be transformed into a valid
 * CKEDITOR.dom.element object.
 *
 *		var element = new CKEDITOR.dom.element( 'span' );
 *		alert( element == CKEDITOR.dom.element.get( element ) ); // true
 *
 *		var element = document.getElementById( 'myElement' );
 *		alert( CKEDITOR.dom.element.get( element ).getName() ); // (e.g.) 'p'
 *
 * @static
 * @param {String/Object} element Element's id or name or native DOM element.
 * @returns {CKEDITOR.dom.element} The transformed element.
 */
CKEDITOR.dom.element.get = function( element ) {
	var el = typeof element == 'string' ? document.getElementById( element ) || document.getElementsByName( element )[ 0 ] : element;

	return el && ( el.$ ? el : new CKEDITOR.dom.element( el ) );
};

CKEDITOR.dom.element.prototype = new CKEDITOR.dom.node();

/**
 * Creates an instance of the {@link CKEDITOR.dom.element} class based on the
 * HTML representation of an element.
 *
 *		var element = CKEDITOR.dom.element.createFromHtml( '<strong class="anyclass">My element</strong>' );
 *		alert( element.getName() ); // 'strong'
 *
 * @static
 * @param {String} html The element HTML. It should define only one element in
 * the "root" level. The "root" element can have child nodes, but not siblings.
 * @returns {CKEDITOR.dom.element} The element instance.
 */
CKEDITOR.dom.element.createFromHtml = function( html, ownerDocument ) {
	var temp = new CKEDITOR.dom.element( 'div', ownerDocument );
	temp.setHtml( html );

	// When returning the node, remove it from its parent to detach it.
	return temp.getFirst().remove();
};

/**
 * @static
 * @todo
 */
CKEDITOR.dom.element.setMarker = function( database, element, name, value ) {
	var id = element.getCustomData( 'list_marker_id' ) || ( element.setCustomData( 'list_marker_id', CKEDITOR.tools.getNextNumber() ).getCustomData( 'list_marker_id' ) ),
		markerNames = element.getCustomData( 'list_marker_names' ) || ( element.setCustomData( 'list_marker_names', {} ).getCustomData( 'list_marker_names' ) );
	database[ id ] = element;
	markerNames[ name ] = 1;

	return element.setCustomData( name, value );
};

/**
 * @static
 * @todo
 */
CKEDITOR.dom.element.clearAllMarkers = function( database ) {
	for ( var i in database )
		CKEDITOR.dom.element.clearMarkers( database, database[ i ], 1 );
};

/**
 * @static
 * @todo
 */
CKEDITOR.dom.element.clearMarkers = function( database, element, removeFromDatabase ) {
	var names = element.getCustomData( 'list_marker_names' ),
		id = element.getCustomData( 'list_marker_id' );
	for ( var i in names )
		element.removeCustomData( i );
	element.removeCustomData( 'list_marker_names' );
	if ( removeFromDatabase ) {
		element.removeCustomData( 'list_marker_id' );
		delete database[ id ];
	}
};
( function() {

CKEDITOR.tools.extend( CKEDITOR.dom.element.prototype, {
	/**
	 * The node type. This is a constant value set to {@link CKEDITOR#NODE_ELEMENT}.
	 *
	 * @readonly
	 * @property {Number} [=CKEDITOR.NODE_ELEMENT]
	 */
	type: CKEDITOR.NODE_ELEMENT,

	/**
	 * Adds a CSS class to the element. It appends the class to the
	 * already existing names.
	 *
	 *		var element = new CKEDITOR.dom.element( 'div' );
	 *		element.addClass( 'classA' ); // <div class="classA">
	 *		element.addClass( 'classB' ); // <div class="classA classB">
	 *		element.addClass( 'classA' ); // <div class="classA classB">
	 *
	 * @param {String} className The name of the class to be added.
	 */
	addClass: function( className ) {
		var c = this.$.className;
		if ( c ) {
			var regex = new RegExp( '(?:^|\\s)' + className + '(?:\\s|$)', '' );
			if ( !regex.test( c ) )
				c += ' ' + className;
		}
		this.$.className = c || className;
	},

	/**
	 * Removes a CSS class name from the elements classes. Other classes
	 * remain untouched.
	 *
	 *		var element = new CKEDITOR.dom.element( 'div' );
	 *		element.addClass( 'classA' );		// <div class="classA">
	 *		element.addClass( 'classB' );		// <div class="classA classB">
	 *		element.removeClass( 'classA' );	// <div class="classB">
	 *		element.removeClass( 'classB' );	// <div>
	 *
	 * @chainable
	 * @param {String} className The name of the class to remove.
	 */
	removeClass: function( className ) {
		var c = this.getAttribute( 'class' );
		if ( c ) {
			var regex = new RegExp( '(?:^|\\s+)' + className + '(?=\\s|$)', 'i' );
			if ( regex.test( c ) ) {
				c = c.replace( regex, '' ).replace( /^\s+/, '' );

				if ( c )
					this.setAttribute( 'class', c );
				else
					this.removeAttribute( 'class' );
			}
		}

		return this;
	},

	/**
	 * Checks if element has class name.
	 *
	 * @param {String} className
	 * @returns {Boolean}
	 */
	hasClass: function( className ) {
		var regex = new RegExp( '(?:^|\\s+)' + className + '(?=\\s|$)', '' );
		return regex.test( this.getAttribute( 'class' ) );
	},

	/**
	 * Append a node as a child of this element.
	 *
	 *		var p = new CKEDITOR.dom.element( 'p' );
	 *
	 *		var strong = new CKEDITOR.dom.element( 'strong' );
	 *		p.append( strong );
	 *
	 *		var em = p.append( 'em' );
	 *
	 *		// Result: '<p><strong></strong><em></em></p>'
	 *
	 * @param {CKEDITOR.dom.node/String} node The node or element name to be appended.
	 * @param {Boolean} [toStart=false] Indicates that the element is to be appended at the start.
	 * @returns {CKEDITOR.dom.node} The appended node.
	 */
	append: function( node, toStart ) {
		if ( typeof node == 'string' )
			node = this.getDocument().createElement( node );

		if ( toStart )
			this.$.insertBefore( node.$, this.$.firstChild );
		else
			this.$.appendChild( node.$ );

		return node;
	},

	/**
	 * Append HTML as a child(ren) of this element.
	 *
	 * @param {String} html
	 */
	appendHtml: function( html ) {
		if ( !this.$.childNodes.length )
			this.setHtml( html );
		else {
			var temp = new CKEDITOR.dom.element( 'div', this.getDocument() );
			temp.setHtml( html );
			temp.moveChildren( this );
		}
	},

	/**
	 * Append text to this element.
	 *
	 *		var p = new CKEDITOR.dom.element( 'p' );
	 *		p.appendText( 'This is' );
	 *		p.appendText( ' some text' );
	 *
	 *		// Result: '<p>This is some text</p>'
	 *
	 * @param {String} text The text to be appended.
	 * @returns {CKEDITOR.dom.node} The appended node.
	 */
	appendText: function( text ) {
		if ( this.$.text != undefined )
			this.$.text += text;
		else
			this.append( new CKEDITOR.dom.text( text ) );
	},

	/**
	 * @todo
	 */
	appendBogus: function() {
		var lastChild = this.getLast();

		// Ignore empty/spaces text.
		while ( lastChild && lastChild.type == CKEDITOR.NODE_TEXT && !CKEDITOR.tools.rtrim( lastChild.getText() ) )
			lastChild = lastChild.getPrevious();
		if ( !lastChild || !lastChild.is || !lastChild.is( 'br' ) ) {
			var bogus = CKEDITOR.env.opera ? this.getDocument().createText( '' ) : this.getDocument().createElement( 'br' );

			CKEDITOR.env.gecko && bogus.setAttribute( 'type', '_moz' );

			this.append( bogus );
		}
	},

	/**
	 * Breaks one of the ancestor element in the element position, moving
	 * this element between the broken parts.
	 *
	 *		// Before breaking:
	 *		//		<b>This <i>is some<span /> sample</i> test text</b>
	 *		// If "element" is <span /> and "parent" is <i>:
	 *		//		<b>This <i>is some</i><span /><i> sample</i> test text</b>
	 *		element.breakParent( parent );
	 *
	 *		// Before breaking:
	 *		//		<b>This <i>is some<span /> sample</i> test text</b>
	 *		// If "element" is <span /> and "parent" is <b>:
	 *		//		<b>This <i>is some</i></b><span /><b><i> sample</i> test text</b>
	 *		element.breakParent( parent );
	 *
	 * @param {CKEDITOR.dom.element} parent The anscestor element to get broken.
	 */
	breakParent: function( parent ) {
		var range = new CKEDITOR.dom.range( this.getDocument() );

		// We'll be extracting part of this element, so let's use our
		// range to get the correct piece.
		range.setStartAfter( this );
		range.setEndAfter( parent );

		// Extract it.
		var docFrag = range.extractContents();

		// Move the element outside the broken element.
		range.insertNode( this.remove() );

		// Re-insert the extracted piece after the element.
		docFrag.insertAfterNode( this );
	},

	/**
	 * Checks if this element contains given node.
	 *
	 * @method
	 * @param {CKEDITOR.dom.node} node
	 * @returns {Boolean}
	 */
	contains: CKEDITOR.env.ie || CKEDITOR.env.webkit ?
		function( node ) {
			var $ = this.$;

			return node.type != CKEDITOR.NODE_ELEMENT ? $.contains( node.getParent().$ ) : $ != node.$ && $.contains( node.$ );
		} : function( node ) {
			return !!( this.$.compareDocumentPosition( node.$ ) & 16 );
		},

	/**
	 * Moves the selection focus to this element.
	 *
	 *		var element = CKEDITOR.document.getById( 'myTextarea' );
	 *		element.focus();
	 *
	 * @method
	 * @param  {Boolean} defer Whether to asynchronously defer the
	 * execution by 100 ms.
	 */
	focus: (function() {
		function exec() {
			// IE throws error if the element is not visible.
			try {
				this.$.focus();
			} catch ( e ) {}
		}

		return function( defer ) {
			if ( defer )
				CKEDITOR.tools.setTimeout( exec, 100, this );
			else
				exec.call( this );
		};
	})(),

	/**
	 * Gets the inner HTML of this element.
	 *
	 *		var element = CKEDITOR.dom.element.createFromHtml( '<div><b>Example</b></div>' );
	 *		alert( element.getHtml() ); // '<b>Example</b>'
	 *
	 * @returns {String} The inner HTML of this element.
	 */
	getHtml: function() {
		var retval = this.$.innerHTML;
		// Strip <?xml:namespace> tags in IE. (#3341).
		return CKEDITOR.env.ie ? retval.replace( /<\?[^>]*>/g, '' ) : retval;
	},

	/**
	 * Gets the outer (inner plus tags) HTML of this element.
	 *
	 *		var element = CKEDITOR.dom.element.createFromHtml( '<div class="bold"><b>Example</b></div>' );
	 *		alert( element.getOuterHtml() ); // '<div class="bold"><b>Example</b></div>'
	 *
	 * @returns {String} The outer HTML of this element.
	 */
	getOuterHtml: function() {
		if ( this.$.outerHTML ) {
			// IE includes the <?xml:namespace> tag in the outerHTML of
			// namespaced element. So, we must strip it here. (#3341)
			return this.$.outerHTML.replace( /<\?[^>]*>/, '' );
		}

		var tmpDiv = this.$.ownerDocument.createElement( 'div' );
		tmpDiv.appendChild( this.$.cloneNode( true ) );
		return tmpDiv.innerHTML;
	},

	/**
	 * Retrieve the bounding rectangle of the current element, in pixels,
	 * relative to the upper-left corner of the browser's client area.
	 *
	 * @returns {Object} The dimensions of the DOM element including
	 * `left`, `top`, `right`, `bottom`, `width` and `height`.
	 */
	getClientRect: function() {
		// http://help.dottoro.com/ljvmcrrn.php
		var rect = CKEDITOR.tools.extend( {}, this.$.getBoundingClientRect() );

		!rect.width && ( rect.width = rect.right - rect.left );
		!rect.height && ( rect.height = rect.bottom - rect.top );

		return rect;
	},

	/**
	 * Sets the inner HTML of this element.
	 *
	 *		var p = new CKEDITOR.dom.element( 'p' );
	 *		p.setHtml( '<b>Inner</b> HTML' );
	 *
	 *		// Result: '<p><b>Inner</b> HTML</p>'
	 *
	 * @method
	 * @param {String} html The HTML to be set for this element.
	 * @returns {String} The inserted HTML.
	 */
	setHtml: ( CKEDITOR.env.ie && CKEDITOR.env.version < 9 ) ?
			// old IEs throws error on HTML manipulation (through the "innerHTML" property)
			// on the element which resides in an DTD invalid position,  e.g. <span><div></div></span>
			// fortunately it can be worked around with DOM manipulation.
			function( html ) {
				try {
					var $ = this.$;

					// Fix the case when setHtml is called on detached element.
					// HTML5 shiv used for document in which this element was created
					// won't affect that detached element. So get document fragment with
					// all HTML5 elements enabled and set innerHTML while this element is appended to it.
					if ( this.getParent() )
						return ( $.innerHTML = html );
					else {
						var $frag = this.getDocument()._getHtml5ShivFrag();
						$frag.appendChild( $ );
						$.innerHTML = html;
						$frag.removeChild( $ );

						return html;
					}
				}
				catch ( e ) {
					this.$.innerHTML = '';

					var temp = new CKEDITOR.dom.element( 'body', this.getDocument() );
					temp.$.innerHTML = html;

					var children = temp.getChildren();
					while ( children.count() )
						this.append( children.getItem( 0 ) );

					return html;
				}
			}
		:
			function( html ) {
				return ( this.$.innerHTML = html );
			},

	/**
	 * Sets the element contents as plain text.
	 *
	 *		var element = new CKEDITOR.dom.element( 'div' );
	 *		element.setText( 'A > B & C < D' );
	 *		alert( element.innerHTML ); // 'A &gt; B &amp; C &lt; D'
	 *
	 * @param {String} text The text to be set.
	 * @returns {String} The inserted text.
	 */
	setText: function( text ) {
		CKEDITOR.dom.element.prototype.setText = ( this.$.innerText != undefined ) ?
			function( text ) {
				return this.$.innerText = text;
			} : function( text ) {
				return this.$.textContent = text;
			};

		return this.setText( text );
	},

	/**
	 * Gets the value of an element attribute.
	 *
	 *		var element = CKEDITOR.dom.element.createFromHtml( '<input type="text" />' );
	 *		alert( element.getAttribute( 'type' ) ); // 'text'
	 *
	 * @method
	 * @param {String} name The attribute name.
	 * @returns {String} The attribute value or null if not defined.
	 */
	getAttribute: (function() {
		var standard = function( name ) {
				return this.$.getAttribute( name, 2 );
			};

		if ( CKEDITOR.env.ie && ( CKEDITOR.env.ie7Compat || CKEDITOR.env.ie6Compat ) ) {
			return function( name ) {
				switch ( name ) {
					case 'class':
						name = 'className';
						break;

					case 'http-equiv':
						name = 'httpEquiv';
						break;

					case 'name':
						return this.$.name;

					case 'tabindex':
						var tabIndex = standard.call( this, name );

						// IE returns tabIndex=0 by default for all
						// elements. For those elements,
						// getAtrribute( 'tabindex', 2 ) returns 32768
						// instead. So, we must make this check to give a
						// uniform result among all browsers.
						if ( tabIndex !== 0 && this.$.tabIndex === 0 )
							tabIndex = null;

						return tabIndex;
						break;

					case 'checked':
						{
							var attr = this.$.attributes.getNamedItem( name ),
								attrValue = attr.specified ? attr.nodeValue // For value given by parser.
								: this.$.checked; // For value created via DOM interface.

							return attrValue ? 'checked' : null;
						}

					case 'hspace':
					case 'value':
						return this.$[ name ];

					case 'style':
						// IE does not return inline styles via getAttribute(). See #2947.
						return this.$.style.cssText;

					case 'contenteditable':
					case 'contentEditable':
						return this.$.attributes.getNamedItem( 'contentEditable' ).specified ? this.$.getAttribute( 'contentEditable' ) : null;
				}

				return standard.call( this, name );
			};
		} else
			return standard;
	})(),

	/**
	 * Gets the nodes list containing all children of this element.
	 *
	 * @returns {CKEDITOR.dom.nodeList}
	 */
	getChildren: function() {
		return new CKEDITOR.dom.nodeList( this.$.childNodes );
	},

	/**
	 * Gets the current computed value of one of the element CSS style
	 * properties.
	 *
	 *		var element = new CKEDITOR.dom.element( 'span' );
	 *		alert( element.getComputedStyle( 'display' ) ); // 'inline'
	 *
	 * @method
	 * @param {String} propertyName The style property name.
	 * @returns {String} The property value.
	 */
	getComputedStyle: CKEDITOR.env.ie ?
		function( propertyName ) {
			return this.$.currentStyle[ CKEDITOR.tools.cssStyleToDomStyle( propertyName ) ];
		} : function( propertyName ) {
			var style = this.getWindow().$.getComputedStyle( this.$, null );
			// Firefox may return null if we call the above on a hidden iframe. (#9117)
			return style ? style.getPropertyValue( propertyName ) : '';
		},

	/**
	 * Gets the DTD entries for this element.
	 *
	 * @returns {Object} An object containing the list of elements accepted
	 * by this element.
	 */
	getDtd: function() {
		var dtd = CKEDITOR.dtd[ this.getName() ];

		this.getDtd = function() {
			return dtd;
		};

		return dtd;
	},

	/**
	 * Gets all this element's descendants having given tag name.
	 *
	 * @method
	 * @param {String} tagName
	 */
	getElementsByTag: CKEDITOR.dom.document.prototype.getElementsByTag,

	/**
	 * Gets the computed tabindex for this element.
	 *
	 *		var element = CKEDITOR.document.getById( 'myDiv' );
	 *		alert( element.getTabIndex() ); // (e.g.) '-1'
	 *
	 * @method
	 * @returns {Number} The tabindex value.
	 */
	getTabIndex: CKEDITOR.env.ie ?
		function() {
			var tabIndex = this.$.tabIndex;

			// IE returns tabIndex=0 by default for all elements. In
			// those cases we must check that the element really has
			// the tabindex attribute set to zero, or it is one of
			// those element that should have zero by default.
			if ( tabIndex === 0 && !CKEDITOR.dtd.$tabIndex[ this.getName() ] && parseInt( this.getAttribute( 'tabindex' ), 10 ) !== 0 )
				tabIndex = -1;

			return tabIndex;
		} : CKEDITOR.env.webkit ?
		function() {
			var tabIndex = this.$.tabIndex;

			// Safari returns "undefined" for elements that should not
			// have tabindex (like a div). So, we must try to get it
			// from the attribute.
			// https://bugs.webkit.org/show_bug.cgi?id=20596
			if ( tabIndex == undefined ) {
				tabIndex = parseInt( this.getAttribute( 'tabindex' ), 10 );

				// If the element don't have the tabindex attribute,
				// then we should return -1.
				if ( isNaN( tabIndex ) )
					tabIndex = -1;
			}

			return tabIndex;
		} : function() {
			return this.$.tabIndex;
		},

	/**
	 * Gets the text value of this element.
	 *
	 * Only in IE (which uses innerText), `<br>` will cause linebreaks,
	 * and sucessive whitespaces (including line breaks) will be reduced to
	 * a single space. This behavior is ok for us, for now. It may change
	 * in the future.
	 *
	 *		var element = CKEDITOR.dom.element.createFromHtml( '<div>Sample <i>text</i>.</div>' );
	 *		alert( <b>element.getText()</b> ); // 'Sample text.'
	 *
	 * @returns {String} The text value.
	 */
	getText: function() {
		return this.$.textContent || this.$.innerText || '';
	},

	/**
	 * Gets the window object that contains this element.
	 *
	 * @returns {CKEDITOR.dom.window} The window object.
	 */
	getWindow: function() {
		return this.getDocument().getWindow();
	},

	/**
	 * Gets the value of the `id` attribute of this element.
	 *
	 *		var element = CKEDITOR.dom.element.createFromHtml( '<p id="myId"></p>' );
	 *		alert( element.getId() ); // 'myId'
	 *
	 * @returns {String} The element id, or null if not available.
	 */
	getId: function() {
		return this.$.id || null;
	},

	/**
	 * Gets the value of the `name` attribute of this element.
	 *
	 *		var element = CKEDITOR.dom.element.createFromHtml( '<input name="myName"></input>' );
	 *		alert( <b>element.getNameAtt()</b> ); // 'myName'
	 *
	 * @returns {String} The element name, or null if not available.
	 */
	getNameAtt: function() {
		return this.$.name || null;
	},

	/**
	 * Gets the element name (tag name). The returned name is guaranteed to
	 * be always full lowercased.
	 *
	 *		var element = new CKEDITOR.dom.element( 'span' );
	 *		alert( element.getName() ); // 'span'
	 *
	 * @returns {String} The element name.
	 */
	getName: function() {
		// Cache the lowercased name inside a closure.
		var nodeName = this.$.nodeName.toLowerCase();

		if ( CKEDITOR.env.ie && !( document.documentMode > 8 ) ) {
			var scopeName = this.$.scopeName;
			if ( scopeName != 'HTML' )
				nodeName = scopeName.toLowerCase() + ':' + nodeName;
		}

		return ( this.getName = function() {
			return nodeName;
		})();
	},

	/**
	 * Gets the value set to this element. This value is usually available
	 * for form field elements.
	 *
	 * @returns {String} The element value.
	 */
	getValue: function() {
		return this.$.value;
	},

	/**
	 * Gets the first child node of this element.
	 *
	 *		var element = CKEDITOR.dom.element.createFromHtml( '<div><b>Example</b></div>' );
	 *		var first = element.getFirst();
	 *		alert( first.getName() ); // 'b'
	 *
	 * @param {Function} evaluator Filtering the result node.
	 * @returns {CKEDITOR.dom.node} The first child node or null if not available.
	 */
	getFirst: function( evaluator ) {
		var first = this.$.firstChild,
			retval = first && new CKEDITOR.dom.node( first );
		if ( retval && evaluator && !evaluator( retval ) )
			retval = retval.getNext( evaluator );

		return retval;
	},

	/**
	 * See {@link #getFirst}.
	 *
	 * @param {Function} evaluator Filtering the result node.
	 * @returns {CKEDITOR.dom.node}
	 */
	getLast: function( evaluator ) {
		var last = this.$.lastChild,
			retval = last && new CKEDITOR.dom.node( last );
		if ( retval && evaluator && !evaluator( retval ) )
			retval = retval.getPrevious( evaluator );

		return retval;
	},

	/**
	 * Gets CSS style value.
	 *
	 * @param {String} name The CSS property name.
	 * @returns {String} Style value.
	 */
	getStyle: function( name ) {
		return this.$.style[ CKEDITOR.tools.cssStyleToDomStyle( name ) ];
	},

	/**
	 * Checks if the element name matches the specified criteria.
	 *
	 *		var element = new CKEDITOR.element( 'span' );
	 *		alert( element.is( 'span' ) );			// true
	 *		alert( element.is( 'p', 'span' ) );		// true
	 *		alert( element.is( 'p' ) );				// false
	 *		alert( element.is( 'p', 'div' ) );		// false
	 *		alert( element.is( { p:1,span:1 } ) );	// true
	 *
	 * @param {String.../Object} name One or more names to be checked, or a {@link CKEDITOR.dtd} object.
	 * @returns {Boolean} `true` if the element name matches any of the names.
	 */
	is: function() {
		var name = this.getName();

		// Check against the specified DTD liternal.
		if ( typeof arguments[ 0 ] == 'object' )
			return !!arguments[ 0 ][ name ];

		// Check for tag names
		for ( var i = 0; i < arguments.length; i++ ) {
			if ( arguments[ i ] == name )
				return true;
		}
		return false;
	},

	/**
	 * Decide whether one element is able to receive cursor.
	 *
	 * @param {Boolean} [textCursor=true] Only consider element that could receive text child.
	 */
	isEditable: function( textCursor ) {
		var name = this.getName();

		if ( this.isReadOnly() || this.getComputedStyle( 'display' ) == 'none' ||
				 this.getComputedStyle( 'visibility' ) == 'hidden' ||
				 CKEDITOR.dtd.$nonEditable[ name ] ||
				 CKEDITOR.dtd.$empty[ name ] ||
				 ( this.is( 'a' ) &&
					 ( this.data( 'cke-saved-name' ) || this.hasAttribute( 'name' ) ) &&
					 !this.getChildCount()
				 ) )
		{
			return false;
		}

		if ( textCursor !== false ) {
			// Get the element DTD (defaults to span for unknown elements).
			var dtd = CKEDITOR.dtd[ name ] || CKEDITOR.dtd.span;
			// In the DTD # == text node.
			return !!( dtd && dtd[ '#' ] );
		}

		return true;
	},

	/**
	 * Compare this element's inner html, tag name, attributes, etc. with other one.
	 *
	 * See [W3C's DOM Level 3 spec - node#isEqualNode](http://www.w3.org/TR/DOM-Level-3-Core/core.html#Node3-isEqualNode)
	 * for more details.
	 *
	 * @param {CKEDITOR.dom.element} otherElement Element to compare.
	 * @returns {Boolean}
	 */
	isIdentical: function( otherElement ) {
		// do shallow clones, but with IDs
		var thisEl = this.clone( 0, 1 ),
			otherEl = otherElement.clone( 0, 1 );

		// Remove distractions.
		thisEl.removeAttributes( [ '_moz_dirty', 'data-cke-expando', 'data-cke-saved-href', 'data-cke-saved-name' ] );
		otherEl.removeAttributes( [ '_moz_dirty', 'data-cke-expando', 'data-cke-saved-href', 'data-cke-saved-name' ] );

		// Native comparison available.
		if ( thisEl.$.isEqualNode ) {
			// Styles order matters.
			thisEl.$.style.cssText = CKEDITOR.tools.normalizeCssText( thisEl.$.style.cssText );
			otherEl.$.style.cssText = CKEDITOR.tools.normalizeCssText( otherEl.$.style.cssText );
			return thisEl.$.isEqualNode( otherEl.$ );
		} else {
			thisEl = thisEl.getOuterHtml();
			otherEl = otherEl.getOuterHtml();

			// Fix tiny difference between link href in older IEs.
			if ( CKEDITOR.env.ie && CKEDITOR.env.version < 9 && this.is( 'a' ) ) {
				var parent = this.getParent();
				if ( parent.type == CKEDITOR.NODE_ELEMENT ) {
					var el = parent.clone();
					el.setHtml( thisEl ), thisEl = el.getHtml();
					el.setHtml( otherEl ), otherEl = el.getHtml();
				}
			}

			return thisEl == otherEl;
		}
	},

	/**
	 * Checks if this element is visible. May not work if the element is
	 * child of an element with visibility set to `hidden`, but works well
	 * on the great majority of cases.
	 *
	 * @returns {Boolean} True if the element is visible.
	 */
	isVisible: function() {
		var isVisible = ( this.$.offsetHeight || this.$.offsetWidth ) && this.getComputedStyle( 'visibility' ) != 'hidden',
			elementWindow, elementWindowFrame;

		// Webkit and Opera report non-zero offsetHeight despite that
		// element is inside an invisible iframe. (#4542)
		if ( isVisible && ( CKEDITOR.env.webkit || CKEDITOR.env.opera ) ) {
			elementWindow = this.getWindow();

			if ( !elementWindow.equals( CKEDITOR.document.getWindow() ) && ( elementWindowFrame = elementWindow.$.frameElement ) ) {
				isVisible = new CKEDITOR.dom.element( elementWindowFrame ).isVisible();
			}
		}

		return !!isVisible;
	},

	/**
	 * Whether it's an empty inline elements which has no visual impact when removed.
	 *
	 * @returns {Boolean}
	 */
	isEmptyInlineRemoveable: function() {
		if ( !CKEDITOR.dtd.$removeEmpty[ this.getName() ] )
			return false;

		var children = this.getChildren();
		for ( var i = 0, count = children.count(); i < count; i++ ) {
			var child = children.getItem( i );

			if ( child.type == CKEDITOR.NODE_ELEMENT && child.data( 'cke-bookmark' ) )
				continue;

			if ( child.type == CKEDITOR.NODE_ELEMENT && !child.isEmptyInlineRemoveable() || child.type == CKEDITOR.NODE_TEXT && CKEDITOR.tools.trim( child.getText() ) ) {
				return false;
			}
		}
		return true;
	},

	/**
	 * Checks if the element has any defined attributes.
	 *
	 *		var element = CKEDITOR.dom.element.createFromHtml( '<div title="Test">Example</div>' );
	 *		alert( element.hasAttributes() ); // true
	 *
	 *		var element = CKEDITOR.dom.element.createFromHtml( '<div>Example</div>' );
	 *		alert( element.hasAttributes() ); // false
	 *
	 * @method
	 * @returns {Boolean} True if the element has attributes.
	 */
	hasAttributes: CKEDITOR.env.ie && ( CKEDITOR.env.ie7Compat || CKEDITOR.env.ie6Compat ) ?
		function() {
			var attributes = this.$.attributes;

			for ( var i = 0; i < attributes.length; i++ ) {
				var attribute = attributes[ i ];

				switch ( attribute.nodeName ) {
					case 'class':
						// IE has a strange bug. If calling removeAttribute('className'),
						// the attributes collection will still contain the "class"
						// attribute, which will be marked as "specified", even if the
						// outerHTML of the element is not displaying the class attribute.
						// Note : I was not able to reproduce it outside the editor,
						// but I've faced it while working on the TC of #1391.
						if ( this.getAttribute( 'class' ) )
							return true;

						// Attributes to be ignored.
					case 'data-cke-expando':
						continue;

						/*jsl:fallthru*/

					default:
						if ( attribute.specified )
							return true;
				}
			}

			return false;
		} : function() {
			var attrs = this.$.attributes,
				attrsNum = attrs.length;

			// The _moz_dirty attribute might get into the element after pasting (#5455)
			var execludeAttrs = { 'data-cke-expando':1,_moz_dirty:1 };

			return attrsNum > 0 && ( attrsNum > 2 || !execludeAttrs[ attrs[ 0 ].nodeName ] || ( attrsNum == 2 && !execludeAttrs[ attrs[ 1 ].nodeName ] ) );
		},

	/**
	 * Checks if the specified attribute is defined for this element.
	 *
	 * @method
	 * @param {String} name The attribute name.
	 * @returns {Boolean} `true` if the specified attribute is defined.
	 */
	hasAttribute: (function() {
		function standard( name ) {
			var $attr = this.$.attributes.getNamedItem( name );
			return !!( $attr && $attr.specified );
		}

		return ( CKEDITOR.env.ie && CKEDITOR.env.version < 8 ) ?
		function( name ) {
			// On IE < 8 the name attribute cannot be retrieved
			// right after the element creation and setting the
			// name with setAttribute.
			if ( name == 'name' )
				return !!this.$.name;

			return standard.call( this, name );
		} : standard;
	})(),

	/**
	 * Hides this element (sets `display: none`).
	 *
	 *		var element = CKEDITOR.document.getById( 'myElement' );
	 *		element.hide();
	 */
	hide: function() {
		this.setStyle( 'display', 'none' );
	},

	/**
	 * Moves this element's children to the target element.
	 *
	 * @param {CKEDITOR.dom.element} target
	 * @param {Boolean} [toStart=false] Insert moved children at the
	 * beginning of the target element.
	 */
	moveChildren: function( target, toStart ) {
		var $ = this.$;
		target = target.$;

		if ( $ == target )
			return;

		var child;

		if ( toStart ) {
			while ( ( child = $.lastChild ) )
				target.insertBefore( $.removeChild( child ), target.firstChild );
		} else {
			while ( ( child = $.firstChild ) )
				target.appendChild( $.removeChild( child ) );
		}
	},

	/**
	 * Merges sibling elements that are identical to this one.
	 *
	 * Identical child elements are also merged. For example:
	 *
	 *		<b><i></i></b><b><i></i></b> => <b><i></i></b>
	 *
	 * @method
	 * @param {Boolean} [inlineOnly=true] Allow only inline elements to be merged.
	 */
	mergeSiblings: (function() {
		function mergeElements( element, sibling, isNext ) {
			if ( sibling && sibling.type == CKEDITOR.NODE_ELEMENT ) {
				// Jumping over bookmark nodes and empty inline elements, e.g. <b><i></i></b>,
				// queuing them to be moved later. (#5567)
				var pendingNodes = [];

				while ( sibling.data( 'cke-bookmark' ) || sibling.isEmptyInlineRemoveable() ) {
					pendingNodes.push( sibling );
					sibling = isNext ? sibling.getNext() : sibling.getPrevious();
					if ( !sibling || sibling.type != CKEDITOR.NODE_ELEMENT )
						return;
				}

				if ( element.isIdentical( sibling ) ) {
					// Save the last child to be checked too, to merge things like
					// <b><i></i></b><b><i></i></b> => <b><i></i></b>
					var innerSibling = isNext ? element.getLast() : element.getFirst();

					// Move pending nodes first into the target element.
					while ( pendingNodes.length )
						pendingNodes.shift().move( element, !isNext );

					sibling.moveChildren( element, !isNext );
					sibling.remove();

					// Now check the last inner child (see two comments above).
					if ( innerSibling && innerSibling.type == CKEDITOR.NODE_ELEMENT )
						innerSibling.mergeSiblings();
				}
			}
		}

		return function( inlineOnly ) {
			if ( !( inlineOnly === false || CKEDITOR.dtd.$removeEmpty[ this.getName() ] || this.is( 'a' ) ) ) // Merge empty links and anchors also. (#5567)
			{
				return;
			}

			mergeElements( this, this.getNext(), true );
			mergeElements( this, this.getPrevious() );
		};
	})(),

	/**
	 * Shows this element (displays it).
	 *
	 *		var element = CKEDITOR.document.getById( 'myElement' );
	 *		element.show();
	 */
	show: function() {
		this.setStyles({
			display: '',
			visibility: ''
		});
	},

	/**
	 * Sets the value of an element attribute.
	 *
	 *		var element = CKEDITOR.document.getById( 'myElement' );
	 *		element.setAttribute( 'class', 'myClass' );
	 *		element.setAttribute( 'title', 'This is an example' );
	 *
	 * @method
	 * @param {String} name The name of the attribute.
	 * @param {String} value The value to be set to the attribute.
	 * @returns {CKEDITOR.dom.element} This element instance.
	 */
	setAttribute: (function() {
		var standard = function( name, value ) {
				this.$.setAttribute( name, value );
				return this;
			};

		if ( CKEDITOR.env.ie && ( CKEDITOR.env.ie7Compat || CKEDITOR.env.ie6Compat ) ) {
			return function( name, value ) {
				if ( name == 'class' )
					this.$.className = value;
				else if ( name == 'style' )
					this.$.style.cssText = value;
				else if ( name == 'tabindex' ) // Case sensitive.
				this.$.tabIndex = value;
				else if ( name == 'checked' )
					this.$.checked = value;
				else if ( name == 'contenteditable' )
					standard.call( this, 'contentEditable', value );
				else
					standard.apply( this, arguments );
				return this;
			};
		} else if ( CKEDITOR.env.ie8Compat && CKEDITOR.env.secure ) {
			return function( name, value ) {
				// IE8 throws error when setting src attribute to non-ssl value. (#7847)
				if ( name == 'src' && value.match( /^http:\/\// ) )
					try {
					standard.apply( this, arguments );
				} catch ( e ) {} else
					standard.apply( this, arguments );
				return this;
			};
		} else
			return standard;
	})(),

	/**
	 * Sets the value of several element attributes.
	 *
	 *		var element = CKEDITOR.document.getById( 'myElement' );
	 *		element.setAttributes( {
	 *			'class':	'myClass',
	 *			title:		'This is an example'
	 *		} );
	 *
	 * @chainable
	 * @param {Object} attributesPairs An object containing the names and
	 * values of the attributes.
	 * @returns {CKEDITOR.dom.element} This element instance.
	 */
	setAttributes: function( attributesPairs ) {
		for ( var name in attributesPairs )
			this.setAttribute( name, attributesPairs[ name ] );
		return this;
	},

	/**
	 * Sets the element value. This function is usually used with form
	 * field element.
	 *
	 * @chainable
	 * @param {String} value The element value.
	 * @returns {CKEDITOR.dom.element} This element instance.
	 */
	setValue: function( value ) {
		this.$.value = value;
		return this;
	},

	/**
	 * Removes an attribute from the element.
	 *
	 *		var element = CKEDITOR.dom.element.createFromHtml( '<div class="classA"></div>' );
	 *		element.removeAttribute( 'class' );
	 *
	 * @method
	 * @param {String} name The attribute name.
	 */
	removeAttribute: (function() {
		var standard = function( name ) {
				this.$.removeAttribute( name );
			};

		if ( CKEDITOR.env.ie && ( CKEDITOR.env.ie7Compat || CKEDITOR.env.ie6Compat ) ) {
			return function( name ) {
				if ( name == 'class' )
					name = 'className';
				else if ( name == 'tabindex' )
					name = 'tabIndex';
				else if ( name == 'contenteditable' )
					name = 'contentEditable';
				standard.call( this, name );
			};
		} else
			return standard;
	})(),

	/**
	 * Removes all element's attributes or just given ones.
	 *
	 * @param {Array} [attributes] The array with attributes names.
	 */
	removeAttributes: function( attributes ) {
		if ( CKEDITOR.tools.isArray( attributes ) ) {
			for ( var i = 0; i < attributes.length; i++ )
				this.removeAttribute( attributes[ i ] );
		} else {
			for ( var attr in attributes )
				attributes.hasOwnProperty( attr ) && this.removeAttribute( attr );
		}
	},

	/**
	 * Removes a style from the element.
	 *
	 *		var element = CKEDITOR.dom.element.createFromHtml( '<div style="display:none"></div>' );
	 *		element.removeStyle( 'display' );
	 *
	 * @method
	 * @param {String} name The style name.
	 */
	removeStyle: function( name ) {
		// Removes the specified property from the current style object.
		var $ = this.$.style;

		// "removeProperty" need to be specific on the following styles.
		if ( !$.removeProperty && ( name == 'border' || name == 'margin' || name == 'padding' ) ) {
			var names = expandedRules( name );
			for ( var i = 0 ; i < names.length ; i++ )
				this.removeStyle( names[ i ] );
			return;
		}

		$.removeProperty ? $.removeProperty( name ) : $.removeAttribute( CKEDITOR.tools.cssStyleToDomStyle( name ) );

		// Eventually remove empty style attribute.
		if ( !this.$.style.cssText )
			this.removeAttribute( 'style' );
	},

	/**
	 * Sets the value of an element style.
	 *
	 *		var element = CKEDITOR.document.getById( 'myElement' );
	 *		element.setStyle( 'background-color', '#ff0000' );
	 *		element.setStyle( 'margin-top', '10px' );
	 *		element.setStyle( 'float', 'right' );
	 *
	 * @param {String} name The name of the style. The CSS naming notation
	 * must be used (e.g. `background-color`).
	 * @param {String} value The value to be set to the style.
	 * @returns {CKEDITOR.dom.element} This element instance.
	 */
	setStyle: function( name, value ) {
		this.$.style[ CKEDITOR.tools.cssStyleToDomStyle( name ) ] = value;
		return this;
	},

	/**
	 * Sets the value of several element styles.
	 *
	 *		var element = CKEDITOR.document.getById( 'myElement' );
	 *		element.setStyles( {
	 *			position:	'absolute',
	 *			float:		'right'
	 *		} );
	 *
	 * @param {Object} stylesPairs An object containing the names and
	 * values of the styles.
	 * @returns {CKEDITOR.dom.element} This element instance.
	 */
	setStyles: function( stylesPairs ) {
		for ( var name in stylesPairs )
			this.setStyle( name, stylesPairs[ name ] );
		return this;
	},

	/**
	 * Sets the opacity of an element.
	 *
	 *		var element = CKEDITOR.document.getById( 'myElement' );
	 *		element.setOpacity( 0.75 );
	 *
	 * @param {Number} opacity A number within the range `[0.0, 1.0]`.
	 */
	setOpacity: function( opacity ) {
		if ( CKEDITOR.env.ie && CKEDITOR.env.version < 9 ) {
			opacity = Math.round( opacity * 100 );
			this.setStyle( 'filter', opacity >= 100 ? '' : 'progid:DXImageTransform.Microsoft.Alpha(opacity=' + opacity + ')' );
		} else
			this.setStyle( 'opacity', opacity );
	},

	/**
	 * Makes the element and its children unselectable.
	 *
	 *		var element = CKEDITOR.document.getById( 'myElement' );
	 *		element.unselectable();
	 *
	 * @method
	 */
	unselectable: function() {
		// CSS unselectable.
		this.setStyles( CKEDITOR.tools.cssVendorPrefix( 'user-select', 'none' ) );

		// For IE/Opera which doesn't support for the above CSS style,
		// the unselectable="on" attribute only specifies the selection
		// process cannot start in the element itself, and it doesn't inherit.
		if ( CKEDITOR.env.ie || CKEDITOR.env.opera ) {
			this.setAttribute( 'unselectable', 'on' );

			var element,
				elements = this.getElementsByTag( "*" );

			for ( var i = 0, count = elements.count() ; i < count ; i++ ) {
				element = elements.getItem( i );
				element.setAttribute( 'unselectable', 'on' );
			}
		}
	},

	/**
	 * Gets closest positioned (`position != static`) ancestor.
	 *
	 * @returns {CKEDITOR.dom.element} Positioned ancestor or `null`.
	 */
	getPositionedAncestor: function() {
		var current = this;
		while ( current.getName() != 'html' ) {
			if ( current.getComputedStyle( 'position' ) != 'static' )
				return current;

			current = current.getParent();
		}
		return null;
	},

	/**
	 * Gets this element's position in document.
	 *
	 * @param {CKEDITOR.dom.document} [refDocument]
	 * @returns {Object} Element's position.
	 * @returns {Number} return.x
	 * @returns {Number} return.y
	 * @todo refDocument
	 */
	getDocumentPosition: function( refDocument ) {
		var x = 0,
			y = 0,
			doc = this.getDocument(),
			body = doc.getBody(),
			quirks = doc.$.compatMode == 'BackCompat';

		if ( document.documentElement[ "getBoundingClientRect" ] ) {
			var box = this.$.getBoundingClientRect(),
				$doc = doc.$,
				$docElem = $doc.documentElement;

			var clientTop = $docElem.clientTop || body.$.clientTop || 0,
				clientLeft = $docElem.clientLeft || body.$.clientLeft || 0,
				needAdjustScrollAndBorders = true;

			// #3804: getBoundingClientRect() works differently on IE and non-IE
			// browsers, regarding scroll positions.
			//
			// On IE, the top position of the <html> element is always 0, no matter
			// how much you scrolled down.
			//
			// On other browsers, the top position of the <html> element is negative
			// scrollTop.
			if ( CKEDITOR.env.ie ) {
				var inDocElem = doc.getDocumentElement().contains( this ),
					inBody = doc.getBody().contains( this );

				needAdjustScrollAndBorders = ( quirks && inBody ) || ( !quirks && inDocElem );
			}

			if ( needAdjustScrollAndBorders ) {
				x = box.left + ( !quirks && $docElem.scrollLeft || body.$.scrollLeft );
				x -= clientLeft;
				y = box.top + ( !quirks && $docElem.scrollTop || body.$.scrollTop );
				y -= clientTop;
			}
		} else {
			var current = this,
				previous = null,
				offsetParent;
			while ( current && !( current.getName() == 'body' || current.getName() == 'html' ) ) {
				x += current.$.offsetLeft - current.$.scrollLeft;
				y += current.$.offsetTop - current.$.scrollTop;

				// Opera includes clientTop|Left into offsetTop|Left.
				if ( !current.equals( this ) ) {
					x += ( current.$.clientLeft || 0 );
					y += ( current.$.clientTop || 0 );
				}

				var scrollElement = previous;
				while ( scrollElement && !scrollElement.equals( current ) ) {
					x -= scrollElement.$.scrollLeft;
					y -= scrollElement.$.scrollTop;
					scrollElement = scrollElement.getParent();
				}

				previous = current;
				current = ( offsetParent = current.$.offsetParent ) ? new CKEDITOR.dom.element( offsetParent ) : null;
			}
		}

		if ( refDocument ) {
			var currentWindow = this.getWindow(),
				refWindow = refDocument.getWindow();

			if ( !currentWindow.equals( refWindow ) && currentWindow.$.frameElement ) {
				var iframePosition = ( new CKEDITOR.dom.element( currentWindow.$.frameElement ) ).getDocumentPosition( refDocument );

				x += iframePosition.x;
				y += iframePosition.y;
			}
		}

		if ( !document.documentElement[ "getBoundingClientRect" ] ) {
			// In Firefox, we'll endup one pixel before the element positions,
			// so we must add it here.
			if ( CKEDITOR.env.gecko && !quirks ) {
				x += this.$.clientLeft ? 1 : 0;
				y += this.$.clientTop ? 1 : 0;
			}
		}

		return { x: x, y: y };
	},

	/**
	 * Make any page element visible inside the browser viewport.
	 *
	 * @param {Boolean} [alignToTop=false]
	 */
	scrollIntoView: function( alignToTop ) {
		var parent = this.getParent();
		if ( !parent )
			return;

		// Scroll the element into parent container from the inner out.
		do {
			// Check ancestors that overflows.
			var overflowed =
				parent.$.clientWidth && parent.$.clientWidth < parent.$.scrollWidth ||
				parent.$.clientHeight && parent.$.clientHeight < parent.$.scrollHeight;

			// Skip body element, which will report wrong clientHeight when containing
			// floated content. (#9523)
			if ( overflowed && !parent.is( 'body' ) )
				this.scrollIntoParent( parent, alignToTop, 1 );

			// Walk across the frame.
			if ( parent.is( 'html' ) ) {
				var win = parent.getWindow();

				// Avoid security error.
				try {
					var iframe = win.$.frameElement;
					iframe && ( parent = new CKEDITOR.dom.element( iframe ) );
				} catch ( er ) {}
			}
		}
		while ( ( parent = parent.getParent() ) );
	},

	/**
	 * Make any page element visible inside one of the ancestors by scrolling the parent.
	 *
	 * @param {CKEDITOR.dom.element/CKEDITOR.dom.window} parent The container to scroll into.
	 * @param {Boolean} [alignToTop] Align the element's top side with the container's
	 * when `true` is specified; align the bottom with viewport bottom when
	 * `false` is specified. Otherwise scroll on either side with the minimum
	 * amount to show the element.
	 * @param {Boolean} [hscroll] Whether horizontal overflow should be considered.
	 */
	scrollIntoParent: function( parent, alignToTop, hscroll ) {
		!parent && ( parent = this.getWindow() );

		var doc = parent.getDocument();
		var isQuirks = doc.$.compatMode == 'BackCompat';

		// On window <html> is scrolled while quirks scrolls <body>.
		if ( parent instanceof CKEDITOR.dom.window )
			parent = isQuirks ? doc.getBody() : doc.getDocumentElement();

		// Scroll the parent by the specified amount.
		function scrollBy( x, y ) {
			// Webkit doesn't support "scrollTop/scrollLeft"
			// on documentElement/body element.
			if ( /body|html/.test( parent.getName() ) )
				parent.getWindow().$.scrollBy( x, y );
			else {
				parent.$[ 'scrollLeft' ] += x;
				parent.$[ 'scrollTop' ] += y;
			}
		}

		// Figure out the element position relative to the specified window.
		function screenPos( element, refWin ) {
			var pos = { x: 0, y: 0 };

			if ( !( element.is( isQuirks ? 'body' : 'html' ) ) ) {
				var box = element.$.getBoundingClientRect();
				pos.x = box.left, pos.y = box.top;
			}

			var win = element.getWindow();
			if ( !win.equals( refWin ) ) {
				var outerPos = screenPos( CKEDITOR.dom.element.get( win.$.frameElement ), refWin );
				pos.x += outerPos.x, pos.y += outerPos.y;
			}

			return pos;
		}

		// calculated margin size.
		function margin( element, side ) {
			return parseInt( element.getComputedStyle( 'margin-' + side ) || 0, 10 ) || 0;
		}

		var win = parent.getWindow();

		var thisPos = screenPos( this, win ),
			parentPos = screenPos( parent, win ),
			eh = this.$.offsetHeight,
			ew = this.$.offsetWidth,
			ch = parent.$.clientHeight,
			cw = parent.$.clientWidth,
			lt, br;

		// Left-top margins.
		lt = {
			x: thisPos.x - margin( this, 'left' ) - parentPos.x || 0,
			y: thisPos.y - margin( this, 'top' ) - parentPos.y || 0
		};

		// Bottom-right margins.
		br = {
			x: thisPos.x + ew + margin( this, 'right' ) - ( ( parentPos.x ) + cw ) || 0,
			y: thisPos.y + eh + margin( this, 'bottom' ) - ( ( parentPos.y ) + ch ) || 0
		};

		// 1. Do the specified alignment as much as possible;
		// 2. Otherwise be smart to scroll only the minimum amount;
		// 3. Never cut at the top;
		// 4. DO NOT scroll when already visible.
		if ( lt.y < 0 || br.y > 0 ) {
			scrollBy( 0, alignToTop === true ? lt.y : alignToTop === false ? br.y : lt.y < 0 ? lt.y : br.y );
		}

		if ( hscroll && ( lt.x < 0 || br.x > 0 ) )
			scrollBy( lt.x < 0 ? lt.x : br.x, 0 );
	},

	/**
	 * Switch the `class` attribute to reflect one of the triple states of an
	 * element in one of {@link CKEDITOR#TRISTATE_ON}, {@link CKEDITOR#TRISTATE_OFF}
	 * or {@link CKEDITOR#TRISTATE_DISABLED}.
	 *
	 *		link.setState( CKEDITOR.TRISTATE_ON );
	 *		// <a class="cke_on" aria-pressed="true">...</a>
	 *		link.setState( CKEDITOR.TRISTATE_OFF );
	 *		// <a class="cke_off">...</a>
	 *		link.setState( CKEDITOR.TRISTATE_DISABLED );
	 *		// <a class="cke_disabled" aria-disabled="true">...</a>
	 *
	 *		span.setState( CKEDITOR.TRISTATE_ON, 'cke_button' );
	 *		// <span class="cke_button_on">...</span>
	 *
	 * @param {Number} state Indicate the element state. One of {@link CKEDITOR#TRISTATE_ON},
	 * {@link CKEDITOR#TRISTATE_OFF}, {@link CKEDITOR#TRISTATE_DISABLED}.
	 * @param [base='cke'] The prefix apply to each of the state class name.
	 * @param [useAria=true] Whether toggle the ARIA state attributes besides of class name change.
	 */
	setState: function( state, base, useAria ) {
		base = base || 'cke';

		switch ( state ) {
			case CKEDITOR.TRISTATE_ON:
				this.addClass( base + '_on' );
				this.removeClass( base + '_off' );
				this.removeClass( base + '_disabled' );
				useAria && this.setAttribute( 'aria-pressed', true );
				useAria && this.removeAttribute( 'aria-disabled' );
				break;

			case CKEDITOR.TRISTATE_DISABLED:
				this.addClass( base + '_disabled' );
				this.removeClass( base + '_off' );
				this.removeClass( base + '_on' );
				useAria && this.setAttribute( 'aria-disabled', true );
				useAria && this.removeAttribute( 'aria-pressed' );
				break;

			default:
				this.addClass( base + '_off' );
				this.removeClass( base + '_on' );
				this.removeClass( base + '_disabled' );
				useAria && this.removeAttribute( 'aria-pressed' );
				useAria && this.removeAttribute( 'aria-disabled' );
				break;
		}
	},

	/**
	 * Returns the inner document of this `<iframe>` element.
	 *
	 * @returns {CKEDITOR.dom.document} The inner document.
	 */
	getFrameDocument: function() {
		var $ = this.$;

		try {
			// In IE, with custom document.domain, it may happen that
			// the iframe is not yet available, resulting in "Access
			// Denied" for the following property access.
			$.contentWindow.document;
		} catch ( e ) {
			// Trick to solve this issue, forcing the iframe to get ready
			// by simply setting its "src" property.
			$.src = $.src;
		}

		return $ && new CKEDITOR.dom.document( $.contentWindow.document );
	},

	/**
	 * Copy all the attributes from one node to the other, kinda like a clone
	 * skipAttributes is an object with the attributes that must **not** be copied.
	 *
	 * @param {CKEDITOR.dom.element} dest The destination element.
	 * @param {Object} skipAttributes A dictionary of attributes to skip.
	 */
	copyAttributes: function( dest, skipAttributes ) {
		var attributes = this.$.attributes;
		skipAttributes = skipAttributes || {};

		for ( var n = 0; n < attributes.length; n++ ) {
			var attribute = attributes[ n ];

			// Lowercase attribute name hard rule is broken for
			// some attribute on IE, e.g. CHECKED.
			var attrName = attribute.nodeName.toLowerCase(),
				attrValue;

			// We can set the type only once, so do it with the proper value, not copying it.
			if ( attrName in skipAttributes )
				continue;

			if ( attrName == 'checked' && ( attrValue = this.getAttribute( attrName ) ) )
				dest.setAttribute( attrName, attrValue );
			// IE BUG: value attribute is never specified even if it exists.
			else if ( attribute.specified || ( CKEDITOR.env.ie && attribute.nodeValue && attrName == 'value' ) ) {
				attrValue = this.getAttribute( attrName );
				if ( attrValue === null )
					attrValue = attribute.nodeValue;

				dest.setAttribute( attrName, attrValue );
			}
		}

		// The style:
		if ( this.$.style.cssText !== '' )
			dest.$.style.cssText = this.$.style.cssText;
	},

	/**
	 * Changes the tag name of the current element.
	 *
	 * @param {String} newTag The new tag for the element.
	 */
	renameNode: function( newTag ) {
		// If it's already correct exit here.
		if ( this.getName() == newTag )
			return;

		var doc = this.getDocument();

		// Create the new node.
		var newNode = new CKEDITOR.dom.element( newTag, doc );

		// Copy all attributes.
		this.copyAttributes( newNode );

		// Move children to the new node.
		this.moveChildren( newNode );

		// Replace the node.
		this.getParent() && this.$.parentNode.replaceChild( newNode.$, this.$ );
		newNode.$[ 'data-cke-expando' ] = this.$[ 'data-cke-expando' ];
		this.$ = newNode.$;
	},

	/**
	 * Gets a DOM tree descendant under the current node.
	 *
	 *		var strong = p.getChild( 0 );
	 *
	 * @method
	 * @param {Array/Number} indices The child index or array of child indices under the node.
	 * @returns {CKEDITOR.dom.node} The specified DOM child under the current node. Null if child does not exist.
	 */
	getChild: (function() {
		function getChild( rawNode, index ) {
			var childNodes = rawNode.childNodes;

			if ( index >= 0 && index < childNodes.length )
				return childNodes[ index ];
		}

		return function( indices ) {
			var rawNode = this.$;

			if ( !indices.slice )
				rawNode = getChild( rawNode, indices );
			else {
				while ( indices.length > 0 && rawNode )
					rawNode = getChild( rawNode, indices.shift() );
			}

			return rawNode ? new CKEDITOR.dom.node( rawNode ) : null;
		};
	})(),

	/**
	 * Gets number of element's children.
	 *
	 * @returns {Number}
	 */
	getChildCount: function() {
		return this.$.childNodes.length;
	},

	/**
	 * Disables browser's context menu in this element.
	 */
	disableContextMenu: function() {
		this.on( 'contextmenu', function( event ) {
			// Cancel the browser context menu.
			if ( !event.data.getTarget().hasClass( 'cke_enable_context_menu' ) )
				event.data.preventDefault();
		});
	},

	/**
	 * Gets element's direction. Supports both CSS `direction` prop and `dir` attr.
	 */
	getDirection: function( useComputed ) {
		if ( useComputed ) {
			return this.getComputedStyle( 'direction' ) ||
					this.getDirection() ||
					this.getParent() && this.getParent().getDirection( 1 ) ||
					this.getDocument().$.dir ||
					'ltr';
		}
		else
			return this.getStyle( 'direction' ) || this.getAttribute( 'dir' );
	},

	/**
	 * Gets, sets and removes custom data to be stored as HTML5 data-* attributes.
	 *
	 *		element.data( 'extra-info', 'test' );	// Appended the attribute data-extra-info="test" to the element.
	 *		alert( element.data( 'extra-info' ) );	// 'test'
	 *		element.data( 'extra-info', false );	// Remove the data-extra-info attribute from the element.
	 *
	 * @param {String} name The name of the attribute, excluding the `data-` part.
	 * @param {String} [value] The value to set. If set to false, the attribute will be removed.
	 */
	data: function( name, value ) {
		name = 'data-' + name;
		if ( value === undefined )
			return this.getAttribute( name );
		else if ( value === false )
			this.removeAttribute( name );
		else
			this.setAttribute( name, value );

		return null;
	},

	/**
	 * Retrieves an editor instance which is based on this element (if any).
	 * It basically loops over {@link CKEDITOR#instances} in search for an instance
	 * that uses the element.
	 *
	 *		var element = new CKEDITOR.dom.element( 'div' );
	 *		element.appendTo( CKEDITOR.document.getBody() );
	 *		CKEDITOR.replace( element );
	 *		alert( element.getEditor().name ); // 'editor1'
	 *
	 * @returns {CKEDITOR.editor} An editor instance or null if nothing has been found.
	 */
	getEditor: function() {
		var instances = CKEDITOR.instances,
			name, instance;

		for ( name in instances ) {
			instance = instances[ name ];

			if ( instance.element.equals( this ) && instance.elementMode != CKEDITOR.ELEMENT_MODE_APPENDTO )
				return instance;
		}

		return null;
	},

	/**
	 * Returns list of elements within this element that match specified `selector`.
	 *
	 * **Notes:**
	 *
	 *	* Not available in IE7.
	 *	* Returned list is not a live collection (like a result of native `querySelectorAll`).
	 *	* Unlike native `querySelectorAll` this method ensures selector contextualization. This is:
	 *
	 *			HTML:		'<body><div><i>foo</i></div></body>'
	 *			Native:		div.querySelectorAll( 'body i' ) // ->		[ <i>foo</i> ]
	 *			Method:		div.find( 'body i' ) // ->					[]
	 *						div.find( 'i' ) // ->						[ <i>foo</i> ]
	 *
	 * @since 4.3
	 * @param {String} selector
	 * @returns {CKEDITOR.dom.nodeList}
	 */
	find: function( selector ) {
		var removeTmpId = createTmpId( this ),
			list = new CKEDITOR.dom.nodeList(
				this.$.querySelectorAll( getContextualizedSelector( this, selector ) )
			);

		removeTmpId();

		return list;
	},

	/**
	 * Returns first element within this element that matches specified `selector`.
	 *
	 * **Notes:**
	 *
	 *	* Not available in IE7.
	 *	* Unlike native `querySelectorAll` this method ensures selector contextualization. This is:
	 *
	 *			HTML:		'<body><div><i>foo</i></div></body>'
	 *			Native:		div.querySelector( 'body i' ) // ->			<i>foo</i>
	 *			Method:		div.findOne( 'body i' ) // ->				null
	 *						div.findOne( 'i' ) // ->					<i>foo</i>
	 *
	 * @since 4.3
	 * @param {String} selector
	 * @returns {CKEDITOR.dom.element}
	 */
	findOne: function( selector ) {
		var removeTmpId = createTmpId( this ),
			found = this.$.querySelector( getContextualizedSelector( this, selector ) );

		removeTmpId();

		return found ? new CKEDITOR.dom.element( found ) : null;
	}
});

	function createTmpId( element ) {
		var hadId = true;

		if ( !element.$.id ) {
			element.$.id = 'cke_tmp_' + CKEDITOR.tools.getNextNumber();
			hadId = false;
		}

		return function() {
			if ( !hadId )
				element.removeAttribute( 'id' );
		};
	}

	function getContextualizedSelector( element, selector ) {
		return '#' + element.$.id + ' ' + selector.split( /,\s*/ ).join( ', #' + element.$.id + ' ' );
	}

	var sides = {
		width: [ 'border-left-width', 'border-right-width', 'padding-left', 'padding-right' ],
		height: [ 'border-top-width', 'border-bottom-width', 'padding-top', 'padding-bottom' ]
	};

	// Generate list of specific style rules, applicable to margin/padding/border.
	function expandedRules( style ) {
		var sides = [ 'top', 'left', 'right', 'bottom' ], components;

		if ( style == 'border' )
				components = [ 'color', 'style', 'width' ];

		var styles = [];
		for ( var i = 0 ; i < sides.length ; i++ ) {

			if ( components ) {
				for ( var j = 0 ; j < components.length ; j++ )
					styles.push( [ style, sides[ i ], components[j] ].join( '-' ) );
			}
			else
				styles.push( [ style, sides[ i ] ].join( '-' ) );
		}

		return styles;
	}

	function marginAndPaddingSize( type ) {
		var adjustment = 0;
		for ( var i = 0, len = sides[ type ].length; i < len; i++ )
			adjustment += parseInt( this.getComputedStyle( sides[ type ][ i ] ) || 0, 10 ) || 0;
		return adjustment;
	}

	/**
	 * Sets the element size considering the box model.
	 *
	 * @param {'width'/'height'} type The dimension to set.
	 * @param {Number} size The length unit in px.
	 * @param {Boolean} isBorderBox Apply the size based on the border box model.
	 */
	CKEDITOR.dom.element.prototype.setSize = function( type, size, isBorderBox ) {
		if ( typeof size == 'number' ) {
			if ( isBorderBox && !( CKEDITOR.env.ie && CKEDITOR.env.quirks ) )
				size -= marginAndPaddingSize.call( this, type );

			this.setStyle( type, size + 'px' );
		}
	};

	/**
	 * Gets the element size, possibly considering the box model.
	 *
	 * @param {'width'/'height'} type The dimension to get.
	 * @param {Boolean} isBorderBox Get the size based on the border box model.
	 */
	CKEDITOR.dom.element.prototype.getSize = function( type, isBorderBox ) {
		var size = Math.max( this.$[ 'offset' + CKEDITOR.tools.capitalize( type ) ], this.$[ 'client' + CKEDITOR.tools.capitalize( type ) ] ) || 0;

		if ( isBorderBox )
			size -= marginAndPaddingSize.call( this, type );

		return size;
	};
})();
