/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Contains the second part of the {@link CKEDITOR} object
 *		definition, which defines the basic editor features to be available in
 *		the root ckeditor_basic.js file.
 */

if ( CKEDITOR.status == 'unloaded' ) {
	(function() {
		CKEDITOR.event.implementOn( CKEDITOR );

		/**
		 * Forces the full CKEditor core code, in the case only the basic code has been
		 * loaded (`ckeditor_basic.js`). This method self-destroys (becomes undefined) in
		 * the first call or as soon as the full code is available.
		 *
		 *		// Check if the full core code has been loaded and load it.
		 *		if ( CKEDITOR.loadFullCore )
		 *			CKEDITOR.loadFullCore();
		 *
		 * @member CKEDITOR
		 */
		CKEDITOR.loadFullCore = function() {
			// If the basic code is not ready, just mark it to be loaded.
			if ( CKEDITOR.status != 'basic_ready' ) {
				CKEDITOR.loadFullCore._load = 1;
				return;
			}

			// Destroy this function.
			delete CKEDITOR.loadFullCore;

			// Append the script to the head.
			var script = document.createElement( 'script' );
			script.type = 'text/javascript';
			script.src = CKEDITOR.basePath + 'ckeditor.js';
			script.src = CKEDITOR.basePath + 'ckeditor_source.js'; // %REMOVE_LINE%

			document.getElementsByTagName( 'head' )[ 0 ].appendChild( script );
		};

		/**
		 * The time to wait (in seconds) to load the full editor code after the
		 * page load, if the "ckeditor_basic" file is used. If set to zero, the
		 * editor is loaded on demand, as soon as an instance is created.
		 *
		 * This value must be set on the page before the page load completion.
		 *
		 *		// Loads the full source after five seconds.
		 *		CKEDITOR.loadFullCoreTimeout = 5;
		 *
		 * @property
		 * @member CKEDITOR
		 */
		CKEDITOR.loadFullCoreTimeout = 0;

		// Documented at ckeditor.js.
		CKEDITOR.add = function( editor ) {
			// For now, just put the editor in the pending list. It will be
			// processed as soon as the full code gets loaded.
			var pending = this._.pending || ( this._.pending = [] );
			pending.push( editor );
		};

		(function() {
			var onload = function() {
					var loadFullCore = CKEDITOR.loadFullCore,
						loadFullCoreTimeout = CKEDITOR.loadFullCoreTimeout;

					if ( !loadFullCore )
						return;

					CKEDITOR.status = 'basic_ready';

					if ( loadFullCore && loadFullCore._load )
						loadFullCore();
					else if ( loadFullCoreTimeout ) {
						setTimeout( function() {
							if ( CKEDITOR.loadFullCore )
								CKEDITOR.loadFullCore();
						}, loadFullCoreTimeout * 1000 );
					}
				};

			CKEDITOR.domReady( onload );
		})();

		CKEDITOR.status = 'basic_loaded';
	})();
}
