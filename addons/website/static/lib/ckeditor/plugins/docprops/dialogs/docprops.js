/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

CKEDITOR.dialog.add( 'docProps', function( editor ) {
	var lang = editor.lang.docprops,
		langCommon = editor.lang.common,
		metaHash = {};

	function getDialogValue( dialogName, callback ) {
		var onOk = function() {
				releaseHandlers( this );
				callback( this, this._.parentDialog );
			};
		var releaseHandlers = function( dialog ) {
				dialog.removeListener( 'ok', onOk );
				dialog.removeListener( 'cancel', releaseHandlers );
			};
		var bindToDialog = function( dialog ) {
				dialog.on( 'ok', onOk );
				dialog.on( 'cancel', releaseHandlers );
			};
		editor.execCommand( dialogName );
		if ( editor._.storedDialogs.colordialog )
			bindToDialog( editor._.storedDialogs.colordialog );
		else {
			CKEDITOR.on( 'dialogDefinition', function( e ) {
				if ( e.data.name != dialogName )
					return;

				var definition = e.data.definition;

				e.removeListener();
				definition.onLoad = CKEDITOR.tools.override( definition.onLoad, function( orginal ) {
					return function() {
						bindToDialog( this );
						definition.onLoad = orginal;
						if ( typeof orginal == 'function' )
							orginal.call( this );
					};
				});
			});
		}
	}

	function handleOther() {
		var dialog = this.getDialog(),
			other = dialog.getContentElement( 'general', this.id + 'Other' );
		if ( !other )
			return;
		if ( this.getValue() == 'other' ) {
			other.getInputElement().removeAttribute( 'readOnly' );
			other.focus();
			other.getElement().removeClass( 'cke_disabled' );
		} else {
			other.getInputElement().setAttribute( 'readOnly', true );
			other.getElement().addClass( 'cke_disabled' );
		}
	}

	function commitMeta( name, isHttp, value ) {
		return function( doc, html, head ) {
			var hash = metaHash,
				val = typeof value != 'undefined' ? value : this.getValue();
			if ( !val && ( name in hash ) )
				hash[ name ].remove();
			else if ( val && ( name in hash ) )
				hash[ name ].setAttribute( 'content', val );
			else if ( val ) {
				var meta = new CKEDITOR.dom.element( 'meta', editor.document );
				meta.setAttribute( isHttp ? 'http-equiv' : 'name', name );
				meta.setAttribute( 'content', val );
				head.append( meta );
			}
		};
	}

	function setupMeta( name, ret ) {
		return function() {
			var hash = metaHash,
				result = ( name in hash ) ? hash[ name ].getAttribute( 'content' ) || '' : '';
			if ( ret )
				return result;
			this.setValue( result );
			return null;
		};
	}

	function commitMargin( name ) {
		return function( doc, html, head, body ) {
			body.removeAttribute( 'margin' + name );
			var val = this.getValue();
			if ( val !== '' )
				body.setStyle( 'margin-' + name, CKEDITOR.tools.cssLength( val ) );
			else
				body.removeStyle( 'margin-' + name );
		};
	}

	function createMetaHash( doc ) {
		var hash = {},
			metas = doc.getElementsByTag( 'meta' ),
			count = metas.count();

		for ( var i = 0; i < count; i++ ) {
			var meta = metas.getItem( i );
			hash[ meta.getAttribute( meta.hasAttribute( 'http-equiv' ) ? 'http-equiv' : 'name' ).toLowerCase() ] = meta;
		}
		return hash;
	}
	// We cannot just remove the style from the element, as it might be affected from non-inline stylesheets.
	// To get the proper result, we should manually set the inline style to its default value.
	function resetStyle( element, prop, resetVal ) {
		element.removeStyle( prop );
		if ( element.getComputedStyle( prop ) != resetVal )
			element.setStyle( prop, resetVal );
	}

	// Utilty to shorten the creation of color fields in the dialog.
	var colorField = function( id, label, fieldProps ) {
			return {
				type: 'hbox',
				padding: 0,
				widths: [ '60%', '40%' ],
				children: [
					CKEDITOR.tools.extend({
					type: 'text',
					id: id,
					label: lang[ label ]
				}, fieldProps || {}, 1 ),
				{
					type: 'button',
					id: id + 'Choose',
					label: lang.chooseColor,
					className: 'colorChooser',
					onClick: function() {
						var self = this;
						getDialogValue( 'colordialog', function( colorDialog ) {
							var dialog = self.getDialog();
							dialog.getContentElement( dialog._.currentTabId, id ).setValue( colorDialog.getContentElement( 'picker', 'selectedColor' ).getValue() );
						});
					}
				}
				]
			};
		};
	var previewSrc = 'javascript:' +
		'void((function(){' + encodeURIComponent(
			'document.open();' +
			( CKEDITOR.env.ie ? '(' + CKEDITOR.tools.fixDomain + ')();' : '' ) +
			'document.write( \'<html style="background-color: #ffffff; height: 100%"><head></head><body style="width: 100%; height: 100%; margin: 0px">' + lang.previewHtml + '</body></html>\' );' +
			'document.close();'
		) + '})())';

	return {
		title: lang.title,
		minHeight: 330,
		minWidth: 500,
		onShow: function() {
			var doc = editor.document,
				html = doc.getElementsByTag( 'html' ).getItem( 0 ),
				head = doc.getHead(),
				body = doc.getBody();
			metaHash = createMetaHash( doc );
			this.setupContent( doc, html, head, body );
		},
		onHide: function() {
			metaHash = {};
		},
		onOk: function() {
			var doc = editor.document,
				html = doc.getElementsByTag( 'html' ).getItem( 0 ),
				head = doc.getHead(),
				body = doc.getBody();
			this.commitContent( doc, html, head, body );
		},
		contents: [
			{
			id: 'general',
			label: langCommon.generalTab,
			elements: [
				{
				type: 'text',
				id: 'title',
				label: lang.docTitle,
				setup: function( doc ) {
					this.setValue( doc.getElementsByTag( 'title' ).getItem( 0 ).data( 'cke-title' ) );
				},
				commit: function( doc, html, head, body, isPreview ) {
					if ( isPreview )
						return;
					doc.getElementsByTag( 'title' ).getItem( 0 ).data( 'cke-title', this.getValue() );
				}
			},
				{
				type: 'hbox',
				children: [
					{
					type: 'select',
					id: 'dir',
					label: langCommon.langDir,
					style: 'width: 100%',
					items: [
						[ langCommon.notSet, '' ],
						[ langCommon.langDirLtr, 'ltr' ],
						[ langCommon.langDirRtl, 'rtl' ]
						],
					setup: function( doc, html, head, body ) {
						this.setValue( body.getDirection() || '' );
					},
					commit: function( doc, html, head, body ) {
						var val = this.getValue();
						if ( val )
							body.setAttribute( 'dir', val );
						else
							body.removeAttribute( 'dir' );
						body.removeStyle( 'direction' );
					}
				},
					{
					type: 'text',
					id: 'langCode',
					label: langCommon.langCode,
					setup: function( doc, html ) {
						this.setValue( html.getAttribute( 'xml:lang' ) || html.getAttribute( 'lang' ) || '' );
					},
					commit: function( doc, html, head, body, isPreview ) {
						if ( isPreview )
							return;
						var val = this.getValue();
						if ( val )
							html.setAttributes({ 'xml:lang': val, lang: val } );
						else
							html.removeAttributes( { 'xml:lang':1,lang:1 } );
					}
				}
				]
			},
				{
				type: 'hbox',
				children: [
					{
					type: 'select',
					id: 'charset',
					label: lang.charset,
					style: 'width: 100%',
					items: [
						[ langCommon.notSet, '' ],
						[ lang.charsetASCII, 'us-ascii' ],
						[ lang.charsetCE, 'iso-8859-2' ],
						[ lang.charsetCT, 'big5' ],
						[ lang.charsetCR, 'iso-8859-5' ],
						[ lang.charsetGR, 'iso-8859-7' ],
						[ lang.charsetJP, 'iso-2022-jp' ],
						[ lang.charsetKR, 'iso-2022-kr' ],
						[ lang.charsetTR, 'iso-8859-9' ],
						[ lang.charsetUN, 'utf-8' ],
						[ lang.charsetWE, 'iso-8859-1' ],
						[ lang.other, 'other' ]
						],
					'default': '',
					onChange: function() {
						this.getDialog().selectedCharset = this.getValue() != 'other' ? this.getValue() : '';
						handleOther.call( this );
					},
					setup: function() {
						this.metaCharset = ( 'charset' in metaHash );

						var func = setupMeta( this.metaCharset ? 'charset' : 'content-type', 1, 1 ),
							val = func.call( this );

						!this.metaCharset && val.match( /charset=[^=]+$/ ) && ( val = val.substring( val.indexOf( '=' ) + 1 ) );

						if ( val ) {
							this.setValue( val.toLowerCase() );
							if ( !this.getValue() ) {
								this.setValue( 'other' );
								var other = this.getDialog().getContentElement( 'general', 'charsetOther' );
								other && other.setValue( val );
							}
							this.getDialog().selectedCharset = val;
						}

						handleOther.call( this );
					},
					commit: function( doc, html, head, body, isPreview ) {
						if ( isPreview )
							return;
						var value = this.getValue(),
							other = this.getDialog().getContentElement( 'general', 'charsetOther' );

						value == 'other' && ( value = other ? other.getValue() : '' );

						value && !this.metaCharset && ( value = ( metaHash[ 'content-type' ] ? metaHash[ 'content-type' ].getAttribute( 'content' ).split( ';' )[ 0 ] : 'text/html' ) + '; charset=' + value );

						var func = commitMeta( this.metaCharset ? 'charset' : 'content-type', 1, value );
						func.call( this, doc, html, head );
					}
				},
					{
					type: 'text',
					id: 'charsetOther',
					label: lang.charsetOther,
					onChange: function() {
						this.getDialog().selectedCharset = this.getValue();
					}
				}
				]
			},
				{
				type: 'hbox',
				children: [
					{
					type: 'select',
					id: 'docType',
					label: lang.docType,
					style: 'width: 100%',
					items: [
						[ langCommon.notSet, '' ],
						[ 'XHTML 1.1', '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">' ],
						[ 'XHTML 1.0 Transitional', '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">' ],
						[ 'XHTML 1.0 Strict', '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">' ],
						[ 'XHTML 1.0 Frameset', '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd">' ],
						[ 'HTML 5', '<!DOCTYPE html>' ],
						[ 'HTML 4.01 Transitional', '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">' ],
						[ 'HTML 4.01 Strict', '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">' ],
						[ 'HTML 4.01 Frameset', '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN" "http://www.w3.org/TR/html4/frameset.dtd">' ],
						[ 'HTML 3.2', '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">' ],
						[ 'HTML 2.0', '<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">' ],
						[ lang.other, 'other' ]
						],
					onChange: handleOther,
					setup: function() {
						if ( editor.docType ) {
							this.setValue( editor.docType );
							if ( !this.getValue() ) {
								this.setValue( 'other' );
								var other = this.getDialog().getContentElement( 'general', 'docTypeOther' );
								other && other.setValue( editor.docType );
							}
						}
						handleOther.call( this );
					},
					commit: function( doc, html, head, body, isPreview ) {
						if ( isPreview )
							return;
						var value = this.getValue(),
							other = this.getDialog().getContentElement( 'general', 'docTypeOther' );
						editor.docType = value == 'other' ? ( other ? other.getValue() : '' ) : value;
					}
				},
					{
					type: 'text',
					id: 'docTypeOther',
					label: lang.docTypeOther
				}
				]
			},
				{
				type: 'checkbox',
				id: 'xhtmlDec',
				label: lang.xhtmlDec,
				setup: function() {
					this.setValue( !!editor.xmlDeclaration );
				},
				commit: function( doc, html, head, body, isPreview ) {
					if ( isPreview )
						return;
					if ( this.getValue() ) {
						editor.xmlDeclaration = '<?xml version="1.0" encoding="' + ( this.getDialog().selectedCharset || 'utf-8' ) + '"?>';
						html.setAttribute( 'xmlns', 'http://www.w3.org/1999/xhtml' );
					} else {
						editor.xmlDeclaration = '';
						html.removeAttribute( 'xmlns' );
					}
				}
			}
			]
		},
			{
			id: 'design',
			label: lang.design,
			elements: [
				{
				type: 'hbox',
				widths: [ '60%', '40%' ],
				children: [
					{
					type: 'vbox',
					children: [
						colorField( 'txtColor', 'txtColor', {
						setup: function( doc, html, head, body ) {
							this.setValue( body.getComputedStyle( 'color' ) );
						},
						commit: function( doc, html, head, body, isPreview ) {
							if ( this.isChanged() || isPreview ) {
								body.removeAttribute( 'text' );
								var val = this.getValue();
								if ( val )
									body.setStyle( 'color', val );
								else
									body.removeStyle( 'color' );
							}
						}
					}),
						colorField( 'bgColor', 'bgColor', {
						setup: function( doc, html, head, body ) {
							var val = body.getComputedStyle( 'background-color' ) || '';
							this.setValue( val == 'transparent' ? '' : val );
						},
						commit: function( doc, html, head, body, isPreview ) {
							if ( this.isChanged() || isPreview ) {
								body.removeAttribute( 'bgcolor' );
								var val = this.getValue();
								if ( val )
									body.setStyle( 'background-color', val );
								else
									resetStyle( body, 'background-color', 'transparent' );
							}
						}
					}),
					{
						type: 'hbox',
						widths: [ '60%', '40%' ],
						padding: 1,
						children: [
							{
							type: 'text',
							id: 'bgImage',
							label: lang.bgImage,
							setup: function( doc, html, head, body ) {
								var val = body.getComputedStyle( 'background-image' ) || '';
								if ( val == 'none' )
									val = '';
								else {
									val = val.replace( /url\(\s*(["']?)\s*([^\)]*)\s*\1\s*\)/i, function( match, quote, url ) {
										return url;
									});
								}
								this.setValue( val );
							},
							commit: function( doc, html, head, body ) {
								body.removeAttribute( 'background' );
								var val = this.getValue();
								if ( val )
									body.setStyle( 'background-image', 'url(' + val + ')' );
								else
									resetStyle( body, 'background-image', 'none' );
							}
						},
							{
							type: 'button',
							id: 'bgImageChoose',
							label: langCommon.browseServer,
							style: 'display:inline-block;margin-top:10px;',
							hidden: true,
							filebrowser: 'design:bgImage'
						}
						]
					},
						{
						type: 'checkbox',
						id: 'bgFixed',
						label: lang.bgFixed,
						setup: function( doc, html, head, body ) {
							this.setValue( body.getComputedStyle( 'background-attachment' ) == 'fixed' );
						},
						commit: function( doc, html, head, body ) {
							if ( this.getValue() )
								body.setStyle( 'background-attachment', 'fixed' );
							else
								resetStyle( body, 'background-attachment', 'scroll' );
						}
					}
					]
				},
					{
					type: 'vbox',
					children: [
						{
						type: 'html',
						id: 'marginTitle',
						html: '<div style="text-align: center; margin: 0px auto; font-weight: bold">' + lang.margin + '</div>'
					},
						{
						type: 'text',
						id: 'marginTop',
						label: lang.marginTop,
						style: 'width: 80px; text-align: center',
						align: 'center',
						inputStyle: 'text-align: center',
						setup: function( doc, html, head, body ) {
							this.setValue( body.getStyle( 'margin-top' ) || body.getAttribute( 'margintop' ) || '' );
						},
						commit: commitMargin( 'top' )
					},
						{
						type: 'hbox',
						children: [
							{
							type: 'text',
							id: 'marginLeft',
							label: lang.marginLeft,
							style: 'width: 80px; text-align: center',
							align: 'center',
							inputStyle: 'text-align: center',
							setup: function( doc, html, head, body ) {
								this.setValue( body.getStyle( 'margin-left' ) || body.getAttribute( 'marginleft' ) || '' );
							},
							commit: commitMargin( 'left' )
						},
							{
							type: 'text',
							id: 'marginRight',
							label: lang.marginRight,
							style: 'width: 80px; text-align: center',
							align: 'center',
							inputStyle: 'text-align: center',
							setup: function( doc, html, head, body ) {
								this.setValue( body.getStyle( 'margin-right' ) || body.getAttribute( 'marginright' ) || '' );
							},
							commit: commitMargin( 'right' )
						}
						]
					},
						{
						type: 'text',
						id: 'marginBottom',
						label: lang.marginBottom,
						style: 'width: 80px; text-align: center',
						align: 'center',
						inputStyle: 'text-align: center',
						setup: function( doc, html, head, body ) {
							this.setValue( body.getStyle( 'margin-bottom' ) || body.getAttribute( 'marginbottom' ) || '' );
						},
						commit: commitMargin( 'bottom' )
					}
					]
				}
				]
			}
			]
		},
			{
			id: 'meta',
			label: lang.meta,
			elements: [
				{
				type: 'textarea',
				id: 'metaKeywords',
				label: lang.metaKeywords,
				setup: setupMeta( 'keywords' ),
				commit: commitMeta( 'keywords' )
			},
				{
				type: 'textarea',
				id: 'metaDescription',
				label: lang.metaDescription,
				setup: setupMeta( 'description' ),
				commit: commitMeta( 'description' )
			},
				{
				type: 'text',
				id: 'metaAuthor',
				label: lang.metaAuthor,
				setup: setupMeta( 'author' ),
				commit: commitMeta( 'author' )
			},
				{
				type: 'text',
				id: 'metaCopyright',
				label: lang.metaCopyright,
				setup: setupMeta( 'copyright' ),
				commit: commitMeta( 'copyright' )
			}
			]
		},
			{
			id: 'preview',
			label: langCommon.preview,
			elements: [
				{
				type: 'html',
				id: 'previewHtml',
				html: '<iframe src="' + previewSrc + '" style="width: 100%; height: 310px" hidefocus="true" frameborder="0" ' +
					'id="cke_docProps_preview_iframe"></iframe>',
				onLoad: function() {
					this.getDialog().on( 'selectPage', function( ev ) {
						if ( ev.data.page == 'preview' ) {
							var self = this;
							setTimeout( function() {
								var doc = CKEDITOR.document.getById( 'cke_docProps_preview_iframe' ).getFrameDocument(),
									html = doc.getElementsByTag( 'html' ).getItem( 0 ),
									head = doc.getHead(),
									body = doc.getBody();
								self.commitContent( doc, html, head, body, 1 );
							}, 50 );
						}
					});
					CKEDITOR.document.getById( 'cke_docProps_preview_iframe' ).getAscendant( 'table' ).setStyle( 'height', '100%' );
				}
			}
			]
		}
		]
	};
});
