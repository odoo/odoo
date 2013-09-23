/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * Represents a command that can be executed on an editor instance.
 *
 *		var command = new CKEDITOR.command( editor, {
 *			exec: function( editor ) {
 *				alert( editor.document.getBody().getHtml() );
 *			}
 *		} );
 *
 * @class
 * @mixins CKEDITOR.event
 * @constructor Creates a command class instance.
 * @param {CKEDITOR.editor} editor The editor instance this command will be
 * related to.
 * @param {CKEDITOR.commandDefinition} commandDefinition The command
 * definition.
 */
CKEDITOR.command = function( editor, commandDefinition ) {
	/**
	 * Lists UI items that are associated to this command. This list can be
	 * used to interact with the UI on command execution (by the execution code
	 * itself, for example).
	 *
	 *		alert( 'Number of UI items associated to this command: ' + command.uiItems.length );
	 */
	this.uiItems = [];

	/**
	 * Executes the command.
	 *
	 *		command.exec(); // The command gets executed.
	 *
	 * @param {Object} [data] Any data to pass to the command. Depends on the
	 * command implementation and requirements.
	 * @returns {Boolean} A boolean indicating that the command has been successfully executed.
	 */
	this.exec = function( data ) {
		if ( this.state == CKEDITOR.TRISTATE_DISABLED || !this.checkAllowed() )
			return false;

		if ( this.editorFocus ) // Give editor focus if necessary (#4355).
			editor.focus();

		if ( this.fire( 'exec' ) === false )
			return true;

		return ( commandDefinition.exec.call( this, editor, data ) !== false );
	};

	/**
	 * Explicitly update the status of the command, by firing the {@link CKEDITOR.command#event-refresh} event,
	 * as well as invoke the {@link CKEDITOR.commandDefinition#refresh} method if defined, this method
	 * is to allow different parts of the editor code to contribute in command status resolution.
	 *
	 * @param {CKEDITOR.editor} editor The editor instance.
	 * @param {CKEDITOR.dom.elementPath} path
	 */
	this.refresh = function( editor, path ) {
		// Do nothing is we're on read-only and this command doesn't support it.
		// We don't need to disabled the command explicitely here, because this
		// is already done by the "readOnly" event listener.
		if ( !this.readOnly && editor.readOnly )
			return true;

		// Disable commands that are not allowed in the current selection path context.
		if ( this.context && !path.isContextFor( this.context ) ) {
			this.disable();
			return true;
		}

		// Disable commands that are not allowed by the active filter.
		if ( !this.checkAllowed( true ) ) {
			this.disable();
			return true;
		}

		// Make the "enabled" state a default for commands enabled from start.
		if ( !this.startDisabled )
			this.enable();

		// Disable commands which shouldn't be enabled in this mode.
		if ( this.modes && !this.modes[ editor.mode ] )
			this.disable();

		if ( this.fire( 'refresh', { editor: editor, path: path } ) === false )
			return true;

		return ( commandDefinition.refresh && commandDefinition.refresh.apply( this, arguments ) !== false );
	};

	var allowed;

	/**
	 * Checks whether this command is allowed by the active allowed
	 * content filter ({@link CKEDITOR.editor#activeFilter}). This means
	 * that if command implements {@link CKEDITOR.feature} interface it will be tested
	 * by the {@link CKEDITOR.filter#checkFeature} method.
	 *
	 * @since 4.1
	 * @param {Boolean} [noCache] Skip cache for example due to active filter change. Since CKEditor 4.2.
	 * @returns {Boolean} Whether this command is allowed.
	 */
	this.checkAllowed = function( noCache ) {
		if ( !noCache && typeof allowed == 'boolean' )
			return allowed;

		return allowed = editor.activeFilter.checkFeature( this );
	};

	CKEDITOR.tools.extend( this, commandDefinition, {
		/**
		 * The editor modes within which the command can be executed. The
		 * execution will have no action if the current mode is not listed
		 * in this property.
		 *
		 *		// Enable the command in both WYSIWYG and Source modes.
		 *		command.modes = { wysiwyg:1,source:1 };
		 *
		 *		// Enable the command in Source mode only.
		 *		command.modes = { source:1 };
		 *
		 * @see CKEDITOR.editor#mode
		 */
		modes: { wysiwyg:1 },

		/**
		 * Indicates that the editor will get the focus before executing
		 * the command.
		 *
		 *		// Do not force the editor to have focus when executing the command.
		 *		command.editorFocus = false;
		 *
		 * @property {Boolean} [=true]
		 */
		editorFocus: 1,

		/**
		 * Indicates that this command is sensible to the selection context.
		 * If `true`, the {@link CKEDITOR.command#method-refresh} method will be
		 * called for this command on the {@link CKEDITOR.editor#event-selectionChange} event.
		 *
		 * @property {Boolean} [=false]
		 */
		contextSensitive: !!commandDefinition.context,

		/**
		 * Indicates the editor state. Possible values are:
		 *
		 * * {@link CKEDITOR#TRISTATE_DISABLED}: the command is
		 *     disabled. It's execution will have no effect. Same as {@link #disable}.
		 * * {@link CKEDITOR#TRISTATE_ON}: the command is enabled
		 *     and currently active in the editor (for context sensitive commands,	for example).
		 * * {@link CKEDITOR#TRISTATE_OFF}: the command is enabled
		 *     and currently inactive in the editor (for context sensitive	commands, for example).
		 *
		 * Do not set this property directly, using the {@link #setState} method instead.
		 *
		 *		if ( command.state == CKEDITOR.TRISTATE_DISABLED )
		 *			alert( 'This command is disabled' );
		 *
		 * @property {Number} [=CKEDITOR.TRISTATE_DISABLED]
		 */
		state: CKEDITOR.TRISTATE_DISABLED
	});

	// Call the CKEDITOR.event constructor to initialize this instance.
	CKEDITOR.event.call( this );
};

