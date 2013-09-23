/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

'use strict';

(function() {
	/**
	 * Filter is a configurable tool for transforming and filtering {@link CKEDITOR.htmlParser.node nodes}.
	 * It is mainly used during data processing phase which is done not on real DOM nodes,
	 * but on their simplified form represented by {@link CKEDITOR.htmlParser.node} class and its subclasses.
	 *
	 *		var filter = new CKEDITOR.htmlParser.filter( {
	 *			text: function( value ) {
	 *				return '@' + value + '@';
	 *			},
	 *			elements: {
	 *				p: function( element ) {
	 *					element.attributes.foo = '1';
	 *				}
	 *			}
	 *		} );
	 *
	 *		var fragment = CKEDITOR.htmlParser.fragment.fromHtml( '<p>Foo<b>bar!</b></p>' ),
	 *			writer = new CKEDITOR.htmlParser.basicWriter();
	 *		filter.applyTo( fragment );
	 *		fragment.writeHtml( writer );
	 *		writer.getHtml(); // '<p foo="1">@Foo@<b>@bar!@</b></p>'
	 *
	 * @class
	 */
	CKEDITOR.htmlParser.filter = CKEDITOR.tools.createClass( {
		/**
		 * @constructor Creates a filter class instance.
		 * @param {CKEDITOR.htmlParser.filterRulesDefinition} [rules]
		 */
		$: function( rules ) {
			/**
			 * ID of filter instance, which is used to mark elements
			 * to which this filter has been already applied.
			 *
			 * @property {Number} id
			 * @readonly
			 */
			this.id = CKEDITOR.tools.getNextNumber();

			/**
			 * Rules for element names.
			 *
			 * @property {CKEDITOR.htmlParser.filterRulesGroup}
			 * @readonly
			 */
			this.elementNameRules = new filterRulesGroup();

			/**
			 * Rules for attribute names.
			 *
			 * @property {CKEDITOR.htmlParser.filterRulesGroup}
			 * @readonly
			 */
			this.attributeNameRules = new filterRulesGroup();

			/**
			 * Hash of elementName => {@link CKEDITOR.htmlParser.filterRulesGroup rules for elements}.
			 *
			 * @readonly
			 */
			this.elementsRules = {};

			/**
			 * Hash of attributeName => {@link CKEDITOR.htmlParser.filterRulesGroup rules for attributes}.
			 *
			 * @readonly
			 */
			this.attributesRules = {};

			/**
			 * Rules for text nodes.
			 *
			 * @property {CKEDITOR.htmlParser.filterRulesGroup}
			 * @readonly
			 */
			this.textRules = new filterRulesGroup();

			/**
			 * Rules for comment nodes.
			 *
			 * @property {CKEDITOR.htmlParser.filterRulesGroup}
			 * @readonly
			 */
			this.commentRules = new filterRulesGroup();

			/**
			 * Rules for a root node.
			 *
			 * @property {CKEDITOR.htmlParser.filterRulesGroup}
			 * @readonly
			 */
			this.rootRules = new filterRulesGroup();

			if ( rules )
				this.addRules( rules, 10 );
		},

		proto: {
			/**
			 * Add rules to this filter.
			 *
			 * @param {CKEDITOR.htmlParser.filterRulesDefinition} rules Object containing filter rules.
			 * @param {Object/Number} [options] Object containing rules' options or a priority
			 * (for a backward compatibility with CKEditor versions up to 4.2.x).
			 * @param {Number} [options.priority=10] The priority of a rule.
			 * @param {Boolean} [options.applyToAll=false] Whether to apply rule to non-editable
			 * elements and their descendants too.
			 */
			addRules: function( rules, options ) {
				var priority;

				// Backward compatibility.
				if ( typeof options == 'number' )
					priority = options;
				// New version - try reading from options.
				else if ( options && ( 'priority' in options ) )
					priority = options.priority;

				// Defaults.
				if ( typeof priority != 'number' )
					priority = 10;
				if ( typeof options != 'object' )
					options = {};

				// Add the elementNames.
				if ( rules.elementNames)
					this.elementNameRules.addMany( rules.elementNames, priority, options );

				// Add the attributeNames.
				if ( rules.attributeNames )
					this.attributeNameRules.addMany( rules.attributeNames, priority, options );

				// Add the elements.
				if ( rules.elements )
					addNamedRules( this.elementsRules, rules.elements, priority, options );

				// Add the attributes.
				if ( rules.attributes )
					addNamedRules( this.attributesRules, rules.attributes, priority, options );

				// Add the text.
				if ( rules.text )
					this.textRules.add( rules.text, priority, options );

				// Add the comment.
				if ( rules.comment )
					this.commentRules.add( rules.comment, priority, options );

				// Add root node rules.
				if ( rules.root )
					this.rootRules.add( rules.root, priority, options );
			},

			/**
			 * Apply this filter to given node.
			 *
			 * @param {CKEDITOR.htmlParser.node} node The node to be filtered.
			 */
			applyTo: function( node ) {
				node.filter( this );
			},

			onElementName: function( context, name ) {
				return this.elementNameRules.execOnName( context, name );
			},

			onAttributeName: function( context, name ) {
				return this.attributeNameRules.execOnName( context, name );
			},

			onText: function( context, text ) {
				return this.textRules.exec( context, text );
			},

			onComment: function( context, commentText, comment ) {
				return this.commentRules.exec( context, commentText, comment );
			},

			onRoot: function( context, element ) {
				return this.rootRules.exec( context, element );
			},

			onElement: function( context, element ) {
				// We must apply filters set to the specific element name as
				// well as those set to the generic ^/$ name. So, add both to an
				// array and process them in a small loop.
				var rulesGroups = [ this.elementsRules[ '^' ], this.elementsRules[ element.name ], this.elementsRules.$ ],
					rulesGroup, ret;

				for ( var i = 0; i < 3; i++ ) {
					rulesGroup = rulesGroups[ i ];
					if ( rulesGroup ) {
						ret = rulesGroup.exec( context, element, this );

						if ( ret === false )
							return null;

						if ( ret && ret != element )
							return this.onNode( context, ret );

						// The non-root element has been dismissed by one of the filters.
						if ( element.parent && !element.name )
							break;
					}
				}

				return element;
			},

			onNode: function( context, node ) {
				var type = node.type;

				return type == CKEDITOR.NODE_ELEMENT ? this.onElement( context, node ) :
					type == CKEDITOR.NODE_TEXT ? new CKEDITOR.htmlParser.text( this.onText( context, node.value ) ) :
					type == CKEDITOR.NODE_COMMENT ? new CKEDITOR.htmlParser.comment( this.onComment( context, node.value ) ) : null;
			},

			onAttribute: function( context, element, name, value ) {
				var rulesGroup = this.attributesRules[ name ];

				if ( rulesGroup )
					return rulesGroup.exec( context, value, element, this );
				return value;
			}
		}
	} );

	/**
	 * Class grouping filter rules for one subject (like element or attribute names).
	 *
	 * @class
	 */
	function filterRulesGroup() {
		/**
		 * Array of objects containing rule, priority and options.
		 *
		 * @property {Object[]}
		 * @readonly
		 */
		this.rules = [];
	}

	CKEDITOR.htmlParser.filterRulesGroup = filterRulesGroup;

	filterRulesGroup.prototype = {
		/**
		 * Adds specified rule to this group.
		 *
		 * @param {Function/Array} rule Function for function based rule or [ pattern, replacement ] array for
		 * rule applicable to names.
		 * @param {Number} priority
		 * @param options
		 */
		add: function( rule, priority, options ) {
			this.rules.splice( this.findIndex( priority ), 0, {
				value: rule,
				priority: priority,
				options: options
			} );
		},

		/**
		 * Adds specified rules to this group.
		 *
		 * @param {Array} rules Array of rules - see {@link #add}.
		 * @param {Number} priority
		 * @param options
		 */
		addMany: function( rules, priority, options ) {
			var args = [ this.findIndex( priority ), 0 ];

			for ( var i = 0, len = rules.length; i < len; i++ ) {
				args.push( {
					value: rules[ i ],
					priority: priority,
					options: options
				} );
			}

			this.rules.splice.apply( this.rules, args );
		},

		/**
		 * Finds an index at which rule with given priority should be inserted.
		 *
		 * @param {Number} priority
		 * @returns {Number} Index.
		 */
		findIndex: function( priority ) {
			var rules = this.rules,
				len = rules.length,
				i = len - 1;

			// Search from the end, because usually rules will be added with default priority, so
			// we will be able to stop loop quickly.
			while ( i >= 0 && priority < rules[ i ].priority )
				i--;

			return i + 1;
		},

		/**
		 * Executes this rules group on given value. Applicable only if function based rules were added.
		 *
		 * All arguments passed to this function will be forwarded to rules' functions.
		 *
		 * @param {CKEDITOR.htmlParser.node/CKEDITOR.htmlParser.fragment/String} currentValue The value to be filtered.
		 * @returns {CKEDITOR.htmlParser.node/CKEDITOR.htmlParser.fragment/String} Filtered value.
		 */
		exec: function( context, currentValue ) {
			var isNode = currentValue instanceof CKEDITOR.htmlParser.node || currentValue instanceof CKEDITOR.htmlParser.fragment,
				// Splice '1' to remove context, which we don't want to pass to filter rules.
				args = Array.prototype.slice.call( arguments, 1 ),
				rules = this.rules,
				len = rules.length,
				orgType, orgName, ret, i, rule;

			for ( i = 0; i < len; i++ ) {
				// Backup the node info before filtering.
				if ( isNode ) {
					orgType = currentValue.type;
					orgName = currentValue.name;
				}

				rule = rules[ i ];
				if ( isRuleApplicable( context, rule ) ) {
					ret = rule.value.apply( null, args );

					if ( ret === false )
						return ret;

					// We're filtering node (element/fragment).
					if ( isNode ) {
						// No further filtering if it's not anymore
						// fitable for the subsequent filters.
						if ( ret && ( ret.name != orgName || ret.type != orgType ) )
							return ret;
					}
					// Filtering value (nodeName/textValue/attrValue).
					else {
						// No further filtering if it's not any more values.
						if ( typeof ret != 'string' )
							return ret;
					}

					// Update currentValue and corresponding argument in args array.
					// Updated values will be used in next for-loop step.
					if ( ret != undefined )
						args[ 0 ] = currentValue = ret;
				}
			}

			return currentValue;
		},

		/**
		 * Executes this rules group on name. Applicable only if filter rules for names were added.
		 *
		 * @param {String} currentName The name to be filtered.
		 * @returns {String} Filtered name.
		 */
		execOnName: function( context, currentName ) {
			var i = 0,
				rules = this.rules,
				len = rules.length,
				rule;

			for ( ; currentName && i < len; i++ ) {
				rule = rules[ i ];
				if ( isRuleApplicable( context, rule ) )
					currentName = currentName.replace( rule.value[ 0 ], rule.value[ 1 ] );
			}

			return currentName;
		}
	};

	function addNamedRules( rulesGroups, newRules, priority, options ) {
		var ruleName, rulesGroup;

		for ( ruleName in newRules ) {
			rulesGroup = rulesGroups[ ruleName ];

			if ( !rulesGroup )
				rulesGroup = rulesGroups[ ruleName ] = new filterRulesGroup();

			rulesGroup.add( newRules[ ruleName ], priority, options );
		}
	}

	function isRuleApplicable( context, rule ) {
		// Do not apply rule if context is nonEditable and rule doesn't have applyToAll option.
		return !context.nonEditable || rule.options.applyToAll;
	}

})();

/**
 * @class CKEDITOR.htmlParser.filterRulesDefinition
 * @abstract
 */