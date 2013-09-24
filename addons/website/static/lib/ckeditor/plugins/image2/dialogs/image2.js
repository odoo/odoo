/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.html or http://ckeditor.com/license
 */

'use strict';

CKEDITOR.dialog.add( 'image2', function( editor ) {

	// RegExp: 123, 123px, empty string ""
	var regexGetSizeOrEmpty = /(^\s*(\d+)(px)?\s*$)|^$/i,

		lockButtonId = CKEDITOR.tools.getNextId(),
		resetButtonId = CKEDITOR.tools.getNextId(),

		lang = editor.lang.image2,
		commonLang = editor.lang.common,

		lockResetStyle = 'margin-top:18px;width:40px;height:20px;',
		lockResetHtml = new CKEDITOR.template(
			'<div>' +
				'<a href="javascript:void(0)" tabindex="-1" title="' + lang.lockRatio + '" class="cke_btn_locked" id="{lockButtonId}" role="checkbox">' +
					'<span class="cke_icon"></span>' +
					'<span class="cke_label">' + lang.lockRatio + '</span>' +
				'</a>' +

				'<a href="javascript:void(0)" tabindex="-1" title="' + lang.resetSize + '" class="cke_btn_reset" id="{resetButtonId}" role="button">' +
					'<span class="cke_label">' + lang.resetSize + '</span>' +
				'</a>' +
			'</div>' ).output( {
				lockButtonId: lockButtonId,
				resetButtonId: resetButtonId
			} ),

		// Global variables referring to the dialog's context.
		doc, widget, image,

		// Global variable referring to this dialog's image pre-loader.
		preLoader,

		// Global variables holding the original size of the image.
		domWidth, domHeight,

		// Global variables related to image pre-loading.
		preLoadedWidth, preLoadedHeight, srcChanged,

		// Global variables related to size locking.
		lockRatio, userDefinedLock,

		// Global variables referring to dialog fields and elements.
		lockButton, resetButton, widthField, heightField;

	// Validates dimension. Allowed values are:
	// "123px", "123", "" (empty string)
	function validateDimension() {
		var match = this.getValue().match( regexGetSizeOrEmpty ),
			isValid = !!( match && parseInt( match[ 1 ], 10 ) !== 0 );

		if ( !isValid )
			alert( commonLang[ 'invalid' + CKEDITOR.tools.capitalize( this.id ) ] );

		return isValid;
	}

	// Creates a function that pre-loads images. The callback function passes
	// [image, width, height] or null if loading failed.
	//
	// @returns {Function}
	function createPreLoader() {
		var image = doc.createElement( 'img' ),
			listeners = [];

		function addListener( event, callback ) {
			listeners.push( image.once( event, function( evt ) {
				removeListeners();
				callback( evt );
			} ) );
		}

		function removeListeners() {
			var l;

			while ( ( l = listeners.pop() ) )
				l.removeListener();
		}

		// @param {String} src.
		// @param {Function} callback.
		return function( src, callback, scope ) {
			addListener( 'load', function() {
				callback.call( scope, image, image.$.width, image.$.height );
			} );

			addListener( 'error', function() {
				callback( null );
			} );

			addListener( 'abort', function() {
				callback( null );
			} );

			image.setAttribute( 'src', src + '?' + Math.random().toString( 16 ).substring( 2 ) );
		};
	}

	function onChangeDimension() {
		// If ratio is un-locked, then we don't care what's next.
		if ( !lockRatio )
			return;

		var value = this.getValue();

		// No reason to auto-scale or unlock if the field is empty.
		if ( !value )
			return;

		// If the value of the field is invalid (e.g. with %), unlock ratio.
		if ( !value.match( regexGetSizeOrEmpty ) )
			toggleLockDimensions( false );

		// No automatic re-scale when dimension is '0'.
		if ( value === '0' )
			return;

		var isWidth = this.id == 'width',
			// If dialog opened for the new image, domWidth and domHeight
			// will be empty. Use dimensions from pre-loader in such case instead.
			width = domWidth || preLoadedWidth,
			height = domHeight || preLoadedHeight;

		// If changing width, then auto-scale height.
		if ( isWidth )
			value = Math.round( height * ( value / width ) );

		// If changing height, then auto-scale width.
		else
			value = Math.round( width * ( value / height ) );

		// If the value is a number, apply it to the other field.
		if ( !isNaN( value ) )
			( isWidth ? heightField : widthField ).setValue( value );
	}

	// Set-up function for lock and reset buttons:
	// 	* Adds lock and reset buttons to focusables. Check if button exist first
	// 	  because it may be disabled e.g. due to ACF restrictions.
	// 	* Register mouseover and mouseout event listeners for UI manipulations.
	// 	* Register click event listeners for buttons.
	function onLoadLockReset() {
		var dialog = this.getDialog();

		function setupMouseClasses( el ) {
			el.on( 'mouseover', function() {
				this.addClass( 'cke_btn_over' );
			}, el );

			el.on( 'mouseout', function() {
				this.removeClass( 'cke_btn_over' );
			}, el );
		}

		// Create references to lock and reset buttons for this dialog instance.
		lockButton = doc.getById( lockButtonId );
		resetButton = doc.getById( resetButtonId );

		// Activate (Un)LockRatio button
		if ( lockButton ) {
			dialog.addFocusable( lockButton, 4 );

			lockButton.on( 'click', function( evt ) {
				toggleLockDimensions();
				evt.data && evt.data.preventDefault();
			}, this.getDialog() );

			setupMouseClasses( lockButton );
		}

		// Activate the reset size button.
		if ( resetButton ) {
			dialog.addFocusable( resetButton, 5 );

			// Fills width and height fields with the original dimensions of the
			// image (stored in widget#data since widget#init).
			resetButton.on( 'click', function( evt ) {
				// If there's a new image loaded, reset button should revert
				// cached dimensions of pre-loaded DOM element.
				if ( srcChanged ) {
					widthField.setValue( preLoadedWidth );
					heightField.setValue( preLoadedHeight );
				}

				// If the old image remains, reset button should revert
				// dimensions as loaded when the dialog was first shown.
				else {
					widthField.setValue( domWidth );
					heightField.setValue( domHeight );
				}

				evt.data && evt.data.preventDefault();
			}, this );

			setupMouseClasses( resetButton );
		}
	}

	function toggleLockDimensions( enable ) {
		// No locking if there's no radio (i.e. due to ACF).
		if ( !lockButton )
			return;

		var width, height;

		// Check image ratio and original image ratio, but respecting user's
		// preference. This is performed when a new image is pre-loaded
		// but not if user already manually locked the ratio.
		if ( enable == 'check' && !userDefinedLock ) {
			width = widthField.getValue();
			height = heightField.getValue();

			var	domRatio = preLoadedWidth * 1000 / preLoadedHeight,
				ratio = width * 1000 / height;

			lockRatio = false;

			// Lock ratio, if there is no width and no height specified.
			if ( !width && !height )
				lockRatio = true;

			// Lock ratio if there is at least width or height specified,
			// and the old ratio that matches the new one.
			else if ( !isNaN( domRatio + ratio ) && Math.round( domRatio ) == Math.round( ratio ) )
				lockRatio = true;
		}

		// True or false.
		else if ( typeof enable == 'boolean' )
			lockRatio = enable;

		// Undefined. User changed lock value.
		else {
			userDefinedLock = true;
			lockRatio = !lockRatio;

			width = widthField.getValue();

			// Automatically adjust height to width to match
			// the original ratio (based on dom- dimensions).
			if ( lockRatio && width ) {
				height = domHeight / domWidth * width;

				if ( !isNaN( height ) )
					heightField.setValue( Math.round( height ) );
			}
		}

		lockButton[ lockRatio ? 'removeClass' : 'addClass' ]( 'cke_btn_unlocked' );
		lockButton.setAttribute( 'aria-checked', lockRatio );

		// Ratio button hc presentation - WHITE SQUARE / BLACK SQUARE
		if ( CKEDITOR.env.hc ) {
			var icon = lockButton.getChild( 0 );
			icon.setHtml( lockRatio ? CKEDITOR.env.ie ? '\u25A0' : '\u25A3' : CKEDITOR.env.ie ? '\u25A1' : '\u25A2' );
		}
	}

	function toggleDimensions( enable ) {
		var method = enable ? 'enable' : 'disable';

		widthField[ method ]();
		heightField[ method ]();
	}

	return {
		title: lang.title,
		minWidth: 250,
		minHeight: 100,
		onLoad: function() {
			// Create a "global" reference to the document for this dialog instance.
			doc = this._.element.getDocument();

			// Create a pre-loader used for determining dimensions of new images.
			preLoader = createPreLoader();
		},
		onShow: function() {
			// Create a "global" reference to edited widget.
			widget = this._.widget;

			// Create a "global" reference to widget's image.
			image = widget.parts.image;

			// Reset global variables.
			preLoadedWidth = preLoadedHeight = srcChanged =
				userDefinedLock = lockRatio = false;

			// TODO: IE8
			// Get the natural width of the image.
			domWidth = image.$.naturalWidth;

			// TODO: IE8
			// Get the natural height of the image.
			domHeight = image.$.naturalHeight;

			// Determine image ratio lock on startup. Delayed, waiting for
			// fields to be filled with setup functions.
			setTimeout( function() {
				toggleLockDimensions( 'check' );
			} );
		},
		contents: [
			{
				id: 'info',
				elements: [
					{
						id: 'src',
						type: 'text',
						label: commonLang.url,
						onKeyup: function() {
							var value = this.getValue();

							toggleDimensions( false );

							// Remember that src is different than default.
							if ( value !== widget.data.src ) {
								// Update dimensions of the image once it's preloaded.
								preLoader( value, function( image, width, height ) {
									// Re-enable width and height fields.
									toggleDimensions( true );

									// There was problem loading the image. Unlock ratio.
									if ( !image )
										return toggleLockDimensions( false );

									// Fill width field with the width of the new image.
									widthField.setValue( width );

									// Fill height field with the height of the new image.
									heightField.setValue( height );

									// Cache the new width.
									preLoadedWidth = width;

									// Cache the new height.
									preLoadedHeight = height;

									// Check for new lock value if image exist.
									toggleLockDimensions( 'check' );
								} );

								srcChanged = true;
							}

							// Value is the same as in widget data but is was
							// modified back in time. Roll back dimensions when restoring
							// default src.
							else if ( srcChanged ) {
								// Re-enable width and height fields.
								toggleDimensions( true );

								// Restore width field with cached width.
								widthField.setValue( domWidth );

								// Restore height field with cached height.
								heightField.setValue( domHeight );

								// Src equals default one back again.
								srcChanged = false;
							}

							// Value is the same as in widget data and it hadn't
							// been modified.
							else {
								// Re-enable width and height fields.
								toggleDimensions( true );
							}
						},
						setup: function( widget ) {
							this.setValue( widget.data.src );
						},
						commit: function( widget ) {
							widget.setData( 'src', this.getValue() );
						},
						validate: CKEDITOR.dialog.validate.notEmpty( lang.urlMissing )
					},
					{
						id: 'alt',
						type: 'text',
						label: lang.alt,
						setup: function( widget ) {
							this.setValue( widget.data.alt );
						},
						commit: function( widget ) {
							widget.setData( 'alt', this.getValue() );
						}
					},
					{
						type: 'hbox',
						widths: [ '25%', '25%', '50%' ],
						requiredContent: 'img[width,height]',
						children: [
							{
								type: 'text',
								width: '45px',
								id: 'width',
								label: commonLang.width,
								validate: validateDimension,
								onKeyUp: onChangeDimension,
								onLoad: function() {
									widthField = this;
								},
								setup: function( widget ) {
									this.setValue( widget.data.width );
								},
								commit: function( widget ) {
									widget.setData( 'width', this.getValue() );
								}
							},
							{
								type: 'text',
								id: 'height',
								width: '45px',
								label: commonLang.height,
								validate: validateDimension,
								onKeyUp: onChangeDimension,
								onLoad: function() {
									heightField = this;
								},
								setup: function( widget ) {
									this.setValue( widget.data.height );
								},
								commit: function( widget ) {
									widget.setData( 'height', this.getValue() );
								}
							},
							{
								id: 'lock',
								type: 'html',
								style: lockResetStyle,
								onLoad: onLoadLockReset,
								html: lockResetHtml
							}
						]
					},
					{
						type: 'hbox',
						id: 'alignment',
						children: [
							{
								id: 'align',
								type: 'radio',
								items: [
									[ 'None', 'none' ],
									[ 'Left', 'left' ],
									[ 'Center', 'center' ],
									[ 'Right', 'right' ] ],
								label: commonLang.align,
								setup: function( widget ) {
									this.setValue( widget.data.align );
								},
								commit: function( widget ) {
									widget.setData( 'align', this.getValue() );
								}
							}
						]
					},
					{
						id: 'hasCaption',
						type: 'checkbox',
						label: lang.captioned,
						setup: function( widget ) {
							this.setValue( widget.data.hasCaption );
						},
						commit: function( widget ) {
							widget.setData( 'hasCaption', this.getValue() );
						}
					}
				]
			}
		]
	};
} );