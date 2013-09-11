/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview The "toolbar" plugin. Renders the default toolbar interface in
 * the editor.
 */

(function() {
	var toolbox = function() {
			this.toolbars = [];
			this.focusCommandExecuted = false;
		};

	toolbox.prototype.focus = function() {
		for ( var t = 0, toolbar; toolbar = this.toolbars[ t++ ]; ) {
			for ( var i = 0, item; item = toolbar.items[ i++ ]; ) {
				if ( item.focus ) {
					item.focus();
					return;
				}
			}
		}
	};

	var commands = {
		toolbarFocus: {
			modes: { wysiwyg:1,source:1 },
			readOnly: 1,

			exec: function( editor ) {
				if ( editor.toolbox ) {
					editor.toolbox.focusCommandExecuted = true;

					// Make the first button focus accessible for IE. (#3417)
					// Adobe AIR instead need while of delay.
					if ( CKEDITOR.env.ie || CKEDITOR.env.air )
						setTimeout( function() {
						editor.toolbox.focus();
					}, 100 );
					else
						editor.toolbox.focus();
				}
			}
		}
	};

	CKEDITOR.plugins.add( 'toolbar', {
		requires: 'button',
		lang: 'af,ar,bg,bn,bs,ca,cs,cy,da,de,el,en,en-au,en-ca,en-gb,eo,es,et,eu,fa,fi,fo,fr,fr-ca,gl,gu,he,hi,hr,hu,id,is,it,ja,ka,km,ko,ku,lt,lv,mk,mn,ms,nb,nl,no,pl,pt,pt-br,ro,ru,si,sk,sl,sq,sr,sr-latn,sv,th,tr,ug,uk,vi,zh,zh-cn', // %REMOVE_LINE_CORE%

		init: function( editor ) {
			var endFlag;

			var itemKeystroke = function( item, keystroke ) {
					var next, toolbar;
					var rtl = editor.lang.dir == 'rtl',
						toolbarGroupCycling = editor.config.toolbarGroupCycling;

					toolbarGroupCycling = toolbarGroupCycling === undefined || toolbarGroupCycling;

					switch ( keystroke ) {
						case 9: // TAB
						case CKEDITOR.SHIFT + 9: // SHIFT + TAB
							// Cycle through the toolbars, starting from the one
							// closest to the current item.
							while ( !toolbar || !toolbar.items.length ) {
								toolbar = keystroke == 9 ? ( ( toolbar ? toolbar.next : item.toolbar.next ) || editor.toolbox.toolbars[ 0 ] ) : ( ( toolbar ? toolbar.previous : item.toolbar.previous ) || editor.toolbox.toolbars[ editor.toolbox.toolbars.length - 1 ] );

								// Look for the first item that accepts focus.
								if ( toolbar.items.length ) {
									item = toolbar.items[ endFlag ? ( toolbar.items.length - 1 ) : 0 ];
									while ( item && !item.focus ) {
										item = endFlag ? item.previous : item.next;

										if ( !item )
											toolbar = 0;
									}
								}
							}

							if ( item )
								item.focus();

							return false;

						case rtl ? 37:
							39 : // RIGHT-ARROW
						case 40: // DOWN-ARROW
							next = item;
							do {
								// Look for the next item in the toolbar.
								next = next.next;

								// If it's the last item, cycle to the first one.
								if ( !next && toolbarGroupCycling ) next = item.toolbar.items[ 0 ];
							}
							while ( next && !next.focus )

							// If available, just focus it, otherwise focus the
							// first one.
							if ( next )
								next.focus();
							else
								// Send a TAB.
								itemKeystroke( item, 9 );

							return false;

						case rtl ? 39:
							37 : // LEFT-ARROW
						case 38: // UP-ARROW
							next = item;
							do {
								// Look for the previous item in the toolbar.
								next = next.previous;

								// If it's the first item, cycle to the last one.
								if ( !next && toolbarGroupCycling ) next = item.toolbar.items[ item.toolbar.items.length - 1 ];
							}
							while ( next && !next.focus )

							// If available, just focus it, otherwise focus the
							// last one.
							if ( next )
								next.focus();
							else {
								endFlag = 1;
								// Send a SHIFT + TAB.
								itemKeystroke( item, CKEDITOR.SHIFT + 9 );
								endFlag = 0;
							}

							return false;

						case 27: // ESC
							editor.focus();
							return false;

						case 13: // ENTER
						case 32: // SPACE
							item.execute();
							return false;
					}
					return true;
				};

			editor.on( 'uiSpace', function( event ) {
				if ( event.data.space != editor.config.toolbarLocation )
					return;

				// Create toolbar only once.
				event.removeListener();

				editor.toolbox = new toolbox();

				var labelId = CKEDITOR.tools.getNextId();

				var output = [
					'<span id="', labelId, '" class="cke_voice_label">', editor.lang.toolbar.toolbars, '</span>',
					'<span id="' + editor.ui.spaceId( 'toolbox' ) + '" class="cke_toolbox" role="group" aria-labelledby="', labelId, '" onmousedown="return false;">' ];

				var expanded = editor.config.toolbarStartupExpanded !== false,
					groupStarted, pendingSeparator;

				// If the toolbar collapser will be available, we'll have
				// an additional container for all toolbars.
				if ( editor.config.toolbarCanCollapse && editor.elementMode != CKEDITOR.ELEMENT_MODE_INLINE )
					output.push( '<span class="cke_toolbox_main"' + ( expanded ? '>' : ' style="display:none">' ) );

				var toolbars = editor.toolbox.toolbars,
					toolbar = getToolbarConfig( editor );

				for ( var r = 0; r < toolbar.length; r++ ) {
					var toolbarId,
						toolbarObj = 0,
						toolbarName,
						row = toolbar[ r ],
						items;

					// It's better to check if the row object is really
					// available because it's a common mistake to leave
					// an extra comma in the toolbar definition
					// settings, which leads on the editor not loading
					// at all in IE. (#3983)
					if ( !row )
						continue;

					if ( groupStarted ) {
						output.push( '</span>' );
						groupStarted = 0;
						pendingSeparator = 0;
					}

					if ( row === '/' ) {
						output.push( '<span class="cke_toolbar_break"></span>' );
						continue;
					}

					items = row.items || row;

					// Create all items defined for this toolbar.
					for ( var i = 0; i < items.length; i++ ) {
						var item = items[ i ],
							canGroup;

						if ( item ) {
							if ( item.type == CKEDITOR.UI_SEPARATOR ) {
								// Do not add the separator immediately. Just save
								// it be included if we already have something in
								// the toolbar and if a new item is to be added (later).
								pendingSeparator = groupStarted && item;
								continue;
							}

							canGroup = item.canGroup !== false;

							// Initialize the toolbar first, if needed.
							if ( !toolbarObj ) {
								// Create the basic toolbar object.
								toolbarId = CKEDITOR.tools.getNextId();
								toolbarObj = { id: toolbarId, items: [] };
								toolbarName = row.name && ( editor.lang.toolbar.toolbarGroups[ row.name ] || row.name );

								// Output the toolbar opener.
								output.push( '<span id="', toolbarId, '" class="cke_toolbar"', ( toolbarName ? ' aria-labelledby="' + toolbarId + '_label"' : '' ), ' role="toolbar">' );

								// If a toolbar name is available, send the voice label.
								toolbarName && output.push( '<span id="', toolbarId, '_label" class="cke_voice_label">', toolbarName, '</span>' );

								output.push( '<span class="cke_toolbar_start"></span>' );

								// Add the toolbar to the "editor.toolbox.toolbars"
								// array.
								var index = toolbars.push( toolbarObj ) - 1;

								// Create the next/previous reference.
								if ( index > 0 ) {
									toolbarObj.previous = toolbars[ index - 1 ];
									toolbarObj.previous.next = toolbarObj;
								}
							}

							if ( canGroup ) {
								if ( !groupStarted ) {
									output.push( '<span class="cke_toolgroup" role="presentation">' );
									groupStarted = 1;
								}
							} else if ( groupStarted ) {
								output.push( '</span>' );
								groupStarted = 0;
							}

							function addItem( item ) {
								var itemObj = item.render( editor, output );
								index = toolbarObj.items.push( itemObj ) - 1;

								if ( index > 0 ) {
									itemObj.previous = toolbarObj.items[ index - 1 ];
									itemObj.previous.next = itemObj;
								}

								itemObj.toolbar = toolbarObj;
								itemObj.onkey = itemKeystroke;

								// Fix for #3052:
								// Prevent JAWS from focusing the toolbar after document load.
								itemObj.onfocus = function() {
									if ( !editor.toolbox.focusCommandExecuted )
										editor.focus();
								};
							}

							if ( pendingSeparator ) {
								addItem( pendingSeparator );
								pendingSeparator = 0;
							}

							addItem( item );
						}
					}

					if ( groupStarted ) {
						output.push( '</span>' );
						groupStarted = 0;
						pendingSeparator = 0;
					}

					if ( toolbarObj )
						output.push( '<span class="cke_toolbar_end"></span></span>' );
				}

				if ( editor.config.toolbarCanCollapse )
					output.push( '</span>' );

				// Not toolbar collapser for inline mode.
				if ( editor.config.toolbarCanCollapse && editor.elementMode != CKEDITOR.ELEMENT_MODE_INLINE ) {
					var collapserFn = CKEDITOR.tools.addFunction( function() {
						editor.execCommand( 'toolbarCollapse' );
					});

					editor.on( 'destroy', function() {
						CKEDITOR.tools.removeFunction( collapserFn );
					});

					editor.addCommand( 'toolbarCollapse', {
						readOnly: 1,
						exec: function( editor ) {
							var collapser = editor.ui.space( 'toolbar_collapser' ),
								toolbox = collapser.getPrevious(),
								contents = editor.ui.space( 'contents' ),
								toolboxContainer = toolbox.getParent(),
								contentHeight = parseInt( contents.$.style.height, 10 ),
								previousHeight = toolboxContainer.$.offsetHeight,
								minClass = 'cke_toolbox_collapser_min',
								collapsed = collapser.hasClass( minClass );

							if ( !collapsed ) {
								toolbox.hide();
								collapser.addClass( minClass );
								collapser.setAttribute( 'title', editor.lang.toolbar.toolbarExpand );
							} else {
								toolbox.show();
								collapser.removeClass( minClass );
								collapser.setAttribute( 'title', editor.lang.toolbar.toolbarCollapse );
							}

							// Update collapser symbol.
							collapser.getFirst().setText( collapsed ? '\u25B2' : // BLACK UP-POINTING TRIANGLE
							'\u25C0' ); // BLACK LEFT-POINTING TRIANGLE

							var dy = toolboxContainer.$.offsetHeight - previousHeight;
							contents.setStyle( 'height', ( contentHeight - dy ) + 'px' );

							editor.fire( 'resize' );
						},

						modes: { wysiwyg:1,source:1 }
					});

					editor.setKeystroke( CKEDITOR.ALT + ( CKEDITOR.env.ie || CKEDITOR.env.webkit ? 189 : 109 ) /*-*/, 'toolbarCollapse' );

					output.push( '<a title="' + ( expanded ? editor.lang.toolbar.toolbarCollapse : editor.lang.toolbar.toolbarExpand )
						+ '" id="' + editor.ui.spaceId( 'toolbar_collapser' )
						+ '" tabIndex="-1" class="cke_toolbox_collapser' );

					if ( !expanded )
						output.push( ' cke_toolbox_collapser_min' );

					output.push( '" onclick="CKEDITOR.tools.callFunction(' + collapserFn + ')">', '<span class="cke_arrow">&#9650;</span>', // BLACK UP-POINTING TRIANGLE
						'</a>' );
				}

				output.push( '</span>' );
				event.data.html += output.join( '' );
			});

			editor.on( 'destroy', function() {

				if ( this.toolbox )
				{
					var toolbars,
						index = 0,
						i, items, instance;
					toolbars = this.toolbox.toolbars;
					for ( ; index < toolbars.length; index++ ) {
						items = toolbars[ index ].items;
						for ( i = 0; i < items.length; i++ ) {
							instance = items[ i ];
							if ( instance.clickFn )
								CKEDITOR.tools.removeFunction( instance.clickFn );
							if ( instance.keyDownFn )
								CKEDITOR.tools.removeFunction( instance.keyDownFn );
						}
					}
				}
			});

			// Manage editor focus  when navigating the toolbar.
			editor.on( 'uiReady', function() {
				var toolbox = editor.ui.space( 'toolbox' );
				toolbox && editor.focusManager.add( toolbox, 1 );
			});

			editor.addCommand( 'toolbarFocus', commands.toolbarFocus );
			editor.setKeystroke( CKEDITOR.ALT + 121 /*F10*/, 'toolbarFocus' );

			editor.ui.add( '-', CKEDITOR.UI_SEPARATOR, {} );
			editor.ui.addHandler( CKEDITOR.UI_SEPARATOR, {
				create: function() {
					return {
						render: function( editor, output ) {
							output.push( '<span class="cke_toolbar_separator" role="separator"></span>' );
							return {};
						}
					};
				}
			});
		}
	});

	function getToolbarConfig( editor ) {
		var removeButtons = editor.config.removeButtons;

		removeButtons = removeButtons && removeButtons.split( ',' );

		function buildToolbarConfig() {

			// Object containing all toolbar groups used by ui items.
			var lookup = getItemDefinedGroups();

			// Take the base for the new toolbar, which is basically a toolbar
			// definition without items.
			var toolbar = CKEDITOR.tools.clone( editor.config.toolbarGroups ) || getPrivateToolbarGroups( editor );

			// Fill the toolbar groups with the available ui items.
			for ( var i = 0; i < toolbar.length; i++ ) {
				var toolbarGroup = toolbar[ i ];

				// Skip toolbar break.
				if ( toolbarGroup == '/' )
					continue;
				// Handle simply group name item.
				else if ( typeof toolbarGroup == 'string' )
					toolbarGroup = toolbar[ i ] = { name: toolbarGroup };

				var items, subGroups = toolbarGroup.groups;

				// Look for items that match sub groups.
				if ( subGroups ) {
					for ( var j = 0, sub; j < subGroups.length; j++ ) {
						sub = subGroups[ j ];

						// If any ui item is registered for this subgroup.
						items = lookup[ sub ];
						items && fillGroup( toolbarGroup, items );
					}
				}

				// Add the main group items as well.
				items = lookup[ toolbarGroup.name ];
				items && fillGroup( toolbarGroup, items );
			}

			return toolbar;
		}

		// Returns an object containing all toolbar groups used by ui items.
		function getItemDefinedGroups() {
			var groups = {},
				itemName, item, itemToolbar, group, order;

			for ( itemName in editor.ui.items ) {
				item = editor.ui.items[ itemName ];
				itemToolbar = item.toolbar || 'others';
				if ( itemToolbar ) {
					// Break the toolbar property into its parts: "group_name[,order]".
					itemToolbar = itemToolbar.split( ',' );
					group = itemToolbar[ 0 ];
					order = parseInt( itemToolbar[ 1 ] || -1, 10 );

					// Initialize the group, if necessary.
					groups[ group ] || ( groups[ group ] = [] );

					// Push the data used to build the toolbar later.
					groups[ group ].push( { name: itemName, order: order} );
				}
			}

			// Put the items in the right order.
			for ( group in groups ) {
				groups[ group ] = groups[ group ].sort( function( a, b ) {
					return a.order == b.order ? 0 :
						b.order < 0 ? -1 :
						a.order < 0 ? 1 :
						a.order < b.order ? -1 :
						1;
				});
			}

			return groups;
		}

		function fillGroup( toolbarGroup, uiItems ) {
			if ( uiItems.length ) {
				if ( toolbarGroup.items )
					toolbarGroup.items.push( editor.ui.create( '-' ) );
				else
					toolbarGroup.items = [];

				var item, name;
				while ( ( item = uiItems.shift() ) ) {
					name = typeof item == 'string' ? item : item.name;

					// Ignore items that are configured to be removed.
					if ( !removeButtons || CKEDITOR.tools.indexOf( removeButtons, name ) == -1 ) {
						item = editor.ui.create( name );

						if ( !item )
							continue;

						if ( !editor.addFeature( item ) )
							continue;

						toolbarGroup.items.push( item );
					}
				}
			}
		}

		function populateToolbarConfig( config ) {
			var toolbar = [],
				i, group, newGroup;

			for ( i = 0; i < config.length; ++i ) {
				group = config[ i ];
				newGroup = {};

				if ( group == '/' )
					toolbar.push( group );
				else if ( CKEDITOR.tools.isArray( group) ) {
					fillGroup( newGroup, CKEDITOR.tools.clone( group ) );
					toolbar.push( newGroup );
				}
				else if ( group.items ) {
					fillGroup( newGroup, CKEDITOR.tools.clone( group.items ) );
					newGroup.name = group.name;
					toolbar.push( newGroup);
				}
			}

			return toolbar;
		}

		var toolbar = editor.config.toolbar;

		// If it is a string, return the relative "toolbar_name" config.
		if ( typeof toolbar == 'string' )
			toolbar = editor.config[ 'toolbar_' + toolbar ];

		return ( editor.toolbar = toolbar ? populateToolbarConfig( toolbar ) : buildToolbarConfig() );
	}

	/**
	 * Add toolbar group. See {@link CKEDITOR.config#toolbarGroups} for more details.
	 *
	 * **Note:** This method won't modify toolbar groups set explicitly by
	 * {@link CKEDITOR.config#toolbarGroups}. It will extend only default setting.
	 *
	 * @param {String} name Group name.
	 * @param {Number/String} previous Name of group after which this one
	 * should be added or `0` if this group should be the first one.
	 * @param {String} [subgroupOf] Name of parent group.
	 * @member CKEDITOR.ui
	 */
	CKEDITOR.ui.prototype.addToolbarGroup = function( name, previous, subgroupOf ) {
		// The toolbarGroups from the privates is the one we gonna use for automatic toolbar creation.
		var toolbarGroups = getPrivateToolbarGroups( this.editor ),
			atStart = previous === 0,
			newGroup = { name: name };

		if ( subgroupOf ) {
			// Transform the subgroupOf name in the real subgroup object.
			subgroupOf = CKEDITOR.tools.search( toolbarGroups, function( group ) {
				return group.name == subgroupOf;
			});

			if ( subgroupOf ) {
				!subgroupOf.groups && ( subgroupOf.groups = [] ) ;

				if ( previous ) {
					// Search the "previous" item and add the new one after it.
					previous = CKEDITOR.tools.indexOf( subgroupOf.groups, previous );
					if ( previous >= 0 ) {
						subgroupOf.groups.splice( previous + 1, 0, name );
						return;
					}
				}

				// If no previous found.

				if ( atStart )
					subgroupOf.groups.splice( 0, 0, name );
				else
					subgroupOf.groups.push(  name );
				return;
			} else {
				// Ignore "previous" if subgroupOf has not been found.
				previous = null;
			}
		}

		if ( previous ) {
			// Transform the "previous" name into its index.
			previous = CKEDITOR.tools.indexOf( toolbarGroups, function( group ) {
				return group.name == previous;
			});
		}

		if ( atStart )
			toolbarGroups.splice( 0, 0, name );
		else if ( typeof previous == 'number' )
			toolbarGroups.splice( previous + 1, 0, newGroup );
		else
			toolbarGroups.push( name );
	};

	function getPrivateToolbarGroups( editor ) {
		return editor._.toolbarGroups || ( editor._.toolbarGroups = [
			{ name: 'document',	   groups: [ 'mode', 'document', 'doctools' ] },
			{ name: 'clipboard',   groups: [ 'clipboard', 'undo' ] },
			{ name: 'editing',     groups: [ 'find', 'selection', 'spellchecker' ] },
			{ name: 'forms' },
			'/',
			{ name: 'basicstyles', groups: [ 'basicstyles', 'cleanup' ] },
			{ name: 'paragraph',   groups: [ 'list', 'indent', 'blocks', 'align' ] },
			{ name: 'links' },
			{ name: 'insert' },
			'/',
			{ name: 'styles' },
			{ name: 'colors' },
			{ name: 'tools' },
			{ name: 'others' },
			{ name: 'about' }
		]);
	}
})();

