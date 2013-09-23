/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Increase and Decrease Indent commands.
 */

(function() {
	'use strict';

	var TRISTATE_DISABLED = CKEDITOR.TRISTATE_DISABLED,
		TRISTATE_OFF = CKEDITOR.TRISTATE_OFF;

	CKEDITOR.plugins.add( 'indent', {
		lang: 'af,ar,bg,bn,bs,ca,cs,cy,da,de,el,en,en-au,en-ca,en-gb,eo,es,et,eu,fa,fi,fo,fr,fr-ca,gl,gu,he,hi,hr,hu,id,is,it,ja,ka,km,ko,ku,lt,lv,mk,mn,ms,nb,nl,no,pl,pt,pt-br,ro,ru,si,sk,sl,sq,sr,sr-latn,sv,th,tr,ug,uk,vi,zh,zh-cn', // %REMOVE_LINE_CORE%
		icons: 'indent,indent-rtl,outdent,outdent-rtl', // %REMOVE_LINE_CORE%

		init: function( editor ) {
			var genericDefinition = CKEDITOR.plugins.indent.genericDefinition;

			// Register generic commands.
			setupGenericListeners( editor, editor.addCommand( 'indent', new genericDefinition( true ) ) );
			setupGenericListeners( editor, editor.addCommand( 'outdent', new genericDefinition() ) );

			// Create and register toolbar button if possible.
			if ( editor.ui.addButton ) {
				editor.ui.addButton( 'Indent', {
					label: editor.lang.indent.indent,
					command: 'indent',
					directional: true,
					toolbar: 'indent,20'
				} );

				editor.ui.addButton( 'Outdent', {
					label: editor.lang.indent.outdent,
					command: 'outdent',
					directional: true,
					toolbar: 'indent,10'
				} );
			}

			// Register dirChanged listener.
			editor.on( 'dirChanged', function( evt ) {
				var range = editor.createRange(),
					dataNode = evt.data.node;

				range.setStartBefore( dataNode );
				range.setEndAfter( dataNode );

				var walker = new CKEDITOR.dom.walker( range ),
					node;

				while ( ( node = walker.next() ) ) {
					if ( node.type == CKEDITOR.NODE_ELEMENT ) {
						// A child with the defined dir is to be ignored.
						if ( !node.equals( dataNode ) && node.getDirection() ) {
							range.setStartAfter( node );
							walker = new CKEDITOR.dom.walker( range );
							continue;
						}

						// Switch alignment classes.
						var classes = editor.config.indentClasses;
						if ( classes ) {
							var suffix = ( evt.data.dir == 'ltr' ) ? [ '_rtl', '' ] : [ '', '_rtl' ];
							for ( var i = 0; i < classes.length; i++ ) {
								if ( node.hasClass( classes[ i ] + suffix[ 0 ] ) ) {
									node.removeClass( classes[ i ] + suffix[ 0 ] );
									node.addClass( classes[ i ] + suffix[ 1 ] );
								}
							}
						}

						// Switch the margins.
						var marginLeft = node.getStyle( 'margin-right' ),
							marginRight = node.getStyle( 'margin-left' );

						marginLeft ? node.setStyle( 'margin-left', marginLeft ) : node.removeStyle( 'margin-left' );
						marginRight ? node.setStyle( 'margin-right', marginRight ) : node.removeStyle( 'margin-right' );
					}
				}
			} );
		}
	} );

	/**
	 * Global command class definitions and global helpers.
	 *
	 * @class
	 * @singleton
	 */
	CKEDITOR.plugins.indent = {
		/**
		 * A base class for a generic command definition, responsible mainly for creating
		 * Increase Indent and Decrease Indent toolbar buttons as well as for refreshing
		 * UI states.
		 *
		 * Commands of this class do not perform any indentation by themselves. They
		 * delegate this job to content-specific indentation commands (i.e. indentlist).
		 *
		 * @class CKEDITOR.plugins.indent.genericDefinition
		 * @extends CKEDITOR.commandDefinition
		 * @param {CKEDITOR.editor} editor The editor instance this command will be
		 * applied to.
		 * @param {String} name The name of the command.
		 * @param {Boolean} [isIndent] Defines the command as indenting or outdenting.
		 */
		genericDefinition: function( isIndent ) {
			/**
			 * Determines whether the command belongs to the indentation family.
			 * Otherwise it is assumed to be an outdenting command.
			 *
			 * @readonly
			 * @property {Boolean} [=false]
			 */
			this.isIndent = !!isIndent;

			// Mimic naive startDisabled behavior for outdent.
			this.startDisabled = !this.isIndent;
		},

		/**
		 * A base class for specific indentation command definitions responsible for
		 * handling a pre-defined set of elements i.e. indentlist for lists or
		 * indentblock for text block elements.
		 *
		 * Commands of this class perform indentation operations and modify the DOM structure.
		 * They listen for events fired by {@link CKEDITOR.plugins.indent.genericDefinition}
		 * and execute defined actions.
		 *
		 * **NOTE**: This is not an {@link CKEDITOR.command editor command}.
		 * Context-specific commands are internal, for indentation system only.
		 *
		 * @class CKEDITOR.plugins.indent.specificDefinition
		 * @param {CKEDITOR.editor} editor The editor instance this command will be
		 * applied to.
		 * @param {String} name The name of the command.
		 * @param {Boolean} [isIndent] Defines the command as indenting or outdenting.
		 */
		specificDefinition: function( editor, name, isIndent ) {
			this.name = name;
			this.editor = editor;

			/**
			 * An object of jobs handled by the command. Each job consists
			 * of two functions: `refresh` and `exec` as well as the execution priority.
			 *
			 *	* The `refresh` function determines whether a job is doable for
			 *	  a particular context. These functions are executed in the
			 *	  order of priorities, one by one, for all plugins that registered
			 *	  jobs. As jobs are related to generic commands, refreshing
			 *	  occurs when the global command is firing the `refresh` event.
			 *
			 *	  **Note**: This function must return either {@link CKEDITOR#TRISTATE_DISABLED}
			 *	  or {@link CKEDITOR#TRISTATE_OFF}.
			 *
			 *	* The `exec` function modifies the DOM if possible. Just like
			 *	  `refresh`, `exec` functions are executed in the order of priorities
			 *	  while the generic command is executed. This function is not executed
			 *	  if `refresh` for this job returned {@link CKEDITOR#TRISTATE_DISABLED}.
			 *
			 *	  **Note**: This function must return a Boolean value, indicating whether it
			 *	  was successful. If a job was successful, then no other jobs are being executed.
			 *
			 * Sample definition:
			 *
			 *		command.jobs = {
			 *			// Priority = 20.
			 *			'20': {
			 *				refresh( editor, path ) {
			 *					if ( condition )
			 *						return CKEDITOR.TRISTATE_OFF;
			 *					else
			 *						return CKEDITOR.TRISTATE_DISABLED;
			 *				},
			 *				exec( editor ) {
			 *					// DOM modified! This was OK.
			 *					return true;
			 *				}
			 *			},
			 *			// Priority = 60. This job is done later.
			 *			'60': {
			 *				// Another job.
			 *			}
			 *		};
			 *
			 * For additional information, please check comments for
			 * the `setupGenericListeners` function.
			 *
			 * @readonly
			 * @property {Object} [={}]
			 */
			this.jobs = {};

			/**
			 * Determines whether the editor that the command belongs to has
			 * {@link CKEDITOR.config#enterMode config.enterMode} set to {@link CKEDITOR#ENTER_BR}.
			 *
			 * @readonly
			 * @see CKEDITOR.config#enterMode
			 * @property {Boolean} [=false]
			 */
			this.enterBr = editor.config.enterMode == CKEDITOR.ENTER_BR;

			/**
			 * Determines whether the command belongs to the indentation family.
			 * Otherwise it is assumed to be an outdenting command.
			 *
			 * @readonly
			 * @property {Boolean} [=false]
			 */
			this.isIndent = !!isIndent;

			/**
			 * The name of the global command related to this one.
			 *
			 * @readonly
			 */
			this.relatedGlobal = isIndent ? 'indent' : 'outdent';

			/**
			 * A keystroke associated with this command (*Tab* or *Shift+Tab*).
			 *
			 * @readonly
			 */
			this.indentKey = isIndent ? 9 : CKEDITOR.SHIFT + 9;

			/**
			 * Stores created markers for the command so they can eventually be
			 * purged after the `exec` function is run.
			 */
			this.database = {};
		},

		/**
		 * Registers content-specific commands as a part of the indentation system
		 * directed by generic commands. Once a command is registered,
		 * it listens for events of a related generic command.
		 *
		 *		CKEDITOR.plugins.indent.registerCommands( editor, {
		 *			'indentlist': new indentListCommand( editor, 'indentlist' ),
		 *			'outdentlist': new indentListCommand( editor, 'outdentlist' )
		 *		} );
		 *
		 * Content-specific commands listen for the generic command's `exec` and
		 * try to execute their own jobs, one after another. If some execution is
		 * successful, `evt.data.done` is set so no more jobs (commands) are involved.
		 *
		 * Content-specific commands also listen for the generic command's `refresh`
		 * and fill the `evt.data.states` object with states of jobs. A generic command
		 * uses this data to determine its own state and to update the UI.
		 *
		 * @member CKEDITOR.plugins.indent
		 * @param {CKEDITOR.editor} editor The editor instance this command is
		 * applied to.
		 * @param {Object} commands An object of {@link CKEDITOR.command}.
		 */
		registerCommands: function( editor, commands ) {
			editor.on( 'pluginsLoaded', function() {
				for ( var name in commands ) {
					( function( editor, command ) {
						var relatedGlobal = editor.getCommand( command.relatedGlobal );

						for ( var priority in command.jobs ) {
							// Observe generic exec event and execute command when necessary.
							// If the command was successfully handled by the command and
							// DOM has been modified, stop event propagation so no other plugin
							// will bother. Job is done.
							relatedGlobal.on( 'exec', function( evt ) {
								if ( evt.data.done )
									return;

								// Make sure that anything this command will do is invisible
								// for undoManager. What undoManager only can see and
								// remember is the execution of the global command (relatedGlobal).
								editor.fire( 'lockSnapshot' );

								if ( command.execJob( editor, priority ) )
									evt.data.done = true;

								editor.fire( 'unlockSnapshot' );

								// Clean up the markers.
								CKEDITOR.dom.element.clearAllMarkers( command.database );
							}, this, null, priority );

							// Observe generic refresh event and force command refresh.
							// Once refreshed, save command state in event data
							// so generic command plugin can update its own state and UI.
							relatedGlobal.on( 'refresh', function( evt ) {
								if ( !evt.data.states )
									evt.data.states = {};

								evt.data.states[ command.name + '@' + priority ] =
									command.refreshJob( editor, priority, evt.data.path );
							}, this, null, priority );
						}

						// Since specific indent commands have no UI elements,
						// they need to be manually registered as a editor feature.
						editor.addFeature( command );
					} )( this, commands[ name ] );
				}
			} );
		}
	};

	CKEDITOR.plugins.indent.genericDefinition.prototype = {
		context: 'p',

		exec: function() {}
	};

	CKEDITOR.plugins.indent.specificDefinition.prototype = {
		/**
		 * Executes the content-specific procedure if the context is correct.
		 * It calls the `exec` function of a job of the given `priority`
		 * that modifies the DOM.
		 *
		 * @param {CKEDITOR.editor} editor The editor instance this command
		 * will be applied to.
		 * @param {Number} priority The priority of the job to be executed.
		 * @returns {Boolean} Indicates whether the job was successful.
		 */
		execJob: function( editor, priority ) {
			var job = this.jobs[ priority ];

			if ( job.state != TRISTATE_DISABLED )
				return job.exec.call( this, editor );
		},

		/**
		 * Calls the `refresh` function of a job of the given `priority`.
		 * The function returns the state of the job which can be either
		 * {@link CKEDITOR#TRISTATE_DISABLED} or {@link CKEDITOR#TRISTATE_OFF}.
		 *
		 * @param {CKEDITOR.editor} editor The editor instance this command
		 * will be applied to.
		 * @param {Number} priority The priority of the job to be executed.
		 * @returns {Number} The state of the job.
		 */
		refreshJob: function( editor, priority, path ) {
			var job = this.jobs[ priority ];

			job.state = job.refresh.call( this, editor, path );

			return job.state;
		},

		/**
		 * Checks if the element path contains the element handled
		 * by this indentation command.
		 *
		 * @param {CKEDITOR.dom.elementPath} node A path to be checked.
		 * @returns {CKEDITOR.dom.element}
		 */
		getContext: function( path ) {
			return path.contains( this.context );
		}
	};

	/**
	 * Attaches event listeners for this generic command. Since the indentation
	 * system is event-oriented, generic commands communicate with
	 * content-specific commands using the `exec` and `refresh` events.
	 *
	 * Listener priorities are crucial. Different indentation phases
	 * are executed with different priorities.
	 *
	 * For the `exec` event:
	 *
	 *	* 0: Selection and bookmarks are saved by the generic command.
	 *	* 1-99: Content-specific commands try to indent the code by executing
	 *	  their own jobs ({@link CKEDITOR.plugins.indent.specificDefinition#jobs}).
	 *	* 100: Bookmarks are re-selected by the generic command.
	 *
	 * The visual interpretation looks as follows:
	 *
	 *		  +------------------+
	 *		  | Exec event fired |
	 *		  +------ + ---------+
	 *		          |
	 *		        0 -<----------+ Selection and bookmarks saved.
	 *		          |
	 *		          |
	 *		       25 -<---+ Exec 1st job of plugin#1 (return false, continuing...).
	 *		          |
	 *		          |
	 *		       50 -<---+ Exec 1st job of plugin#2 (return false, continuing...).
	 *		          |
	 *		          |
	 *		       75 -<---+ Exec 2nd job of plugin#1 (only if plugin#2 failed).
	 *		          |
	 *		          |
	 *		      100 -<-----------+ Re-select bookmarks, clean-up.
	 *		          |
	 *		+-------- v ----------+
	 *		| Exec event finished |
	 *		+---------------------+
	 *
	 * For the `refresh` event:
	 *
	 *	* <100: Content-specific commands refresh their job states according
	 *	  to the given path. Jobs save their states in the `evt.data.states` object
	 *	  passed along with the event. This can be either {@link CKEDITOR#TRISTATE_DISABLED}
	 *	  or {@link CKEDITOR#TRISTATE_OFF}.
	 *	* 100: Command state is determined according to what states
	 *	  have been returned by content-specific jobs (`evt.data.states`).
	 *	  UI elements are updated at this stage.
	 *
	 *	  **Note**: If there is at least one job with the {@link CKEDITOR#TRISTATE_OFF} state,
	 *	  then the generic command state is also {@link CKEDITOR#TRISTATE_OFF}. Otherwise,
	 *	  the command state is {@link CKEDITOR#TRISTATE_DISABLED}.
	 *
	 * @param {CKEDITOR.command} command The command to be set up.
	 * @private
	 */
	function setupGenericListeners( editor, command ) {
		var selection, bookmarks;

		// Set the command state according to content-specific
		// command states.
		command.on( 'refresh', function( evt ) {
			// If no state comes with event data, disable command.
			var states = [ TRISTATE_DISABLED ];

			for ( var s in evt.data.states )
				states.push( evt.data.states[ s ] );

			this.setState( CKEDITOR.tools.search( states, TRISTATE_OFF ) ?
					TRISTATE_OFF
				:
					TRISTATE_DISABLED );
		}, command, null, 100 );

		// Initialization. Save bookmarks and mark event as not handled
		// by any plugin (command) yet.
		command.on( 'exec', function( evt ) {
			selection = editor.getSelection();
			bookmarks = selection.createBookmarks( 1 );

			// Mark execution as not handled yet.
			if ( !evt.data )
				evt.data = {};

			evt.data.done = false;
		}, command, null, 0 );

		// Housekeeping. Make sure selectionChange will be called.
		// Also re-select previously saved bookmarks.
		command.on( 'exec', function( evt ) {
			editor.forceNextSelectionCheck();
			selection.selectBookmarks( bookmarks );
		}, command, null, 100 );
	}
})();