CKEDITOR.command.prototype = {
	/**
	 * Enables the command for execution. The command state (see
	 * {@link CKEDITOR.command#property-state}) available before disabling it is restored.
	 *
	 *		command.enable();
	 *		command.exec(); // Execute the command.
	 */
	enable: function() {
		if ( this.state == CKEDITOR.TRISTATE_DISABLED && this.checkAllowed() )
			this.setState( ( !this.preserveState || ( typeof this.previousState == 'undefined' ) ) ? CKEDITOR.TRISTATE_OFF : this.previousState );
	},

	/**
	 * Disables the command for execution. The command state (see
	 * {@link CKEDITOR.command#property-state}) will be set to {@link CKEDITOR#TRISTATE_DISABLED}.
	 *
	 *		command.disable();
	 *		command.exec(); // "false" - Nothing happens.
	 */
	disable: function() {
		this.setState( CKEDITOR.TRISTATE_DISABLED );
	},

	/**
	 * Sets the command state.
	 *
	 *		command.setState( CKEDITOR.TRISTATE_ON );
	 *		command.exec(); // Execute the command.
	 *		command.setState( CKEDITOR.TRISTATE_DISABLED );
	 *		command.exec(); // 'false' - Nothing happens.
	 *		command.setState( CKEDITOR.TRISTATE_OFF );
	 *		command.exec(); // Execute the command.
	 *
	 * @param {Number} newState The new state. See {@link #property-state}.
	 * @returns {Boolean} Returns `true` if the command state changed.
	 */
	setState: function( newState ) {
		// Do nothing if there is no state change.
		if ( this.state == newState )
			return false;

		if ( newState != CKEDITOR.TRISTATE_DISABLED && !this.checkAllowed() )
			return false;

		this.previousState = this.state;

		// Set the new state.
		this.state = newState;

		// Fire the "state" event, so other parts of the code can react to the
		// change.
		this.fire( 'state' );

		return true;
	},

	/**
	 * Toggles the on/off (active/inactive) state of the command. This is
	 * mainly used internally by context sensitive commands.
	 *
	 *		command.toggleState();
	 */
	toggleState: function() {
		if ( this.state == CKEDITOR.TRISTATE_OFF )
			this.setState( CKEDITOR.TRISTATE_ON );
		else if ( this.state == CKEDITOR.TRISTATE_ON )
			this.setState( CKEDITOR.TRISTATE_OFF );
	}
};

CKEDITOR.event.implementOn( CKEDITOR.command.prototype );

/**
 * Indicates the previous command state.
 *
 *		alert( command.previousState );
 *
 * @property {Number} previousState
 * @see #state
 */

/**
 * Fired when the command state changes.
 *
 *		command.on( 'state', function() {
 *			// Alerts the new state.
 *			alert( this.state );
 *		} );
 *
 * @event state
 */

 /**
 * @event refresh
 * @todo
 */
