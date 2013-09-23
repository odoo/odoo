/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

CKEDITOR.plugins.add( 'menu', {
	requires: 'floatpanel',

	beforeInit: function( editor ) {
		var groups = editor.config.menu_groups.split( ',' ),
			groupsOrder = editor._.menuGroups = {},
			menuItems = editor._.menuItems = {};

		for ( var i = 0; i < groups.length; i++ )
			groupsOrder[ groups[ i ] ] = i + 1;

		/**
		 * Registers an item group to the editor context menu in order to make it
		 * possible to associate it with menu items later.
		 *
		 * @param {String} name Specify a group name.
		 * @param {Number} [order=100] Define the display sequence of this group
		 * inside the menu. A smaller value gets displayed first.
		 * @member CKEDITOR.editor
		 */
		editor.addMenuGroup = function( name, order ) {
			groupsOrder[ name ] = order || 100;
		};

		/**
		 * Adds an item from the specified definition to the editor context menu.
		 *
		 * @method
		 * @param {String} name The menu item name.
		 * @param {Object} definition The menu item definition.
		 * @member CKEDITOR.editor
		 */
		editor.addMenuItem = function( name, definition ) {
			if ( groupsOrder[ definition.group ] )
				menuItems[ name ] = new CKEDITOR.menuItem( this, name, definition );
		};

		/**
		 * Adds one or more items from the specified definition array to the editor context menu.
		 *
		 * @method
		 * @param {Array} definitions List of definitions for each menu item as if {@link #addMenuItem} is called.
		 * @member CKEDITOR.editor
		 */
		editor.addMenuItems = function( definitions ) {
			for ( var itemName in definitions ) {
				this.addMenuItem( itemName, definitions[ itemName ] );
			}
		};

		/**
		 * Retrieves a particular menu item definition from the editor context menu.
		 *
		 * @method
		 * @param {String} name The name of the desired menu item.
		 * @returns {Object}
		 * @member CKEDITOR.editor
		 */
		editor.getMenuItem = function( name ) {
			return menuItems[ name ];
		};

		/**
		 * Removes a particular menu item added before from the editor context menu.
		 *
		 * @since 3.6.1
		 * @method
		 * @param {String} name The name of the desired menu item.
		 * @member CKEDITOR.editor
		 */
		editor.removeMenuItem = function( name ) {
			delete menuItems[ name ];
		};
	}
});

