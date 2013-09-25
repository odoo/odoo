/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

'use strict';

(function() {

	var DRAG_HANDLER_SIZE = 14;

	CKEDITOR.plugins.add( 'widget', {
		onLoad: function() {
			CKEDITOR.addCss(
				'.cke_widget_wrapper{' +
					'position:relative;' +
					'outline:none' +
				'}' +
				'.cke_widget_inline{' +
					'display:inline-block' +
				'}' +
				'.cke_widget_wrapper:hover>.cke_widget_element{' +
					'outline:2px solid yellow;' +
					'cursor:default' +
				'}' +
				'.cke_widget_wrapper:hover .cke_widget_editable{' +
					'outline:2px solid yellow' +
				'}' +
				'.cke_widget_wrapper.cke_widget_focused>.cke_widget_element,' +
				// We need higher specificity than hover style.
				'.cke_widget_wrapper .cke_widget_editable.cke_widget_editable_focused{' +
					'outline:2px solid #ace' +
				'}' +
				'.cke_widget_editable{' +
					'cursor:text' +
				'}' +
				'.cke_widget_drag_handler_container{' +
					'position:absolute;' +
					'width:' + DRAG_HANDLER_SIZE + 'px;' +
					'height:0;' +
					'opacity:0.75;' +
					'transition:height 0s 0.2s' + // Delay hiding drag handler.
				'}' +
				'.cke_widget_wrapper:hover>.cke_widget_drag_handler_container{' +
					'height:' + DRAG_HANDLER_SIZE + 'px;' +
					'transition:none' +
				'}' +
				'.cke_widget_drag_handler_container:hover{' +
					'opacity:1' +
				'}'+
				'img.cke_widget_drag_handler{' +
					'cursor:move' +
				'}' +
				'.cke_widget_mask{' +
					'position:absolute;' +
					'top:0;' +
					'left:0;' +
					'width:100%;' +
					'height:100%' +
				'}'
			);
		},

		beforeInit: function( editor ) {
			editor.widgets = new Repository( editor );
		},

		afterInit: function( editor ) {
			addWidgetButtons( editor );
			setupContextMenu( editor );
		}
	} );

	/**
	 * @class CKEDITOR.plugins.widget.repository
	 * @mixins CKEDITOR.event
	 */
	function Repository( editor ) {
		this.editor = editor;
		this.registered = {};
		this.instances = {};
		this.selected = [];
		this.focused = null;
		this.widgetHoldingFocusedEditable = null;
		this._ = {
			nextId: 0,
			upcasts: [],
			filters: {}
		};

		setupDataProcessing( this );
		setupWidgetsObserver( this );
		setupSelectionObserver( this );
		setupMouseObserver( this );
		setupKeyboardObserver( this );
		setupDragAndDrop( this );
	}

	Repository.prototype = {
		/**
		 * Minimum interval between selection checks.
		 *
		 * @private
		 */
		MIN_SELECTION_CHECK_INTERVAL: 500,

		/**
		 * Minimum interval between widgets checks.
		 *
		 * @private
		 */
		MIN_WIDGETS_CHECK_INTERVAL: 1000,

		/**
		 * Adds widget definition to the repository.
		 *
		 * @param {String} name
		 * @param {CKEDITOR.plugins.widget.definition} widgetDef
		 * @returns {CKEDITOR.plugins.widget.registeredDefinition}
		 */
		add: function( name, widgetDef ) {
			// Create prototyped copy of original widget defintion, so we won't modify it.
			widgetDef = CKEDITOR.tools.prototypedCopy( widgetDef );
			widgetDef.name = name;
			widgetDef.repository = this;
			widgetDef.definition = widgetDef;

			widgetDef._ = widgetDef._ || {};

			this.editor.fire( 'widgetDefinition', widgetDef );

			if ( widgetDef.template )
				widgetDef.template = new CKEDITOR.template( widgetDef.template );

			addWidgetCommand( this.editor, widgetDef );
			addWidgetProcessors( this, widgetDef );

			// Register widget automatically if it does not have a button.
			if ( !widgetDef.button )
				this.editor.addFeature( widgetDef );

			this.registered[ name ] = widgetDef;

			return widgetDef;
		},

		/**
		 * Checks selection to update widgets states (select and focus).
		 *
		 * This method is triggered by {@link #event-checkSelection} event.
		 */
		checkSelection: function() {
			var sel = this.editor.getSelection(),
				selectedElement = sel.getSelectedElement(),
				updater = stateUpdater( this ),
				widget;

			// Widget is focused so commit and finish checking.
			if ( selectedElement && ( widget = this.getByElement( selectedElement, true ) ) )
				return updater.focus( widget ).select( widget ).commit();

			var range = sel.getRanges()[ 0 ];

			// No ranges or collapsed range mean that nothing is selected, so commit and finish checking.
			if ( !range || range.collapsed )
				return updater.commit();

			// Range is not empty, so create walker checking for wrappers.
			var walker = new CKEDITOR.dom.walker( range ),
				wrapper;

			walker.evaluator = isWidgetWrapper2;

			while ( ( wrapper = walker.next() ) )
				updater.select( this.getByElement( wrapper ) );

			updater.commit();
		},

		/**
		 * Checks if all widgets instances are still present in DOM.
		 * Destroys those which are not.
		 *
		 * This method is triggered by {@link #event-checkWidigets} event.
		 */
		checkWidgets: function() {
			if ( this.editor.mode != 'wysiwyg' )
				return;

			var toBeDestroyed = [],
				editable = this.editor.editable(),
				instances = this.instances,
				id;

			if ( !editable )
				return;

			for ( id in instances ) {
				if ( !editable.contains( instances[ id ].wrapper ) )
					this.destroy( instances[ id ], true );
			}
		},

		del: function( widget ) {
			if ( this.focused === widget ) {
				var editor = widget.editor,
					range = editor.createRange(),
					found;

				// If haven't found place for caret on the default side,
				// try to find it on the other side.
				if ( !( found = range.moveToClosestEditablePosition( widget.wrapper, true ) ) )
					found = range.moveToClosestEditablePosition( widget.wrapper, false );

				if ( found )
					editor.getSelection().selectRanges( [ range ] );
			}

			widget.wrapper.remove();
			this.destroy( widget, true );
		},

		/**
		 * Removes and destroys widget instance.
		 *
		 * @param {CKEDITOR.plugins.widget} widget
		 * @param {Boolean} [offline] Whether widget is offline (detached from DOM tree) -
		 * in this case DOM (attributes, classes, etc.) will not be cleaned up.
		 */
		destroy: function( widget, offline ) {
			if ( this.widgetHoldingFocusedEditable === widget )
				setFocusedEditable( this, widget, null, offline );

			widget.destroy( offline );
			delete this.instances[ widget.id ];
			this.fire( 'instanceDestroyed', widget );
		},

		/**
		 * Removes and destroys all widgets instances.
		 *
		 * @param {Boolean} [offline] Whether widgets are offline (detached from DOM tree) -
		 * in this case DOM (attributes, classes, etc.) will not be cleaned up.
		 */
		destroyAll: function( offline ) {
			var instances = this.instances,
				widget;

			for ( var id in instances ) {
				widget = instances[ id ];
				this.destroy( widget, offline );
			}
		},

		/**
		 * Gets widget instance by element which may be
		 * widget's wrapper or any of its children.
		 *
		 * @param {CKEDITOR.dom.element} element
		 * @param {Boolean} [checkWrapperOnly] Check only if `element` equals wrapper.
		 * @returns {CKEDITOR.plugins.widget} Widget instance or `null`.
		 */
		getByElement: function( element, checkWrapperOnly ) {
			if ( !element )
				return null;

			var wrapper;

			for ( var id in this.instances ) {
				wrapper = this.instances[ id ].wrapper;
				if ( wrapper.equals( element ) || ( !checkWrapperOnly && wrapper.contains( element ) ) )
					return this.instances[ id ];
			}

			return null;
		},

		/**
		 * Initializes widget on given element if widget hasn't
		 * been initialzed on it yet.
		 *
		 * @param {CKEDITOR.dom.element} element
		 * @param {String/CKEDITOR.plugins.widget.definition} widgetDef Name of a widget type or a widget definition.
		 * Widget definition should be previously registered by {@link CKEDITOR.plugins.widget.repository#add}.
		 * @param startupData Widget's startup data (has precedence over defaults one).
		 * @returns {CKEDITOR.plugins.widget} The widget instance or null if there's no widget for given element.
		 */
		initOn: function( element, widgetDef, startupData ) {
			if ( !widgetDef )
				widgetDef = this.registered[ element.data( 'widget' ) ];
			else if ( typeof widgetDef == 'string' )
				widgetDef = this.registered[ widgetDef ];

			if ( !widgetDef )
				return null;

			// Wrap element if still wasn't wrapped (was added during runtime by method that skips dataProcessor).
			var wrapper = this.wrapElement( element, widgetDef.name );

			if ( wrapper ) {
				// Check if widget wrapper is new (widget hasn't been initialzed on it yet).
				// This class will be removed by widget constructor to avoid locking snapshot twice.
				if ( wrapper.hasClass( 'cke_widget_new' ) ) {
					var widget = new Widget( this, this._.nextId++, element, widgetDef, startupData );

					// Widget could be destroyed when initializing it.
					if ( widget.isInited() ) {
						this.instances[ widget.id ] = widget;

						return widget;
					} else
						return null;
				}

				// Widget already has been initialized, so try to widget by element
				return this.getByElement( element );
			}

			// No wrapper means that there's no widget for this element.
			return null;
		},

		/**
		 * Initializes widgets on all elements which were wrapped by {@link #wrapElement} and
		 * haven't been initialized yet.
		 *
		 * @param {CKEDITOR.dom.element} [container=editor.editable()] Container which will be checked for not
		 * initialized widgets. Defaults to editor's editable element.
		 * @returns {CKEDITOR.plugins.widget[]} Array of widget instances which have been initialized.
		 */
		initOnAll: function( container ) {
			var newWidgets = ( container || this.editor.editable() ).find( '.cke_widget_new' ),
				newInstances = [],
				instance;

			for ( var i = newWidgets.count(); i--; ) {
				instance = this.initOn( newWidgets.getItem( i ).getFirst( isWidgetElement2 ) );
				if ( instance )
					newInstances.push( instance );
			}

			return newInstances;
		},

		/**
		 * Wraps element with a widget container.
		 *
		 * If this method is called on {@link CKEDITOR.htmlParser.element}, then it will
		 * also take care of fixing DOM after wrapping (wrapper may not be allowed in element's parent).
		 *
		 * @param {CKEDITOR.dom.element/CKEDITOR.htmlParser.element} The widget element to be wrapperd.
		 * @param {String} [widgetName]
		 * @returns {CKEDITOR.dom.element/CKEDITOR.htmlParser.element} The wrapper element or `null` if
		 * widget of this type is not registered.
		 */
		wrapElement: function( element, widgetName ) {
			var wrapper = null,
				widgetDef,
				isInline;

			if ( element instanceof CKEDITOR.dom.element ) {
				widgetDef = this.registered[ widgetName || element.data( 'widget' ) ];
				if ( !widgetDef )
					return null;

				// Do not wrap already wrapped element.
				wrapper = element.getParent();
				if ( wrapper && wrapper.type == CKEDITOR.NODE_ELEMENT && wrapper.data( 'cke-widget-wrapper' ) )
					return wrapper;

				// If attribute isn't already set (e.g. for pasted widget), set it.
				if ( !element.hasAttribute( 'data-cke-widget-keep-attr' ) )
					element.data( 'cke-widget-keep-attr', element.data( 'widget' ) ? 1 : 0 );
				if ( widgetName )
					element.data( 'widget', widgetName );

				isInline = isWidgetInline( widgetDef, element.getName() );

				wrapper = new CKEDITOR.dom.element( isInline ? 'span' : 'div' );
				wrapper.setAttributes( getWrapperAttributes( isInline ) );

				// Replace element unless it is a detached one.
				if ( element.getParent( true ) )
					wrapper.replace( element );
				element.appendTo( wrapper );
			}
			else if ( element instanceof CKEDITOR.htmlParser.element ) {
				widgetDef = this.registered[ widgetName || element.attributes[ 'data-widget' ] ];
				if ( !widgetDef )
					return null;

				wrapper = element.parent;
				if ( wrapper && wrapper.type == CKEDITOR.NODE_ELEMENT && wrapper.attributes[ 'data-cke-widget-wrapper' ] )
					return wrapper;

				// If attribute isn't already set (e.g. for pasted widget), set it.
				if ( !( 'data-cke-widget-keep-attr' in element.attributes ) )
					element.attributes[ 'data-cke-widget-keep-attr' ] = element.attributes[ 'data-widget' ] ? 1 : 0;
				if ( widgetName )
					element.attributes[ 'data-widget' ] = widgetName;

				isInline = isWidgetInline( widgetDef, element.name );

				wrapper = new CKEDITOR.htmlParser.element( isInline ? 'span' : 'div', getWrapperAttributes( isInline ) );

				var parent = element.parent,
					index;

				// Don't detach already detached element.
				if ( parent ) {
					index = element.getIndex();
					element.remove();
				}

				wrapper.add( element );

				// Insert wrapper fixing DOM (splitting parents if wrapper is not allowed inside them).
				parent && insertElement( parent, index, wrapper );
			}

			return wrapper;
		}

		// %REMOVE_START%
		// Expose for tests.
		,
		getNestedEditable: getNestedEditable,

		createEditableFilter: createEditableFilter

		// %REMOVE_END%
	};

	CKEDITOR.event.implementOn( Repository.prototype );


	/**
	 * @class CKEDITOR.plugins.widget
	 * @mixins CKEDITOR.event
	 */
	function Widget( widgetsRepo, id, element, widgetDef, startupData ) {
		var editor = widgetsRepo.editor;

		// Extend this widget with widgetDef-specific methods and properties.
		CKEDITOR.tools.extend( this, widgetDef, {
			/**
			 * The editor instance.
			 *
			 * @readonly
			 * @property {CKEDITOR.editor}
			 */
			editor: editor,

			/**
			 * This widget's unique (per editor instance) id.
			 *
			 * @readonly
			 * @property {Number}
			 */
			id: id,

			inline: element.getParent().getName() == 'span',

			/**
			 * Widget's main element.
			 *
			 * @readonly
			 * @property {CKEDITOR.dom.element}
			 */
			element: element,

			/**
			 * Widget's data object.
			 *
			 * Data can only be set by {@link #setData} method.
			 *
			 * @readonly
			 */
			data: CKEDITOR.tools.extend( {}, typeof widgetDef.defaults == 'function' ? widgetDef.defaults() : widgetDef.defaults ),

			/**
			 * Is data ready. Set to `true` when data from all sources
			 * ({@link CKEDITOR.plugins.widget.definition#defaults}, set
			 * in {@link #init} method and loaded from widget's element)
			 * are finally loaded. This is immediately followed by first {@link #event-data}.
			 *
			 * @readonly
			 */
			dataReady: false,

			// Revert what widgetDef could override (automatic #edit listener).
			edit: Widget.prototype.edit,

			/**
			 * Contains nested editable which currently holds focus.
			 *
			 * @readonly
			 * @property {CKEDITOR.dom.element}
			 */
			focusedEditable: null,

			// WAAARNING: Overwrite widgetDef's priv object, because otherwise violent unicorn's gonna visit you.
			_: {
				downcastFn: ( widgetDef.downcast && typeof widgetDef.downcast == 'string' ) ?
					widgetDef.downcasts[ widgetDef.downcast ] : widgetDef.downcast
			}
		}, true );

		/**
		 * Object of widget's component elements.
		 *
		 * For every `partName => selector` pair in {@link CKEDITOR.plugins.widget.definition#parts}
		 * one `partName => element` pair is added to this object during
		 * widget initialization.
		 *
		 * @property {Object} parts
		 */

		widgetsRepo.fire( 'instanceCreated', this );

		setupWidget( this, widgetDef );

		this.init && this.init();

		// Finally mark widget as inited.
		this.inited = true;

		setupWidgetData( this, startupData );

		// If at some point (e.g. in #data listener) widget hasn't been destroyed
		// and widget is already attached to document then fire #ready.
		if ( this.isInited() && editor.editable().contains( this.wrapper ) ) {
			this.ready = true;
			this.fire( 'ready' );
		}
	}

	Widget.prototype = {
		/**
		 * Destroys this widget instance.
		 *
		 * Use {@link CKEDITOR.plugins.widget.repository#destroy} when possible instead of this method.
		 *
		 * This method fires {#event-destroy} event.
		 *
		 * @param {Boolean} [offline] Whether widget is offline (detached from DOM tree) -
		 * in this case DOM (attributes, classes, etc.) will not be cleaned up.
		 */
		destroy: function( offline ) {
			var editor = this.editor;

			this.fire( 'destroy' );

			if ( this.editables ) {
				for ( var name in this.editables )
					this.destroyEditable( name, offline );
			}

			if ( !offline ) {
				if ( this.element.data( 'cke-widget-keep-attr' ) == '0' )
					this.element.removeAttribute( 'data-widget' );
				this.element.removeAttributes( [ 'data-cke-widget-data', 'data-cke-widget-keep-attr' ] );
				this.element.removeClass( 'cke_widget_element' );
				this.element.replace( this.wrapper );
			}

			this.wrapper = null;
		},

		/**
		 * Destroys nested editable.
		 *
		 * @param {String} editableName Nested editable name.
		 * @param {Boolean} [offline] See {@link #method-destroy} method.
		 */
		destroyEditable: function( editableName, offline ) {
			var editable = this.editables[ editableName ];

			editable.removeListener( 'focus', onEditableFocus );
			editable.removeListener( 'blur', onEditableBlur );
			this.editor.focusManager.remove( editable );

			if ( !offline ) {
				editable.removeClass( 'cke_widget_editable' );
				editable.removeClass( 'cke_widget_editable_focused' );
				editable.removeAttributes( [ 'contenteditable', 'data-cke-widget-editable' ] );
			}

			delete this.editables[ editableName ];
		},

		/**
		 * Starts widget editing.
		 *
		 * This method fires {@link CKEDITOR.plugins.widget#event-edit} event
		 * which may be cancelled in order to prevent from opening dialog.
		 *
		 * Dialog name is obtained from event's data `dialog` property or
		 * from {@link CKEDITOR.plugins.widget.definition#dialog}.
		 */
		edit: function() {
			var evtData = { dialog: this.dialog },
				that = this;

			// Edit event was blocked, but there's no dialog to be automatically opened.
			if ( !this.fire( 'edit', evtData ) || !evtData.dialog )
				return;

			this.editor.openDialog( evtData.dialog, function( dialog ) {
				var showListener,
					okListener;

				// Allow to add a custom dialog handler.
				if ( !that.fire( 'dialog', dialog ) )
					return;

				// Make widget accessible beyond setup and commit.
				dialog._.widget = that;

				showListener = dialog.on( 'show', function() {
					dialog.setupContent( that );
				} );

				okListener = dialog.on( 'ok', function() {
					// Commit dialog's fields, but prevent from
					// firing data event for every field. Fire only one,
					// bulk event at the end.
					var dataChanged,
						dataListener = that.on( 'data', function( evt ) {
							dataChanged = 1;
							evt.cancel();
						}, null, null, 0 );

					// Create snapshot preceeding snapshot with changed widget...
					// TODO it should not be required, but it is and I found similar
					// code in dialog#ok listener in dialog/plugin.js.
					that.editor.fire( 'saveSnapshot' );
					dialog.commitContent( that );

					dataListener.removeListener();
					if ( dataChanged ) {
						that.fire( 'data', that.data );
						that.editor.fire( 'saveSnapshot' );
					}
				} );

				dialog.once( 'hide', function() {
					showListener.removeListener();
					okListener.removeListener();
				} );
			} );
		},

		/**
		 * Initializes nested editable.
		 *
		 * **Note**: only elements from {@link CKEDITOR.dtd#$editable} may become editables.
		 *
		 * @param {String} editableName The nested editable name.
		 * @param {CKEDITOR.plugins.widget.nestedEditableDefinition} definition The definition of nested editable.
		 * @returns {Boolean} Whether an editable was successfully initialized.
		 */
		initEditable: function( editableName, definition ) {
			var editable = this.wrapper.findOne( definition.selector );

			if ( editable && editable.is( CKEDITOR.dtd.$editable ) ) {
				editable = new NestedEditable( this.editor, editable, {
					filter: createEditableFilter.call( this.repository, this.name, editableName, definition )
				} );
				this.editables[ editableName ] = editable;

				editable.setAttributes( {
					contenteditable: 'true',
					'data-cke-widget-editable': editableName
				} );
				editable.addClass( 'cke_widget_editable' );
				// This class may be left when d&ding widget which
				// had focused editable. Clean this class here, not in
				// cleanUpWidgetElement for performance and code size reasons.
				editable.removeClass( 'cke_widget_editable_focused' );

				this.editor.focusManager.add( editable );
				editable.on( 'focus', onEditableFocus, this );
				CKEDITOR.env.ie && editable.on( 'blur', onEditableBlur, this );

				// Finally, process editable's data. This data wasn't processed when loading
				// editor's data, becuase they need to be processed separately, with its own filters and settings.
				editable.setData( editable.getHtml() );

				return true;
			}

			return false;
		},

		/**
		 * Checks if widget has already been initialized. This means, for example,
		 * that widget has mask, element styles have been transferred to wrapper etc.
		 *
		 * @returns {Boolean}
		 */
		isInited: function() {
			return !!( this.wrapper && this.inited );
		},

		/**
		 * TODO
		 *
		 * @returns {Boolean}
		 */
		isReady: function() {
			return this.isInited() && this.ready;
		},

		/**
		 * Focuses widget by selecting it.
		 */
		focus: function() {
			var sel = this.editor.getSelection();

			if ( sel )
				sel.fake( this.wrapper );

			// Always focus editor (not only when focusManger.hasFocus is false) (because of #10483).
			this.editor.focus();
		},

		/**
		 * Sets widget value(s) in {@link #propeorty-data} object.
		 * If given value(s) modifies current ones {@link #event-data} event is fired.
		 *
		 *		this.setData( 'align', 'left' );
		 *		this.data.align; // -> 'left'
		 *
		 *		this.setData( { align: 'right', opened: false } );
		 *		this.data.align; // -> 'right'
		 *		this.data.opened; // -> false
		 *
		 * Set values are stored in {@link #element}'s attribute (`data-cke-widget-data`),
		 * in JSON string, so therefore {@link #property-data} should contain
		 * only serializable data.
		 *
		 * @param {String/Object} keyOrData
		 * @param {Object} value
		 * @chainable
		 */
		setData: function( key, value ) {
			var data = this.data,
				modified = 0;

			if ( typeof key == 'string' ) {
				if ( data[ key ] !== value ) {
					data[ key ] = value;
					modified = 1;
				}
			}
			else {
				var newData = key;

				for ( key in newData ) {
					if ( data[ key ] !== newData[ key ] ) {
						modified = 1;
						data[ key ] = newData[ key ];
					}
				}
			}

			// Block firing data event and overwriting data element before setupWidgetData is executed.
			if ( modified && this.dataReady ) {
				writeDataToElement( this );
				this.fire( 'data', data );
			}

			return this;
		},

		/**
		 * Changes widget's focus state. Usually executed automatically after
		 * widget has been focused by {@link #focus} method or selection was moved
		 * out of widget.
		 *
		 * @param {Boolean} selected Whether to select or deselect this widget.
		 * @chainable
		 */
		setFocused: function( focused ) {
			this.wrapper[ focused ? 'addClass' : 'removeClass' ]( 'cke_widget_focused' );
			this.fire( focused ? 'focus' : 'blur' );
			return this;
		},

		/**
		 * Changes widget's select state. Usually executed automatically after
		 * widget has been selected by {@link #focus} method or selection was moved
		 * out of widget.
		 *
		 * @param {Boolean} selected Whether to select or deselect this widget.
		 * @chainable
		 */
		setSelected: function( selected ) {
			this.wrapper[ selected ? 'addClass' : 'removeClass' ]( 'cke_widget_selected' );
			this.fire(  selected ? 'select' : 'deselect' );
			return this;
		}
	};

	CKEDITOR.event.implementOn( Widget.prototype );


	/**
	 * Wrapper class for editable elements inside widgets.
	 *
	 * Don't use directly. Use {@link CKEDITOR.plugins.widget.definition#editables} or
	 * {@link CKEDITOR.plugins.widget#initEditable}.
	 *
	 * @class CKEDITOR.plugins.widget.nestedEditable
	 * @extends CKEDITOR.dom.element
	 * @constructor
	 * @param {CKEDITOR.editor} editor
	 * @param {CKEDITOR.dom.element} element
	 * @param config
	 * @param {CKEDITOR.filter} [config.filter]
	 */
	function NestedEditable( editor, element, config ) {
		// Call the base constructor.
		CKEDITOR.dom.element.call( this, element.$ );
		this.editor = editor;
		this.filter = config.filter;
	}

	NestedEditable.prototype = CKEDITOR.tools.extend( CKEDITOR.tools.prototypedCopy( CKEDITOR.dom.element.prototype ), {
		setData: function( data ) {
			data = this.editor.dataProcessor.toHtml( data, {
				context: this.getName(),
				filter: this.filter,
				enterMode: this.filter ? this.filter.getAllowedEnterMode() : this.editor.enterMode
			} );
			this.setHtml( data );
		},

		getData: function() {
			return this.editor.dataProcessor.toDataFormat( this.getHtml(), {
				context: this.getName(),
				filter: this.filter,
				enterMode: this.filter ? this.filter.getAllowedEnterMode() : this.editor.enterMode
			} );
		}
	} );


	//
	// REPOSITORY helpers -----------------------------------------------------
	//

	function addWidgetButtons( editor ) {
		var widgets = editor.widgets.registered,
			widget,
			widgetName,
			widgetButton;

		for ( widgetName in widgets ) {
			widget = widgets[ widgetName ];

			// Create button if defined.
			widgetButton = widget.button;
			if ( widgetButton && editor.ui.addButton ) {
				editor.ui.addButton( CKEDITOR.tools.capitalize( widget.name, true ), {
					label: widgetButton,
					command: widget.name,
					toolbar: 'insert,10'
				} );
			}
		}
	}

	// Create a command creating and editing widget.
	//
	// @param editor
	// @param {CKEDITOR.plugins.widget.registeredDefinition} widgetDef
	function addWidgetCommand( editor, widgetDef ) {
		editor.addCommand( widgetDef.name, {
			exec: function() {
				var focused = editor.widgets.focused;
				// If a widget of the same type is focused, start editing.
				if ( focused && focused.name == widgetDef.name )
					focused.edit();
				// Otherwise...
				// ... use insert method is was defined.
				else if ( widgetDef.insert )
					widgetDef.insert();
				// ... or create a brand-new widget from template.
				else if ( widgetDef.template ) {
					var defaults = typeof widgetDef.defaults == 'function' ? widgetDef.defaults() : widgetDef.defaults,
						element = CKEDITOR.dom.element.createFromHtml( widgetDef.template.output( defaults ) ),
						instance,
						wrapper = editor.widgets.wrapElement( element, widgetDef.name ),
						temp = new CKEDITOR.dom.documentFragment( wrapper.getDocument() ),
						editWasCanceled = true;

					// Append wrapper to a temporary document. This will unify the environment
					// in which #data listeners work when creating and editing widget.
					temp.append( wrapper );
					instance = editor.widgets.initOn( element, widgetDef );

					// Instance could be destroyed during initialization.
					// In this case finalize creation if some new widget
					// was left in temporary document fragment.
					if ( !instance ) {
						finalizeCreation();
						return;
					}

					// Listen on edit to finalize widget insertion.
					//
					// * If dialog was set, then insert widget after dialog was successfully saved or destroy this
					// temporary instance.
					// * If dialog wasn't set and edit wasn't canceled, insert widget.
					var editListener = instance.once( 'edit', function( evt ) {
						editWasCanceled = false;

						if ( evt.data.dialog ) {
							instance.once( 'dialog', function( evt ) {
								var dialog = evt.data,
									okListener,
									cancelListener;

								// Finalize creation AFTER (20) new data was set.
								okListener = dialog.once( 'ok', finalizeCreation, null, null, 20 );

								cancelListener = dialog.once( 'cancel', function() {
									editor.widgets.destroy( instance, true );
								} );

								dialog.once( 'hide', function() {
									okListener.removeListener();
									cancelListener.removeListener();
								} );
							} );
						}
						// Dialog hasn't been set, so insert widget now.
						else
							finalizeCreation();
					}, null, null, 999 );

					instance.edit();

					// Remove listener in case someone canceled it before this
					// listener was executed.
					editListener.removeListener();

					// In case edit was canceled - finalize creation here which should happen anyway (just without
					// initial edit).
					if ( editWasCanceled )
						finalizeCreation();
				}

				function finalizeCreation() {
					var wrapper = temp.getFirst();
					if ( wrapper && isWidgetWrapper2( wrapper ) ) {
						editor.insertElement( wrapper );

						var widget = editor.widgets.getByElement( wrapper );
						// Fire postponed #ready event.
						widget.ready = true;
						widget.fire( 'ready' );
						widget.focus();
					}
				}
			},

			refresh: function( editor, path ) {
				// Disable widgets' commands inside nested editables -
				// check if blockLimit is a nested editable or a descendant of any.
				this.setState( getNestedEditable( editor.editable(), path.blockLimit ) ? CKEDITOR.TRISTATE_DISABLED : CKEDITOR.TRISTATE_OFF );
			},
			// A hack to force command refreshing on context change.
			context: 'div',

			allowedContent: widgetDef.allowedContent,
			requiredContent: widgetDef.requiredContent,
			contentForms: widgetDef.contentForms,
			contentTransformations: widgetDef.contentTransformations
		} );
	}

	function addWidgetProcessors( widgetsRepo, widgetDef ) {
		var upcast = widgetDef.upcast,
			upcasts;

		if ( !upcast )
			return;

		// Multiple upcasts defined in string.
		if ( typeof upcast == 'string' ) {
			upcasts = upcast.split( ',' );
			while ( upcasts.length )
				widgetsRepo._.upcasts.push( [ widgetDef.upcasts[ upcasts.pop() ], widgetDef.name ] );
		}
		// Single rule which is automatically activated.
		else
			widgetsRepo._.upcasts.push( [ upcast, widgetDef.name ] );
	}

	function blurWidget( widgetsRepo, widget ) {
		widgetsRepo.focused = null;

		if ( widget.isInited() ) {
			// Widget could be destroyed in the meantime - e.g. data could be set.
			widgetsRepo.fire( 'widgetBlurred', { widget: widget } );
			widget.setFocused( false );
		}
	}

	// Unwraps widget element and clean up element.
	//
	// This function is used to clean up pasted widgets.
	// It should have similar result to widget#destroy plus
	// some additional adjustments, specific for pasting.
	//
	// @param {CKEDITOR.htmlParser.element} el
	function cleanUpWidgetElement( el ) {
		var parent = el.parent;
		if ( parent.type == CKEDITOR.NODE_ELEMENT && parent.attributes[ 'data-cke-widget-wrapper' ] )
			parent.replaceWith( el );
	}

	// Similar to cleanUpWidgetElement, but works on DOM and finds
	// widget elements by its own.
	//
	// Unlike cleanUpWidgetElement it will wrap element back.
	//
	// @param {CKEDITOR.dom.element} container
	function cleanUpAllWidgetElements( widgetsRepo, container ) {
		var wrappers = container.find( '.cke_widget_wrapper' ),
			wrapper, element,
			i = 0,
			l = wrappers.count();

		for ( ; i < l; ++i ) {
			wrapper = wrappers.getItem( i );
			element = wrapper.getFirst( isWidgetElement2 );
			// If wrapper contains widget element - unwrap it and wrap again.
			if ( element.type == CKEDITOR.NODE_ELEMENT && element.data( 'widget' ) ) {
				element.replace( wrapper );
				widgetsRepo.wrapElement( element );
			}
			// Otherwise - something is wrong... clean this up.
			else
				wrapper.remove();
		}
	}

	// Creates {@link CKEDITOR.filter} instance for given widget, editable and rules.
	//
	// Once filter for widget-editable pair is created it is cached, so the same instance
	// will be returned when method is executed again.
	//
	// @param {String} widgetName
	// @param {String} editableName
	// @param {CKEDITOR.plugins.widget.nestedEditableDefinition} editableDefinition The nested editable definition.
	// @returns {CKEDITOR.filter} Filter instance or `null` if rules are not defined.
	// @context CKEDITOR.plugins.widget.repository
	function createEditableFilter( widgetName, editableName, editableDefinition ) {
		if ( !editableDefinition.allowedContent )
			return null;

		var editables = this._.filters[ widgetName ];

		if ( !editables )
			this._.filters[ widgetName ] = editables = {};

		var filter = editables[ editableName ];

		if ( !filter )
			editables[ editableName ] = filter = new CKEDITOR.filter( editableDefinition.allowedContent );

		return filter;
	}

	// Gets nested editable if node is its descendant or the editable itself.
	//
	// @param {CKEDITOR.dom.element} guard Stop ancestor search on this node (usually editor's editable).
	// @param {CKEDITOR.dom.node} node Start search from this node.
	// @returns {CKEDITOR.dom.element} Element or null.
	function getNestedEditable( guard, node ) {
		if ( !node || node.equals( guard ) )
			return null;

		if ( isNestedEditable2( node ) )
			return node;

		return getNestedEditable( guard, node.getParent() );
	}

	function getWrapperAttributes( inlineWidget ) {
		return {
			// tabindex="-1" means that it can receive focus by code.
			tabindex: -1,
			contenteditable: 'false',
			'data-cke-widget-wrapper': 1,
			'data-cke-filter': 'off',
			// Class cke_widget_new marks widgets which haven't been initialized yet.
			'class': 'cke_widget_wrapper cke_widget_new cke_widget_' +
				( inlineWidget ? 'inline' : 'block' )
		};
	}

	// Inserts element at given index.
	// It will check DTD and split ancestor elements up to the first
	// that can contain this element.
	//
	// @param {CKEDITOR.htmlParser.element} parent
	// @param {Number} index
	// @param {CKEDITOR.htmlParser.element} element
	function insertElement( parent, index, element ) {
		// Do not split doc fragment...
		if ( parent.type == CKEDITOR.NODE_ELEMENT ) {
			var parentAllows = CKEDITOR.dtd[ parent.name ];
			// Parent element is known (included in DTD) and cannot contain
			// this element.
			if ( parentAllows && !parentAllows[ element.name ] ) {
				var parent2 = parent.split( index ),
					parentParent = parent.parent;

				// Element will now be inserted at right parent's index.
				index = parent2.getIndex();

				// If left part of split is empty - remove it.
				if ( !parent.children.length ) {
					index -= 1;
					parent.remove();
				}

				// If right part of split is empty - remove it.
				if ( !parent2.children.length )
					parent2.remove();

				// Try inserting as grandpas' children.
				return insertElement( parentParent, index, element );
			}
		}

		// Finally we can add this element.
		parent.add( element, index );
	}

	// @param {CKEDITOR.htmlParser.element}
	function isWidgetElement( element ) {
		return element.type == CKEDITOR.NODE_ELEMENT && !!element.attributes[ 'data-widget' ];
	}

	// @param {CKEDITOR.dom.element}
	function isWidgetElement2( element ) {
		return element.type == CKEDITOR.NODE_ELEMENT && element.hasAttribute( 'data-widget' );
	}

	// Whether for this definition and element widget should be created in inline or block mode.
	function isWidgetInline( widgetDef, elementName ) {
		return typeof widgetDef.inline == 'boolean' ? widgetDef.inline : !!CKEDITOR.dtd.$inline[ elementName ];
	}

	// @param {CKEDITOR.htmlParser.element}
	function isWidgetWrapper( element ) {
		return element.type == CKEDITOR.NODE_ELEMENT && element.attributes[ 'data-cke-widget-wrapper' ];
	}

	// @param {CKEDITOR.dom.element}
	function isWidgetWrapper2( element ) {
		return element.type == CKEDITOR.NODE_ELEMENT && element.hasAttribute( 'data-cke-widget-wrapper' );
	}

	// @param {CKEDITOR.dom.element}
	function isNestedEditable2( node ) {
		return node.type == CKEDITOR.NODE_ELEMENT && node.hasAttribute( 'data-cke-widget-editable' );
	}

	function moveSelectionToDropPosition( editor, dropEvt ) {
		var $evt = dropEvt.data.$,
			$range,
			range = editor.createRange();

		// Make testing possible.
		if ( dropEvt.data.testRange ) {
			dropEvt.data.testRange.select();
			return;
		}

		// Webkits.
		if ( document.caretRangeFromPoint ) {
			$range = editor.document.$.caretRangeFromPoint( $evt.clientX, $evt.clientY );
			range.setStart( CKEDITOR.dom.node( $range.startContainer ), $range.startOffset );
			range.collapse( true );
		}
		// FF.
		else if ( $evt.rangeParent ) {
			range.setStart( CKEDITOR.dom.node( $evt.rangeParent ), $evt.rangeOffset );
			range.collapse( true );
		}
		// IEs.
		else if ( document.body.createTextRange ) {
			$range = editor.document.getBody().$.createTextRange();
			$range.moveToPoint( $evt.clientX, $evt.clientY );
			var id = 'cke-temp-' + ( new Date() ).getTime();
			$range.pasteHTML( '<span id="' + id + '">\u200b</span>' );

			var span = editor.document.getById( id );
			range.moveToPosition( span, CKEDITOR.POSITION_BEFORE_START );
			span.remove();
		}

		range.select();
	}

	function moveWidget( editor, sourceWidget ) {
		var widgetHtml = sourceWidget.wrapper.getOuterHtml();

		sourceWidget.wrapper.remove();
		editor.widgets.destroy( sourceWidget, true );

		// Create snapshot for the removed widget.
		editor.fire( 'saveSnapshot' );

		// Lock snapshot while pasting to merge those changes with the previous snapshot.
		// This way we are grouping all changes done by moveWidget into one snapshot.
		editor.fire( 'lockSnapshot' );
		editor.execCommand( 'paste', widgetHtml );
		editor.fire( 'unlockSnapshot' );
	}

	function onEditableKey( widget, keyCode ) {
		var focusedEditable = widget.focusedEditable,
			range;

		// CTRL+A.
		if ( keyCode == CKEDITOR.CTRL + 65 ) {
			var bogus = focusedEditable.getBogus();

			range = widget.editor.createRange();
			range.selectNodeContents( focusedEditable );
			// Exclude bogus if exists.
			if ( bogus )
				range.setEndAt( bogus, CKEDITOR.POSITION_BEFORE_START );

			range.select();
			// Cancel event - block default.
			return false;
		}
		// DEL or BACKSPACE.
		else if ( keyCode == 8 || keyCode == 46 ) {
			var ranges = widget.editor.getSelection().getRanges();

			range = ranges[ 0 ];

			// Block del or backspace if at editable's boundary.
			return !( ranges.length == 1 && range.collapsed &&
				range.checkBoundaryOfElement( focusedEditable, CKEDITOR[ keyCode == 8 ? 'START' : 'END' ] ) );
		}
	}

	function setFocusedEditable( widgetsRepo, widget, editableElement, offline ) {
		widgetsRepo.editor.fire( 'lockSnapshot' );

		if ( editableElement ) {
			var editableName = editableElement.data( 'cke-widget-editable' ),
				editableInstance = widget.editables[ editableName ];

			widgetsRepo.widgetHoldingFocusedEditable = widget;
			widget.focusedEditable = editableInstance;
			editableElement.addClass( 'cke_widget_editable_focused' );

			if ( editableInstance.filter )
				widgetsRepo.editor.setActiveFilter( editableInstance.filter );
		} else {
			if ( !offline )
				widget.focusedEditable.removeClass( 'cke_widget_editable_focused' );

			widget.focusedEditable = null;
			widgetsRepo.widgetHoldingFocusedEditable = null;
			widgetsRepo.editor.setActiveFilter( null );
		}

		widgetsRepo.editor.fire( 'unlockSnapshot' );
	}

	function setupContextMenu( editor ) {
		if ( !editor.contextMenu )
			return;

		editor.contextMenu.addListener( function( element ) {
			var widget = editor.widgets.getByElement( element, true );

			if ( widget )
				return widget.fire( 'contextMenu', {} );
		} );
	}

	// Set up data processing like:
	// * toHtml/toDataFormat,
	// * pasting handling,
	// * undo/redo handling.
	function setupDataProcessing( widgetsRepo ) {
		var editor = widgetsRepo.editor;

		setupUpcasting( widgetsRepo );
		setupDowncasting( widgetsRepo );

		editor.on( 'contentDomUnload', function() {
			widgetsRepo.destroyAll( true );
		} );

		// Handle pasted single widget.
		editor.on( 'paste', function( evt ) {
			evt.data.dataValue = evt.data.dataValue.replace(
				/^(?:<div id="cke_copybin">)?<span [^>]*data-cke-copybin-start="1"[^>]*>.?<\/span>([\s\S]+)<span [^>]*data-cke-copybin-end="1"[^>]*>.?<\/span>(?:<\/div>)?$/,
				'$1'
			);
		} );
	}

	function setupDowncasting( widgetsRepo ) {
		var editor = widgetsRepo.editor,
			downcastingSessions = {},
			nestedEditableScope = false;

		// Listen before htmlDP#htmlFilter is applied to cache all widgets, because we'll
		// loose data-cke-* attributes.
		editor.on( 'toDataFormat', function( evt ) {
			// To avoid conflicts between htmlDP#toDF calls done at the same time
			// (e.g. nestedEditable#getData called during downcasting some widget)
			// mark every toDataFormat event chain with the downcasting session id.
			var id = CKEDITOR.tools.getNextNumber(),
				toBeDowncasted = [];
			evt.data.downcastingSessionId = id;
			downcastingSessions[ id ] = toBeDowncasted;

			evt.data.dataValue.forEach( function( element ) {
				var attrs = element.attributes,
					widget, widgetElement;

				// Wrapper.
				// Perform first part of downcasting (cleanup) and cache widgets,
				// because after applying DP's filter all data-cke-* attributes will be gone.
				if ( 'data-cke-widget-id' in attrs ) {
					widget = widgetsRepo.instances[ attrs[ 'data-cke-widget-id' ] ];
					if ( widget ) {
						widgetElement = element.getFirst( isWidgetElement );
						toBeDowncasted.push( {
							wrapper: element,
							element: widgetElement,
							widget: widget
						} );

						// If widget did not have data-cke-widget attribute before upcasting remove it.
						if ( widgetElement.attributes[ 'data-cke-widget-keep-attr' ] != '1' )
							delete widgetElement.attributes[ 'data-widget' ];
					}
				}
				// Nested editable.
				else if ( 'data-cke-widget-editable' in attrs ) {
					delete attrs[ 'contenteditable' ];

					// Replace nested editable's content with its output data.
					var editable = toBeDowncasted[ toBeDowncasted.length - 1 ].widget.editables[ attrs[ 'data-cke-widget-editable' ] ];
					element.setHtml( editable.getData() );

					// Don't check children - there won't be next wrapper or nested editable which we
					// should process in this session.
					return false;
				}
			}, CKEDITOR.NODE_ELEMENT );
		}, null, null, 8 );

		// Listen after dataProcessor.htmlFilter and ACF were applied
		// so wrappers securing widgets' contents are removed after all filtering was done.
		editor.on( 'toDataFormat', function( evt ) {
			// Ignore some unmarked sessions.
			if ( !evt.data.downcastingSessionId )
				return;

			var toBeDowncasted = downcastingSessions[ evt.data.downcastingSessionId ],
				toBe, widget, widgetElement, retElement;

			while ( ( toBe = toBeDowncasted.shift() ) ) {
				widget = toBe.widget;
				widgetElement = toBe.element;
				retElement = widget._.downcastFn && widget._.downcastFn.call( widget, widgetElement );

				// Returned element always defaults to widgetElement.
				if ( !retElement )
					retElement = widgetElement;

				toBe.wrapper.replaceWith( retElement );
			}
		}, null, null, 13 );
	}

	function setupDragAndDrop( widgetsRepo ) {
		var editor = widgetsRepo.editor;

		editor.on( 'contentDom', function() {
			var editable = editor.editable();

			editable.attachListener( editable, 'drop', function( evt ) {
				var dataStr = evt.data.$.dataTransfer.getData( 'text' ),
					dataObj,
					sourceWidget;

				if ( !dataStr )
					return;

				try {
					dataObj = JSON.parse( dataStr );
				} catch ( e ) {
					// Do nothing - data couldn't be parsed so it's not a CKEditor's data.
					return;
				}

				if ( dataObj.type != 'cke-widget' )
					return;

				evt.data.preventDefault();

				// Something went wrong... maybe someone is dragging widgets between editors/windows/tabs/browsers/frames.
				if ( dataObj.editor != editor.name || !( sourceWidget = widgetsRepo.instances[ dataObj.id ] ) )
					return;

				// Save the snapshot with the state before moving widget.
				// TODO unfortunately at this stage widget is not focused any more so
				// undoing will not select widget which was moved.
				editor.fire( 'saveSnapshot' );

				moveSelectionToDropPosition( editor, evt );

				// Hack to prevent cursor loss on Firefox. Without timeout widget is
				// correctly pasted but then cursor is invisible (although it works) and can be restored
				// only by blurring editable.
				if ( CKEDITOR.env.gecko )
					setTimeout( moveWidget, 0, editor, sourceWidget );
				else
					moveWidget( editor, sourceWidget );
			} );
		} );
	}

	// Setup mouse observer which will trigger:
	// * widget focus on widget click,
	// * widget#doubleclick forwarded from editor#doubleclick.
	function setupMouseObserver( widgetsRepo ) {
		var editor = widgetsRepo.editor;

		editor.on( 'contentDom', function() {
			var editable = editor.editable(),
				evtRoot = editable.isInline() ? editable : editor.document,
				widget,
				mouseDownOnDragHandler;

			editable.attachListener( evtRoot, 'mousedown', function( evt ) {
				var target = evt.data.getTarget();

				widget = widgetsRepo.getByElement( target );
				mouseDownOnDragHandler = 0; // Reset.

				// Ignore mousedown on drag and drop handler.
				if ( target.type == CKEDITOR.NODE_ELEMENT && target.hasAttribute( 'data-cke-widget-drag-handler' ) ) {
					mouseDownOnDragHandler = 1;
					return;
				}

				// Widget was clicked, but not editable nested in it.
				if ( widget ) {
					if ( !getNestedEditable( widget.wrapper, target ) ) {
						evt.data.preventDefault();
						if ( !CKEDITOR.env.ie )
							widget.focus();
					}
					// Reset widget so mouseup listener is not confused.
					else
						widget = null;
				}
			} );

			// Focus widget on mouseup if mousedown was fired on drag handler.
			// Note: mouseup won't be fired at all if widget was dragged and dropped, so
			// this code will be executed only when drag handler was clicked.
			editable.attachListener( evtRoot, 'mouseup', function() {
				if ( widget && mouseDownOnDragHandler ) {
					mouseDownOnDragHandler = 0;
					widget.focus();
				}
			} );

			// On IE it is not enough to block mousedown. If widget wrapper (element with
			// contenteditable=false attribute) is clicked directly (it is a target),
			// then after mouseup/click IE will select that element.
			// It is not possible to prevent that default action,
			// so we force fake selection after everything happened.
			if ( CKEDITOR.env.ie ) {
				editable.attachListener( evtRoot, 'mouseup', function( evt ) {
					if ( widget ) {
						setTimeout( function() {
							widget.focus();
							widget = null;
						} );
					}
				} );
			}
		} );

		editor.on( 'doubleclick', function( evt ) {
			var widget = widgetsRepo.getByElement( evt.data.element );

			// Not in widget or in nested editable.
			if ( !widget || getNestedEditable( widget.wrapper, evt.data.element ) )
				return;

			return widget.fire( 'doubleclick', { element: evt.data.element } );
		}, null, null, 1 );
	}

	// Setup editor#key observer which will forward it
	// to focused widget.
	function setupKeyboardObserver( widgetsRepo ) {
		var editor = widgetsRepo.editor;

		editor.on( 'key', function( evt ) {
			var focused = widgetsRepo.focused,
				widgetHoldingFocusedEditable = widgetsRepo.widgetHoldingFocusedEditable,
				ret;

			if ( focused )
				ret = focused.fire( 'key', { keyCode: evt.data.keyCode } );
			else if ( widgetHoldingFocusedEditable )
				ret = onEditableKey( widgetHoldingFocusedEditable, evt.data.keyCode );

			return ret;
		}, null, null, 1 );
	}

	// Setup selection observer which will trigger:
	// * widget select & focus on selection change,
	// * nested editable focus (related properites and classes) on selection change,
	// * deselecting and blurring all widgets on data,
	// * blurring widget on editor blur.
	function setupSelectionObserver( widgetsRepo ) {
		var editor = widgetsRepo.editor;

		editor.on( 'selectionCheck', function() {
			widgetsRepo.fire( 'checkSelection' );
		} );

		widgetsRepo.on( 'checkSelection', widgetsRepo.checkSelection, widgetsRepo );

		editor.on( 'selectionChange', function( evt ) {
			var nestedEditable = getNestedEditable( editor.editable(), evt.data.selection.getStartElement() ),
				newWidget = nestedEditable && widgetsRepo.getByElement( nestedEditable ),
				oldWidget = widgetsRepo.widgetHoldingFocusedEditable;

			if ( oldWidget ) {
				if ( oldWidget !== newWidget || !oldWidget.focusedEditable.equals( nestedEditable ) ) {
					setFocusedEditable( widgetsRepo, oldWidget, null );

					if ( newWidget && nestedEditable )
						setFocusedEditable( widgetsRepo, newWidget, nestedEditable );
				}
			}
			// It may happen that there's no widget even if editable was found -
			// e.g. if selection was automatically set in editable although widget wasn't initialized yet.
			else if ( newWidget && nestedEditable )
				setFocusedEditable( widgetsRepo, newWidget, nestedEditable );
		} );

		// Invalidate old widgets early - immediately on dataReady.
		editor.on( 'dataReady', function( evt ) {
			// Deselect and blur all widgets.
			stateUpdater( widgetsRepo ).commit();
		} );

		editor.on( 'blur', function() {
			var widget;

			if ( ( widget = widgetsRepo.focused ) )
				blurWidget( widgetsRepo, widget );

			if ( ( widget = widgetsRepo.widgetHoldingFocusedEditable ) )
				setFocusedEditable( widgetsRepo, widget, null );
		} );
	}

	function setupUpcasting( widgetsRepo ) {
		var editor = widgetsRepo.editor,
			upcasts = widgetsRepo._.upcasts,
			processedWidgetOnly,
			snapshotLoaded;

		editor.on( 'dataReady', function() {
			// Clean up all widgets loaded from snapshot.
			if ( snapshotLoaded )
				cleanUpAllWidgetElements( widgetsRepo, editor.editable() );
			snapshotLoaded = 0;

			// Some widgets were destroyed on contentDomUnload,
			// some on loadSnapshot, but that does not include
			// e.g. setHtml on inline editor or widgets removed just
			// before setting data.
			widgetsRepo.destroyAll( true );
			widgetsRepo.initOnAll();
		} );

		editor.on( 'afterPaste', function() {
			editor.fire( 'lockSnapshot' );

			// Init is enough (no clean up needed),
			// because inserted widgets were cleaned up by toHtml.
			var newInstances = widgetsRepo.initOnAll();

			// If just a widget was pasted and nothing more focus it.
			if ( processedWidgetOnly && newInstances.length == 1 )
				newInstances[ 0 ].focus();

			editor.fire( 'unlockSnapshot' );
		} );

		// Set flag so dataReady will know that additional
		// cleanup is needed, because snapshot containing widgets was loaded.
		editor.on( 'loadSnapshot', function( evt ) {
			// Primitive but sufficient check which will prevent from executing
			// heavier cleanUpAllWidgetElements if not needed.
			if ( ( /data-cke-widget/ ).test( evt.data ) )
				snapshotLoaded = 1;

			widgetsRepo.destroyAll( true );
		}, null, null, 9 );

		// Listen after ACF (so data are filtered),
		// but before dataProcessor.dataFilter was applied (so we can secure widgets' internals).
		editor.on( 'toHtml', function( evt ) {
			var toBeWrapped = [],
				toBe,
				element;

			evt.data.dataValue.forEach( function( element ) {
				// Wrapper found - find widget element, add it to be
				// cleaned up (unwrapped) and wrapped and stop iterating in this branch.
				if ( 'data-cke-widget-wrapper' in element.attributes ) {
					element = element.getFirst( isWidgetElement );

					if ( element )
						toBeWrapped.push( [ element ] );

					// Do not iterate over descendants.
					return false;
				}
				// Widget element found - add it to be cleaned up (just in case)
				// and wrapped and stop iterating in this branch.
				else if ( 'data-widget' in element.attributes ) {
					toBeWrapped.push( [ element ] );

					// Do not iterate over descendants.
					return false;
				}
				else if ( upcasts.length ) {
					var upcast, upcasted,
						data,
						i = 0,
						l = upcasts.length;

					for ( ; i < l; ++i ) {
						upcast = upcasts[ i ];
						data = {};

						if ( ( upcasted = upcast[ 0 ]( element, data ) ) ) {
							// If upcast function returned element, upcast this one.
							// It can be e.g. a new element wrapping the original one.
							if ( upcasted instanceof CKEDITOR.htmlParser.element )
								element = upcasted;

							// Set initial data attr with data from upcast method.
							element.attributes[ 'data-cke-widget-data' ] = JSON.stringify( data );

							toBeWrapped.push( [ element, upcast[ 1 ] ] );

							// Do not iterate over descendants.
							return false;
						}
					}
				}
			}, CKEDITOR.NODE_ELEMENT );

			// Clean up and wrap all queued elements.
			while ( ( toBe = toBeWrapped.pop() ) ) {
				cleanUpWidgetElement( toBe[ 0 ] );
				widgetsRepo.wrapElement( toBe[ 0 ], toBe[ 1 ] );
			}

			// Used to determine whether only widget was pasted.
			processedWidgetOnly = evt.data.dataValue.children.length == 1 &&
				isWidgetWrapper( evt.data.dataValue.children[ 0 ] );
		}, null, null, 8 );
	}

	// Setup observer which will trigger checkWidgets on:
	// * keyup.
	function setupWidgetsObserver( widgetsRepo ) {
		var editor = widgetsRepo.editor,
			buffer = CKEDITOR.tools.eventsBuffer( widgetsRepo.MIN_WIDGETS_CHECK_INTERVAL, function() {
				widgetsRepo.fire( 'checkWidgets' );
			} ),
			ignoredKeys = { 16:1,17:1,18:1,37:1,38:1,39:1,40:1,225:1 }; // SHIFT,CTRL,ALT,LEFT,UP,RIGHT,DOWN,RIGHT ALT(FF)

		editor.on( 'contentDom', function() {
			var editable = editor.editable();

			// Schedule check on keyup, but not more often than once per MIN_CHECK_DELAY.
			editable.attachListener( editable.isInline() ? editable : editor.document, 'keyup', function( evt ) {
				if ( !( evt.data.getKey() in ignoredKeys ) )
					buffer.input();
			}, null, null, 999 );
		} );

		editor.on( 'contentDomUnload', buffer.reset );

		widgetsRepo.on( 'checkWidgets', widgetsRepo.checkWidgets, widgetsRepo );
	}

	// Helper for coordinating which widgets should be
	// selected/deselected and which one should be focused/blurred.
	function stateUpdater( widgetsRepo ) {
		var currentlySelected = widgetsRepo.selected,
			toBeSelected = [],
			toBeDeselected = currentlySelected.slice( 0 ),
			focused = null;

		return {
			select: function( widget ) {
				if ( CKEDITOR.tools.indexOf( currentlySelected, widget ) < 0 )
					toBeSelected.push( widget );

				var index = CKEDITOR.tools.indexOf( toBeDeselected, widget );
				if ( index >= 0 )
					toBeDeselected.splice( index, 1 );

				return this;
			},

			focus: function( widget ) {
				focused = widget;
				return this;
			},

			commit: function() {
				var focusedChanged = widgetsRepo.focused !== focused,
					widget;

				widgetsRepo.editor.fire( 'lockSnapshot' );

				if ( focusedChanged && ( widget = widgetsRepo.focused ) ) {
					blurWidget( widgetsRepo, widget );
				}

				while ( ( widget = toBeDeselected.pop() ) ) {
					currentlySelected.splice( CKEDITOR.tools.indexOf( currentlySelected, widget ), 1 );
					// Widget could be destroyed in the meantime - e.g. data could be set.
					if ( widget.isInited() )
						widget.setSelected( false );
				}

				if ( focusedChanged && focused ) {
					widgetsRepo.focused = focused;
					widgetsRepo.fire( 'widgetFocused', { widget: focused } );
					focused.setFocused( true );
				}

				while ( ( widget = toBeSelected.pop() ) ) {
					currentlySelected.push( widget );
					widget.setSelected( true );
				}

				widgetsRepo.editor.fire( 'unlockSnapshot' );
			}
		};
	}


	//
	// WIDGET helpers ---------------------------------------------------------
	//

	var transparentImageData = 'data:image/gif;base64,R0lGODlhAQABAPABAP///wAAACH5BAEKAAAALAAAAAABAAEAAAICRAEAOw%3D%3D',
		// LEFT, RIGHT, UP, DOWN, DEL, BACKSPACE - unblock default fake sel handlers.
		keystrokesNotBlockedByWidget = { 37:1,38:1,39:1,40:1,8:1,46:1 };

	function cancel( evt ) {
		evt.cancel();
	}

	function copySingleWidget( widget, isCut ) {
		var editor = widget.editor,
			copybin = new CKEDITOR.dom.element( 'div', editor.document );

		copybin.setAttributes( {
			id: 'cke_copybin'
		} );

		copybin.setHtml( '<span data-cke-copybin-start="1">\u200b</span>' + widget.wrapper.getOuterHtml() + '<span data-cke-copybin-end="1">\u200b</span>' );

		// Save snapshot with the current state.
		editor.fire( 'saveSnapshot' );

		// Ignore copybin.
		editor.fire( 'lockSnapshot' );

		editor.editable().append( copybin );

		var listener1 = editor.on( 'selectionChange', cancel, null, null, 0 ),
			listener2 = widget.repository.on( 'checkSelection', cancel, null, null, 0 );

		// Once the clone of the widget is inside of copybin, select
		// the entire contents. This selection will be copied by the
		// native browser's clipboard system.
		var range = editor.createRange();
		range.selectNodeContents( copybin );
		range.select();

		setTimeout( function() {
			copybin.remove();

			if ( !isCut )
				widget.focus();

			listener1.removeListener();
			listener2.removeListener();

			editor.fire( 'unlockSnapshot' );

			if ( isCut ) {
				widget.repository.del( widget );
				editor.fire( 'saveSnapshot' );
			}
		}, 0 );
	}

	// [IE] Force keeping focus because IE sometimes forgets to fire focus on main editable
	// when blurring nested editable.
	// @context widget
	function onEditableBlur() {
		var active = CKEDITOR.document.getActive(),
			editor = this.editor,
			editable = editor.editable();

		// If focus stays within editor override blur and set currentActive because it should be
		// automatically changed to editable on editable#focus but it is not fired.
		if ( ( editable.isInline() ? editable : editor.document.getWindow().getFrame() ).equals( active ) )
			editor.focusManager.focus( editable );
	}

	// Force selectionChange when editable was focused.
	// Similar to hack in selection.js#~620.
	// @context widget
	function onEditableFocus() {
		// Gecko does not support 'DOMFocusIn' event on which we unlock selection
		// in selection.js to prevent selection locking when entering nested editables.
		if ( CKEDITOR.env.gecko )
			this.editor.unlockSelection();

		// We don't need to force selectionCheck on Webkit, because on Webkit
		// we do that on DOMFocusIn in selection.js.
		if ( !CKEDITOR.env.webkit ) {
			this.editor.forceNextSelectionCheck();
			this.editor.selectionChange( 1 );
		}
	}

	// Position drag handler according to the widget's element position.
	function positionDragHandler( widget ) {
		var handler = widget.dragHandlerContainer;

		handler.setStyle( 'top', widget.element.$.offsetTop - DRAG_HANDLER_SIZE + 'px' );
		handler.setStyle( 'left', widget.element.$.offsetLeft + 'px' );
	}

	function setupDragHandler( widget ) {
		var editor = widget.editor,
			img = new CKEDITOR.dom.element( 'img', editor.document ),
			container = new CKEDITOR.dom.element( 'span', editor.document );

		container.setAttributes( {
			'class': 'cke_widget_drag_handler_container',
			// Split background and background-image for IE8 which will break on rgba().
			style: 'background:rgba(220,220,220,0.5);background-image:url(' + editor.plugins.widget.path + 'images/handle.png)'
		} );

		img.setAttributes( {
			draggable: 'true',
			'class': 'cke_widget_drag_handler',
			'data-cke-widget-drag-handler': '1',
			src: transparentImageData,
			width: DRAG_HANDLER_SIZE,
			height: DRAG_HANDLER_SIZE
		} );

		img.on( 'dragstart', function( evt ) {
			evt.data.$.dataTransfer.setData( 'text', JSON.stringify( { type: 'cke-widget', editor: editor.name, id: widget.id } ) );
		} );

		container.append( img );
		widget.wrapper.append( container );
		widget.dragHandlerContainer = container;
	}

	function setupEditables( widget ) {
		var editableName,
			editableDef,
			definedEditables = widget.editables;

		widget.editables = {};

		if ( !widget.editables )
			return;

		for ( editableName in definedEditables ) {
			editableDef = definedEditables[ editableName ];
			widget.initEditable( editableName, typeof editableDef == 'string' ? { selector: editableDef } : editableDef );
		}
	}

	function setupMask( widget ) {
		if ( !widget.mask )
			return;

		var img = new CKEDITOR.dom.element( 'img', widget.editor.document );
		img.setAttributes( {
			src: transparentImageData,
			'class': 'cke_widget_mask'
		} );
		widget.wrapper.append( img );
		widget.mask = img;
	}

	// Replace parts object containing:
	// partName => selector pairs
	// with:
	// partName => element pairs
	function setupParts( widget ) {
		if ( widget.parts ) {
			var parts = {},
				el, partName;

			for ( partName in widget.parts ) {
				el = widget.wrapper.findOne( widget.parts[ partName ] );
				parts[ partName ] = el;
			}
			widget.parts = parts;
		}
	}

	function setupWidget( widget, widgetDef ) {
		setupWrapper( widget );
		setupParts( widget );
		setupEditables( widget );
		setupMask( widget );
		setupDragHandler( widget );

		widget.wrapper.removeClass( 'cke_widget_new' );
		widget.element.addClass( 'cke_widget_element' );

		widget.on( 'key', function( evt ) {
			var keyCode = evt.data.keyCode;

			// ENTER.
			if ( keyCode == 13 )
				widget.edit();
			// CTRL+C or CTRL+X.
			else if ( keyCode == CKEDITOR.CTRL + 67 || keyCode == CKEDITOR.CTRL + 88 ) {
				copySingleWidget( widget, keyCode == CKEDITOR.CTRL + 88 );
				return; // Do not preventDefault.
			}
			// Pass chosen keystrokes to other plugins or default fake sel handlers.
			// Pass all CTRL keystrokes.
			else if ( keyCode in keystrokesNotBlockedByWidget || ( CKEDITOR.CTRL & keyCode ) )
				return;

			return false;
		}, null, null, 999 );
		// Listen with high priority so it's possible
		// to overwrite this callback.

		widget.on( 'doubleclick', function( evt ) {
			widget.edit();
			evt.cancel();
		} );

		if ( widgetDef.data )
			widget.on( 'data', widgetDef.data );

		if ( widgetDef.edit )
			widget.on( 'edit', widgetDef.edit );

		widget.on( 'data', function() {
			positionDragHandler( widget );
		}, null, null, 999 );
	}

	function setupWidgetData( widget, startupData ) {
		var widgetDataAttr = widget.element.data( 'cke-widget-data' );

		if ( widgetDataAttr )
			widget.setData( JSON.parse( widgetDataAttr ) );
		if ( startupData )
			widget.setData( startupData );

		// Unblock data and...
		widget.dataReady = true;

		// Write data to element because this was blocked when data wasn't ready.
		writeDataToElement( widget );

		// Fire data event first time, because this was blocked when data wasn't ready.
		widget.fire( 'data', widget.data );
	}

	function setupWrapper( widget ) {
		// Retrieve widget wrapper. Assign an id to it.
		var wrapper = widget.wrapper = widget.element.getParent();
		wrapper.setAttribute( 'data-cke-widget-id', widget.id );
	}

	function writeDataToElement( widget ) {
		widget.element.data( 'cke-widget-data', JSON.stringify( widget.data ) );
	}

	//
	// EXPOSE PUBLIC API ------------------------------------------------------
	//

	CKEDITOR.plugins.widget = Widget;
	Widget.repository = Repository;
	Widget.nestedEditable = NestedEditable;
})();

