/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

CKEDITOR.plugins.add( 'richcombo', {
	requires: 'floatpanel,listblock,button',

	beforeInit: function( editor ) {
		editor.ui.addHandler( CKEDITOR.UI_RICHCOMBO, CKEDITOR.ui.richCombo.handler );
	}
});

(function() {
	var template = '<span id="{id}"' +
		' class="cke_combo cke_combo__{name} {cls}"' +
		' role="presentation">' +
			'<span id="{id}_label" class="cke_combo_label">{label}</span>' +
			'<a class="cke_combo_button" hidefocus=true title="{title}" tabindex="-1"' +
			( CKEDITOR.env.gecko && CKEDITOR.env.version >= 10900 && !CKEDITOR.env.hc ? '' : '" href="javascript:void(\'{titleJs}\')"' ) +
			' hidefocus="true"' +
			' role="button"' +
			' aria-labelledby="{id}_label"' +
			' aria-haspopup="true"';

	// Some browsers don't cancel key events in the keydown but in the
	// keypress.
	// TODO: Check if really needed for Gecko+Mac.
	if ( CKEDITOR.env.opera || ( CKEDITOR.env.gecko && CKEDITOR.env.mac ) )
		template += ' onkeypress="return false;"';

	// With Firefox, we need to force the button to redraw, otherwise it
	// will remain in the focus state.
	if ( CKEDITOR.env.gecko )
		template += ' onblur="this.style.cssText = this.style.cssText;"';

	template +=
		' onkeydown="return CKEDITOR.tools.callFunction({keydownFn},event,this);"' +
		' onmousedown="return CKEDITOR.tools.callFunction({mousedownFn},event);" ' +
		' onfocus="return CKEDITOR.tools.callFunction({focusFn},event);" ' +
			( CKEDITOR.env.ie ? 'onclick="return false;" onmouseup' : 'onclick' ) + // #188
				'="CKEDITOR.tools.callFunction({clickFn},this);return false;">' +
			'<span id="{id}_text" class="cke_combo_text cke_combo_inlinelabel">{label}</span>' +
			'<span class="cke_combo_open">' +
				'<span class="cke_combo_arrow">' +
				// BLACK DOWN-POINTING TRIANGLE
	( CKEDITOR.env.hc ? '&#9660;' : CKEDITOR.env.air ? '&nbsp;' : '' ) +
				'</span>' +
			'</span>' +
		'</a>' +
		'</span>';

	var rcomboTpl = CKEDITOR.addTemplate( 'combo', template );

	/**
	 * Button UI element.
	 *
	 * @readonly
	 * @property {String} [='richcombo']
	 * @member CKEDITOR
	 */
	CKEDITOR.UI_RICHCOMBO = 'richcombo';

	/**
	 * @class
	 * @todo
	 */
	CKEDITOR.ui.richCombo = CKEDITOR.tools.createClass({
		$: function( definition ) {
			// Copy all definition properties to this object.
			CKEDITOR.tools.extend( this, definition,
			// Set defaults.
			{
				// The combo won't participate in toolbar grouping.
				canGroup: false,
				title: definition.label,
				modes: { wysiwyg:1 },
				editorFocus: 1
			});

			// We don't want the panel definition in this object.
			var panelDefinition = this.panel || {};
			delete this.panel;

			this.id = CKEDITOR.tools.getNextNumber();

			this.document = ( panelDefinition.parent && panelDefinition.parent.getDocument() ) || CKEDITOR.document;

			panelDefinition.className = 'cke_combopanel';
			panelDefinition.block = {
				multiSelect: panelDefinition.multiSelect,
				attributes: panelDefinition.attributes
			};
			panelDefinition.toolbarRelated = true;

			this._ = {
				panelDefinition: panelDefinition,
				items: {}
			};
		},

		proto: {
			renderHtml: function( editor ) {
				var output = [];
				this.render( editor, output );
				return output.join( '' );
			},

			/**
			 * Renders the combo.
			 *
			 * @param {CKEDITOR.editor} editor The editor instance which this button is
			 * to be used by.
			 * @param {Array} output The output array to which append the HTML relative
			 * to this button.
			 */
			render: function( editor, output ) {
				var env = CKEDITOR.env;

				var id = 'cke_' + this.id;
				var clickFn = CKEDITOR.tools.addFunction( function( el ) {

				// Restore locked selection in Opera.
				if ( selLocked ) {
					editor.unlockSelection( 1 );
					selLocked = 0;
				}

					instance.execute( el );
				}, this );

				var combo = this;
				var instance = {
					id: id,
					combo: this,
					focus: function() {
						var element = CKEDITOR.document.getById( id ).getChild( 1 );
						element.focus();
					},
					execute: function( el ) {
						var _ = combo._;

						if ( _.state == CKEDITOR.TRISTATE_DISABLED )
							return;

						combo.createPanel( editor );

						if ( _.on ) {
							_.panel.hide();
							return;
						}

						combo.commit();
						var value = combo.getValue();
						if ( value )
							_.list.mark( value );
						else
							_.list.unmarkAll();

						_.panel.showBlock( combo.id, new CKEDITOR.dom.element( el ), 4 );
					},
					clickFn: clickFn
				};

				function updateState() {
					var state = this.modes[ editor.mode ] ? CKEDITOR.TRISTATE_OFF : CKEDITOR.TRISTATE_DISABLED;
					this.setState( editor.readOnly && !this.readOnly ? CKEDITOR.TRISTATE_DISABLED : state );
					this.setValue( '' );
				}

				editor.on( 'mode', updateState, this );
				// If this combo is sensitive to readOnly state, update it accordingly.
				!this.readOnly && editor.on( 'readOnly', updateState, this );

				var keyDownFn = CKEDITOR.tools.addFunction( function( ev, element ) {
					ev = new CKEDITOR.dom.event( ev );

					var keystroke = ev.getKeystroke();
					switch ( keystroke ) {
						case 13: // ENTER
						case 32: // SPACE
						case 40: // ARROW-DOWN
							// Show panel
							CKEDITOR.tools.callFunction( clickFn, element );
							break;
						default:
							// Delegate the default behavior to toolbar button key handling.
							instance.onkey( instance, keystroke );
					}

					// Avoid subsequent focus grab on editor document.
					ev.preventDefault();
				});

				var focusFn = CKEDITOR.tools.addFunction( function() {
					instance.onfocus && instance.onfocus();
				});

				var selLocked = 0;
				var mouseDownFn = CKEDITOR.tools.addFunction( function() {
					// Opera: lock to prevent loosing editable text selection when clicking on button.
					if ( CKEDITOR.env.opera ) {
						var edt = editor.editable();
						if ( edt.isInline() && edt.hasFocus ) {
							editor.lockSelection();
							selLocked = 1;
						}
					}
				});

				// For clean up
				instance.keyDownFn = keyDownFn;

				var params = {
					id: id,
					name: this.name || this.command,
					label: this.label,
					title: this.title,
					cls: this.className || '',
					titleJs: env.gecko && env.version >= 10900 && !env.hc ? '' : ( this.title || '' ).replace( "'", '' ),
					keydownFn: keyDownFn,
					mousedownFn: mouseDownFn,
					focusFn: focusFn,
					clickFn: clickFn
				};

				rcomboTpl.output( params, output );

				if ( this.onRender )
					this.onRender();

				return instance;
			},

			createPanel: function( editor ) {
				if ( this._.panel )
					return;

				var panelDefinition = this._.panelDefinition,
					panelBlockDefinition = this._.panelDefinition.block,
					panelParentElement = panelDefinition.parent || CKEDITOR.document.getBody(),
					namedPanelCls = 'cke_combopanel__' + this.name,
					panel = new CKEDITOR.ui.floatPanel( editor, panelParentElement, panelDefinition ),
					list = panel.addListBlock( this.id, panelBlockDefinition ),
					me = this;

				panel.onShow = function() {
					this.element.addClass( namedPanelCls );

					me.setState( CKEDITOR.TRISTATE_ON );

					me._.on = 1;

					me.editorFocus && editor.focus();

					if ( me.onOpen )
						me.onOpen();

					list.focus( !list.multiSelect && me.getValue() );
				};

				panel.onHide = function( preventOnClose ) {
					this.element.removeClass( namedPanelCls );

					me.setState( me.modes && me.modes[ editor.mode ] ? CKEDITOR.TRISTATE_OFF : CKEDITOR.TRISTATE_DISABLED );

					me._.on = 0;

					if ( !preventOnClose && me.onClose )
						me.onClose();
				};

				panel.onEscape = function() {
					// Hide drop-down with focus returned.
					panel.hide( 1 );
				};

				list.onClick = function( value, marked ) {

					if ( me.onClick )
						me.onClick.call( me, value, marked );

					panel.hide();
				};

				this._.panel = panel;
				this._.list = list;

				panel.getBlock( this.id ).onHide = function() {
					me._.on = 0;
					me.setState( CKEDITOR.TRISTATE_OFF );
				};

				if ( this.init )
					this.init();
			},

			setValue: function( value, text ) {
				this._.value = value;

				var textElement = this.document.getById( 'cke_' + this.id + '_text' );
				if ( textElement ) {
					if ( !( value || text ) ) {
						text = this.label;
						textElement.addClass( 'cke_combo_inlinelabel' );
					} else
						textElement.removeClass( 'cke_combo_inlinelabel' );

					textElement.setText( typeof text != 'undefined' ? text : value );
				}
			},

			getValue: function() {
				return this._.value || '';
			},

			unmarkAll: function() {
				this._.list.unmarkAll();
			},

			mark: function( value ) {
				this._.list.mark( value );
			},

			hideItem: function( value ) {
				this._.list.hideItem( value );
			},

			hideGroup: function( groupTitle ) {
				this._.list.hideGroup( groupTitle );
			},

			showAll: function() {
				this._.list.showAll();
			},

			add: function( value, html, text ) {
				this._.items[ value ] = text || value;
				this._.list.add( value, html, text );
			},

			startGroup: function( title ) {
				this._.list.startGroup( title );
			},

			commit: function() {
				if ( !this._.committed ) {
					this._.list.commit();
					this._.committed = 1;
					CKEDITOR.ui.fire( 'ready', this );
				}
				this._.committed = 1;
			},

			setState: function( state ) {
				if ( this._.state == state )
					return;

				var el = this.document.getById( 'cke_' + this.id );
				el.setState( state, 'cke_combo' );

				state == CKEDITOR.TRISTATE_DISABLED ?
					el.setAttribute( 'aria-disabled', true ) :
					el.removeAttribute( 'aria-disabled' );

				this._.state = state;
			},

			enable: function() {
				if ( this._.state == CKEDITOR.TRISTATE_DISABLED )
					this.setState( this._.lastState );
			},

			disable: function() {
				if ( this._.state != CKEDITOR.TRISTATE_DISABLED ) {
					this._.lastState = this._.state;
					this.setState( CKEDITOR.TRISTATE_DISABLED );
				}
			}
		},

		/**
		 * Represents richCombo handler object.
		 *
		 * @class CKEDITOR.ui.richCombo.handler
		 * @singleton
		 * @extends CKEDITOR.ui.handlerDefinition
		 */
		statics: {
			handler: {
				/**
				 * Transforms a richCombo definition in a {@link CKEDITOR.ui.richCombo} instance.
				 *
				 * @param {Object} definition
				 * @returns {CKEDITOR.ui.richCombo}
				 */
				create: function( definition ) {
					return new CKEDITOR.ui.richCombo( definition );
				}
			}
		}
	});

	/**
	 * @member CKEDITOR.ui
	 * @param {String}
	 * @param {Object} definition
	 * @todo
	 */
	CKEDITOR.ui.prototype.addRichCombo = function( name, definition ) {
		this.add( name, CKEDITOR.UI_RICHCOMBO, definition );
	};

})();
