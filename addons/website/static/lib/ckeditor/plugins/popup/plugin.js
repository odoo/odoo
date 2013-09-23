/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

CKEDITOR.plugins.add( 'popup' );

CKEDITOR.tools.extend( CKEDITOR.editor.prototype, {
	/**
	 * Opens Browser in a popup. The `width` and `height` parameters accept
	 * numbers (pixels) or percent (of screen size) values.
	 *
	 * @member CKEDITOR.editor
	 * @param {String} url The url of the external file browser.
	 * @param {Number/String} [width='80%'] Popup window width.
	 * @param {Number/String} [height='70%'] Popup window height.
	 * @param {String} [options='location=no,menubar=no,toolbar=no,dependent=yes,minimizable=no,modal=yes,alwaysRaised=yes,resizable=yes,scrollbars=yes']
	 * Popup window features.
	 */
	popup: function( url, width, height, options ) {
		width = width || '80%';
		height = height || '70%';

		if ( typeof width == 'string' && width.length > 1 && width.substr( width.length - 1, 1 ) == '%' )
			width = parseInt( window.screen.width * parseInt( width, 10 ) / 100, 10 );

		if ( typeof height == 'string' && height.length > 1 && height.substr( height.length - 1, 1 ) == '%' )
			height = parseInt( window.screen.height * parseInt( height, 10 ) / 100, 10 );

		if ( width < 640 )
			width = 640;

		if ( height < 420 )
			height = 420;

		var top = parseInt( ( window.screen.height - height ) / 2, 10 ),
			left = parseInt( ( window.screen.width - width ) / 2, 10 );

		options = ( options || 'location=no,menubar=no,toolbar=no,dependent=yes,minimizable=no,modal=yes,alwaysRaised=yes,resizable=yes,scrollbars=yes' ) + ',width=' + width +
			',height=' + height +
			',top=' + top +
			',left=' + left;

		var popupWindow = window.open( '', null, options, true );

		// Blocked by a popup blocker.
		if ( !popupWindow )
			return false;

		try {
			// Chrome is problematic with moveTo/resizeTo, but it's not really needed here (#8855).
			var ua = navigator.userAgent.toLowerCase();
			if ( ua.indexOf( ' chrome/' ) == -1 ) {
				popupWindow.moveTo( left, top );
				popupWindow.resizeTo( width, height );
			}
			popupWindow.focus();
			popupWindow.location.href = url;
		} catch ( e ) {
			popupWindow = window.open( url, null, options, true );
		}

		return true;
	}
});
