/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview The "elementspath" plugin. It shows all elements in the DOM
 *		parent tree relative to the current selection in the editing area.
 */

(function() {
	var commands = {
		toolbarFocus: {
			editorFocus: false,
			readOnly: 1,
			exec: function( editor ) {
				var idBase = editor._.elementsPath.idBase;
				var element = CKEDITOR.document.getById( idBase + '0' );

				// Make the first button focus accessible for IE. (#3417)
				// Adobe AIR instead need while of delay.
				element && element.focus( CKEDITOR.env.ie || CKEDITOR.env.air );
			}
		}
	};

	var emptyHtml = '<span class="cke_path_empty">&nbsp;</span>';

	var extra = '';

	// Some browsers don't cancel key events in the keydown but in the
	// keypress.
	// TODO: Check if really needed for Gecko+Mac.
	if ( CKEDITOR.env.opera || ( CKEDITOR.env.gecko && CKEDITOR.env.mac ) )
		extra += ' onkeypress="return false;"';

	// With Firefox, we need to force the button to redraw, otherwise it
	// will remain in the focus state.
	if ( CKEDITOR.env.gecko )
		extra += ' onblur="this.style.cssText = this.style.cssText;"';

	var pathItemTpl = CKEDITOR.addTemplate( 'pathItem', '<a' +
		' id="{id}"' +
		' href="{jsTitle}"' +
		' tabindex="-1"' +
		' class="cke_path_item"' +
		' title="{label}"' +
		( ( CKEDITOR.env.gecko && CKEDITOR.env.version < 10900 ) ? ' onfocus="event.preventBubble();"' : '' ) +
		extra +
		' hidefocus="true" ' +
		' onkeydown="return CKEDITOR.tools.callFunction({keyDownFn},{index}, event );"' +
		' onclick="CKEDITOR.tools.callFunction({clickFn},{index}); return false;"' +
		' role="button" aria-label="{label}">' +
		'{text}' +
		'</a>' );

	CKEDITOR.plugins.add( 'elementspath', {
		lang: 'af,ar,bg,bn,bs,ca,cs,cy,da,de,el,en,en-au,en-ca,en-gb,eo,es,et,eu,fa,fi,fo,fr,fr-ca,gl,gu,he,hi,hr,hu,is,it,ja,ka,km,ko,ku,lt,lv,mk,mn,ms,nb,nl,no,pl,pt,pt-br,ro,ru,si,sk,sl,sq,sr,sr-latn,sv,th,tr,ug,uk,vi,zh,zh-cn', // %REMOVE_LINE_CORE%
		init: function( editor ) {
			editor.on( 'uiSpace', function( event ) {
				if ( event.data.space == 'bottom' )
					initElementsPath( editor, event.data );
			} );
		}
	} );

	function initElementsPath( editor, bottomSpaceData ) {
		var spaceId = editor.ui.spaceId( 'path' );
		var spaceElement;
		var getSpaceElement = function() {
				if ( !spaceElement )
					spaceElement = CKEDITOR.document.getById( spaceId );
				return spaceElement;
			};

		var idBase = 'cke_elementspath_' + CKEDITOR.tools.getNextNumber() + '_';

		editor._.elementsPath = { idBase: idBase, filters: [] };

		bottomSpaceData.html += '<span id="' + spaceId + '_label" class="cke_voice_label">' + editor.lang.elementspath.eleLabel + '</span>' +
			'<span id="' + spaceId + '" class="cke_path" role="group" aria-labelledby="' + spaceId + '_label">' + emptyHtml + '</span>';

		// Register the ui element to the focus manager.
		editor.on( 'uiReady', function() {
			var element = editor.ui.space( 'path' );
			element && editor.focusManager.add( element, 1 );
		} );

		function onClick( elementIndex ) {
			var element = editor._.elementsPath.list[ elementIndex ];
			if ( element.equals( editor.editable() ) ) {
				var range = editor.createRange();
				range.selectNodeContents( element );
				range.select();
			} else
				editor.getSelection().selectElement( element );

			// It is important to focus() *after* the above selection
			// manipulation, otherwise Firefox will have troubles. #10119
			editor.focus();
		}

		var onClickHanlder = CKEDITOR.tools.addFunction( onClick );

		var onKeyDownHandler = CKEDITOR.tools.addFunction( function( elementIndex, ev ) {
			var idBase = editor._.elementsPath.idBase,
				element;

			ev = new CKEDITOR.dom.event( ev );

			var rtl = editor.lang.dir == 'rtl';
			switch ( ev.getKeystroke() ) {
				case rtl ? 39:
					37 : // LEFT-ARROW
				case 9: // TAB
					element = CKEDITOR.document.getById( idBase + ( elementIndex + 1 ) );
					if ( !element )
						element = CKEDITOR.document.getById( idBase + '0' );
					element.focus();
					return false;

				case rtl ? 37:
					39 : // RIGHT-ARROW
				case CKEDITOR.SHIFT + 9: // SHIFT + TAB
					element = CKEDITOR.document.getById( idBase + ( elementIndex - 1 ) );
					if ( !element )
						element = CKEDITOR.document.getById( idBase + ( editor._.elementsPath.list.length - 1 ) );
					element.focus();
					return false;

				case 27: // ESC
					editor.focus();
					return false;

				case 13: // ENTER	// Opera
				case 32: // SPACE
					onClick( elementIndex );
					return false;
			}
			return true;
		} );

		editor.on( 'selectionChange', function( ev ) {
			var env = CKEDITOR.env,
				editable = editor.editable(),
				selection = ev.data.selection,
				element = selection.getStartElement(),
				html = [],
				elementsList = editor._.elementsPath.list = [],
				filters = editor._.elementsPath.filters;

			while ( element ) {
				var ignore = 0,
					name;

				if ( element.data( 'cke-display-name' ) )
					name = element.data( 'cke-display-name' );
				else if ( element.data( 'cke-real-element-type' ) )
					name = element.data( 'cke-real-element-type' );
				else
					name = element.getName();

				for ( var i = 0; i < filters.length; i++ ) {
					var ret = filters[ i ]( element, name );
					if ( ret === false ) {
						ignore = 1;
						break;
					}
					name = ret || name;
				}

				if ( !ignore ) {
					var index = elementsList.push( element ) - 1,
						label = editor.lang.elementspath.eleTitle.replace( /%1/, name );

					var item = pathItemTpl.output({
						id: idBase + index,
						label: label,
						text: name,
						jsTitle: 'javascript:void(\'' + name + '\')',
						index: index,
						keyDownFn: onKeyDownHandler,
						clickFn: onClickHanlder
					} );
					html.unshift( item );

				}

				if ( element.equals( editable ) )
					break;

				element = element.getParent();
			}

			var space = getSpaceElement();
			space.setHtml( html.join( '' ) + emptyHtml );
			editor.fire( 'elementsPathUpdate', { space: space } );
		} );

		function empty() {
			spaceElement && spaceElement.setHtml( emptyHtml );
			delete editor._.elementsPath.list;
		}

		editor.on( 'readOnly', empty );
		editor.on( 'contentDomUnload', empty );

		editor.addCommand( 'elementsPathFocus', commands.toolbarFocus );
		editor.setKeystroke( CKEDITOR.ALT + 122 /*F11*/, 'elementsPathFocus' );
	}
})();

/**
 * Fired when the contents of the elementsPath are changed.
 *
 * @event elementsPathUpdate
 * @member CKEDITOR.editor
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param data
 * @param {CKEDITOR.dom.element} data.space The elementsPath container.
 */
