/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview The "show border" plugin. The command display visible outline
 * border line around all table elements if table doesn't have a none-zero 'border' attribute specified.
 */

(function() {
	var commandDefinition = {
		preserveState: true,
		editorFocus: false,
		readOnly: 1,

		exec: function( editor ) {
			this.toggleState();
			this.refresh( editor );
		},

		refresh: function( editor ) {
			if ( editor.document ) {
				var funcName = ( this.state == CKEDITOR.TRISTATE_ON ) ? 'attachClass' : 'removeClass';
				editor.editable()[ funcName ]( 'cke_show_borders' );
			}
		}
	};

	var showBorderClassName = 'cke_show_border';

	CKEDITOR.plugins.add( 'showborders', {
		modes: { 'wysiwyg':1 },

		onLoad: function() {
			var cssStyleText,
				cssTemplate =
			// TODO: For IE6, we don't have child selector support,
			// where nested table cells could be incorrect.
			( CKEDITOR.env.ie6Compat ? [
				'.%1 table.%2,',
					'.%1 table.%2 td, .%1 table.%2 th',
					'{',
					'border : #d3d3d3 1px dotted',
					'}'
				] : [
				'.%1 table.%2,',
				'.%1 table.%2 > tr > td, .%1 table.%2 > tr > th,',
				'.%1 table.%2 > tbody > tr > td, .%1 table.%2 > tbody > tr > th,',
				'.%1 table.%2 > thead > tr > td, .%1 table.%2 > thead > tr > th,',
				'.%1 table.%2 > tfoot > tr > td, .%1 table.%2 > tfoot > tr > th',
				'{',
					'border : #d3d3d3 1px dotted',
				'}'
				] ).join( '' );

			cssStyleText = cssTemplate.replace( /%2/g, showBorderClassName ).replace( /%1/g, 'cke_show_borders ' );

			CKEDITOR.addCss( cssStyleText );
		},

		init: function( editor ) {

			var command = editor.addCommand( 'showborders', commandDefinition );
			command.canUndo = false;

			if ( editor.config.startupShowBorders !== false )
				command.setState( CKEDITOR.TRISTATE_ON );

			// Refresh the command on setData.
			editor.on( 'mode', function() {
				if ( command.state != CKEDITOR.TRISTATE_DISABLED )
					command.refresh( editor );
			}, null, null, 100 );

			// Refresh the command on wysiwyg frame reloads.
			editor.on( 'contentDom', function() {
				if ( command.state != CKEDITOR.TRISTATE_DISABLED )
					command.refresh( editor );
			});

			editor.on( 'removeFormatCleanup', function( evt ) {
				var element = evt.data;
				if ( editor.getCommand( 'showborders' ).state == CKEDITOR.TRISTATE_ON && element.is( 'table' ) && ( !element.hasAttribute( 'border' ) || parseInt( element.getAttribute( 'border' ), 10 ) <= 0 ) )
					element.addClass( showBorderClassName );
			});
		},

		afterInit: function( editor ) {
			var dataProcessor = editor.dataProcessor,
				dataFilter = dataProcessor && dataProcessor.dataFilter,
				htmlFilter = dataProcessor && dataProcessor.htmlFilter;

			if ( dataFilter ) {
				dataFilter.addRules({
					elements: {
						'table': function( element ) {
							var attributes = element.attributes,
								cssClass = attributes[ 'class' ],
								border = parseInt( attributes.border, 10 );

							if ( ( !border || border <= 0 ) && ( !cssClass || cssClass.indexOf( showBorderClassName ) == -1 ) )
								attributes[ 'class' ] = ( cssClass || '' ) + ' ' + showBorderClassName;
						}
					}
				});
			}

			if ( htmlFilter ) {
				htmlFilter.addRules({
					elements: {
						'table': function( table ) {
							var attributes = table.attributes,
								cssClass = attributes[ 'class' ];

							cssClass && ( attributes[ 'class' ] = cssClass.replace( showBorderClassName, '' ).replace( /\s{2}/, ' ' ).replace( /^\s+|\s+$/, '' ) );
						}
					}
				});
			}
		}
	});

	// Table dialog must be aware of it.
	CKEDITOR.on( 'dialogDefinition', function( ev ) {
		var dialogName = ev.data.name;

		if ( dialogName == 'table' || dialogName == 'tableProperties' ) {
			var dialogDefinition = ev.data.definition,
				infoTab = dialogDefinition.getContents( 'info' ),
				borderField = infoTab.get( 'txtBorder' ),
				originalCommit = borderField.commit;

			borderField.commit = CKEDITOR.tools.override( originalCommit, function( org ) {
				return function( data, selectedTable ) {
					org.apply( this, arguments );
					var value = parseInt( this.getValue(), 10 );
					selectedTable[ ( !value || value <= 0 ) ? 'addClass' : 'removeClass' ]( showBorderClassName );
				};
			});

			var advTab = dialogDefinition.getContents( 'advanced' ),
				classField = advTab && advTab.get( 'advCSSClasses' );

			if ( classField ) {
				classField.setup = CKEDITOR.tools.override( classField.setup, function( originalSetup ) {
					return function() {
						originalSetup.apply( this, arguments );
						this.setValue( this.getValue().replace( /cke_show_border/, '' ) );
					};
				});

				classField.commit = CKEDITOR.tools.override( classField.commit, function( originalCommit ) {
					return function( data, element ) {
						originalCommit.apply( this, arguments );

						if ( !parseInt( element.getAttribute( 'border' ), 10 ) )
							element.addClass( 'cke_show_border' );
					};
				});
			}
		}
	});

})();

/**
 * Whether to automatically enable the "show borders" command when the editor loads.
 *
 *		config.startupShowBorders = false;
 *
 * @cfg {Boolean} [startupShowBorders=true]
 * @member CKEDITOR.config
 */