/**
 * Separator UI element.
 *
 * @readonly
 * @property {String} [='separator']
 * @member CKEDITOR
 */
CKEDITOR.UI_SEPARATOR = 'separator';

/**
 * The "UI space" to which rendering the toolbar. For the default editor implementation,
 * the recommended options are `'top'` and `'bottom'`.
 *
 *		config.toolbarLocation = 'bottom';
 *
 * @cfg
 * @member CKEDITOR.config
 */
CKEDITOR.config.toolbarLocation = 'top';

/**
 * The toolbox (alias toolbar) definition. It is a toolbar name or an array of
 * toolbars (strips), each one being also an array, containing a list of UI items.
 *
 * If set to `null`, generate toolbar automatically using all available buttons
 * and {@link #toolbarGroups} as a toolbar groups layout.
 *
 *		// Defines a toolbar with only one strip containing the "Source" button, a
 *		// separator and the "Bold" and "Italic" buttons.
 *		config.toolbar = [
 *			[ 'Source', '-', 'Bold', 'Italic' ]
 *		];
 *
 *		// Similar to example the above, defines a "Basic" toolbar with only one strip containing three buttons.
 *		// Note that this setting is composed by "toolbar_" added by the toolbar name, which in this case is called "Basic".
 *		// This second part of the setting name can be anything. You must use this name in the CKEDITOR.config.toolbar setting,
 *		// so you instruct the editor which toolbar_(name) setting to use.
 *		config.toolbar_Basic = [
 *			[ 'Source', '-', 'Bold', 'Italic' ]
 *		];
 *		// Load toolbar_Name where Name = Basic.
 *		config.toolbar = 'Basic';
 *
 * @cfg {Array/String} [toolbar=null]
 * @member CKEDITOR.config
 */

