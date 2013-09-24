/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

(function() {

	function setupAdvParams( element ) {
		var attrName = this.att;

		var value = element && element.hasAttribute( attrName ) && element.getAttribute( attrName ) || '';

		if ( value !== undefined )
			this.setValue( value );
	}

	function commitAdvParams() {
		// Dialogs may use different parameters in the commit list, so, by
		// definition, we take the first CKEDITOR.dom.element available.
		var element;

		for ( var i = 0; i < arguments.length; i++ ) {
			if ( arguments[ i ] instanceof CKEDITOR.dom.element ) {
				element = arguments[ i ];
				break;
			}
		}

		if ( element ) {
			var attrName = this.att,
				value = this.getValue();

			if ( value )
				element.setAttribute( attrName, value );
			else
				element.removeAttribute( attrName, value );
		}
	}

	var defaultTabConfig = { id:1,dir:1,classes:1,styles:1 };

	CKEDITOR.plugins.add( 'dialogadvtab', {
		requires : 'dialog',

		// Returns allowed content rule for the content created by this plugin.
		allowedContent: function( tabConfig ) {
			if ( !tabConfig )
				tabConfig = defaultTabConfig;

			var allowedAttrs = [];
			if ( tabConfig.id )
				allowedAttrs.push( 'id' );
			if ( tabConfig.dir )
				allowedAttrs.push( 'dir' );

			var allowed = '';

			if ( allowedAttrs.length )
				allowed += '[' + allowedAttrs.join( ',' ) +  ']';

			if ( tabConfig.classes )
				allowed += '(*)';
			if ( tabConfig.styles )
				allowed += '{*}';

			return allowed;
		},

		// @param tabConfig
		// id, dir, classes, styles
		createAdvancedTab: function( editor, tabConfig, element ) {
			if ( !tabConfig )
				tabConfig = defaultTabConfig;

			var lang = editor.lang.common;

			var result = {
				id: 'advanced',
				label: lang.advancedTab,
				title: lang.advancedTab,
				elements: [
					{
					type: 'vbox',
					padding: 1,
					children: []
				}
				]
			};

			var contents = [];

			if ( tabConfig.id || tabConfig.dir ) {
				if ( tabConfig.id ) {
					contents.push({
						id: 'advId',
						att: 'id',
						type: 'text',
						requiredContent: element ? element + '[id]' : null,
						label: lang.id,
						setup: setupAdvParams,
						commit: commitAdvParams
					});
				}

				if ( tabConfig.dir ) {
					contents.push({
						id: 'advLangDir',
						att: 'dir',
						type: 'select',
						requiredContent: element ? element + '[dir]' : null,
						label: lang.langDir,
						'default': '',
						style: 'width:100%',
						items: [
							[ lang.notSet, '' ],
							[ lang.langDirLTR, 'ltr' ],
							[ lang.langDirRTL, 'rtl' ]
							],
						setup: setupAdvParams,
						commit: commitAdvParams
					});
				}

				result.elements[ 0 ].children.push({
					type: 'hbox',
					widths: [ '50%', '50%' ],
					children: [].concat( contents )
				});
			}

			if ( tabConfig.styles || tabConfig.classes ) {
				contents = [];

				if ( tabConfig.styles ) {
					contents.push({
						id: 'advStyles',
						att: 'style',
						type: 'text',
						requiredContent: element ? element + '{cke-xyz}' : null,
						label: lang.styles,
						'default': '',

						validate: CKEDITOR.dialog.validate.inlineStyle( lang.invalidInlineStyle ),
						onChange: function() {},

						getStyle: function( name, defaultValue ) {
							var match = this.getValue().match( new RegExp( '(?:^|;)\\s*' + name + '\\s*:\\s*([^;]*)', 'i' ) );
							return match ? match[ 1 ] : defaultValue;
						},

						updateStyle: function( name, value ) {
							var styles = this.getValue();

							var tmp = editor.document.createElement( 'span' );
							tmp.setAttribute( 'style', styles );
							tmp.setStyle( name, value );
							styles = CKEDITOR.tools.normalizeCssText( tmp.getAttribute( 'style' ) );

							this.setValue( styles, 1 );
						},

						setup: setupAdvParams,

						commit: commitAdvParams

					});
				}

				if ( tabConfig.classes ) {
					contents.push({
						type: 'hbox',
						widths: [ '45%', '55%' ],
						children: [
							{
							id: 'advCSSClasses',
							att: 'class',
							type: 'text',
							requiredContent: element ? element + '(cke-xyz)' : null,
							label: lang.cssClasses,
							'default': '',
							setup: setupAdvParams,
							commit: commitAdvParams

						}
						]
					});
				}

				result.elements[ 0 ].children.push({
					type: 'hbox',
					widths: [ '50%', '50%' ],
					children: [].concat( contents )
				});
			}

			return result;
		}
	});

})();
