/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the {@link CKEDITOR.env} object which contains
 *		environment and browser information.
 */

if ( !CKEDITOR.env ) {
	/**
	 * Environment and browser information.
	 *
	 * @class CKEDITOR.env
	 * @singleton
	 */
	CKEDITOR.env = (function() {
		var agent = navigator.userAgent.toLowerCase();
		var opera = window.opera;

		var env = {
			/**
			 * Indicates that CKEditor is running in Internet Explorer.
			 *
			 *		if ( CKEDITOR.env.ie )
			 *			alert( 'I\'m running in IE!' );
			 *
			 * @property {Boolean}
			 */
			ie: eval( '/*@cc_on!@*/false' ),
			// Use eval to preserve conditional comment when compiling with Google Closure Compiler (#93).

			/**
			 * Indicates that CKEditor is running in Opera.
			 *
			 *		if ( CKEDITOR.env.opera )
			 *			alert( 'I\'m running in Opera!' );
			 *
			 * @property {Boolean}
			 */
			opera: ( !!opera && opera.version ),

			/**
			 * Indicates that CKEditor is running in a WebKit-based browser, like Safari.
			 *
			 *		if ( CKEDITOR.env.webkit )
			 *			alert( 'I\'m running in a WebKit browser!' );
			 *
			 * @property {Boolean}
			 */
			webkit: ( agent.indexOf( ' applewebkit/' ) > -1 ),

			/**
			 * Indicates that CKEditor is running in Adobe AIR.
			 *
			 *		if ( CKEDITOR.env.air )
			 *			alert( 'I\'m on AIR!' );
			 *
			 * @property {Boolean}
			 */
			air: ( agent.indexOf( ' adobeair/' ) > -1 ),

			/**
			 * Indicates that CKEditor is running on Macintosh.
			 *
			 *		if ( CKEDITOR.env.mac )
			 *			alert( 'I love apples!'' );
			 *
			 * @property {Boolean}
			 */
			mac: ( agent.indexOf( 'macintosh' ) > -1 ),

			/**
			 * Indicates that CKEditor is running in a Quirks Mode environemnt.
			 *
			 *		if ( CKEDITOR.env.quirks )
			 *			alert( 'Nooooo!' );
			 *
			 * @property {Boolean}
			 */
			quirks: ( document.compatMode == 'BackCompat' ),

			/**
			 * Indicates that CKEditor is running in a mobile environemnt.
			 *
			 *		if ( CKEDITOR.env.mobile )
			 *			alert( 'I\'m running with CKEditor today!' );
			 *
			 * @property {Boolean}
			 */
			mobile: ( agent.indexOf( 'mobile' ) > -1 ),

			/**
			 * Indicates that CKEditor is running on Apple iPhone/iPad/iPod devices.
			 *
			 *		if ( CKEDITOR.env.iOS )
			 *			alert( 'I like little apples!' );
			 *
			 * @property {Boolean}
			 */
			iOS: /(ipad|iphone|ipod)/.test( agent ),

			/**
			 * Indicates that the browser has a custom domain enabled. This has
			 * been set with `document.domain`.
			 *
			 *		if ( CKEDITOR.env.isCustomDomain() )
			 *			alert( 'I\'m in a custom domain!' );
			 *
			 * @returns {Boolean} `true` if a custom domain is enabled.
			 * @deprecated
			 */
			isCustomDomain: function() {
				if ( !this.ie )
					return false;

				var domain = document.domain,
					hostname = window.location.hostname;

				return domain != hostname && domain != ( '[' + hostname + ']' ); // IPv6 IP support (#5434)
			},

			/**
			 * Indicates that the page is running under an encrypted connection.
			 *
			 *		if ( CKEDITOR.env.secure )
			 *			alert( 'I\'m on SSL!' );
			 *
			 * @returns {Boolean} `true` if the page has an encrypted connection.
			 */
			secure: location.protocol == 'https:'
		};

		/**
		 * Indicates that CKEditor is running in a Gecko-based browser, like
		 * Firefox.
		 *
		 *		if ( CKEDITOR.env.gecko )
		 *			alert( 'I\'m riding a gecko!' );
		 *
		 * @property {Boolean}
		 */
		env.gecko = ( navigator.product == 'Gecko' && !env.webkit && !env.opera );

		/**
		 * Indicates that CKEditor is running in Chrome.
		 *
		 *		if ( CKEDITOR.env.chrome )
		 *			alert( 'I\'m running in Chrome!' );
		 *
		 * @property {Boolean} chrome
		 */

		 /**
		 * Indicates that CKEditor is running in Safari (including the mobile version).
		 *
		 *		if ( CKEDITOR.env.safari )
		 *			alert( 'I\'m on Safari!' );
		 *
		 * @property {Boolean} safari
		 */
		if ( env.webkit ) {
			if ( agent.indexOf( 'chrome' ) > -1 )
				env.chrome = true;
			else
				env.safari = true;
		}

		var version = 0;

		// Internet Explorer 6.0+
		if ( env.ie ) {
			// We use env.version for feature detection, so set it properly.
			if ( env.quirks || !document.documentMode )
				version = parseFloat( agent.match( /msie (\d+)/ )[ 1 ] );
			else
				version = document.documentMode;

			// Deprecated features available just for backwards compatibility.
			env.ie9Compat = version == 9;
			env.ie8Compat = version == 8;
			env.ie7Compat = version == 7;
			env.ie6Compat = version < 7 || ( env.quirks && version < 10 );

			/**
			 * Indicates that CKEditor is running in an IE6-like environment, which
			 * includes IE6 itself as well as IE7, IE8 and IE9 in Quirks Mode.
			 *
			 * @deprecated
			 * @property {Boolean} ie6Compat
			 */

			/**
			 * Indicates that CKEditor is running in an IE7-like environment, which
			 * includes IE7 itself and IE8's IE7 Document Mode.
			 *
			 * @deprecated
			 * @property {Boolean} ie7Compat
			 */

			/**
			 * Indicates that CKEditor is running in Internet Explorer 8 on
			 * Standards Mode.
			 *
			 * @deprecated
			 * @property {Boolean} ie8Compat
			 */

			/**
			 * Indicates that CKEditor is running in Internet Explorer 9 on
			 * Standards Mode.
			 *
			 * @deprecated
			 * @property {Boolean} ie9Compat
			 */
		}

		// Gecko.
		if ( env.gecko ) {
			var geckoRelease = agent.match( /rv:([\d\.]+)/ );
			if ( geckoRelease ) {
				geckoRelease = geckoRelease[ 1 ].split( '.' );
				version = geckoRelease[ 0 ] * 10000 + ( geckoRelease[ 1 ] || 0 ) * 100 + ( geckoRelease[ 2 ] || 0 ) * 1;
			}
		}

		// Opera 9.50+
		if ( env.opera )
			version = parseFloat( opera.version() );

		// Adobe AIR 1.0+
		// Checked before Safari because AIR have the WebKit rich text editor
		// features from Safari 3.0.4, but the version reported is 420.
		if ( env.air )
			version = parseFloat( agent.match( / adobeair\/(\d+)/ )[ 1 ] );

		// WebKit 522+ (Safari 3+)
		if ( env.webkit )
			version = parseFloat( agent.match( / applewebkit\/(\d+)/ )[ 1 ] );

		/**
		 * Contains the browser version.
		 *
		 * For Gecko-based browsers (like Firefox) it contains the revision
		 * number with first three parts concatenated with a padding zero
		 * (e.g. for revision 1.9.0.2 we have 10900).
		 *
		 * For WebKit-based browsers (like Safari and Chrome) it contains the
		 * WebKit build version (e.g. 522).
		 *
		 * For IE browsers, it matches the "Document Mode".
		 *
		 *		if ( CKEDITOR.env.ie && CKEDITOR.env.version <= 6 )
		 *			alert( 'Ouch!' );
		 *
		 * @property {Number}
		 */
		env.version = version;

		/**
		 * Indicates that CKEditor is running in a compatible browser.
		 *
		 *		if ( CKEDITOR.env.isCompatible )
		 *			alert( 'Your browser is pretty cool!' );
		 *
		 * @property {Boolean}
		 */
		env.isCompatible =
			// White list of mobile devices that CKEditor supports.
			env.iOS && version >= 534 ||
			!env.mobile && (
				( env.ie && version > 6 ) ||
				( env.gecko && version >= 10801 ) ||
				( env.opera && version >= 9.5 ) ||
				( env.air && version >= 1 ) ||
				( env.webkit && version >= 522 ) ||
				false
			);

		/**
		 * Indicates that CKEditor is running in the HiDPI environment.
		 *
		 *		if ( CKEDITOR.env.hidpi )
		 *			alert( 'You are using a screen with high pixel density.' );
		 *
		 * @property {Boolean}
		 */
		env.hidpi = window.devicePixelRatio >= 2;

		/**
		 * A CSS class that denotes the browser where CKEditor runs and is appended
		 * to the HTML element that contains the editor. It makes it easier to apply
		 * browser-specific styles to editor instances.
		 *
		 *		myDiv.className = CKEDITOR.env.cssClass;
		 *
		 * @property {String}
		 */
		env.cssClass = 'cke_browser_' + ( env.ie ? 'ie' : env.gecko ? 'gecko' : env.opera ? 'opera' : env.webkit ? 'webkit' : 'unknown' );

		if ( env.quirks )
			env.cssClass += ' cke_browser_quirks';

		if ( env.ie ) {
			env.cssClass += ' cke_browser_ie' + ( env.quirks || env.version < 7 ? '6' : env.version );

			if ( env.quirks )
				env.cssClass += ' cke_browser_iequirks';
		}

		if ( env.gecko ) {
			if ( version < 10900 )
				env.cssClass += ' cke_browser_gecko18';
			else if ( version <= 11000 )
				env.cssClass += ' cke_browser_gecko19';
		}

		if ( env.air )
			env.cssClass += ' cke_browser_air';

		if ( env.iOS )
			env.cssClass += ' cke_browser_ios';

		if ( env.hidpi )
			env.cssClass += ' cke_hidpi';

		return env;
	})();
}

// PACKAGER_RENAME( CKEDITOR.env )
// PACKAGER_RENAME( CKEDITOR.env.ie )