/**
 * The toolbar groups definition.
 *
 * If toolbar layout isn't explicitly defined by {@link #toolbar} setting, then
 * this setting is used to group all defined buttons (see {@link CKEDITOR.ui#addButton}).
 * Buttons are associated with toolbar groups by `toolbar` property in their definition objects.
 *
 * New groups may be dynamically added during the editor and plugins initialization by
 * {@link CKEDITOR.ui#addToolbarGroup}. Although only if default setting was used.
 *
 *		// Default setting.
 *		config.toolbarGroups = [
 *			{ name: 'document',	   groups: [ 'mode', 'document', 'doctools' ] },
 *			{ name: 'clipboard',   groups: [ 'clipboard', 'undo' ] },
 *			{ name: 'editing',     groups: [ 'find', 'selection', 'spellchecker' ] },
 *			{ name: 'forms' },
 *			'/',
 *			{ name: 'basicstyles', groups: [ 'basicstyles', 'cleanup' ] },
 *			{ name: 'paragraph',   groups: [ 'list', 'indent', 'blocks', 'align' ] },
 *			{ name: 'links' },
 *			{ name: 'insert' },
 *			'/',
 *			{ name: 'styles' },
 *			{ name: 'colors' },
 *			{ name: 'tools' },
 *			{ name: 'others' },
 *			{ name: 'about' }
 *		];
 *
 * @cfg {Array} [toolbarGroups=see example]
 * @member CKEDITOR.config
 */

