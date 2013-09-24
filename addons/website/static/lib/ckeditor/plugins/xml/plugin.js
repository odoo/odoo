/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the {@link CKEDITOR.xml} class, which represents a
 *		loaded XML document.
 */

(function() {
	CKEDITOR.plugins.add( 'xml', {} );

	/**
	 * Represents a loaded XML document.
	 *
	 *		var xml = new CKEDITOR.xml( '<books><book title="My Book" /></books>' );
	 *
	 * @class
	 * @constructor Creates xml class instance.
	 * @param {Object/String} xmlObjectOrData A native XML (DOM document) object or
	 * a string containing the XML definition to be loaded.
	 */
	CKEDITOR.xml = function( xmlObjectOrData ) {
		var baseXml = null;

		if ( typeof xmlObjectOrData == 'object' )
			baseXml = xmlObjectOrData;
		else {
			var data = ( xmlObjectOrData || '' ).replace( /&nbsp;/g, '\xA0' );
			if ( window.DOMParser )
				baseXml = ( new DOMParser() ).parseFromString( data, 'text/xml' );
			else if ( window.ActiveXObject ) {
				try {
					baseXml = new ActiveXObject( 'MSXML2.DOMDocument' );
				} catch ( e ) {
					try {
						baseXml = new ActiveXObject( 'Microsoft.XmlDom' );
					} catch ( e ) {}
				}

				if ( baseXml ) {
					baseXml.async = false;
					baseXml.resolveExternals = false;
					baseXml.validateOnParse = false;
					baseXml.loadXML( data );
				}
			}
		}

		/**
		 * The native XML (DOM document) used by the class instance.
		 */
		this.baseXml = baseXml;
	};

	CKEDITOR.xml.prototype = {
		/**
		 * Get a single node from the XML document, based on a XPath query.
		 *
		 *		// Create the XML instance.
		 *		var xml = new CKEDITOR.xml( '<list><item id="test1" /><item id="test2" /></list>' );
		 *		// Get the first <item> node.
		 *		var itemNode = <b>xml.selectSingleNode( 'list/item' )</b>;
		 *		// Alert "item".
		 *		alert( itemNode.nodeName );
		 *
		 * @param {String} xpath The XPath query to execute.
		 * @param {Object} [contextNode] The XML DOM node to be used as the context
		 * for the XPath query. The document root is used by default.
		 * @returns {Object} A XML node element or null if the query has no results.
		 */
		selectSingleNode: function( xpath, contextNode ) {
			var baseXml = this.baseXml;

			if ( contextNode || ( contextNode = baseXml ) ) {
				if ( CKEDITOR.env.ie || contextNode.selectSingleNode ) // IE
				return contextNode.selectSingleNode( xpath );
				else if ( baseXml.evaluate ) // Others
				{
					var result = baseXml.evaluate( xpath, contextNode, null, 9, null );
					return ( result && result.singleNodeValue ) || null;
				}
			}

			return null;
		},

		/**
		 * Gets a list node from the XML document, based on a XPath query.
		 *
		 *		// Create the XML instance.
		 *		var xml = new CKEDITOR.xml( '<list><item id="test1" /><item id="test2" /></list>' );
		 *		// Get the first <item> node.
		 *		var itemNodes = xml.selectSingleNode( 'list/item' );
		 *		// Alert "item" twice, one for each <item>.
		 *		for ( var i = 0 ; i < itemNodes.length ; i++ )
		 *			alert( itemNodes[i].nodeName );
		 *
		 * @param {String} xpath The XPath query to execute.
		 * @param {Object} [contextNode] The XML DOM node to be used as the context
		 * for the XPath query. The document root is used by default.
		 * @returns {Array} An array containing all matched nodes. The array will
		 * be empty if the query has no results.
		 */
		selectNodes: function( xpath, contextNode ) {
			var baseXml = this.baseXml,
				nodes = [];

			if ( contextNode || ( contextNode = baseXml ) ) {
				if ( CKEDITOR.env.ie || contextNode.selectNodes ) // IE
				return contextNode.selectNodes( xpath );
				else if ( baseXml.evaluate ) // Others
				{
					var result = baseXml.evaluate( xpath, contextNode, null, 5, null );

					if ( result ) {
						var node;
						while ( ( node = result.iterateNext() ) )
							nodes.push( node );
					}
				}
			}

			return nodes;
		},

		/**
		 * Gets the string representation of hte inner contents of a XML node,
		 * based on a XPath query.
		 *
		 *		// Create the XML instance.
		 *		var xml = new CKEDITOR.xml( '<list><item id="test1" /><item id="test2" /></list>' );
		 *		// Alert "<item id="test1" /><item id="test2" />".
		 *		alert( xml.getInnerXml( 'list' ) );
		 *
		 * @param {String} xpath The XPath query to execute.
		 * @param {Object} [contextNode] The XML DOM node to be used as the context
		 * for the XPath query. The document root is used by default.
		 * @returns {String} The textual representation of the inner contents of
		 * the node or null if the query has no results.
		 */
		getInnerXml: function( xpath, contextNode ) {
			var node = this.selectSingleNode( xpath, contextNode ),
				xml = [];
			if ( node ) {
				node = node.firstChild;
				while ( node ) {
					if ( node.xml ) // IE
					xml.push( node.xml );
					else if ( window.XMLSerializer ) // Others
					xml.push( ( new XMLSerializer() ).serializeToString( node ) );

					node = node.nextSibling;
				}
			}

			return xml.length ? xml.join( '' ) : null;
		}
	};
})();
