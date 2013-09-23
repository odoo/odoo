/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

(function() {
	CKEDITOR.on( 'dialogDefinition', function( ev ) {
		var tab,
			name = ev.data.name,
			definition = ev.data.definition;

		if ( name == 'link' ) {
			definition.removeContents( 'target' );
			definition.removeContents( 'upload' );
			definition.removeContents( 'advanced' );
			tab = definition.getContents( 'info' );
			tab.remove( 'emailSubject' );
			tab.remove( 'emailBody' );
		} else if ( name == 'image' ) {
			definition.removeContents( 'advanced' );
			tab = definition.getContents( 'Link' );
			tab.remove( 'cmbTarget' );
			tab = definition.getContents( 'info' );
			tab.remove( 'txtAlt' );
			tab.remove( 'basic' );
		}
	});

	var bbcodeMap = { b: 'strong', u: 'u', i: 'em', color: 'span', size: 'span', quote: 'blockquote', code: 'code', url: 'a', email: 'span', img: 'span', '*': 'li', list: 'ol' },
		convertMap = { strong: 'b', b: 'b', u: 'u', em: 'i', i: 'i', code: 'code', li: '*' },
		tagnameMap = { strong: 'b', em: 'i', u: 'u', li: '*', ul: 'list', ol: 'list', code: 'code', a: 'link', img: 'img', blockquote: 'quote' },
		stylesMap = { color: 'color', size: 'font-size' },
		attributesMap = { url: 'href', email: 'mailhref', quote: 'cite', list: 'listType' };

	// List of block-like tags.
	var dtd = CKEDITOR.dtd,
		blockLikeTags = CKEDITOR.tools.extend( { table:1 }, dtd.$block, dtd.$listItem, dtd.$tableContent, dtd.$list );

	var semicolonFixRegex = /\s*(?:;\s*|$)/;

	function serializeStyleText( stylesObject ) {
		var styleText = '';
		for ( var style in stylesObject ) {
			var styleVal = stylesObject[ style ],
				text = ( style + ':' + styleVal ).replace( semicolonFixRegex, ';' );

			styleText += text;
		}
		return styleText;
	}

	// Maintain the map of smiley-to-description.
	var smileyMap = { smiley: ':)', sad: ':(', wink: ';)', laugh: ':D', cheeky: ':P', blush: ':*)', surprise: ':-o', indecision: ':|', angry: '>:(', angel: 'o:)', cool: '8-)', devil: '>:-)', crying: ';(', kiss: ':-*' },
		smileyReverseMap = {},
		smileyRegExp = [];

	// Build regexp for the list of smiley text.
	for ( var i in smileyMap ) {
		smileyReverseMap[ smileyMap[ i ] ] = i;
		smileyRegExp.push( smileyMap[ i ].replace( /\(|\)|\:|\/|\*|\-|\|/g, function( match ) {
			return '\\' + match;
		}));
	}

	smileyRegExp = new RegExp( smileyRegExp.join( '|' ), 'g' );

	var decodeHtml = (function() {
		var regex = [],
			entities = {
				nbsp: '\u00A0', // IE | FF
				shy: '\u00AD', // IE
				gt: '\u003E', // IE | FF |   --   | Opera
				lt: '\u003C' // IE | FF | Safari | Opera
			};

		for ( var entity in entities )
			regex.push( entity );

		regex = new RegExp( '&(' + regex.join( '|' ) + ');', 'g' );

		return function( html ) {
			return html.replace( regex, function( match, entity ) {
				return entities[ entity ];
			});
		};
	})();

	CKEDITOR.BBCodeParser = function() {
		this._ = {
			bbcPartsRegex: /(?:\[([^\/\]=]*?)(?:=([^\]]*?))?\])|(?:\[\/([a-z]{1,16})\])/ig
		};
	};

	CKEDITOR.BBCodeParser.prototype = {
		parse: function( bbcode ) {
			var parts, part,
				lastIndex = 0;

			while ( ( parts = this._.bbcPartsRegex.exec( bbcode ) ) ) {
				var tagIndex = parts.index;
				if ( tagIndex > lastIndex ) {
					var text = bbcode.substring( lastIndex, tagIndex );
					this.onText( text, 1 );
				}

				lastIndex = this._.bbcPartsRegex.lastIndex;

				// "parts" is an array with the following items:
				// 0 : The entire match for opening/closing tags and line-break;
				// 1 : line-break;
				// 2 : open of tag excludes option;
				// 3 : tag option;
				// 4 : close of tag;

				part = ( parts[ 1 ] || parts[ 3 ] || '' ).toLowerCase();
				// Unrecognized tags should be delivered as a simple text (#7860).
				if ( part && !bbcodeMap[ part ] ) {
					this.onText( parts[ 0 ] );
					continue;
				}

				// Opening tag
				if ( parts[ 1 ] ) {
					var tagName = bbcodeMap[ part ],
						attribs = {},
						styles = {},
						optionPart = parts[ 2 ];

					if ( optionPart ) {
						if ( part == 'list' ) {
							if ( !isNaN( optionPart ) )
								optionPart = 'decimal';
							else if ( /^[a-z]+$/.test( optionPart ) )
								optionPart = 'lower-alpha';
							else if ( /^[A-Z]+$/.test( optionPart ) )
								optionPart = 'upper-alpha';
						}

						if ( stylesMap[ part ] ) {
							// Font size represents percentage.
							if ( part == 'size' )
								optionPart += '%';

							styles[ stylesMap[ part ] ] = optionPart;
							attribs.style = serializeStyleText( styles );
						} else if ( attributesMap[ part ] )
							attribs[ attributesMap[ part ] ] = optionPart;
					}

					// Two special handling - image and email, protect them
					// as "span" with an attribute marker.
					if ( part == 'email' || part == 'img' )
						attribs[ 'bbcode' ] = part;

					this.onTagOpen( tagName, attribs, CKEDITOR.dtd.$empty[ tagName ] );
				}
				// Closing tag
				else if ( parts[ 3 ] )
					this.onTagClose( bbcodeMap[ part ] );
			}

			if ( bbcode.length > lastIndex )
				this.onText( bbcode.substring( lastIndex, bbcode.length ), 1 );
		}
	};

	/**
	 * Creates a {@link CKEDITOR.htmlParser.fragment} from an HTML string.
	 *
	 *		var fragment = CKEDITOR.htmlParser.fragment.fromHtml( '<b>Sample</b> Text' );
	 *		alert( fragment.children[ 0 ].name );		// 'b'
	 *		alert( fragment.children[ 1 ].value );	// ' Text'
	 *
	 * @static
	 * @member CKEDITOR.htmlParser.fragment
	 * @param {String} source The HTML to be parsed, filling the fragment.
	 * @returns {CKEDITOR.htmlParser.fragment} The fragment created.
	 */
	CKEDITOR.htmlParser.fragment.fromBBCode = function( source ) {
		var parser = new CKEDITOR.BBCodeParser(),
			fragment = new CKEDITOR.htmlParser.fragment(),
			pendingInline = [],
			pendingBrs = 0,
			currentNode = fragment,
			returnPoint;

		function checkPending( newTagName ) {
			if ( pendingInline.length > 0 ) {
				for ( var i = 0; i < pendingInline.length; i++ ) {
					var pendingElement = pendingInline[ i ],
						pendingName = pendingElement.name,
						pendingDtd = CKEDITOR.dtd[ pendingName ],
						currentDtd = currentNode.name && CKEDITOR.dtd[ currentNode.name ];

					if ( ( !currentDtd || currentDtd[ pendingName ] ) && ( !newTagName || !pendingDtd || pendingDtd[ newTagName ] || !CKEDITOR.dtd[ newTagName ] ) ) {
						// Get a clone for the pending element.
						pendingElement = pendingElement.clone();

						// Add it to the current node and make it the current,
						// so the new element will be added inside of it.
						pendingElement.parent = currentNode;
						currentNode = pendingElement;

						// Remove the pending element (back the index by one
						// to properly process the next entry).
						pendingInline.splice( i, 1 );
						i--;
					}
				}
			}
		}

		function checkPendingBrs( tagName, closing ) {
			var len = currentNode.children.length,
				previous = len > 0 && currentNode.children[ len - 1 ],
				lineBreakParent = !previous && writer.getRule( tagnameMap[ currentNode.name ], 'breakAfterOpen' ),
				lineBreakPrevious = previous && previous.type == CKEDITOR.NODE_ELEMENT && writer.getRule( tagnameMap[ previous.name ], 'breakAfterClose' ),
				lineBreakCurrent = tagName && writer.getRule( tagnameMap[ tagName ], closing ? 'breakBeforeClose' : 'breakBeforeOpen' );

			if ( pendingBrs && ( lineBreakParent || lineBreakPrevious || lineBreakCurrent ) )
				pendingBrs--;

			// 1. Either we're at the end of block, where it requires us to compensate the br filler
			// removing logic (from htmldataprocessor).
			// 2. Or we're at the end of pseudo block, where it requires us to compensate
			// the bogus br effect.
			if ( pendingBrs && tagName in blockLikeTags )
				pendingBrs++;

			while ( pendingBrs && pendingBrs-- )
				currentNode.children.push( previous = new CKEDITOR.htmlParser.element( 'br' ) );
		}

		function addElement( node, target ) {
			checkPendingBrs( node.name, 1 );

			target = target || currentNode || fragment;

			var len = target.children.length,
				previous = len > 0 && target.children[ len - 1 ] || null;

			node.previous = previous;
			node.parent = target;

			target.children.push( node );

			if ( node.returnPoint ) {
				currentNode = node.returnPoint;
				delete node.returnPoint;
			}
		}

		parser.onTagOpen = function( tagName, attributes, selfClosing ) {
			var element = new CKEDITOR.htmlParser.element( tagName, attributes );

			// This is a tag to be removed if empty, so do not add it immediately.
			if ( CKEDITOR.dtd.$removeEmpty[ tagName ] ) {
				pendingInline.push( element );
				return;
			}

			var currentName = currentNode.name;

			var currentDtd = currentName && ( CKEDITOR.dtd[ currentName ] || ( currentNode._.isBlockLike ? CKEDITOR.dtd.div : CKEDITOR.dtd.span ) );

			// If the element cannot be child of the current element.
			if ( currentDtd && !currentDtd[ tagName ] ) {
				var reApply = false,
					addPoint; // New position to start adding nodes.

				// If the element name is the same as the current element name,
				// then just close the current one and append the new one to the
				// parent. This situation usually happens with <p>, <li>, <dt> and
				// <dd>, specially in IE. Do not enter in this if block in this case.
				if ( tagName == currentName )
					addElement( currentNode, currentNode.parent );
				else if ( tagName in CKEDITOR.dtd.$listItem ) {
					parser.onTagOpen( 'ul', {} );
					addPoint = currentNode;
					reApply = true;
				} else {
					addElement( currentNode, currentNode.parent );

					// The current element is an inline element, which
					// cannot hold the new one. Put it in the pending list,
					// and try adding the new one after it.
					pendingInline.unshift( currentNode );
					reApply = true;
				}

				if ( addPoint )
					currentNode = addPoint;
				// Try adding it to the return point, or the parent element.
				else
					currentNode = currentNode.returnPoint || currentNode.parent;

				if ( reApply ) {
					parser.onTagOpen.apply( this, arguments );
					return;
				}
			}

			checkPending( tagName );
			checkPendingBrs( tagName );

			element.parent = currentNode;
			element.returnPoint = returnPoint;
			returnPoint = 0;

			if ( element.isEmpty )
				addElement( element );
			else
				currentNode = element;
		};

		parser.onTagClose = function( tagName ) {
			// Check if there is any pending tag to be closed.
			for ( var i = pendingInline.length - 1; i >= 0; i-- ) {
				// If found, just remove it from the list.
				if ( tagName == pendingInline[ i ].name ) {
					pendingInline.splice( i, 1 );
					return;
				}
			}

			var pendingAdd = [],
				newPendingInline = [],
				candidate = currentNode;

			while ( candidate.type && candidate.name != tagName ) {
				// If this is an inline element, add it to the pending list, if we're
				// really closing one of the parents element later, they will continue
				// after it.
				if ( !candidate._.isBlockLike )
					newPendingInline.unshift( candidate );

				// This node should be added to it's parent at this point. But,
				// it should happen only if the closing tag is really closing
				// one of the nodes. So, for now, we just cache it.
				pendingAdd.push( candidate );

				candidate = candidate.parent;
			}

			if ( candidate.type ) {
				// Add all elements that have been found in the above loop.
				for ( i = 0; i < pendingAdd.length; i++ ) {
					var node = pendingAdd[ i ];
					addElement( node, node.parent );
				}

				currentNode = candidate;


				addElement( candidate, candidate.parent );

				// The parent should start receiving new nodes now, except if
				// addElement changed the currentNode.
				if ( candidate == currentNode )
					currentNode = currentNode.parent;

				pendingInline = pendingInline.concat( newPendingInline );
			}
		};

		parser.onText = function( text ) {
			var currentDtd = CKEDITOR.dtd[ currentNode.name ];
			if ( !currentDtd || currentDtd[ '#' ] ) {
				checkPendingBrs();
				checkPending();

				text.replace( /(\r\n|[\r\n])|[^\r\n]*/g, function( piece, lineBreak ) {
					if ( lineBreak !== undefined && lineBreak.length )
						pendingBrs++;
					else if ( piece.length ) {
						var lastIndex = 0;

						// Create smiley from text emotion.
						piece.replace( smileyRegExp, function( match, index ) {
							addElement( new CKEDITOR.htmlParser.text( piece.substring( lastIndex, index ) ), currentNode );
							addElement( new CKEDITOR.htmlParser.element( 'smiley', { desc: smileyReverseMap[ match ] } ), currentNode );
							lastIndex = index + match.length;
						});

						if ( lastIndex != piece.length )
							addElement( new CKEDITOR.htmlParser.text( piece.substring( lastIndex, piece.length ) ), currentNode );
					}
				});
			}
		};

		// Parse it.
		parser.parse( CKEDITOR.tools.htmlEncode( source ) );

		// Close all hanging nodes.
		while ( currentNode.type != CKEDITOR.NODE_DOCUMENT_FRAGMENT ) {
			var parent = currentNode.parent,
				node = currentNode;

			addElement( node, parent );
			currentNode = parent;
		}

		return fragment;
	};

	var BBCodeWriter = CKEDITOR.tools.createClass({
		$: function() {
			this._ = {
				output: [],
				rules: []
			};

			// List and list item.
			this.setRules( 'list', { breakBeforeOpen:1,breakAfterOpen:1,breakBeforeClose:1,breakAfterClose:1 });

			this.setRules( '*', {
				breakBeforeOpen: 1,
				breakAfterOpen: 0,
				breakBeforeClose: 1,
				breakAfterClose: 0
			});

			this.setRules( 'quote', {
				breakBeforeOpen: 1,
				breakAfterOpen: 0,
				breakBeforeClose: 0,
				breakAfterClose: 1
			});
		},

		proto: {
			//
			// Sets formatting rules for a given tag. The possible rules are:
			// <ul>
			//	<li><b>breakBeforeOpen</b>: break line before the opener tag for this element.</li>
			//	<li><b>breakAfterOpen</b>: break line after the opener tag for this element.</li>
			//	<li><b>breakBeforeClose</b>: break line before the closer tag for this element.</li>
			//	<li><b>breakAfterClose</b>: break line after the closer tag for this element.</li>
			// </ul>
			//
			// All rules default to "false". Each call to the function overrides
			// already present rules, leaving the undefined untouched.
			//
			// @param {String} tagName The tag name to which set the rules.
			// @param {Object} rules An object containing the element rules.
			// @example
			// // Break line before and after "img" tags.
			// writer.setRules( 'list',
			//		 {
			//				 breakBeforeOpen : true
			//				 breakAfterOpen : true
			//		 });
			setRules: function( tagName, rules ) {
				var currentRules = this._.rules[ tagName ];

				if ( currentRules )
					CKEDITOR.tools.extend( currentRules, rules, true );
				else
					this._.rules[ tagName ] = rules;
			},

			getRule: function( tagName, ruleName ) {
				return this._.rules[ tagName ] && this._.rules[ tagName ][ ruleName ];
			},

			openTag : function( tag ) {
				if ( tag in bbcodeMap ) {
					if ( this.getRule( tag, 'breakBeforeOpen' ) )
						this.lineBreak( 1 );

					this.write( '[', tag );
				}
			},

			openTagClose : function( tag ) {
				if ( tag == 'br' )
					this._.output.push( '\n' );
				else if ( tag in bbcodeMap ) {
					this.write( ']' );
					if ( this.getRule( tag, 'breakAfterOpen' ) )
						this.lineBreak( 1 );
				}
			},

			attribute : function( name, val ) {
				if ( name == 'option' ) {
					// Force simply ampersand in attributes.
					if ( typeof val == 'string' )
						val = val.replace( /&amp;/g, '&' );

					this.write( '=', val );
				}
			},

			closeTag: function( tag ) {
				if ( tag in bbcodeMap ) {
					if ( this.getRule( tag, 'breakBeforeClose' ) )
						this.lineBreak( 1 );

					tag != '*' && this.write( '[/', tag, ']' );

					if ( this.getRule( tag, 'breakAfterClose' ) )
						this.lineBreak( 1 );
				}
			},

			text: function( text ) {
				this.write( text );
			},

			comment: function() {},

			// Output line-break for formatting.
			lineBreak: function() {
				// Avoid line break when:
				// 1) Previous tag already put one.
				// 2) We're at output start.
				if ( !this._.hasLineBreak && this._.output.length ) {
					this.write( '\n' );
					this._.hasLineBreak = 1;
				}
			},

			write: function() {
				this._.hasLineBreak = 0;
				var data = Array.prototype.join.call( arguments, '' );
				this._.output.push( data );
			},

			reset: function() {
				this._.output = [];
				this._.hasLineBreak = 0;
			},

			getHtml: function( reset ) {
				var bbcode = this._.output.join( '' );

				if ( reset )
					this.reset();

				return decodeHtml( bbcode );
			}
		}
	});

	var writer = new BBCodeWriter();

	CKEDITOR.plugins.add( 'bbcode', {
		requires: 'entities',

		beforeInit: function( editor ) {
			// Adapt some critical editor configuration for better support
			// of BBCode environment.
			var config = editor.config;
			CKEDITOR.tools.extend( config, {
				enterMode: CKEDITOR.ENTER_BR,
				basicEntities: false,
				entities: false,
				fillEmptyBlocks: false
			}, true );

			editor.filter.disable();
		},

		init: function( editor ) {
			var config = editor.config;

			function BBCodeToHtml( code ) {
				var fragment = CKEDITOR.htmlParser.fragment.fromBBCode( code ),
					writer = new CKEDITOR.htmlParser.basicWriter();

				fragment.writeHtml( writer, bbcodeFilter );
				return writer.getHtml( true );
			}

			var bbcodeFilter = new CKEDITOR.htmlParser.filter();
			bbcodeFilter.addRules({
				elements: {
					blockquote: function( element ) {
						var quoted = new CKEDITOR.htmlParser.element( 'div' );
						quoted.children = element.children;
						element.children = [ quoted ];
						var citeText = element.attributes.cite;
						if ( citeText ) {
							var cite = new CKEDITOR.htmlParser.element( 'cite' );
							cite.add( new CKEDITOR.htmlParser.text( citeText.replace( /^"|"$/g, '' ) ) );
							delete element.attributes.cite;
							element.children.unshift( cite );
						}
					},
					span: function( element ) {
						var bbcode;
						if ( ( bbcode = element.attributes.bbcode ) ) {
							if ( bbcode == 'img' ) {
								element.name = 'img';
								element.attributes.src = element.children[ 0 ].value;
								element.children = [];
							} else if ( bbcode == 'email' ) {
								element.name = 'a';
								element.attributes.href = 'mailto:' + element.children[ 0 ].value;
							}

							delete element.attributes.bbcode;
						}
					},
					ol: function( element ) {
						if ( element.attributes.listType ) {
							if ( element.attributes.listType != 'decimal' )
								element.attributes.style = 'list-style-type:' + element.attributes.listType;
						} else
							element.name = 'ul';

						delete element.attributes.listType;
					},
					a: function( element ) {
						if ( !element.attributes.href )
							element.attributes.href = element.children[ 0 ].value;
					},
					smiley: function( element ) {
						element.name = 'img';

						var description = element.attributes.desc,
							image = config.smiley_images[ CKEDITOR.tools.indexOf( config.smiley_descriptions, description ) ],
							src = CKEDITOR.tools.htmlEncode( config.smiley_path + image );

						element.attributes = {
							src: src,
							'data-cke-saved-src': src,
							title: description,
							alt: description
						};
					}
				}
			});

			editor.dataProcessor.htmlFilter.addRules({
				elements: {
					$: function( element ) {
						var attributes = element.attributes,
							style = CKEDITOR.tools.parseCssText( attributes.style, 1 ),
							value;

						var tagName = element.name;
						if ( tagName in convertMap )
							tagName = convertMap[ tagName ];
						else if ( tagName == 'span' ) {
							if ( ( value = style.color ) ) {
								tagName = 'color';
								value = CKEDITOR.tools.convertRgbToHex( value );
							} else if ( ( value = style[ 'font-size' ] ) ) {
								var percentValue = value.match( /(\d+)%$/ );
								if ( percentValue ) {
									value = percentValue[ 1 ];
									tagName = 'size';
								}
							}
						} else if ( tagName == 'ol' || tagName == 'ul' ) {
							if ( ( value = style[ 'list-style-type' ] ) ) {
								switch ( value ) {
									case 'lower-alpha':
										value = 'a';
										break;
									case 'upper-alpha':
										value = 'A';
										break;
								}
							} else if ( tagName == 'ol' )
								value = 1;

							tagName = 'list';
						} else if ( tagName == 'blockquote' ) {
							try {
								var cite = element.children[ 0 ],
									quoted = element.children[ 1 ],
									citeText = cite.name == 'cite' && cite.children[ 0 ].value;

								if ( citeText ) {
									value = '"' + citeText + '"';
									element.children = quoted.children;
								}

							} catch ( er ) {}

							tagName = 'quote';
						} else if ( tagName == 'a' ) {
							if ( ( value = attributes.href ) ) {
								if ( value.indexOf( 'mailto:' ) !== -1 ) {
									tagName = 'email';
									// [email] should have a single text child with email address.
									element.children = [ new CKEDITOR.htmlParser.text( value.replace( 'mailto:', '' ) ) ];
									value = '';
								} else {
									var singleton = element.children.length == 1 && element.children[ 0 ];
									if ( singleton && singleton.type == CKEDITOR.NODE_TEXT && singleton.value == value )
										value = '';

									tagName = 'url';
								}
							}
						} else if ( tagName == 'img' ) {
							element.isEmpty = 0;

							// Translate smiley (image) to text emotion.
							var src = attributes[ 'data-cke-saved-src' ] || attributes.src,
								alt = attributes.alt;

							if ( src && src.indexOf( editor.config.smiley_path ) != -1 && alt )
								return new CKEDITOR.htmlParser.text( smileyMap[ alt ] );
							else
								element.children = [ new CKEDITOR.htmlParser.text( src ) ];
						}

						element.name = tagName;
						value && ( element.attributes.option = value );

						return null;
					},

					// Remove any bogus br from the end of a pseudo block,
					// e.g. <div>some text<br /><p>paragraph</p></div>
					br: function( element ) {
						var next = element.next;
						if ( next && next.name in blockLikeTags )
							return false;
					}
				}
			}, 1 );

			editor.dataProcessor.writer = writer;

			function onSetData( evt ) {
				var bbcode = evt.data.dataValue;
				evt.data.dataValue = BBCodeToHtml( bbcode );
			}

			// Skip the first "setData" call from inline creator, to allow content of
			// HTML to be loaded from the page element.
			if ( editor.elementMode == CKEDITOR.ELEMENT_MODE_INLINE )
				editor.once( 'contentDom', function() {
					editor.on( 'setData', onSetData );
				});
			else
				editor.on( 'setData', onSetData );

		},

		afterInit: function( editor ) {
			var filters;
			if ( editor._.elementsPath ) {
				// Eliminate irrelevant elements from displaying, e.g body and p.
				if ( ( filters = editor._.elementsPath.filters ) ) {
					filters.push( function( element ) {
						var htmlName = element.getName(),
							name = tagnameMap[ htmlName ] || false;

						// Specialized anchor presents as email.
						if ( name == 'link' && element.getAttribute( 'href' ).indexOf( 'mailto:' ) === 0 )
							name = 'email';
						// Styled span could be either size or color.
						else if ( htmlName == 'span' ) {
							if ( element.getStyle( 'font-size' ) )
								name = 'size';
							else if ( element.getStyle( 'color' ) )
								name = 'color';
						} else if ( name == 'img' ) {
							var src = element.data( 'cke-saved-src' ) || element.getAttribute( 'src' );
							if ( src && src.indexOf( editor.config.smiley_path ) === 0 )
								name = 'smiley';
						}

						return name;
					});
				}
			}
		}
	});

})();