(function() {
	var menuItemSource = '<span class="cke_menuitem">' +
		'<a id="{id}"' +
		' class="cke_menubutton cke_menubutton__{name} cke_menubutton_{state} {cls}" href="{href}"' +
		' title="{title}"' +
		' tabindex="-1"' +
		'_cke_focus=1' +
		' hidefocus="true"' +
		' role="menuitem"' +
		' aria-haspopup="{hasPopup}"' +
		' aria-disabled="{disabled}"';

	// Some browsers don't cancel key events in the keydown but in the
	// keypress.
	// TODO: Check if really needed for Gecko+Mac.
	if ( CKEDITOR.env.opera || ( CKEDITOR.env.gecko && CKEDITOR.env.mac ) )
		menuItemSource += ' onkeypress="return false;"';

	// With Firefox, we need to force the button to redraw, otherwise it
	// will remain in the focus state.
	if ( CKEDITOR.env.gecko )
		menuItemSource += ' onblur="this.style.cssText = this.style.cssText;"';

	// #188
	menuItemSource += ' onmouseover="CKEDITOR.tools.callFunction({hoverFn},{index});"' +
			' onmouseout="CKEDITOR.tools.callFunction({moveOutFn},{index});" ' +
			( CKEDITOR.env.ie ? 'onclick="return false;" onmouseup' : 'onclick' ) +
				'="CKEDITOR.tools.callFunction({clickFn},{index}); return false;"' +
			'>';

	menuItemSource +=
				'<span class="cke_menubutton_inner">' +
					'<span class="cke_menubutton_icon">' +
						'<span class="cke_button_icon cke_button__{iconName}_icon" style="{iconStyle}"></span>' +
					'</span>' +
					'<span class="cke_menubutton_label">' +
						'{label}' +
					'</span>' +
					'{arrowHtml}' +
				'</span>' +
			'</a></span>';

	var menuArrowSource = '<span class="cke_menuarrow">' +
				'<span>{label}</span>' +
			'</span>';

	var menuItemTpl = CKEDITOR.addTemplate( 'menuItem', menuItemSource ),
		menuArrowTpl = CKEDITOR.addTemplate( 'menuArrow', menuArrowSource );

	/**
	 * @class
	 * @todo
	 */
	CKEDITOR.menu = CKEDITOR.tools.createClass({
		$: function( editor, definition ) {
			definition = this._.definition = definition || {};
			this.id = CKEDITOR.tools.getNextId();

			this.editor = editor;
			this.items = [];
			this._.listeners = [];

			this._.level = definition.level || 1;

			var panelDefinition = CKEDITOR.tools.extend( {}, definition.panel, {
				css: [ CKEDITOR.skin.getPath( 'editor' ) ],
				level: this._.level - 1,
				block: {}
			});

			var attrs = panelDefinition.block.attributes = ( panelDefinition.attributes || {} );
			// Provide default role of 'menu'.
			!attrs.role && ( attrs.role = 'menu' );
			this._.panelDefinition = panelDefinition;
		},

		_: {
			onShow: function() {
				var selection = this.editor.getSelection(),
					start = selection && selection.getStartElement(),
					path = this.editor.elementPath(),
					listeners = this._.listeners;

				this.removeAll();
				// Call all listeners, filling the list of items to be displayed.
				for ( var i = 0; i < listeners.length; i++ ) {
					var listenerItems = listeners[ i ]( start, selection, path );

					if ( listenerItems ) {
						for ( var itemName in listenerItems ) {
							var item = this.editor.getMenuItem( itemName );

							if ( item && ( !item.command || this.editor.getCommand( item.command ).state ) ) {
								item.state = listenerItems[ itemName ];
								this.add( item );
							}
						}
					}
				}
			},

			onClick: function( item ) {
				this.hide();

				if ( item.onClick )
					item.onClick();
				else if ( item.command )
					this.editor.execCommand( item.command );
			},

			onEscape: function( keystroke ) {
				var parent = this.parent;
				// 1. If it's sub-menu, close it, with focus restored on this.
				// 2. In case of a top-menu, close it, with focus returned to page.
				if ( parent )
					parent._.panel.hideChild( 1 );
				else if ( keystroke == 27 )
					this.hide( 1 );

				return false;
			},

			onHide: function() {
				this.onHide && this.onHide();
			},

			showSubMenu: function( index ) {
				var menu = this._.subMenu,
					item = this.items[ index ],
					subItemDefs = item.getItems && item.getItems();

				// If this item has no subitems, we just hide the submenu, if
				// available, and return back.
				if ( !subItemDefs ) {
					// Hide sub menu with focus returned.
					this._.panel.hideChild( 1 );
					return;
				}

				// Create the submenu, if not available, or clean the existing
				// one.
				if ( menu )
					menu.removeAll();
				else {
					menu = this._.subMenu = new CKEDITOR.menu( this.editor, CKEDITOR.tools.extend( {}, this._.definition, { level: this._.level + 1 }, true ) );
					menu.parent = this;
					menu._.onClick = CKEDITOR.tools.bind( this._.onClick, this );
				}

				// Add all submenu items to the menu.
				for ( var subItemName in subItemDefs ) {
					var subItem = this.editor.getMenuItem( subItemName );
					if ( subItem ) {
						subItem.state = subItemDefs[ subItemName ];
						menu.add( subItem );
					}
				}

				// Get the element representing the current item.
				var element = this._.panel.getBlock( this.id ).element.getDocument().getById( this.id + String( index ) );

				// Show the submenu.
				// This timeout is needed to give time for the sub-menu get
				// focus when JAWS is running. (#9844)
				setTimeout( function() {
					menu.show( element, 2 );
				},0);
			}
		},

		proto: {
			add: function( item ) {
				// Later we may sort the items, but Array#sort is not stable in
				// some browsers, here we're forcing the original sequence with
				// 'order' attribute if it hasn't been assigned. (#3868)
				if ( !item.order )
					item.order = this.items.length;

				this.items.push( item );
			},

			removeAll: function() {
				this.items = [];
			},

			show: function( offsetParent, corner, offsetX, offsetY ) {
				// Not for sub menu.
				if ( !this.parent ) {
					this._.onShow();
					// Don't menu with zero items.
					if ( !this.items.length )
						return;
				}

				corner = corner || ( this.editor.lang.dir == 'rtl' ? 2 : 1 );

				var items = this.items,
					editor = this.editor,
					panel = this._.panel,
					element = this._.element;

				// Create the floating panel for this menu.
				if ( !panel ) {
					panel = this._.panel = new CKEDITOR.ui.floatPanel( this.editor, CKEDITOR.document.getBody(), this._.panelDefinition, this._.level );

					panel.onEscape = CKEDITOR.tools.bind( function( keystroke ) {
						if ( this._.onEscape( keystroke ) === false )
							return false;
					}, this );

					panel.onShow = function() {
						// Menu need CSS resets, compensate class name.
						var holder = panel._.panel.getHolderElement();
						holder.getParent().addClass( 'cke cke_reset_all' );
					};

					panel.onHide = CKEDITOR.tools.bind( function() {
						this._.onHide && this._.onHide();
					}, this );

					// Create an autosize block inside the panel.
					var block = panel.addBlock( this.id, this._.panelDefinition.block );
					block.autoSize = true;

					var keys = block.keys;
					keys[ 40 ] = 'next'; // ARROW-DOWN
					keys[ 9 ] = 'next'; // TAB
					keys[ 38 ] = 'prev'; // ARROW-UP
					keys[ CKEDITOR.SHIFT + 9 ] = 'prev'; // SHIFT + TAB
					keys[ ( editor.lang.dir == 'rtl' ? 37 : 39 ) ] = CKEDITOR.env.ie ? 'mouseup' : 'click'; // ARROW-RIGHT/ARROW-LEFT(rtl)
					keys[ 32 ] = CKEDITOR.env.ie ? 'mouseup' : 'click'; // SPACE
					CKEDITOR.env.ie && ( keys[ 13 ] = 'mouseup' ); // Manage ENTER, since onclick is blocked in IE (#8041).

					element = this._.element = block.element;

					var elementDoc = element.getDocument();
					elementDoc.getBody().setStyle( 'overflow', 'hidden' );
					elementDoc.getElementsByTag( 'html' ).getItem( 0 ).setStyle( 'overflow', 'hidden' );

					this._.itemOverFn = CKEDITOR.tools.addFunction( function( index ) {
						clearTimeout( this._.showSubTimeout );
						this._.showSubTimeout = CKEDITOR.tools.setTimeout( this._.showSubMenu, editor.config.menu_subMenuDelay || 400, this, [ index ] );
					}, this );

					this._.itemOutFn = CKEDITOR.tools.addFunction( function( index ) {
						clearTimeout( this._.showSubTimeout );
					}, this );

					this._.itemClickFn = CKEDITOR.tools.addFunction( function( index ) {
						var item = this.items[ index ];

						if ( item.state == CKEDITOR.TRISTATE_DISABLED ) {
							this.hide( 1 );
							return;
						}

						if ( item.getItems )
							this._.showSubMenu( index );
						else
							this._.onClick( item );
					}, this );
				}

				// Put the items in the right order.
				sortItems( items );

				// Apply the editor mixed direction status to menu.
				var path = editor.elementPath(),
					mixedDirCls = ( path && path.direction() != editor.lang.dir ) ? ' cke_mixed_dir_content' : '';

				// Build the HTML that composes the menu and its items.
				var output = [ '<div class="cke_menu' + mixedDirCls + '" role="presentation">' ];

				var length = items.length,
					lastGroup = length && items[ 0 ].group;

				for ( var i = 0; i < length; i++ ) {
					var item = items[ i ];
					if ( lastGroup != item.group ) {
						output.push( '<div class="cke_menuseparator" role="separator"></div>' );
						lastGroup = item.group;
					}

					item.render( this, i, output );
				}

				output.push( '</div>' );

				// Inject the HTML inside the panel.
				element.setHtml( output.join( '' ) );

				CKEDITOR.ui.fire( 'ready', this );

				// Show the panel.
				if ( this.parent )
					this.parent._.panel.showAsChild( panel, this.id, offsetParent, corner, offsetX, offsetY );
				else
					panel.showBlock( this.id, offsetParent, corner, offsetX, offsetY );

				editor.fire( 'menuShow', [ panel ] );
			},

			addListener: function( listenerFn ) {
				this._.listeners.push( listenerFn );
			},

			hide: function( returnFocus ) {
				this._.onHide && this._.onHide();
				this._.panel && this._.panel.hide( returnFocus );
			}
		}
	});

	function sortItems( items ) {
		items.sort( function( itemA, itemB ) {
			if ( itemA.group < itemB.group )
				return -1;
			else if ( itemA.group > itemB.group )
				return 1;

			return itemA.order < itemB.order ? -1 : itemA.order > itemB.order ? 1 : 0;
		});
	}

	/**
	 * @class
	 * @todo
	 */
	CKEDITOR.menuItem = CKEDITOR.tools.createClass({
		$: function( editor, name, definition ) {
			CKEDITOR.tools.extend( this, definition,
			// Defaults
			{
				order: 0,
				className: 'cke_menubutton__' + name
			});

			// Transform the group name into its order number.
			this.group = editor._.menuGroups[ this.group ];

			this.editor = editor;
			this.name = name;
		},

		proto: {
			render: function( menu, index, output ) {
				var id = menu.id + String( index ),
					state = ( typeof this.state == 'undefined' ) ? CKEDITOR.TRISTATE_OFF : this.state;

				var stateName = state == CKEDITOR.TRISTATE_ON ? 'on' : state == CKEDITOR.TRISTATE_DISABLED ? 'disabled' : 'off';

				var hasSubMenu = this.getItems;
				// ltr: BLACK LEFT-POINTING POINTER
				// rtl: BLACK RIGHT-POINTING POINTER
				var arrowLabel = '&#' + ( this.editor.lang.dir == 'rtl' ? '9668' : '9658' ) + ';';

				var iconName = this.name;
				if ( this.icon && !( /\./ ).test( this.icon ) )
					iconName = this.icon;

				var params = {
					id: id,
					name: this.name,
					iconName: iconName,
					label: this.label,
					cls: this.className || '',
					state: stateName,
					hasPopup: hasSubMenu ? 'true' : 'false',
					disabled: state == CKEDITOR.TRISTATE_DISABLED,
					title: this.label,
					href: 'javascript:void(\'' + ( this.label || '' ).replace( "'" + '' ) + '\')',
					hoverFn: menu._.itemOverFn,
					moveOutFn: menu._.itemOutFn,
					clickFn: menu._.itemClickFn,
					index: index,
					iconStyle: CKEDITOR.skin.getIconStyle( iconName, ( this.editor.lang.dir == 'rtl' ), iconName == this.icon ? null : this.icon, this.iconOffset ),
					arrowHtml: hasSubMenu ? menuArrowTpl.output({ label: arrowLabel } ) : ''
				};

				menuItemTpl.output( params, output );
			}
		}
	});

})();


/**
 * The amount of time, in milliseconds, the editor waits before displaying submenu
 * options when moving the mouse over options that contain submenus, like the
 * "Cell Properties" entry for tables.
 *
 *		// Remove the submenu delay.
 *		config.menu_subMenuDelay = 0;
 *
 * @cfg {Number} [menu_subMenuDelay=400]
 * @member CKEDITOR.config
 */

/**
 * Fired when a menu is shown.
 *
 * @event menuShow
 * @member CKEDITOR.editor
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param {CKEDITOR.ui.panel[]} data
 */

/**
 * A comma separated list of items group names to be displayed in the context
 * menu. The order of items will reflect the order specified in this list if
 * no priority was defined in the groups.
 *
 *		config.menu_groups = 'clipboard,table,anchor,link,image';
 *
 * @cfg {String} [menu_groups=see source]
 * @member CKEDITOR.config
 */
CKEDITOR.config.menu_groups = 'clipboard,' +
	'form,' +
	'tablecell,tablecellproperties,tablerow,tablecolumn,table,' +
	'anchor,link,image,flash,' +
	'checkbox,radio,textfield,hiddenfield,imagebutton,button,select,textarea,div';
