/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the "virtual" {@link CKEDITOR.commandDefinition} class,
 *		which contains the defintion of a command. This file is for
 *		documentation purposes only.
 */

/**
 * Virtual class that illustrates the features of command objects to be
 * passed to the {@link CKEDITOR.editor#addCommand} function.
 *
 * @class CKEDITOR.commandDefinition
 * @abstract
 */

/**
 * The function to be fired when the commend is executed.
 *
 *		editorInstance.addCommand( 'sample', {
 *			exec: function( editor ) {
 *				alert( 'Executing a command for the editor name "' + editor.name + '"!' );
 *			}
 *		} );
 *
 * @method exec
 * @param {CKEDITOR.editor} editor The editor within which run the command.
 * @param {Object} [data] Additional data to be used to execute the command.
 * @returns {Boolean} Whether the command has been successfully executed.
 * Defaults to `true`, if nothing is returned.
 */

/**
 * Whether the command need to be hooked into the redo/undo system.
 *
 *		editorInstance.addCommand( 'alertName', {
 *			exec: function( editor ) {
 *				alert( editor.name );
 *			},
 *			canUndo: false // No support for undo/redo.
 *		} );
 *
 * @property {Boolean} [canUndo=true]
 */

/**
 * Whether the command is asynchronous, which means that the
 * {@link CKEDITOR.editor#event-afterCommandExec} event will be fired by the
 * command itself manually, and that the return value of this command is not to
 * be returned by the {@link #exec} function.
 *
 * 		editorInstance.addCommand( 'loadOptions', {
 * 			exec: function( editor ) {
 * 				// Asynchronous operation below.
 * 				CKEDITOR.ajax.loadXml( 'data.xml', function() {
 * 					editor.fire( 'afterCommandExec' );
 * 				} );
 * 			},
 * 			async: true // The command need some time to complete after exec function returns.
 * 		} );
 *
 * @property {Boolean} [async=false]
 */

/**
 * Whether the command should give focus to the editor before execution.
 *
 *		editorInstance.addCommand( 'maximize', {
 *				exec: function( editor ) {
 *				// ...
 *			},
 *			editorFocus: false // The command doesn't require focusing the editing document.
 *		} );
 *
 * @property {Boolean} [editorFocus=true]
 * @see CKEDITOR.command#editorFocus
 */


/**
 * Whether the command state should be set to {@link CKEDITOR#TRISTATE_DISABLED} on startup.
 *
 *		editorInstance.addCommand( 'unlink', {
 *			exec: function( editor ) {
 *				// ...
 *			},
 *			startDisabled: true // Command is unavailable until selection is inside a link.
 *		} );
 *
 * @property {Boolean} [startDisabled=false]
 */

/**
 * Indicates that this command is sensible to the selection context.
 * If `true`, the {@link CKEDITOR.command#method-refresh} method will be
 * called for this command on selection changes, with a single parameter
 * representing the current elements path.
 *
 * @property {Boolean} [contextSensitive=true]
 */

/**
 * Defined by command definition a function to determinate the command state, it will be invoked
 * when editor has it's `states` or `selection` changed.
 *
 * **Note:** The function provided must be calling {@link CKEDITOR.command#setState} in all circumstance,
 * if it is intended to update the command state.
 *
 * @method refresh
 * @param {CKEDITOR.editor} editor
 * @param {CKEDITOR.dom.elementPath} path
 */

/**
 * Sets the element name used to reflect the command state on selection changes.
 * If the selection is in a place where the element is not allowed, the command
 * will be disabled.
 * Setting this property overrides {@link #contextSensitive} to `true`.
 *
 * @property {Boolean} [context=true]
 */

/**
 * The editor modes within which the command can be executed. The execution
 * will have no action if the current mode is not listed in this property.
 *
 *		editorInstance.addCommand( 'link', {
 *			exec: function( editor ) {
 *				// ...
 *			},
 *			modes: { wysiwyg:1 } // Command is available in wysiwyg mode only.
 *		} );
 *
 * @property {Object} [modes={ wysiwyg:1 }]
 * @see CKEDITOR.command#modes
 */