/**
 * Whether the toolbar can be collapsed by the user. If disabled, the collapser
 * button will not be displayed.
 *
 *		config.toolbarCanCollapse = true;
 *
 * @cfg {Boolean} [toolbarCanCollapse=false]
 * @member CKEDITOR.config
 */

/**
 * Whether the toolbar must start expanded when the editor is loaded.
 *
 * Setting this option to `false` will affect toolbar only when
 * {@link #toolbarCanCollapse} is set to `true`:
 *
 *		config.toolbarCanCollapse = true;
 *		config.toolbarStartupExpanded = false;
 *
 * @cfg {Boolean} [toolbarStartupExpanded=true]
 * @member CKEDITOR.config
 */

/**
 * When enabled, makes the arrow keys navigation cycle within the current
 * toolbar group. Otherwise the arrows will move through all items available in
 * the toolbar. The *TAB* key will still be used to quickly jump among the
 * toolbar groups.
 *
 *		config.toolbarGroupCycling = false;
 *
 * @since 3.6
 * @cfg {Boolean} [toolbarGroupCycling=true]
 * @member CKEDITOR.config
 */

/**
 * List of toolbar button names that must not be rendered. This will work as
 * well for non-button toolbar items, like the Font combos.
 *
 *		config.removeButtons = 'Underline,JustifyCenter';
 *
 * This configuration should not be overused, having
 * {@link CKEDITOR.config#removePlugins} removing features from the editor. In
 * some cases though, a single plugin may define a set of toolbar buttons and
 * removeButtons may be useful when just a few of them are to be removed.
 *
 * @cfg {String} [removeButtons]
 * @member CKEDITOR.config
 */

/**
 * Toolbar definition used by the editor. It is crated from the
 * {@link CKEDITOR.config#toolbar} if it is set or automatically
 * based on {@link CKEDITOR.config#toolbarGroups}.
 *
 * @readonly
 * @property {Object} toolbar
 * @member CKEDITOR.editor
 */
