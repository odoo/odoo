/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the {@link CKEDITOR.scriptLoader} object, used to load scripts
 *		asynchronously.
 */

/**
 * Load scripts asynchronously.
 *
 * @class
 * @singleton
 */
CKEDITOR.scriptLoader = (function() {
	var uniqueScripts = {},
		waitingList = {};

	return {
		/**
		 * Loads one or more external script checking if not already loaded
		 * previously by this function.
		 *
		 *		CKEDITOR.scriptLoader.load( '/myscript.js' );
		 *
		 *		CKEDITOR.scriptLoader.load( '/myscript.js', function( success ) {
		 *			// Alerts true if the script has been properly loaded.
		 *			// HTTP error 404 should return false.
		 *			alert( success );
		 *		} );
		 *
		 *		CKEDITOR.scriptLoader.load( [ '/myscript1.js', '/myscript2.js' ], function( completed, failed ) {
		 *			alert( 'Number of scripts loaded: ' + completed.length );
		 *			alert( 'Number of failures: ' + failed.length );
		 *		} );
		 *
		 * @param {String/Array} scriptUrl One or more URLs pointing to the
		 * scripts to be loaded.
		 * @param {Function} [callback] A function to be called when the script
		 * is loaded and executed. If a string is passed to `scriptUrl`, a
		 * boolean parameter is passed to the callback, indicating the
		 * success of the load. If an array is passed instead, two arrays
		 * parameters are passed to the callback - the first contains the
		 * URLs that have been properly loaded and the second the failed ones.
		 * @param {Object} [scope] The scope (`this` reference) to be used for
		 * the callback call. Defaults to {@link CKEDITOR}.
		 * @param {Boolean} [showBusy] Changes the cursor of the document while
		 * the script is loaded.
		 */
		load: function( scriptUrl, callback, scope, showBusy ) {
			var isString = ( typeof scriptUrl == 'string' );

			if ( isString )
				scriptUrl = [ scriptUrl ];

			if ( !scope )
				scope = CKEDITOR;

			var scriptCount = scriptUrl.length,
				completed = [],
				failed = [];

			var doCallback = function( success ) {
					if ( callback ) {
						if ( isString )
							callback.call( scope, success );
						else
							callback.call( scope, completed, failed );
					}
				};

			if ( scriptCount === 0 ) {
				doCallback( true );
				return;
			}

			var checkLoaded = function( url, success ) {
					( success ? completed : failed ).push( url );

					if ( --scriptCount <= 0 ) {
						showBusy && CKEDITOR.document.getDocumentElement().removeStyle( 'cursor' );
						doCallback( success );
					}
				};

			var onLoad = function( url, success ) {
					// Mark this script as loaded.
					uniqueScripts[ url ] = 1;

					// Get the list of callback checks waiting for this file.
					var waitingInfo = waitingList[ url ];
					delete waitingList[ url ];

					// Check all callbacks waiting for this file.
					for ( var i = 0; i < waitingInfo.length; i++ )
						waitingInfo[ i ]( url, success );
				};

			var loadScript = function( url ) {
					if ( uniqueScripts[ url ] ) {
						checkLoaded( url, true );
						return;
					}

					var waitingInfo = waitingList[ url ] || ( waitingList[ url ] = [] );
					waitingInfo.push( checkLoaded );

					// Load it only for the first request.
					if ( waitingInfo.length > 1 )
						return;

					// Create the <script> element.
					var script = new CKEDITOR.dom.element( 'script' );
					script.setAttributes({
						type: 'text/javascript',
						src: url } );

					if ( callback ) {
						if ( CKEDITOR.env.ie ) {
							// FIXME: For IE, we are not able to return false on error (like 404).
							script.$.onreadystatechange = function() {
								if ( script.$.readyState == 'loaded' || script.$.readyState == 'complete' ) {
									script.$.onreadystatechange = null;
									onLoad( url, true );
								}
							};
						} else {
							script.$.onload = function() {
								// Some browsers, such as Safari, may call the onLoad function
								// immediately. Which will break the loading sequence. (#3661)
								setTimeout( function() {
									onLoad( url, true );
								}, 0 );
							};

							// FIXME: Opera and Safari will not fire onerror.
							script.$.onerror = function() {
								onLoad( url, false );
							};
						}
					}

					// Append it to <head>.
					script.appendTo( CKEDITOR.document.getHead() );

					CKEDITOR.fire( 'download', url ); // %REMOVE_LINE%
				};

			showBusy && CKEDITOR.document.getDocumentElement().setStyle( 'cursor', 'wait' );
			for ( var i = 0; i < scriptCount; i++ ) {
				loadScript( scriptUrl[ i ] );
			}
		},

		/**
		 * Loads a script in a queue, so only one is loaded at the same time.
		 *
		 * @since 4.1.2
		 * @param {String} scriptUrl URL pointing to the script to be loaded.
		 * @param {Function} [callback] A function to be called when the script
		 * is loaded and executed. A boolean parameter is passed to the callback,
		 * indicating the success of the load.
		 *
		 * @see CKEDITOR.scriptLoader#load
		 */
		queue: (function() {
			var pending = [];

			// Loads the very first script from queue and removes it.
			function loadNext() {
				var script;

				if ( ( script = pending[ 0 ] ) )
					this.load( script.scriptUrl, script.callback, CKEDITOR, 0 );
			}

			return function( scriptUrl, callback ) {
				var that = this;

				// This callback calls the standard callback for the script
				// and loads the very next script from pending list.
				function callbackWrapper() {
					callback && callback.apply( this, arguments );

					// Removed the just loaded script from the queue.
					pending.shift();

					loadNext.call( that );
				}

				// Let's add this script to the queue
				pending.push( { scriptUrl: scriptUrl, callback: callbackWrapper } );

				// If the queue was empty, then start loading.
				if ( pending.length == 1 )
					loadNext.call( this );
			};
		})()
	};
})();
