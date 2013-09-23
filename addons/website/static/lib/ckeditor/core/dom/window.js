/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the {@link CKEDITOR.dom.document} class, which
 *		represents a DOM document.
 */

/**
 * Represents a DOM window.
 *
 *		var document = new CKEDITOR.dom.window( window );
 *
 * @class
 * @extends CKEDITOR.dom.domObject
 * @constructor Creates a window class instance.
 * @param {Object} domWindow A native DOM window.
 */
CKEDITOR.dom.window = function( domWindow ) {
	CKEDITOR.dom.domObject.call( this, domWindow );
};

CKEDITOR.dom.window.prototype = new CKEDITOR.dom.domObject();

CKEDITOR.tools.extend( CKEDITOR.dom.window.prototype, {
	/**
	 * Moves the selection focus to this window.
	 *
	 *		var win = new CKEDITOR.dom.window( window );
	 *		win.focus();
	 */
	focus: function() {
		this.$.focus();
	},

	/**
	 * Gets the width and height of this window's viewable area.
	 *
	 *		var win = new CKEDITOR.dom.window( window );
	 *		var size = win.getViewPaneSize();
	 *		alert( size.width );
	 *		alert( size.height );
	 *
	 * @returns {Object} An object with the `width` and `height`
	 * properties containing the size.
	 */
	getViewPaneSize: function() {
		var doc = this.$.document,
			stdMode = doc.compatMode == 'CSS1Compat';
		return {
			width: ( stdMode ? doc.documentElement.clientWidth : doc.body.clientWidth ) || 0,
			height: ( stdMode ? doc.documentElement.clientHeight : doc.body.clientHeight ) || 0
		};
	},

	/**
	 * Gets the current position of the window's scroll.
	 *
	 *		var win = new CKEDITOR.dom.window( window );
	 *		var pos = win.getScrollPosition();
	 *		alert( pos.x );
	 *		alert( pos.y );
	 *
	 * @returns {Object} An object with the `x` and `y` properties
	 * containing the scroll position.
	 */
	getScrollPosition: function() {
		var $ = this.$;

		if ( 'pageXOffset' in $ ) {
			return {
				x: $.pageXOffset || 0,
				y: $.pageYOffset || 0
			};
		} else {
			var doc = $.document;
			return {
				x: doc.documentElement.scrollLeft || doc.body.scrollLeft || 0,
				y: doc.documentElement.scrollTop || doc.body.scrollTop || 0
			};
		}
	},

	/**
	 * Gets the frame element containing this window context.
	 *
	 * @returns {CKEDITOR.dom.element} The frame element or `null` if not in a frame context.
	 */
	getFrame: function() {
		var iframe = this.$.frameElement;
		return iframe ? new CKEDITOR.dom.element.get( iframe ) : null;
	}
});