/**
 * Event fired when widget is ready (fully initialized). This event is fired after:
 *
 * * {@link #init} is called,
 * * first {@link #data} event is fired,
 * * widget is attached to document.
 *
 * Therefore, in case of widget creation with command which opens dialog, this event
 * will be delayed after dialog is closed and widget is finally inserted into document.
 *
 * **Note**: if your widget does not use automatic dialog binding (i.e. you open the dialog manually)
 * or other situation occurs in which widget wrapper is not attached to document at the time when it is
 * initialized, you need to take care of firing {@link #ready} yourself.
 *
 * @event ready
 * @member CKEDITOR.plugins.widget
 */

/**
 * Event fired when widget is about to be destroyed, but before it is
 * fully torn down.
 *
 * @event destroy
 * @member CKEDITOR.plugins.widget
 */

/**
 * Event fired when widget is focused.
 *
 * Widget can be focused by executing {@link #method-focus}.
 *
 * @event focus
 * @member CKEDITOR.plugins.widget
 */

/**
 * Event fired when widget is blurred.
 *
 * @event blur
 * @member CKEDITOR.plugins.widget
 */

/**
 * Event fired when widget is selected.
 *
 * @event select
 * @member CKEDITOR.plugins.widget
 */

/**
 * Event fired when widget is deselected.
 *
 * @event deselect
 * @member CKEDITOR.plugins.widget
 */

