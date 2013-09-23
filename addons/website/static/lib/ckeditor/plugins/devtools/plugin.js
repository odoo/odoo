/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

CKEDITOR.plugins.add( 'devtools', {
	lang: 'en,bg,cs,cy,da,de,el,eo,et,fa,fi,fr,gu,he,hr,it,ku,nb,nl,no,pl,tr,ug,uk,vi,zh-cn', // %REMOVE_LINE_CORE%

	init: function( editor ) {
		editor._.showDialogDefinitionTooltips = 1;
	},
	onLoad: function() {
		CKEDITOR.document.appendStyleText( CKEDITOR.config.devtools_styles || '#cke_tooltip { padding: 5px; border: 2px solid #333; background: #ffffff }' +
			'#cke_tooltip h2 { font-size: 1.1em; border-bottom: 1px solid; margin: 0; padding: 1px; }' +
			'#cke_tooltip ul { padding: 0pt; list-style-type: none; }' );
	}
});

(function() {
	function defaultCallback( editor, dialog, element, tabName ) {
		var lang = editor.lang.devtools,
			link = '<a href="http://docs.ckeditor.com/#!/api/CKEDITOR.dialog.definition.' +
			( element ? ( element.type == 'text' ? 'textInput' : element.type ) : 'content' ) +
			'" target="_blank">' + ( element ? element.type : 'content' ) + '</a>',
			str = '<h2>' + lang.title + '</h2>' +
			'<ul>' +
			'<li><strong>' + lang.dialogName + '</strong> : ' + dialog.getName() + '</li>' +
			'<li><strong>' + lang.tabName + '</strong> : ' + tabName + '</li>';

		if ( element )
			str += '<li><strong>' + lang.elementId + '</strong> : ' + element.id + '</li>';

		str += '<li><strong>' + lang.elementType + '</strong> : ' + link + '</li>';

		return str + '</ul>';
	}

	function showTooltip( callback, el, editor, dialog, obj, tabName ) {
		var pos = el.getDocumentPosition(),
			styles = { 'z-index': CKEDITOR.dialog._.currentZIndex + 10, top: ( pos.y + el.getSize( 'height' ) ) + 'px' };

		tooltip.setHtml( callback( editor, dialog, obj, tabName ) );
		tooltip.show();

		// Translate coordinate for RTL.
		if ( editor.lang.dir == 'rtl' ) {
			var viewPaneSize = CKEDITOR.document.getWindow().getViewPaneSize();
			styles.right = ( viewPaneSize.width - pos.x - el.getSize( 'width' ) ) + 'px';
		} else
			styles.left = pos.x + 'px';

		tooltip.setStyles( styles );
	}

	var tooltip;
	CKEDITOR.on( 'reset', function() {
		tooltip && tooltip.remove();
		tooltip = null;
	});

	CKEDITOR.on( 'dialogDefinition', function( evt ) {
		var editor = evt.editor;
		if ( editor._.showDialogDefinitionTooltips ) {
			if ( !tooltip ) {
				tooltip = CKEDITOR.dom.element.createFromHtml( '<div id="cke_tooltip" tabindex="-1" style="position: absolute"></div>', CKEDITOR.document );
				tooltip.hide();
				tooltip.on( 'mouseover', function() {
					this.show();
				});
				tooltip.on( 'mouseout', function() {
					this.hide();
				});
				tooltip.appendTo( CKEDITOR.document.getBody() );
			}

			var dialog = evt.data.definition.dialog,
				callback = editor.config.devtools_textCallback || defaultCallback;

			dialog.on( 'load', function() {
				var tabs = dialog.parts.tabs.getChildren(),
					tab;
				for ( var i = 0, len = tabs.count(); i < len; i++ ) {
					tab = tabs.getItem( i );
					tab.on( 'mouseover', function() {
						var id = this.$.id;
						showTooltip( callback, this, editor, dialog, null, id.substring( 4, id.lastIndexOf( '_' ) ) );
					});
					tab.on( 'mouseout', function() {
						tooltip.hide();
					});
				}

				dialog.foreach( function( obj ) {
					if ( obj.type in { hbox:1,vbox:1 } )
						return;

					var el = obj.getElement();
					if ( el ) {
						el.on( 'mouseover', function() {
							showTooltip( callback, this, editor, dialog, obj, dialog._.currentTabId );
						});
						el.on( 'mouseout', function() {
							tooltip.hide();
						});
					}
				});
			});
		}
	});
})();

/**
 * A function that returns the text to be displayed inside the Developer Tools
 * tooltip when hovering over a dialog UI element.
 *
 *		// This is actually the default value.
 *		// Show dialog window name, tab ID, and element ID.
 *		config.devtools_textCallback = function( editor, dialog, element, tabName ) {
 *			var lang = editor.lang.devtools,
 *				link = '<a href="http://docs.ckeditor.com/#!/api/CKEDITOR.dialog.definition.' +
 *					( element ? ( element.type == 'text' ? 'textInput' : element.type ) : 'content' ) +
 *					'.html" target="_blank">' + ( element ? element.type : 'content' ) + '</a>',
 *				str =
 *					'<h2>' + lang.title + '</h2>' +
 *					'<ul>' +
 *						'<li><strong>' + lang.dialogName + '</strong> : ' + dialog.getName() + '</li>' +
 *						'<li><strong>' + lang.tabName + '</strong> : ' + tabName + '</li>';
 *
 *			if ( element )
 *				str += '<li><strong>' + lang.elementId + '</strong> : ' + element.id + '</li>';
 *
 *			str += '<li><strong>' + lang.elementType + '</strong> : ' + link + '</li>';
 *
 *			return str + '</ul>';
 *		};
 *
 * @since 3.6
 * @cfg {Function} [devtools_textCallback=see example]
 * @member CKEDITOR.config
 * @param {CKEDITOR.editor} editor
 * @param dialog
 * @param element
 * @param tabName
 */

/**
 * A setting that stores CSS rules to be injected into the page with styles to be applied to the tooltip element.
 *
 *		// This is actually the default value.
 *		CKEDITOR.config.devtools_styles =
 *			'#cke_tooltip { padding: 5px; border: 2px solid #333; background: #ffffff }' +
 *			'#cke_tooltip h2 { font-size: 1.1em; border-bottom: 1px solid; margin: 0; padding: 1px; }' +
 *			'#cke_tooltip ul { padding: 0pt; list-style-type: none; }';
 *
 * @since 3.6
 * @cfg {String} [devtools_styles=see example]
 * @member CKEDITOR.config
 */
