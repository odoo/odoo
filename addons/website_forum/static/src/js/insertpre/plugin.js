/*
 Copyright (c) 2003-2012, CKSource - Frederico Knabben. All rights reserved.
 For licensing, see LICENSE.html or http://ckeditor.com/license
*/
// Add Extra Plugin seprated by comma sign
CKEDITOR.config.extraPlugins = 'insertpre';

var plugin_path = window.location.protocol + "//" + window.location.hostname + (window.location.port ? ':' + window.location.port: '') + '/website_forum/static/src/js/insertpre/';

CKEDITOR.plugins.add( 'insertpre',
	{
		requires: 'dialog',
		icons: plugin_path + 'icons/insertpre-color.png', // %REMOVE_LINE_CORE%
		onLoad : function()
		{
			if ( CKEDITOR.config.insertpre_class )
			{
				CKEDITOR.addCss(
					'pre.' + CKEDITOR.config.insertpre_class + ' {' +
						CKEDITOR.config.insertpre_style +
						'}'
				);
			}
		},
		init : function( editor )
		{
			// allowed and required content is the same for this plugin
			var required = CKEDITOR.config.insertpre_class ? ( 'pre( ' + CKEDITOR.config.insertpre_class + ' )' ) : 'pre';
			editor.addCommand( 'insertpre', new CKEDITOR.dialogCommand( 'insertpre', {
				allowedContent : required,
				requiredContent : required
			} ) );
			editor.ui.addButton && editor.ui.addButton( 'InsertPre',
				{
					label : 'Insert code snippet',
					icon : plugin_path + 'icons/insertpre-color.png',
					command : 'insertpre',
					toolbar: 'insert,99'
				} );

			if ( editor.contextMenu )
			{
				editor.addMenuGroup( 'code' );
				editor.addMenuItem( 'insertpre',
					{
						label : 'Edit code',
						icon : plugin_path + 'icons/insertpre-color.png',
						command : 'insertpre',
						group : 'code'
					});
				editor.contextMenu.addListener( function( element )
				{
					if ( element )
						element = element.getAscendant( 'pre', true );
					if ( element && !element.isReadOnly() && element.hasClass( editor.config.insertpre_class ) )
						return { insertpre : CKEDITOR.TRISTATE_OFF };
					return null;
				});
			}

			CKEDITOR.dialog.add( 'insertpre', function( editor )
			{
				return {
					title : 'Insert code snippet',
					minWidth : 540,
					minHeight : 380,
					contents : [
						{
							id : 'general',
							label : 'Code',
							elements : [
								{
									type : 'textarea',
									id : 'contents',
									label : 'Code',
									cols: 140,
									rows: 22,
									validate : CKEDITOR.dialog.validate.notEmpty( 'The code field cannot be empty.' ),
									required : true,
									setup : function( element )
									{
										var html = element.getHtml();
										if ( html )
										{
											var div = document.createElement( 'div' );
											div.innerHTML = html;
											this.setValue( div.firstChild.nodeValue );
										}
									},
									commit : function( element )
									{
										element.setHtml( CKEDITOR.tools.htmlEncode( this.getValue() ) );
									}
								}
							]
						}
					],
					onShow : function()
					{
						var sel = editor.getSelection(),
							element = sel.getStartElement();
						if ( element )
							element = element.getAscendant( 'pre', true );

						if ( !element || element.getName() != 'pre' || !element.hasClass( editor.config.insertpre_class ) )
						{
							element = editor.document.createElement( 'pre' );
							this.insertMode = true;
						}
						else
							this.insertMode = false;

						this.pre = element;
						this.setupContent( this.pre );
					},
					onOk : function()
					{
						if ( editor.config.insertpre_class )
							this.pre.setAttribute( 'class', editor.config.insertpre_class );

						if ( this.insertMode )
							editor.insertElement( this.pre );

						this.commitContent( this.pre );
					}
				};
			} );
		}
	} );

if (typeof(CKEDITOR.config.insertpre_style) == 'undefined')
	CKEDITOR.config.insertpre_style = 'background-color:#F8F8F8;border:1px solid #DDD;padding:10px;';
if (typeof(CKEDITOR.config.insertpre_class)  == 'undefined')
	CKEDITOR.config.insertpre_class = 'prettyprint';