/**
 * Event fired by {@link #method-edit}. It can be cancelled
 * in order to stop default action (opening dialog).
 *
 * @event edit
 * @member CKEDITOR.plugins.widget
 * @param data
 * @param {String} data.dialog Defaults to {@link CKEDITOR.plugins.widget.definition#dialog}
 * and can be changed or set by listener.
 */

/**
 * Event fired when dialog for widget editing is opened.
 * This event can be cancelled in order to handle editing dialog
 * in a custom manner.
 *
 * @event dialog
 * @member CKEDITOR.plugins.widget
 * @param {CKEDITOR.dialog} data The opened dialog instance.
 */

/**
 * Event fired when key is pressed on focused widget.
 * This event is forwarded from {@link CKEDITOR.editor#key} event and
 * has the ability to block editor's keystrokes.
 *
 * @event key
 * @member CKEDITOR.plugins.widget
 * @param data
 * @param {Number} data.keyCode A number representing the key code (or combination).
 */

 /**
  * Event fired when widget was double clicked.
  *
  * @event doubleclick
  * @member CKEDITOR.plugins.widget
  * @param data
  * @param {CKEDITOR.dom.element} data.element The double clicked element.
  */

 /**
  * Event fired when context menu is opened for a widget.
  *
  * @event contextMenu
  * @member CKEDITOR.plugins.widget
  * @param data The object contaning context menu options to be added
  * for this widget. See {@link CKEDITOR.plugins.contextMenu#addListener}.
  */

/**
 * Event fired when widget instance is created, but before it is fully
 * initialized.
 *
 * @event instanceCreated
 * @member CKEDITOR.plugins.widget.repository
 * @param {CKEDITOR.plugins.widget} data The widget instance.
 */

/**
 * Event fired when widget instance was destroyed.
 *
 * See also {@link CKEDITOR.plugins.widget#event-destroy}.
 *
 * @event instanceDestroyed
 * @member CKEDITOR.plugins.widget.repository
 * @param {CKEDITOR.plugins.widget} data The widget instance.
 */

/**
 * Event fired to trigger selection check.
 *
 * See {@link #method-checkSelection} method.
 *
 * @event checkSelection
 * @member CKEDITOR.plugins.widget.repository
 */

/**
 * Event fired to trigger widgets check.
 *
 * See {@link #method-checkWidgets} method.
 *
 * @event checkWidgets
 * @member CKEDITOR.plugins.widget.repository
 */