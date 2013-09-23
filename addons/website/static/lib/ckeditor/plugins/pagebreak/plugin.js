/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Horizontal Page Break
 */

// Register a plugin named "pagebreak".
CKEDITOR.plugins.add( 'pagebreak', {
	requires: 'fakeobjects',

	lang: 'af,ar,bg,bn,bs,ca,cs,cy,da,de,el,en,en-au,en-ca,en-gb,eo,es,et,eu,fa,fi,fo,fr,fr-ca,gl,gu,he,hi,hr,hu,id,is,it,ja,ka,km,ko,ku,lt,lv,mk,mn,ms,nb,nl,no,pl,pt,pt-br,ro,ru,si,sk,sl,sq,sr,sr-latn,sv,th,tr,ug,uk,vi,zh,zh-cn', // %REMOVE_LINE_CORE%
	icons: 'pagebreak,pagebreak-rtl', // %REMOVE_LINE_CORE%
	hidpi: true, // %REMOVE_LINE_CORE%
	onLoad: function() {
		var cssStyles = [
			'{',
				'background: url(' + CKEDITOR.getUrl( this.path + 'images/pagebreak.gif' ) + ') no-repeat center center;',
				'clear: both;',
				'width:100%; _width:99.9%;',
				'border-top: #999999 1px dotted;',
				'border-bottom: #999999 1px dotted;',
				'padding:0;',
				'height: 5px;',
				'cursor: default;',
			'}'
			].join( '' ).replace( /;/g, ' !important;' ); // Increase specificity to override other styles, e.g. block outline.

		// Add the style that renders our placeholder.
		CKEDITOR.addCss( 'div.cke_pagebreak' + cssStyles );
	},
	init: function( editor ) {
		if ( editor.blockless )
			return;

		// Register the command.
		editor.addCommand( 'pagebreak', CKEDITOR.plugins.pagebreakCmd );

		// Register the toolbar button.
		editor.ui.addButton && editor.ui.addButton( 'PageBreak', {
			label: editor.lang.pagebreak.toolbar,
			command: 'pagebreak',
			toolbar: 'insert,70'
		});

		// Opera needs help to select the page-break.
		CKEDITOR.env.opera && editor.on( 'contentDom', function() {
			editor.document.on( 'click', function( evt ) {
				var target = evt.data.getTarget();
				if ( target.is( 'div' ) && target.hasClass( 'cke_pagebreak' ) )
					editor.getSelection().selectElement( target );
			});
		});
	},

	afterInit: function( editor ) {
		var label = editor.lang.pagebreak.alt;

		// Register a filter to displaying placeholders after mode change.
		var dataProcessor = editor.dataProcessor,
			dataFilter = dataProcessor && dataProcessor.dataFilter,
			htmlFilter = dataProcessor && dataProcessor.htmlFilter;

		if ( htmlFilter ) {
			htmlFilter.addRules({
				attributes: {
					'class': function( value, element ) {
						var className = value.replace( 'cke_pagebreak', '' );
						if ( className != value ) {
							var span = CKEDITOR.htmlParser.fragment.fromHtml( '<span style="display: none;">&nbsp;</span>' ).children[ 0 ];
							element.children.length = 0;
							element.add( span );
							var attrs = element.attributes;
							delete attrs[ 'aria-label' ];
							delete attrs.contenteditable;
							delete attrs.title;
						}
						return className;
					}
				}
			}, 5 );
		}

		if ( dataFilter ) {
			dataFilter.addRules({
				elements: {
					div: function( element ) {
						var attributes = element.attributes,
							style = attributes && attributes.style,
							child = style && element.children.length == 1 && element.children[ 0 ],
							childStyle = child && ( child.name == 'span' ) && child.attributes.style;

						if ( childStyle && ( /page-break-after\s*:\s*always/i ).test( style ) && ( /display\s*:\s*none/i ).test( childStyle ) ) {
							attributes.contenteditable = "false";
							attributes[ 'class' ] = "cke_pagebreak";
							attributes[ 'data-cke-display-name' ] = "pagebreak";
							attributes[ 'aria-label' ] = label;
							attributes[ 'title' ] = label;

							element.children.length = 0;
						}
					}
				}
			});
		}
	}
});

// TODO Much probably there's no need to expose this object as public object.

CKEDITOR.plugins.pagebreakCmd = {
	exec: function( editor ) {
		var label = editor.lang.pagebreak.alt;

		// Create read-only element that represents a print break.
		var pagebreak = CKEDITOR.dom.element.createFromHtml( '<div style="' +
			'page-break-after: always;"' +
			'contenteditable="false" ' +
			'title="' + label + '" ' +
			'aria-label="' + label + '" ' +
			'data-cke-display-name="pagebreak" ' +
			'class="cke_pagebreak">' +
			'</div>', editor.document );

		editor.insertElement( pagebreak );
	},
	context: 'div',
	allowedContent: {
		div: {
			styles: '!page-break-after'
		},
		span: {
			match: function( element ) {
				var parent = element.parent;
				return parent && parent.name == 'div' && parent.styles[ 'page-break-after' ];
			},
			styles: 'display'
		}
	},
	requiredContent: 'div{page-break-after}'
};
