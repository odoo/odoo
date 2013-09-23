/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Plugin for making iframe based dialogs.
 */

CKEDITOR.plugins.add( 'iframedialog', {
	requires: 'dialog',
	onLoad: function() {
		/**
		 * An iframe base dialog.
		 *
		 * @static
		 * @member CKEDITOR.dialog
		 * @param {String} name Name of the dialog.
		 * @param {String} title Title of the dialog.
		 * @param {Number} minWidth Minimum width of the dialog.
		 * @param {Number} minHeight Minimum height of the dialog.
		 * @param {Function} [onContentLoad] Function called when the iframe has been loaded.
		 * If it isn't specified, the inner frame is notified of the dialog events (`'load'`,
		 * `'resize'`, `'ok'` and `'cancel'`) on a function called `'onDialogEvent'`.
		 * @param {Object} [userDefinition] Additional properties for the dialog definition.
		 */
		CKEDITOR.dialog.addIframe = function( name, title, src, minWidth, minHeight, onContentLoad, userDefinition ) {
			var element = {
				type: 'iframe',
				src: src,
				width: '100%',
				height: '100%'
			};

			if ( typeof( onContentLoad ) == 'function' )
				element.onContentLoad = onContentLoad;
			else
				element.onContentLoad = function() {
				var element = this.getElement(),
					childWindow = element.$.contentWindow;

				// If the inner frame has defined a "onDialogEvent" function, setup listeners
				if ( childWindow.onDialogEvent ) {
					var dialog = this.getDialog(),
						notifyEvent = function( e ) {
							return childWindow.onDialogEvent( e );
						};

					dialog.on( 'ok', notifyEvent );
					dialog.on( 'cancel', notifyEvent );
					dialog.on( 'resize', notifyEvent );

					// Clear listeners
					dialog.on( 'hide', function( e ) {
						dialog.removeListener( 'ok', notifyEvent );
						dialog.removeListener( 'cancel', notifyEvent );
						dialog.removeListener( 'resize', notifyEvent );

						e.removeListener();
					});

					// Notify child iframe of load:
					childWindow.onDialogEvent({
						name: 'load',
						sender: this,
						editor: dialog._.editor
					});
				}
			};

			var definition = {
				title: title,
				minWidth: minWidth,
				minHeight: minHeight,
				contents: [
					{
					id: 'iframe',
					label: title,
					expand: true,
					elements: [ element ],
					style: 'width:' + element.width + ';height:' + element.height
				}
				]
			};

			for ( var i in userDefinition )
				definition[ i ] = userDefinition[ i ];

			this.add( name, function() {
				return definition;
			});
		};

		(function() {
			/**
			 * An iframe element.
			 *
			 * @class CKEDITOR.ui.dialog.iframeElement
			 * @extends CKEDITOR.ui.dialog.uiElement
			 * @constructor
			 * @private
			 * @param {CKEDITOR.dialog} dialog Parent dialog object.
			 * @param {CKEDITOR.dialog.definition.uiElement} elementDefinition
			 * The element definition. Accepted fields:
			 *
			 * * `src` (Required) The src field of the iframe.
			 * * `width` (Required) The iframe's width.
			 * * `height` (Required) The iframe's height.
			 * * `onContentLoad` (Optional) A function to be executed
			 *     after the iframe's contents has finished loading.
			 *
			 * @param {Array} htmlList List of HTML code to output to.
			 */
			var iframeElement = function( dialog, elementDefinition, htmlList ) {
					if ( arguments.length < 3 )
						return;

					var _ = ( this._ || ( this._ = {} ) ),
						contentLoad = elementDefinition.onContentLoad && CKEDITOR.tools.bind( elementDefinition.onContentLoad, this ),
						cssWidth = CKEDITOR.tools.cssLength( elementDefinition.width ),
						cssHeight = CKEDITOR.tools.cssLength( elementDefinition.height );
					_.frameId = CKEDITOR.tools.getNextId() + '_iframe';

					// IE BUG: Parent container does not resize to contain the iframe automatically.
					dialog.on( 'load', function() {
						var iframe = CKEDITOR.document.getById( _.frameId ),
							parentContainer = iframe.getParent();

						parentContainer.setStyles({
							width: cssWidth,
							height: cssHeight
						});
					});

					var attributes = {
						src: '%2',
						id: _.frameId,
						frameborder: 0,
						allowtransparency: true
					};
					var myHtml = [];

					if ( typeof( elementDefinition.onContentLoad ) == 'function' )
						attributes.onload = 'CKEDITOR.tools.callFunction(%1);';

					CKEDITOR.ui.dialog.uiElement.call( this, dialog, elementDefinition, myHtml, 'iframe', {
						width: cssWidth,
						height: cssHeight
					}, attributes, '' );

					// Put a placeholder for the first time.
					htmlList.push( '<div style="width:' + cssWidth + ';height:' + cssHeight + ';" id="' + this.domId + '"></div>' );

					// Iframe elements should be refreshed whenever it is shown.
					myHtml = myHtml.join( '' );
					dialog.on( 'show', function() {
						var iframe = CKEDITOR.document.getById( _.frameId ),
							parentContainer = iframe.getParent(),
							callIndex = CKEDITOR.tools.addFunction( contentLoad ),
							html = myHtml.replace( '%1', callIndex ).replace( '%2', CKEDITOR.tools.htmlEncode( elementDefinition.src ) );
						parentContainer.setHtml( html );
					});
				};

			iframeElement.prototype = new CKEDITOR.ui.dialog.uiElement;

			CKEDITOR.dialog.addUIElement( 'iframe', {
				build: function( dialog, elementDefinition, output ) {
					return new iframeElement( dialog, elementDefinition, output );
				}
			});
		})();
	}
});
