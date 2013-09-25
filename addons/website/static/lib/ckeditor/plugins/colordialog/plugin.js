/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

CKEDITOR.plugins.colordialog = {
	requires: 'dialog',
	lang: 'af,ar,bg,bn,bs,ca,cs,cy,da,de,el,en,en-au,en-ca,en-gb,eo,es,et,eu,fa,fi,fo,fr,fr-ca,gl,gu,he,hi,hr,hu,is,it,ja,ka,km,ko,ku,lt,lv,mk,mn,ms,nb,nl,no,pl,pt,pt-br,ro,ru,si,sk,sl,sq,sr,sr-latn,sv,th,tr,ug,uk,vi,zh,zh-cn', // %REMOVE_LINE_CORE%
	init: function( editor ) {
		editor.addCommand( 'colordialog', new CKEDITOR.dialogCommand( 'colordialog' ) );
		CKEDITOR.dialog.add( 'colordialog', this.path + 'dialogs/colordialog.js' );

		/**
		 * Open up color dialog and to receive the selected color.
		 *
		 * @param {Function} callback The callback when color dialog is closed
		 * @param {String} callback.color The color value received if selected on the dialog.
		 * @param [scope] The scope in which the callback will be bound.
		 * @member CKEDITOR.editor
		 */
		editor.getColorFromDialog = function( callback, scope ) {
			var onClose = function( evt ) {
				releaseHandlers( this );
				var color = evt.name == 'ok' ? this.getValueOf( 'picker', 'selectedColor' ) : null;
				callback.call( scope, color );
			};
			var releaseHandlers = function( dialog ) {
				dialog.removeListener( 'ok', onClose );
				dialog.removeListener( 'cancel', onClose );
			};
			var bindToDialog = function( dialog ) {
				dialog.on( 'ok', onClose );
				dialog.on( 'cancel', onClose );
			};

			editor.execCommand( 'colordialog' );

			if ( editor._.storedDialogs && editor._.storedDialogs.colordialog )
				bindToDialog( editor._.storedDialogs.colordialog );
			else {
				CKEDITOR.on( 'dialogDefinition', function( e ) {
					if ( e.data.name != 'colordialog' )
						return;

					var definition = e.data.definition;

					e.removeListener();
					definition.onLoad = CKEDITOR.tools.override( definition.onLoad,
						function( orginal ) {
							return function() {
								bindToDialog( this );
								definition.onLoad = orginal;
								if ( typeof orginal == 'function' )
									orginal.call( this );
							};
						} );
				} );
			}
		};


	}
};

CKEDITOR.plugins.add( 'colordialog', CKEDITOR.plugins.colordialog );
