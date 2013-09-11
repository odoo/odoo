/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview stylesheetParser plugin.
 */

(function() {
	// We want to extract only the elements with classes defined in the stylesheets:
	function parseClasses( aRules, skipSelectors, validSelectors ) {
		// aRules are just the different rules in the style sheets
		// We want to merge them and them split them by commas, so we end up with only
		// the selectors
		var s = aRules.join( ' ' );
		// Remove selectors splitting the elements, leave only the class selector (.)
		s = s.replace( /(,|>|\+|~)/g, ' ' );
		// Remove attribute selectors: table[border="0"]
		s = s.replace( /\[[^\]]*/g, '' );
		// Remove Ids: div#main
		s = s.replace( /#[^\s]*/g, '' );
		// Remove pseudo-selectors and pseudo-elements: :hover :nth-child(2n+1) ::before
		s = s.replace( /\:{1,2}[^\s]*/g, '' );

		s = s.replace( /\s+/g, ' ' );

		var aSelectors = s.split( ' ' ),
			aClasses = [];

		for ( var i = 0; i < aSelectors.length; i++ ) {
			var selector = aSelectors[ i ];

			if ( validSelectors.test( selector ) && !skipSelectors.test( selector ) ) {
				// If we still don't know about this one, add it
				if ( CKEDITOR.tools.indexOf( aClasses, selector ) == -1 )
					aClasses.push( selector );
			}
		}

		return aClasses;
	}

	function LoadStylesCSS( theDoc, skipSelectors, validSelectors ) {
		var styles = [],
			// It will hold all the rules of the applied stylesheets (except those internal to CKEditor)
			aRules = [],
			i;

		for ( i = 0; i < theDoc.styleSheets.length; i++ ) {
			var sheet = theDoc.styleSheets[ i ],
				node = sheet.ownerNode || sheet.owningElement;

			// Skip the internal stylesheets
			if ( node.getAttribute( 'data-cke-temp' ) )
				continue;

			// Exclude stylesheets injected by extensions
			if ( sheet.href && sheet.href.substr( 0, 9 ) == 'chrome://' )
				continue;

			// Bulletproof with x-domain content stylesheet.
			try {
				var sheetRules = sheet.cssRules || sheet.rules;
				for ( var j = 0; j < sheetRules.length; j++ )
					aRules.push( sheetRules[ j ].selectorText );
			} catch ( e ) {}
		}

		var aClasses = parseClasses( aRules, skipSelectors, validSelectors );

		// Add each style to our "Styles" collection.
		for ( i = 0; i < aClasses.length; i++ ) {
			var oElement = aClasses[ i ].split( '.' ),
				element = oElement[ 0 ].toLowerCase(),
				sClassName = oElement[ 1 ];

			styles.push({
				name: element + '.' + sClassName,
				element: element,
				attributes: { 'class': sClassName }
			});
		}

		return styles;
	}

	// Register a plugin named "stylesheetparser".
	CKEDITOR.plugins.add( 'stylesheetparser', {
		init: function( editor ) {
			// Stylesheet parser is incompatible with filter (#10136).
			editor.filter.disable();

			var cachedDefinitions;

			editor.once( 'stylesSet', function( evt ) {
				// Cancel event and fire it again when styles are ready.
				evt.cancel();

				// Overwrite editor#getStylesSet asap (contentDom is the first moment
				// when editor.document is ready), but before stylescombo reads styles set (priority 5).
				editor.once( 'contentDom', function() {
					editor.getStylesSet( function( definitions ) {
						// Rules that must be skipped
						var skipSelectors = editor.config.stylesheetParser_skipSelectors || ( /(^body\.|^\.)/i ),
							// Rules that are valid
							validSelectors = editor.config.stylesheetParser_validSelectors || ( /\w+\.\w+/ );

						cachedDefinitions = definitions.concat( LoadStylesCSS( editor.document.$, skipSelectors, validSelectors ) );

						editor.getStylesSet = function( callback ) {
							if ( cachedDefinitions )
								return callback( cachedDefinitions );
						};

						editor.fire( 'stylesSet', { styles: cachedDefinitions } );
					} );
				} );
			}, null, null, 1 );
		}
	});
})();


/**
 * A regular expression that defines whether a CSS rule will be
 * skipped by the Stylesheet Parser plugin. A CSS rule matching
 * the regular expression will be ignored and will not be available
 * in the Styles drop-down list.
 *
 *		// Ignore rules for body and caption elements, classes starting with "high", and any class defined for no specific element.
 *		config.stylesheetParser_skipSelectors = /(^body\.|^caption\.|\.high|^\.)/i;
 *
 * @since 3.6
 * @cfg {RegExp} [stylesheetParser_skipSelectors=/(^body\.|^\.)/i]
 * @member CKEDITOR.config
 * @see CKEDITOR.config#stylesheetParser_validSelectors
 */

/**
 * A regular expression that defines which CSS rules will be used
 * by the Stylesheet Parser plugin. A CSS rule matching the regular
 * expression will be available in the Styles drop-down list.
 *
 *		// Only add rules for p and span elements.
 *		config.stylesheetParser_validSelectors = /\^(p|span)\.\w+/;
 *
 * @since 3.6
 * @cfg {RegExp} [stylesheetParser_validSelectors=/\w+\.\w+/]
 * @member CKEDITOR.config
 * @see CKEDITOR.config#stylesheetParser_skipSelectors
 */
