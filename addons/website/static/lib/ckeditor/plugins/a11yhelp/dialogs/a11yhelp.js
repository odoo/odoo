/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

CKEDITOR.dialog.add( 'a11yHelp', function( editor ) {
	var lang = editor.lang.a11yhelp,
		id = CKEDITOR.tools.getNextId();

	// CharCode <-> KeyChar.
	var keyMap = {
		8: "BACKSPACE",
		9: "TAB",
		13: "ENTER",
		16: "SHIFT",
		17: "CTRL",
		18: "ALT",
		19: "PAUSE",
		20: "CAPSLOCK",
		27: "ESCAPE",
		33: "PAGE UP",
		34: "PAGE DOWN",
		35: "END",
		36: "HOME",
		37: "LEFT ARROW",
		38: "UP ARROW",
		39: "RIGHT ARROW",
		40: "DOWN ARROW",
		45: "INSERT",
		46: "DELETE",
		91: "LEFT WINDOW KEY",
		92: "RIGHT WINDOW KEY",
		93: "SELECT KEY",
		96: "NUMPAD  0",
		97: "NUMPAD  1",
		98: "NUMPAD  2",
		99: "NUMPAD  3",
		100: "NUMPAD  4",
		101: "NUMPAD  5",
		102: "NUMPAD  6",
		103: "NUMPAD  7",
		104: "NUMPAD  8",
		105: "NUMPAD  9",
		106: "MULTIPLY",
		107: "ADD",
		109: "SUBTRACT",
		110: "DECIMAL POINT",
		111: "DIVIDE",
		112: "F1",
		113: "F2",
		114: "F3",
		115: "F4",
		116: "F5",
		117: "F6",
		118: "F7",
		119: "F8",
		120: "F9",
		121: "F10",
		122: "F11",
		123: "F12",
		144: "NUM LOCK",
		145: "SCROLL LOCK",
		186: "SEMI-COLON",
		187: "EQUAL SIGN",
		188: "COMMA",
		189: "DASH",
		190: "PERIOD",
		191: "FORWARD SLASH",
		192: "GRAVE ACCENT",
		219: "OPEN BRACKET",
		220: "BACK SLASH",
		221: "CLOSE BRAKET",
		222: "SINGLE QUOTE"
	};

	// Modifier keys override.
	keyMap[ CKEDITOR.ALT ] = 'ALT';
	keyMap[ CKEDITOR.SHIFT ] = 'SHIFT';
	keyMap[ CKEDITOR.CTRL ] = 'CTRL';

	// Sort in desc.
	var modifiers = [ CKEDITOR.ALT, CKEDITOR.SHIFT, CKEDITOR.CTRL ];

	function representKeyStroke( keystroke ) {
		var quotient, modifier,
			presentation = [];

		for ( var i = 0; i < modifiers.length; i++ ) {
			modifier = modifiers[ i ];
			quotient = keystroke / modifiers[ i ];
			if ( quotient > 1 && quotient <= 2 ) {
				keystroke -= modifier;
				presentation.push( keyMap[ modifier ] );
			}
		}

		presentation.push( keyMap[ keystroke ] || String.fromCharCode( keystroke ) );

		return presentation.join( '+' );
	}

	var variablesPattern = /\$\{(.*?)\}/g;

	var replaceVariables = (function() {
		// Swaps keystrokes with their commands in object literal.
		// This makes searching keystrokes by command much easier.
		var keystrokesByCode = editor.keystrokeHandler.keystrokes,
			keystrokesByName = {};

		for ( var i in keystrokesByCode )
			keystrokesByName[ keystrokesByCode[ i ] ] = i;

		return function( match, name ) {
			// Return the keystroke representation or leave match untouched
			// if there's no keystroke for such command.
			return keystrokesByName[ name ] ? representKeyStroke( keystrokesByName[ name ] ) : match;
		};
	})();

	// Create the help list directly from lang file entries.
	function buildHelpContents() {
		var pageTpl = '<div class="cke_accessibility_legend" role="document" aria-labelledby="' + id + '_arialbl" tabIndex="-1">%1</div>' +
				'<span id="' + id + '_arialbl" class="cke_voice_label">' + lang.contents + ' </span>',
			sectionTpl = '<h1>%1</h1><dl>%2</dl>',
			itemTpl = '<dt>%1</dt><dd>%2</dd>';

		var pageHtml = [],
			sections = lang.legend,
			sectionLength = sections.length;

		for ( var i = 0; i < sectionLength; i++ ) {
			var section = sections[ i ],
				sectionHtml = [],
				items = section.items,
				itemsLength = items.length;

			for ( var j = 0; j < itemsLength; j++ ) {
				var item = items[ j ],
					itemLegend = item.legend.replace( variablesPattern, replaceVariables );

				// (#9765) If some commands haven't been replaced in the legend,
				// most likely their keystrokes are unavailable and we shouldn't include
				// them in our help list.
				if ( itemLegend.match( variablesPattern ) )
					continue;

				sectionHtml.push( itemTpl.replace( '%1', item.name ).replace( '%2', itemLegend ) );
			}

			pageHtml.push( sectionTpl.replace( '%1', section.name ).replace( '%2', sectionHtml.join( '' ) ) );
		}

		return pageTpl.replace( '%1', pageHtml.join( '' ) );
	}

	return {
		title: lang.title,
		minWidth: 600,
		minHeight: 400,
		contents: [
			{
			id: 'info',
			label: editor.lang.common.generalTab,
			expand: true,
			elements: [
				{
				type: 'html',
				id: 'legends',
				style: 'white-space:normal;',
				focus: function() { this.getElement().focus(); },
				html: buildHelpContents() + '<style type="text/css">' +
					'.cke_accessibility_legend' +
					'{' +
						'width:600px;' +
						'height:400px;' +
						'padding-right:5px;' +
						'overflow-y:auto;' +
						'overflow-x:hidden;' +
					'}' +
					// Some adjustments are to be done for IE6 and Quirks to work "properly" (#5757)
					'.cke_browser_quirks .cke_accessibility_legend,' +
					'.cke_browser_ie6 .cke_accessibility_legend' +
					'{' +
						'height:390px' +
					'}' +
					// Override non-wrapping white-space rule in reset css.
					'.cke_accessibility_legend *' +
					'{' +
						'white-space:normal;' +
					'}' +
					'.cke_accessibility_legend h1' +
					'{' +
						'font-size: 20px;' +
						'border-bottom: 1px solid #AAA;' +
						'margin: 5px 0px 15px;' +
					'}' +
					'.cke_accessibility_legend dl' +
					'{' +
						'margin-left: 5px;' +
					'}' +
					'.cke_accessibility_legend dt' +
					'{' +
						'font-size: 13px;' +
						'font-weight: bold;' +
					'}' +
					'.cke_accessibility_legend dd' +
					'{' +
						'margin:10px' +
					'}' +
					'</style>'
			}
			]
		}
		],
		buttons: [ CKEDITOR.dialog.cancelButton ]
	};
});
