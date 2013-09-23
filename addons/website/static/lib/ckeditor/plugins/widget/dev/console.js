/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

'use strict';

(function() {

	CKCONSOLE.add( 'widget', {
		panels: [
			{
				type: 'box',
				content: '<ul class="ckconsole_list ckconsole_value" data-value="instances"></ul>',

				refresh: function( editor ) {
					var instances = obj2Array( editor.widgets.instances );

					return {
						header: 'Instances (' + instances.length + ')',
						instances: generateInstancesList( instances )
					};
				},

				refreshOn: function( editor, refresh ) {
					editor.widgets.on( 'instanceCreated', function( evt ) {
						refresh();

						evt.data.on( 'data', refresh );
					} );

					editor.widgets.on( 'instanceDestroyed', refresh );
				}
			},

			{
				type: 'box',
				content:
					'<ul class="ckconsole_list">' +
						'<li>focused: <span class="ckconsole_value" data-value="focused"></span></li>' +
						'<li>selected: <span class="ckconsole_value" data-value="selected"></span></li>' +
					'</ul>',

				refresh: function( editor ) {
					var focused = editor.widgets.focused,
						selected = editor.widgets.selected,
						selectedIds = [];

					for ( var i = 0; i < selected.length; ++i )
						selectedIds.push( selected[ i ].id );

					return {
						header: 'Focus &amp; selection',
						focused: focused ? 'id: ' + focused.id : '-',
						selected: selectedIds.length ? 'id: ' + selectedIds.join( ', id: ' ) : '-'
					};
				},

				refreshOn: function( editor, refresh ) {
					editor.on( 'selectionCheck', refresh, null, null, 999 );
				}
			},

			{
				type: 'log',

				on: function( editor, log, logFn ) {
					// Add all listeners with high priorities to log
					// messages in the correct order when one event depends on another.
					// E.g. selectionChange triggers widget selection - if this listener
					// for selectionChange will be executed later than that one, then order
					// will be incorrect.

					editor.on( 'selectionChange', function( evt ) {
						var msg = 'selection change',
							sel = evt.data.selection,
							el = sel.getSelectedElement(),
							widget;

						if ( el && ( widget = editor.widgets.getByElement( el, true ) ) )
							msg += ' (id: ' + widget.id + ')';

						log( msg );
					}, null, null, 1 );

					editor.widgets.on( 'instanceDestroyed', function( evt ) {
						log( 'instance destroyed (id: ' + evt.data.id + ')' );
					}, null, null, 1 );

					editor.widgets.on( 'instanceCreated', function( evt ) {
						log( 'instance created (id: ' + evt.data.id + ')' );
					}, null, null, 1 );

					editor.widgets.on( 'widgetFocused', function( evt ) {
						log( 'widget focused (id: ' + evt.data.widget.id + ')' );
					}, null, null, 1 );

					editor.widgets.on( 'widgetBlurred', function( evt ) {
						log( 'widget blurred (id: ' + evt.data.widget.id + ')' );
					}, null, null, 1 );

					editor.widgets.on( 'checkWidgets', logFn( 'checking widgets' ), null, null, 1 );
					editor.widgets.on( 'checkSelection', logFn( 'checking selection' ), null, null, 1 );
				}
			}
		]
	} );

	function generateInstancesList( instances ) {
		var html = '',
			instance;

		for ( var i = 0; i < instances.length; ++i ) {
			instance = instances[ i ];
			html += itemTpl.output( { id: instance.id, name: instance.name, data: JSON.stringify( instance.data ) } );
		}
		return html;
	}

	function obj2Array( obj ) {
		var arr = [];
		for ( var id in obj )
			arr.push( obj[ id ] );

		return arr;
	}

	var itemTpl = new CKEDITOR.template( '<li>id: <code>{id}</code>, name: <code>{name}</code>, data: <code>{data}</code></li>' );
})();