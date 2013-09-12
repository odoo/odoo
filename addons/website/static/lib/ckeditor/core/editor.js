/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the {@link CKEDITOR.editor} class that represents an
 *		editor instance.
 */

(function() {
	// Override the basic constructor defined at editor_basic.js.
	Editor.prototype = CKEDITOR.editor.prototype;
	CKEDITOR.editor = Editor;

	/**
	 * Represents an editor instance. This constructor should be rarely
	 * used in favor of the {@link CKEDITOR} editor creation functions.
	 *
	 * @class CKEDITOR.editor
	 * @mixins CKEDITOR.event
	 * @constructor Creates an editor class instance.
	 * @param {Object} [instanceConfig] Configuration values for this specific instance.
	 * @param {CKEDITOR.dom.element} [element] The DOM element upon which this editor
	 * will be created.
	 * @param {Number} [mode] The element creation mode to be used by this editor.
	 */
	function Editor( instanceConfig, element, mode ) {
		// Call the CKEDITOR.event constructor to initialize this instance.
		CKEDITOR.event.call( this );

		// Make a clone of the config object, to avoid having it touched by our code. (#9636)
		instanceConfig = instanceConfig && CKEDITOR.tools.clone( instanceConfig );

		// if editor is created off one page element.
		if ( element !== undefined ) {
			// Asserting element and mode not null.
			if ( !( element instanceof CKEDITOR.dom.element ) )
				throw new Error( 'Expect element of type CKEDITOR.dom.element.' );
			else if ( !mode )
				throw new Error( 'One of the element modes must be specified.' );

			if ( CKEDITOR.env.ie && CKEDITOR.env.quirks && mode == CKEDITOR.ELEMENT_MODE_INLINE )
				throw new Error( 'Inline element mode is not supported on IE quirks.' );

			if ( !isSupportedElement( element, mode ) )
				throw new Error( 'The specified element mode is not supported on element: "' + element.getName() + '".' );

			/**
			 * The original host page element upon which the editor is created, it's only
			 * supposed to be provided by the concrete editor creator and is not subjected to
			 * be modified.
			 *
			 * @readonly
			 * @property {CKEDITOR.dom.element}
			 */
			this.element = element;

			/**
			 * This property indicate the way how this instance is associated with the {@link #element}.
			 *
			 * @readonly
			 * @property {Number}
			 * @see CKEDITOR#ELEMENT_MODE_INLINE
			 * @see CKEDITOR#ELEMENT_MODE_REPLACE
			 */
			this.elementMode = mode;

			this.name = ( this.elementMode != CKEDITOR.ELEMENT_MODE_APPENDTO ) && ( element.getId() || element.getNameAtt() );
		}
		else
			this.elementMode = CKEDITOR.ELEMENT_MODE_NONE;

		// Declare the private namespace.
		this._ = {};

		this.commands = {};

		/**
		 * Contains all UI templates created for this editor instance.
		 *
		 * @readonly
		 * @property {Object}
		 */
		this.templates = {};

		/**
		 * A unique identifier of this editor instance.
		 *
		 * **Note:** It will be originated from the ID or name
		 * attribute of the {@link #element}, otherwise a name pattern of
		 * `'editor{n}'` will be used.
		 *
		 * @readonly
		 * @property {String}
		 */
		this.name = this.name || genEditorName();

		/**
		 * A unique random string assigned to each editor instance in the page.
		 *
		 * @readonly
		 * @property {String}
		 */
		this.id = CKEDITOR.tools.getNextId();

		/**
		 * Indicates editor initialization status. The following statuses are available:
		 *
		 *	* **unloaded**: the initial state - editor's instance has been initialized,
		 *	but its components (config, plugins, language files) are not loaded yet.
		 *	* **loaded**: editor's components have been loaded - see {@link CKEDITOR.editor#loaded} event.
		 *	* **ready**: editor is fully initialized and ready - see {@link CKEDITOR.editor#instanceReady} event.
		 *	* **destroyed**: the editor has been destroyed - see {@link CKEDITOR.editor#method-destroy} method.
		 *
		 * @since 4.1
		 * @readonly
		 * @property {String}
		 */
		this.status = 'unloaded';

		/**
		 * The configurations for this editor instance. It inherits all
		 * settings defined in {@link CKEDITOR.config}, combined with settings
		 * loaded from custom configuration files and those defined inline in
		 * the page when creating the editor.
		 *
		 *		var editor = CKEDITOR.instances.editor1;
		 *		alert( editor.config.skin ); // e.g. 'moono'
		 *
		 * @readonly
		 * @property {CKEDITOR.config}
		 */
		this.config = CKEDITOR.tools.prototypedCopy( CKEDITOR.config );

		/**
		 * Namespace containing UI features related to this editor instance.
		 *
		 * @readonly
		 * @property {CKEDITOR.ui}
		 */
		this.ui = new CKEDITOR.ui( this );

		/**
		 * Controls the focus state of this editor instance. This property
		 * is rarely used for normal API operations. It is mainly
		 * destinated to developer adding UI elements to the editor interface.
		 *
		 * @readonly
		 * @property {CKEDITOR.focusManager}
		 */
		this.focusManager = new CKEDITOR.focusManager( this );

		/**
		 * Controls keystrokes typing in this editor instance.
		 *
		 * @readonly
		 * @property {CKEDITOR.keystrokeHandler}
		 */
		this.keystrokeHandler = new CKEDITOR.keystrokeHandler( this );

		// Make the editor update its command states on mode change.
		this.on( 'readOnly', updateCommands );
		this.on( 'selectionChange', function( evt ) {
			updateCommandsContext( this, evt.data.path );
		} );
		this.on( 'activeFilterChange', function( evt ) {
			updateCommandsContext( this, this.elementPath(), true );
		} );
		this.on( 'mode', updateCommands );

		// Handle startup focus.
		this.on( 'instanceReady', function( event ) {
			this.config.startupFocus && this.focus();
		} );

		CKEDITOR.fire( 'instanceCreated', null, this );

		// Add this new editor to the CKEDITOR.instances collections.
		CKEDITOR.add( this );

		// Return the editor instance immediately to enable early stage event registrations.
		CKEDITOR.tools.setTimeout( function() {
			initConfig( this, instanceConfig );
		}, 0, this );
	}

	var nameCounter = 0;

	function genEditorName() {
		do {
			var name = 'editor' + ( ++nameCounter );
		}
		while ( CKEDITOR.instances[ name ] )

		return name;
	}

	// Asserting element DTD depending on mode.
	function isSupportedElement( element, mode ) {
		if ( mode == CKEDITOR.ELEMENT_MODE_INLINE )
			return element.is( CKEDITOR.dtd.$editable ) || element.is( 'textarea' );
		else if ( mode == CKEDITOR.ELEMENT_MODE_REPLACE )
			return !element.is( CKEDITOR.dtd.$nonBodyContent );
		return 1;
	}

	function updateCommands() {
		var commands = this.commands,
			name;

		for ( name in commands )
			updateCommand( this, commands[ name ] );
	}

	function updateCommand( editor, cmd ) {
		cmd[ cmd.startDisabled ? 'disable' : editor.readOnly && !cmd.readOnly ? 'disable' : cmd.modes[ editor.mode ] ? 'enable' : 'disable' ]();
	}

	function updateCommandsContext( editor, path, forceRefresh ) {
		var command,
			name,
			commands = editor.commands;

		for ( name in commands ) {
			command = commands[ name ];

			if ( forceRefresh || command.contextSensitive )
				command.refresh( editor, path );
		}
	}

	// ##### START: Config Privates

	// These function loads custom configuration files and cache the
	// CKEDITOR.editorConfig functions defined on them, so there is no need to
	// download them more than once for several instances.
	var loadConfigLoaded = {};

	function loadConfig( editor ) {
		var customConfig = editor.config.customConfig;

		// Check if there is a custom config to load.
		if ( !customConfig )
			return false;

		customConfig = CKEDITOR.getUrl( customConfig );

		var loadedConfig = loadConfigLoaded[ customConfig ] || ( loadConfigLoaded[ customConfig ] = {} );

		// If the custom config has already been downloaded, reuse it.
		if ( loadedConfig.fn ) {
			// Call the cached CKEDITOR.editorConfig defined in the custom
			// config file for the editor instance depending on it.
			loadedConfig.fn.call( editor, editor.config );

			// If there is no other customConfig in the chain, fire the
			// "configLoaded" event.
			if ( CKEDITOR.getUrl( editor.config.customConfig ) == customConfig || !loadConfig( editor ) )
				editor.fireOnce( 'customConfigLoaded' );
		} else {
			// Load the custom configuration file.
			// To resolve customConfig race conflicts, use scriptLoader#queue
			// instead of scriptLoader#load (#6504).
			CKEDITOR.scriptLoader.queue( customConfig, function() {
				// If the CKEDITOR.editorConfig function has been properly
				// defined in the custom configuration file, cache it.
				if ( CKEDITOR.editorConfig )
					loadedConfig.fn = CKEDITOR.editorConfig;
				else
					loadedConfig.fn = function() {};

				// Call the load config again. This time the custom
				// config is already cached and so it will get loaded.
				loadConfig( editor );
			});
		}

		return true;
	}

	function initConfig( editor, instanceConfig ) {
		// Setup the lister for the "customConfigLoaded" event.
		editor.on( 'customConfigLoaded', function() {
			if ( instanceConfig ) {
				// Register the events that may have been set at the instance
				// configuration object.
				if ( instanceConfig.on ) {
					for ( var eventName in instanceConfig.on ) {
						editor.on( eventName, instanceConfig.on[ eventName ] );
					}
				}

				// Overwrite the settings from the in-page config.
				CKEDITOR.tools.extend( editor.config, instanceConfig, true );

				delete editor.config.on;
			}

			onConfigLoaded( editor );
		});

		// The instance config may override the customConfig setting to avoid
		// loading the default ~/config.js file.
		if ( instanceConfig && instanceConfig.customConfig != undefined )
			editor.config.customConfig = instanceConfig.customConfig;

		// Load configs from the custom configuration files.
		if ( !loadConfig( editor ) )
			editor.fireOnce( 'customConfigLoaded' );
	}

	// ##### END: Config Privates

	// Set config related properties.
	function onConfigLoaded( editor ) {
		var config = editor.config;

		/**
		 * Indicates the read-only state of this editor. This is a read-only property.
		 *
		 * @since 3.6
		 * @readonly
		 * @property {Boolean}
		 * @see CKEDITOR.editor#setReadOnly
		 */
		editor.readOnly = !!(
			config.readOnly || (
				editor.elementMode == CKEDITOR.ELEMENT_MODE_INLINE ?
						editor.element.is( 'textarea' ) ?
								editor.element.hasAttribute( 'disabled' )
							:
								editor.element.isReadOnly()
					:
						editor.elementMode == CKEDITOR.ELEMENT_MODE_REPLACE ?
								editor.element.hasAttribute( 'disabled' )
							:
								false
			)
		);

		/**
		 * Indicates that the editor is running into an environment where
		 * no block elements are accepted inside the content.
		 *
		 * @readonly
		 * @property {Boolean}
		 */
		editor.blockless = editor.elementMode == CKEDITOR.ELEMENT_MODE_INLINE ?
			!( editor.element.is( 'textarea' ) || CKEDITOR.dtd[ editor.element.getName() ][ 'p' ] ) :
			false;

		/**
		 * The [tabbing navigation](http://en.wikipedia.org/wiki/Tabbing_navigation) order determined for this editor instance.
		 * This can be set by the <code>{@link CKEDITOR.config#tabIndex}</code>
		 * setting or taken from the `tabindex` attribute of the
		 * {@link #element} associated with the editor.
		 *
		 *		alert( editor.tabIndex ); // e.g. 0
		 *
		 * @readonly
		 * @property {Number} [=0]
		 */
		editor.tabIndex = config.tabIndex || editor.element && editor.element.getAttribute( 'tabindex' ) || 0;

		editor.activeEnterMode = editor.enterMode = validateEnterMode( editor, config.enterMode );
		editor.activeShiftEnterMode = editor.shiftEnterMode = validateEnterMode( editor, config.shiftEnterMode );

		// Set CKEDITOR.skinName. Note that it is not possible to have
		// different skins on the same page, so the last one to set it "wins".
		if ( config.skin )
			CKEDITOR.skinName = config.skin;

		// Fire the "configLoaded" event.
		editor.fireOnce( 'configLoaded' );

		initComponents( editor );
	}

	// Various other core components that read editor configuration.
	function initComponents( editor ) {
		// Documented in dataprocessor.js.
		editor.dataProcessor = new CKEDITOR.htmlDataProcessor( editor );

		// Set activeFilter directly to avoid firing event.
		editor.filter = editor.activeFilter = new CKEDITOR.filter( editor );

		loadSkin( editor );
	}

	function loadSkin( editor ) {
		CKEDITOR.skin.loadPart( 'editor', function() {
			loadLang( editor );
		});
	}

	function loadLang( editor ) {
		CKEDITOR.lang.load( editor.config.language, editor.config.defaultLanguage, function( languageCode, lang ) {
			var configTitle = editor.config.title;

			/**
			 * The code for the language resources that have been loaded
			 * for the user interface elements of this editor instance.
			 *
			 *		alert( editor.langCode ); // e.g. 'en'
			 *
			 * @readonly
			 * @property {String}
			 */
			editor.langCode = languageCode;

			/**
			 * An object that contains all language strings used by the editor interface.
			 *
			 *		alert( editor.lang.basicstyles.bold ); // e.g. 'Negrito' (if the language is set to Portuguese)
			 *
			 * @readonly
			 * @property {Object} lang
			 */
			// As we'll be adding plugin specific entries that could come
			// from different language code files, we need a copy of lang,
			// not a direct reference to it.
			editor.lang = CKEDITOR.tools.prototypedCopy( lang );

			/**
			 * Indicates the human-readable title of this editor. Although this is a read-only property,
			 * it can be initialized with {@link CKEDITOR.config#title}.
			 *
			 * **Note:** Please do not confuse this property with {@link CKEDITOR.editor#name editor.name}
			 * which identifies the instance in the {@link CKEDITOR#instances} literal.
			 *
			 * @since 4.2
			 * @readonly
			 * @property {String/Boolean}
			 */
			editor.title = typeof configTitle == 'string' || configTitle === false ? configTitle : [ editor.lang.editor, editor.name ].join( ', ' );

			// We're not able to support RTL in Firefox 2 at this time.
			if ( CKEDITOR.env.gecko && CKEDITOR.env.version < 10900 && editor.lang.dir == 'rtl' )
				editor.lang.dir = 'ltr';

			if ( !editor.config.contentsLangDirection ) {
				// Fallback to either the editable element direction or editor UI direction depending on creators.
				editor.config.contentsLangDirection = editor.elementMode == CKEDITOR.ELEMENT_MODE_INLINE ? editor.element.getDirection( 1 ) : editor.lang.dir;
			}

			editor.fire( 'langLoaded' );

			preloadStylesSet( editor );
		});
	}

	// Preloads styles set file (config.stylesSet).
	// If stylesSet was defined directly (by an array)
	// this function will call loadPlugins fully synchronously.
	// If stylesSet is a string (path) loadPlugins will
	// be called asynchronously.
	// In both cases - styles will be preload before plugins initialization.
	function preloadStylesSet( editor ) {
		editor.getStylesSet( function( styles ) {
			// Wait for editor#loaded, so plugins could add their listeners.
			// But listen with high priority to fire editor#stylesSet before editor#uiReady and editor#setData.
			editor.once( 'loaded', function() {
				// Note: we can't use fireOnce because this event may canceled and fired again.
				editor.fire( 'stylesSet', { styles: styles } );
			}, null, null, 1 );

			loadPlugins( editor );
		} );
	}

	function loadPlugins( editor ) {
		var config = editor.config,
			plugins = config.plugins,
			extraPlugins = config.extraPlugins,
			removePlugins = config.removePlugins;

		if ( extraPlugins ) {
			// Remove them first to avoid duplications.
			var extraRegex = new RegExp( '(?:^|,)(?:' + extraPlugins.replace( /\s*,\s*/g, '|' ) + ')(?=,|$)', 'g' );
			plugins = plugins.replace( extraRegex, '' );

			plugins += ',' + extraPlugins;
		}

		if ( removePlugins ) {
			var removeRegex = new RegExp( '(?:^|,)(?:' + removePlugins.replace( /\s*,\s*/g, '|' ) + ')(?=,|$)', 'g' );
			plugins = plugins.replace( removeRegex, '' );
		}

		// Load the Adobe AIR plugin conditionally.
		CKEDITOR.env.air && ( plugins += ',adobeair' );

		// Load all plugins defined in the "plugins" setting.
		CKEDITOR.plugins.load( plugins.split( ',' ), function( plugins ) {
			// The list of plugins.
			var pluginsArray = [];

			// The language code to get loaded for each plugin. Null
			// entries will be appended for plugins with no language files.
			var languageCodes = [];

			// The list of URLs to language files.
			var languageFiles = [];

			/**
			 * An object that contains references to all plugins used by this
			 * editor instance.
			 *
			 *		alert( editor.plugins.dialog.path ); // e.g. 'http://example.com/ckeditor/plugins/dialog/'
			 *
			 *		// Check if a plugin is available.
			 *		if ( editor.plugins.image ) {
			 *			...
			 *		}
			 *
			 * @readonly
			 * @property {Object}
			 */
			editor.plugins = plugins;

			// Loop through all plugins, to build the list of language
			// files to get loaded.
			//
			// Check also whether any of loaded plugins doesn't require plugins
			// defined in config.removePlugins. Throw non-blocking error if this happens.
			for ( var pluginName in plugins ) {
				var plugin = plugins[ pluginName ],
					pluginLangs = plugin.lang,
					lang = null,
					requires = plugin.requires,
					match, name;

				// Transform it into a string, if it's not one.
				if ( CKEDITOR.tools.isArray( requires ) )
					requires = requires.join( ',' );

				if ( requires && ( match = requires.match( removeRegex ) ) ) {
					while ( ( name = match.pop() ) ) {
						CKEDITOR.tools.setTimeout( function( name, pluginName ) {
							throw new Error( 'Plugin "' + name.replace( ',', '' ) + '" cannot be removed from the plugins list, because it\'s required by "' + pluginName + '" plugin.');
						}, 0, null, [ name, pluginName ] );
					}
				}

				// If the plugin has "lang".
				if ( pluginLangs && !editor.lang[ pluginName ] ) {
					// Trasnform the plugin langs into an array, if it's not one.
					if ( pluginLangs.split )
						pluginLangs = pluginLangs.split( ',' );

					// Resolve the plugin language. If the current language
					// is not available, get English or the first one.
					if ( CKEDITOR.tools.indexOf( pluginLangs, editor.langCode ) >= 0 )
						lang = editor.langCode;
					else {
						// The language code may have the locale information (zh-cn).
						// Fall back to locale-less in that case (zh).
						var langPart = editor.langCode.replace( /-.*/, '' );
						if ( langPart != editor.langCode && CKEDITOR.tools.indexOf( pluginLangs, langPart ) >= 0 )
							lang = langPart;
						// Try the only "generic" option we have: English.
						else if ( CKEDITOR.tools.indexOf( pluginLangs, 'en' ) >= 0 )
							lang = 'en';
						else
							lang = pluginLangs[ 0 ];
					}

					if ( !plugin.langEntries || !plugin.langEntries[ lang ] ) {
						// Put the language file URL into the list of files to
						// get downloaded.
						languageFiles.push( CKEDITOR.getUrl( plugin.path + 'lang/' + lang + '.js' ) );
					} else {
						editor.lang[ pluginName ] = plugin.langEntries[ lang ];
						lang = null;
					}
				}

				// Save the language code, so we know later which
				// language has been resolved to this plugin.
				languageCodes.push( lang );

				pluginsArray.push( plugin );
			}

			// Load all plugin specific language files in a row.
			CKEDITOR.scriptLoader.load( languageFiles, function() {
				// Initialize all plugins that have the "beforeInit" and "init" methods defined.
				var methods = [ 'beforeInit', 'init', 'afterInit' ];
				for ( var m = 0; m < methods.length; m++ ) {
					for ( var i = 0; i < pluginsArray.length; i++ ) {
						var plugin = pluginsArray[ i ];

						// Uses the first loop to update the language entries also.
						if ( m === 0 && languageCodes[ i ] && plugin.lang && plugin.langEntries )
							editor.lang[ plugin.name ] = plugin.langEntries[ languageCodes[ i ] ];

						// Call the plugin method (beforeInit and init).
						if ( plugin[ methods[ m ] ] )
							plugin[ methods[ m ] ]( editor );
					}
				}

				editor.fireOnce( 'pluginsLoaded' );

				// Setup the configured keystrokes.
				config.keystrokes && editor.setKeystroke( editor.config.keystrokes );

				// Setup the configured blocked keystrokes.
				for ( i = 0; i < editor.config.blockedKeystrokes.length; i++ )
					editor.keystrokeHandler.blockedKeystrokes[ editor.config.blockedKeystrokes[ i ] ] = 1;

				editor.status = 'loaded';
				editor.fireOnce( 'loaded' );
				CKEDITOR.fire( 'instanceLoaded', null, editor );
			});
		});
	}

	// Send to data output back to editor's associated element.
	function updateEditorElement() {
		var element = this.element;

		// Some editor creation mode will not have the
		// associated element.
		if ( element && this.elementMode != CKEDITOR.ELEMENT_MODE_APPENDTO ) {
			var data = this.getData();

			if ( this.config.htmlEncodeOutput )
				data = CKEDITOR.tools.htmlEncode( data );

			if ( element.is( 'textarea' ) )
				element.setValue( data );
			else
				element.setHtml( data );

			return true;
		}
		return false;
	}

	// Always returns ENTER_BR in case of blockless editor.
	function validateEnterMode( editor, enterMode ) {
		return editor.blockless ? CKEDITOR.ENTER_BR : enterMode;
	}

	CKEDITOR.tools.extend( CKEDITOR.editor.prototype, {
		/**
		 * Adds a command definition to the editor instance. Commands added with
		 * this function can be executed later with the <code>{@link #execCommand}</code> method.
		 *
		 * 		editorInstance.addCommand( 'sample', {
		 * 			exec: function( editor ) {
		 * 				alert( 'Executing a command for the editor name "' + editor.name + '"!' );
		 * 			}
		 * 		} );
		 *
		 * @param {String} commandName The indentifier name of the command.
		 * @param {CKEDITOR.commandDefinition} commandDefinition The command definition.
		 */
		addCommand: function( commandName, commandDefinition ) {
			commandDefinition.name = commandName.toLowerCase();
			var cmd = new CKEDITOR.command( this, commandDefinition );

			// Update command when mode is set.
			// This guarantees that commands added before first editor#mode
			// aren't immediately updated, but waits for editor#mode and that
			// commands added later are immediately refreshed, even when added
			// before instanceReady. #10103, #10249
			if ( this.mode )
				updateCommand( this, cmd );

			return this.commands[ commandName ] = cmd;
		},

		/**
		 * Attaches the editor to a form to call {@link #updateElement} before form submission.
		 * This method is called by both creators ({@link CKEDITOR#replace replace} and
		 * {@link CKEDITOR#inline inline}), so there is no reason to call it manually.
		 *
		 * @private
		 */
		_attachToForm: function() {
			var editor = this,
				element = editor.element,
				form = new CKEDITOR.dom.element( element.$.form );

			// If are replacing a textarea, we must
			if ( element.is( 'textarea' ) ) {
				if ( form ) {
					function onSubmit( evt ) {
						editor.updateElement();

						// #8031 If textarea had required attribute and editor is empty fire 'required' event and if
						// it was cancelled, prevent submitting the form.
						if ( editor._.required && !element.getValue() && editor.fire( 'required' ) === false ) {
							// When user press save button event (evt) is undefined (see save plugin).
							// This method works because it throws error so originalSubmit won't be called.
							// Also this error won't be shown because it will be caught in save plugin.
							evt.data.preventDefault();
						}
					}
					form.on( 'submit', onSubmit );

					function isFunction( f ) {
						// For IE8 typeof fun == object so we cannot use it.
						return !!( f && f.call && f.apply );
					}

					// Check if there is no element/elements input with name == "submit".
					// If they exists they will overwrite form submit function (form.$.submit).
					// If form.$.submit is overwritten we can not do anything with it.
					if ( isFunction( form.$.submit ) ) {
						// Setup the submit function because it doesn't fire the
						// "submit" event.
						form.$.submit = CKEDITOR.tools.override( form.$.submit, function( originalSubmit ) {
							return function() {
								onSubmit();

								// For IE, the DOM submit function is not a
								// function, so we need third check.
								if ( originalSubmit.apply )
									originalSubmit.apply( this );
								else
									originalSubmit();
							};
						} );
					}

					// Remove 'submit' events registered on form element before destroying.(#3988)
					editor.on( 'destroy', function() {
						form.removeListener( 'submit', onSubmit );
					} );
				}
			}
		},

		/**
		 * Destroys the editor instance, releasing all resources used by it.
		 * If the editor replaced an element, the element will be recovered.
		 *
		 *		alert( CKEDITOR.instances.editor1 ); // e.g. object
		 *		CKEDITOR.instances.editor1.destroy();
		 *		alert( CKEDITOR.instances.editor1 ); // undefined
		 *
		 * @param {Boolean} [noUpdate] If the instance is replacing a DOM
		 * element, this parameter indicates whether or not to update the
		 * element with the instance contents.
		 */
		destroy: function( noUpdate ) {
			this.fire( 'beforeDestroy' );

			!noUpdate && updateEditorElement.call( this );

			this.editable( null );

			this.status = 'destroyed';

			this.fire( 'destroy' );

			// Plug off all listeners to prevent any further events firing.
			this.removeAllListeners();

			CKEDITOR.remove( this );
			CKEDITOR.fire( 'instanceDestroyed', null, this );
		},

		/**
		 * @param {CKEDITOR.dom.node} [startNode] From which the path should start, if not specified default to editor selection's
		 * start element yield by {@link CKEDITOR.dom.selection#getStartElement}.
		 * @returns {CKEDITOR.dom.elementPath}
		 * @see CKEDITOR.dom.elementPath
		 */
		elementPath: function( startNode ) {
			startNode = startNode || this.getSelection().getStartElement();
			return startNode ? new CKEDITOR.dom.elementPath( startNode, this.editable() ) : null;
		},

		/**
		 * Shortcut to create a {@link CKEDITOR.dom.range} instance from the editable element.
		 *
		 * @returns {CKEDITOR.dom.range} The dom range created if the editable has presented.
		 * @see CKEDITOR.dom.range
		 */
		createRange: function() {
			var editable = this.editable();
			return editable ? new CKEDITOR.dom.range( editable ) : null;
		},

		/**
		 * Executes a command associated with the editor.
		 *
		 *		editorInstance.execCommand( 'bold' );
		 *
		 * @param {String} commandName The indentifier name of the command.
		 * @param {Object} [data] Data to be passed to the command.
		 * @returns {Boolean} `true` if the command was executed
		 * successfully, otherwise `false`.
		 * @see CKEDITOR.editor#addCommand
		 */
		execCommand: function( commandName, data ) {
			var command = this.getCommand( commandName );

			var eventData = {
				name: commandName,
				commandData: data,
				command: command
			};

			if ( command && command.state != CKEDITOR.TRISTATE_DISABLED ) {
				if ( this.fire( 'beforeCommandExec', eventData ) !== true ) {
					eventData.returnValue = command.exec( eventData.commandData );

					// Fire the 'afterCommandExec' immediately if command is synchronous.
					if ( !command.async && this.fire( 'afterCommandExec', eventData ) !== true )
						return eventData.returnValue;
				}
			}

			// throw 'Unknown command name "' + commandName + '"';
			return false;
		},

		/**
		 * Gets one of the registered commands. Note that after registering a
		 * command definition with {@link #addCommand}, it is
		 * transformed internally into an instance of
		 * {@link CKEDITOR.command}, which will then be returned by this function.
		 *
		 * @param {String} commandName The name of the command to be returned.
		 * This is the same name that is used to register the command with `addCommand`.
		 * @returns {CKEDITOR.command} The command object identified by the provided name.
		 */
		getCommand: function( commandName ) {
			return this.commands[ commandName ];
		},

		/**
		 * Gets the editor data. The data will be in raw format. It is the same
		 * data that is posted by the editor.
		 *
		 *		if ( CKEDITOR.instances.editor1.getData() == '' )
		 *			alert( 'There is no data available' );
		 *
		 * @returns {String} The editor data.
		 */
		getData: function( noEvents ) {
			!noEvents && this.fire( 'beforeGetData' );

			var eventData = this._.data;

			if ( typeof eventData != 'string' ) {
				var element = this.element;
				if ( element && this.elementMode == CKEDITOR.ELEMENT_MODE_REPLACE )
					eventData = element.is( 'textarea' ) ? element.getValue() : element.getHtml();
				else
					eventData = '';
			}

			eventData = { dataValue: eventData };

			// Fire "getData" so data manipulation may happen.
			!noEvents && this.fire( 'getData', eventData );

			return eventData.dataValue;
		},

		/**
		 * Gets the "raw data" currently available in the editor. This is a
		 * fast method which returns the data as is, without processing, so it is
		 * not recommended to use it on resulting pages. Instead it can be used
		 * combined with the {@link #method-loadSnapshot} method in order
		 * to be able to automatically save the editor data from time to time
		 * while the user is using the editor, to avoid data loss, without risking
		 * performance issues.
		 *
		 *		alert( editor.getSnapshot() );
		 *
		 * @see CKEDITOR.editor#getData
		 */
		getSnapshot: function() {
			var data = this.fire( 'getSnapshot' );

			if ( typeof data != 'string' ) {
				var element = this.element;
				if ( element && this.elementMode == CKEDITOR.ELEMENT_MODE_REPLACE )
					data = element.is( 'textarea' ) ? element.getValue() : element.getHtml();
			}

			return data;
		},

		/**
		 * Loads "raw data" into the editor. The data is loaded with processing
		 * straight to the editing area. It should not be used as a way to load
		 * any kind of data, but instead in combination with
		 * {@link #method-getSnapshot} produced data.
		 *
		 *		var data = editor.getSnapshot();
		 *		editor.loadSnapshot( data );
		 *
		 * @see CKEDITOR.editor#setData
		 */
		loadSnapshot: function( snapshot ) {
			this.fire( 'loadSnapshot', snapshot );
		},

		/**
		 * Sets the editor data. The data must be provided in the raw format (HTML).
		 *
		 * Note that this method is asynchronous. The `callback` parameter must
		 * be used if interaction with the editor is needed after setting the data.
		 *
		 *		CKEDITOR.instances.editor1.setData( '<p>This is the editor data.</p>' );
		 *
		 *		CKEDITOR.instances.editor1.setData( '<p>Some other editor data.</p>', function() {
		 *			this.checkDirty(); // true
		 *		});
		 *
		 * @param {String} data HTML code to replace the curent content in the editor.
		 * @param {Function} callback Function to be called after the `setData` is completed.
		 * @param {Boolean} internal Whether to suppress any event firing when copying data internally inside the editor.
		 */
		setData: function( data, callback, internal ) {
			if ( callback ) {
				this.on( 'dataReady', function( evt ) {
					evt.removeListener();
					callback.call( evt.editor );
				});
			}

			// Fire "setData" so data manipulation may happen.
			var eventData = { dataValue: data };
			!internal && this.fire( 'setData', eventData );

			this._.data = eventData.dataValue;

			!internal && this.fire( 'afterSetData', eventData );
		},

		/**
		 * Puts or restores the editor into read-only state. When in read-only,
		 * the user is not able to change the editor contents, but can still use
		 * some editor features. This function sets the {@link #property-readOnly}
		 * property of the editor, firing the {@link #event-readOnly} event.
		 *
		 * **Note:** the current editing area will be reloaded.
		 *
		 * @since 3.6
		 * @param {Boolean} [isReadOnly] Indicates that the editor must go
		 * read-only (`true`, default) or be restored and made editable (`false`).
		 */
		setReadOnly: function( isReadOnly ) {
			isReadOnly = ( isReadOnly == undefined ) || isReadOnly;

			if ( this.readOnly != isReadOnly ) {
				this.readOnly = isReadOnly;

				// Block or release BACKSPACE key according to current read-only
				// state to prevent browser's history navigation (#9761).
				this.keystrokeHandler.blockedKeystrokes[ 8 ] = +isReadOnly;

				this.editable().setReadOnly( isReadOnly );

				// Fire the readOnly event so the editor features can update
				// their state accordingly.
				this.fire( 'readOnly' );
			}
		},

		/**
		 * Inserts HTML code into the currently selected position in the editor in WYSIWYG mode.
		 *
		 * * `"html"` - content being inserted will completely override styles
		 *    of selected position.
		 * * `"unfiltered_html"` - like `"html"` but content isn't filtered with {@link CKEDITOR.filter}.
		 * * `"text"` - content being inserted will inherit styles applied in
		 *    selected position. This mode should be used when inserting "htmlified" plain text
		 *    (HTML without inline styles and styling elements like
		 *    `<b/>, <strong/>, <span style="..."/>`).
		 *
		 * Example:
		 *
		 *		CKEDITOR.instances.editor1.insertHtml( '<p>This is a new paragraph.</p>' );
		 *
		 * @param {String} html HTML code to be inserted into the editor.
		 * @param {String} [mode='html'] Mode in which HTML will be inserted.
		 */
		insertHtml: function( html, mode ) {
			this.fire( 'insertHtml', { dataValue: html, mode: mode } );
		},

		/**
		 * Insert text content into the currently selected position in the
		 * editor in WYSIWYG mode. The styles of the selected element will be applied to the inserted text.
		 * Spaces around the text will be leaving untouched.
		 *
		 *		CKEDITOR.instances.editor1.insertText( ' line1 \n\n line2' );
		 *
		 * @since 3.5
		 * @param {String} text Text to be inserted into the editor.
		 */
		insertText: function( text ) {
			this.fire( 'insertText', text );
		},

		/**
		 * Inserts an element into the currently selected position in the
		 * editor in WYSIWYG mode.
		 *
		 *		var element = CKEDITOR.dom.element.createFromHtml( '<img src="hello.png" border="0" title="Hello" />' );
		 *		CKEDITOR.instances.editor1.insertElement( element );
		 *
		 * @param {CKEDITOR.dom.element} element The element to be inserted
		 * into the editor.
		 */
		insertElement: function( element ) {
			this.fire( 'insertElement', element );
		},

		/**
		 * Moves the selection focus to the editing area space in the editor.
		 */
		focus: function() {
			this.fire( 'beforeFocus' );
		},

		/**
		 * Checks whether the current editor contents present changes when
		 * compared to the contents loaded into the editor at startup, or to
		 * the contents available in the editor when {@link #resetDirty}
		 * was called.
		 *
		 *		function beforeUnload( evt ) {
		 *			if ( CKEDITOR.instances.editor1.checkDirty() )
		 *				return evt.returnValue = "You will lose the changes made in the editor.";
		 *		}
		 *
		 *		if ( window.addEventListener )
		 *			window.addEventListener( 'beforeunload', beforeUnload, false );
		 *		else
		 *			window.attachEvent( 'onbeforeunload', beforeUnload );
		 *
		 * @returns {Boolean} `true` if the contents contain changes.
		 */
		checkDirty: function() {
			return this.status == 'ready' && this._.previousValue !== this.getSnapshot();
		},

		/**
		 * Resets the "dirty state" of the editor so subsequent calls to
		 * {@link #checkDirty} will return `false` if the user will not
		 * have made further changes to the contents.
		 *
		 *		alert( editor.checkDirty() ); // e.g. true
		 *		editor.resetDirty();
		 *		alert( editor.checkDirty() ); // false
		 */
		resetDirty: function() {
			this._.previousValue = this.getSnapshot();
		},

		/**
		 * Updates the <code>&lt;textarea&gt;</code> element that was replaced by the editor with
		 * the current data available in the editor.
		 *
		 * **Note:** This method will only affect those editor instances created
		 * with {@link CKEDITOR#ELEMENT_MODE_REPLACE} element mode or inline instances
		 * bound to `<textarea>` elements.
		 *
		 *		CKEDITOR.instances.editor1.updateElement();
		 *		alert( document.getElementById( 'editor1' ).value ); // The current editor data.
		 *
		 * @see CKEDITOR.editor#element
		 */
		updateElement: function() {
			return updateEditorElement.call( this );
		},

		/**
		 * Assigns keystrokes associated to editor commands.
		 *
		 *		editor.setKeystroke( CKEDITOR.CTRL + 115, 'save' );	// Assigned CTRL+S to "save" command.
		 *		editor.setKeystroke( CKEDITOR.CTRL + 115, false );	// Disabled CTRL+S keystroke assignment.
		 *		editor.setKeystroke( [
		 *			[ CKEDITOR.ALT + 122, false ],
		 *			[ CKEDITOR.CTRL + 121, 'link' ],
		 *			[ CKEDITOR.SHIFT + 120, 'bold' ]
		 *		] );
		 *
		 * This method may be used in the following cases:
		 *
		 * * By plugins (like `link` or `basicstyles`) to set their keystrokes when plugins are being loaded.
		 * * During the runtime to modify existing keystrokes.
		 *
		 * The editor handles keystroke configuration in the following order:
		 *
		 * 1. Plugins use this method to define default keystrokes.
		 * 2. Editor extends default keystrokes with {@link CKEDITOR.config#keystrokes}.
		 * 3. Editor blocks keystrokes defined in {@link CKEDITOR.config#blockedKeystrokes}.
		 *
		 * After all, you can still set new keystrokes using this method during the runtime.
		 *
		 * @since 4.0
		 * @param {Number/Array} keystroke Keystroke or an array of keystroke definitions.
		 * @param {String/Boolean} [behavior] A command to be executed on the keystroke.
		 */
		setKeystroke: function() {
			var keystrokes = this.keystrokeHandler.keystrokes,
				newKeystrokes = CKEDITOR.tools.isArray( arguments[ 0 ] ) ? arguments[ 0 ] : [ [].slice.call( arguments, 0 ) ],
				keystroke, behavior;

			for ( var i = newKeystrokes.length; i--; ) {
				keystroke = newKeystrokes[ i ];
				behavior = 0;

				// It may be a pair of: [ key, command ]
				if ( CKEDITOR.tools.isArray( keystroke ) ) {
					behavior = keystroke[ 1 ];
					keystroke = keystroke[ 0 ];
				}

				if ( behavior )
					keystrokes[ keystroke ] = behavior;
				else
					delete keystrokes[ keystroke ];
			}
		},

		/**
		 * Shorthand for {@link CKEDITOR.filter#addFeature}.
		 *
		 * @since 4.1
		 * @param {CKEDITOR.feature} feature See {@link CKEDITOR.filter#addFeature}.
		 * @returns {Boolean} See {@link CKEDITOR.filter#addFeature}.
		 */
		addFeature: function( feature ) {
			return this.filter.addFeature( feature );
		},

		/**
		 * Sets the active filter ({@link #activeFilter}). Fires {@link #activeFilterChange} event.
		 *
		 *		// Set active filter which allows only 4 elements.
		 *		// Buttons like Bold, Italic will be disabled.
		 *		var filter = new CKEDITOR.filter( 'p strong em br' );
		 *		editor.setActiveFilter( filter );
		 *
		 * If new filter does not allow tags required by default enter modes ({@link CKEDITOR.config#enterMode} and
		 * {@link CKEDITOR.config#shiftEnterMode}), then current enter modes ({@link #enterMode} and {@link #shiftEnterMode})
		 * will be downgraded to other values.
		 *
		 * @since 4.3
		 * @param {CKEDITOR.filter} filter Filter instance or a falsy value (e.g. `null`) to reset to the default one.
		 */
		setActiveFilter: function( filter ) {
			if ( !filter )
				filter = this.filter;

			if ( this.activeFilter !== filter ) {
				this.activeFilter = filter;
				this.fire( 'activeFilterChange' );

				// Reseted active filter to the main one - reset enter modes too.
				if ( filter === this.filter )
					this.setActiveEnterMode( null, null );
				else
					this.setActiveEnterMode( filter.getAllowedEnterMode(), filter.getAllowedEnterMode( true ) );
			}
		},

		/**
		 * Sets current enter modes ({@link #enterMode} and {@link #shiftEnterMode}). Fires {@link @enterModeChange} event.
		 *
		 * Prior to CKEditor 4.3 enter modes were static and it was enough to check {@link CKEDITOR.config#enterMode}
		 * and {@link CKEDITOR.config#shiftEnterMode}. Since 4.3 these options are sources of initial
		 * {@link #enterMode} and {@link #shiftEnterMode} values. Thanks to this method it's possible to change
		 * enter modes during runtime.
		 *
		 * This method should not be used to configure editor &ndash; use {@link CKEDITOR.config#enterMode} and
		 * {@link CKEDITOR.config#shiftEnterMode} instead. This method should be used only to dynamically change
		 * enter mode during runtime based on selection changes (e.g. when selection is moved into the `<pre>` element).
		 * Keep in mind that changed enter mode may be overwritten by other plugin/feature when it decided that
		 * the changed context requires this.
		 *
		 * **Note:** Since CKEditor 4.3 plugins authors should check {@link #enterMode} and {@link #shiftEnterMode}
		 * instead of {@link CKEDITOR.config#enterMode} and {@link CKEDITOR.config#shiftEnterMode}.
		 *
		 * **Note:** In case of blockless editor (inline editor based on element which cannot contain block elements
		 * &ndash; see {@link CKEDITOR.editor#blockless}) only {@link CKEDITOR#ENTER_BR} is a valid enter mode. Therefore
		 * this method will not allow to set other values.
		 *
		 * **Note:** Changing the {@link #activeFilter active filter} may cuase enter mode change if default enter modes
		 * are not allowed by the new filter.
		 *
		 * @since 4.3
		 * @param {Number} enterMode One of {@link CKEDITOR#ENTER_P}, {@link CKEDITOR#ENTER_DIV}, {@link CKEDITOR#ENTER_BR}.
		 * Pass falsy value (e.g. `null`) to reset enter mode to default value.
		 * @param {Number} shiftEnterMode See `enterMode` argument.
		 */
		setActiveEnterMode: function( enterMode, shiftEnterMode ) {
			// Validate passed modes or use default ones (validated on init).
			enterMode = enterMode ? validateEnterMode( this, enterMode ) : this.enterMode;
			shiftEnterMode = shiftEnterMode ? validateEnterMode( this, shiftEnterMode ) : this.shiftEnterMode;

			if ( this.activeEnterMode != enterMode || this.activeShiftEnterMode != shiftEnterMode ) {
				this.activeEnterMode = enterMode;
				this.activeShiftEnterMode = shiftEnterMode;
				this.fire( 'activeEnterModeChange' );
			}
		}
	});
})();

/**
 * The editor has no associated element.
 *
 * @readonly
 * @property {Number} [=0]
 * @member CKEDITOR
 */
CKEDITOR.ELEMENT_MODE_NONE = 0;

/**
 * The element is to be replaced by the editor instance.
 *
 * @readonly
 * @property {Number} [=1]
 * @member CKEDITOR
 */
CKEDITOR.ELEMENT_MODE_REPLACE = 1;

/**
 * The editor is to be created inside the element.
 *
 * @readonly
 * @property {Number} [=2]
 * @member CKEDITOR
 */
CKEDITOR.ELEMENT_MODE_APPENDTO = 2;

/**
 * The editor is to be attached to the element, using it as the editing block.
 *
 * @readonly
 * @property {Number} [=3]
 * @member CKEDITOR
 */
CKEDITOR.ELEMENT_MODE_INLINE = 3;

/**
 * Whether to escape HTML when the editor updates the original input element.
 *
 *		config.htmlEncodeOutput = true;
 *
 * @since 3.1
 * @cfg {Boolean} [htmlEncodeOutput=false]
 * @member CKEDITOR.config
 */

/**
 * If `true`, makes the editor start in read-only state. Otherwise, it will check
 * if the linked `<textarea>` element has the `disabled` attribute.
 *
 *		config.readOnly = true;
 *
 * @since 3.6
 * @cfg {Boolean} [readOnly=false]
 * @member CKEDITOR.config
 * @see CKEDITOR.editor#setReadOnly
 */

/**
 * Sets whether an editable element should have focus when the editor is loading for the first time.
 *
 *		config.startupFocus = true;
 *
 * @cfg {Boolean} [startupFocus=false]
 * @member CKEDITOR.config
 */

 /**
 * Customizes the {@link CKEDITOR.editor#title human-readable title} of this editor. This title is displayed in
 * tooltips and impacts various accessibility aspects, e.g. it is commonly used by screen readers
 * for distinguishing editor instances and for navigation. Accepted values are a string or `false`.
 *
 * **Note:** When `config.title` is set globally, the same value will be applied to all editor instances
 * loaded with this config. This may severely affect accessibility as screen reader users will be unable
 * to distinguish particular editor instances and navigate between them.
 *
 * **Note:** Setting `config.title = false` may also impair accessibility in a similar way.
 *
 * **Note:** Please do not confuse this property with {@link CKEDITOR.editor#name}
 * which identifies the instance in the {@link CKEDITOR#instances} literal.
 *
 *		// Sets the title to 'My WYSIWYG editor.'. The original title of the element (if it exists)
 *		// will be restored once the editor instance is destroyed.
 *		config.title = 'My WYSIWYG editor.';
 *
 *		// Do not touch the title. If the element already has a title, it remains unchanged.
 *		// Also if no title attribute exists, nothing new will be added.
 *		config.title = false;
 *
 * @since 4.2
 * @cfg {String/Boolean} [title=based on editor.name]
 * @member CKEDITOR.config
 * @see CKEDITOR.editor.name
 * @see CKEDITOR.editor.title
 */

/**
 * Sets listeners on editor's events.
 *
 * **Note:** This property can only be set in the `config` object passed directly
 * to {@link CKEDITOR#replace}, {@link CKEDITOR#inline}, and other creators.
 *
 *		CKEDITOR.replace( 'editor1', {
 *			on: {
 *				instanceReady: function() {
 *					alert( this.name ); // 'editor1'
 *				},
 *
 *				key: function() {
 *					// ...
 *				}
 *			}
 *		} );
 *
 * @cfg {Object} on
 * @member CKEDITOR.config
 */

/**
 * The outermost element in the DOM tree in which the editable element resides. It is provided
 * by a specific editor creator after editor UI is created and is not intended to
 * be modified.
 *
 *		var editor = CKEDITOR.instances.editor1;
 *		alert( editor.container.getName() ); // 'span'
 *
 * @readonly
 * @property {CKEDITOR.dom.element} container
 */

/**
 * The document that stores the editor contents.
 *
 * * For the framed editor it is equal to the document inside the
 * iframe containing the editable element.
 * * For the inline editor it is equal to {@link CKEDITOR#document}.
 *
 * The document object is available after the {@link #contentDom} event is fired
 * and may be invalidated when the {@link #contentDomUnload} event is fired
 * (framed editor only).
 *
 *		editor.on( 'contentDom', function() {
 *			console.log( editor.document );
 *		} );
 *
 * @readonly
 * @property {CKEDITOR.dom.document} document
 */

/**
 * The window instance related to the {@link #document} property.
 *
 * It is always equal to the `editor.document.getWindow()`.
 *
 * See {@link #document} property documentation.
 *
 * @readonly
 * @property {CKEDITOR.dom.window} window
 */

/**
 * The main filter instance used for input data filtering, data
 * transformations, and activation of features.
 *
 * It points to a {@link CKEDITOR.filter} instance set up based on
 * editor configuration.
 *
 * @since 4.1
 * @readonly
 * @property {CKEDITOR.filter} filter
 */

/**
 * The active filter instance. This instance will be used to make a decision which
 * commands, buttons and other {@link CKEDITOR.feature features} can be enabled.
 *
 * By default it equals {@link #filter}, but can be changed by {@link setActiveFilter}.
 *
 *		editor.on( 'activeFilterChange', function() {
 *			if ( editor.activeFilter.check( 'cite' ) )
 *				// Do something when <cite> was enabled - e.g. enable a button.
 *			else
 *				// Otherwise do something else.
 *		} );
 *
 * @since 4.3
 * @readonly
 * @property {CKEDITOR.filter} activeFilter
 */

/**
 * Fired when a CKEDITOR instance is created, but still before initializing it.
 * To interact with a fully initialized instance, use the
 * {@link CKEDITOR#instanceReady} event instead.
 *
 * @event instanceCreated
 * @member CKEDITOR
 * @param {CKEDITOR.editor} editor The editor instance that has been created.
 */

/**
 * Fired when CKEDITOR instance's components (config, languages and plugins) are fully
 * loaded and initialized. However, the editor will be fully ready to for interaction
 * on {@link CKEDITOR#instanceReady}.
 *
 * @event instanceLoaded
 * @member CKEDITOR
 * @param {CKEDITOR.editor} editor This editor instance that has been loaded.
 */

/**
 * Fired when a CKEDITOR instance is destroyed.
 *
 * @event instanceDestroyed
 * @member CKEDITOR
 * @param {CKEDITOR.editor} editor The editor instance that has been destroyed.
 */

/**
 * Fired when a CKEDITOR instance is created, fully initialized and ready for interaction.
 *
 * @event instanceReady
 * @member CKEDITOR
 * @param {CKEDITOR.editor} editor The editor instance that has been created.
 */

/**
 * Fired when the language is loaded into the editor instance.
 *
 * @since 3.6.1
 * @event langLoaded
 * @param {CKEDITOR.editor} editor This editor instance.
 */

/**
 * Fired when all plugins are loaded and initialized into the editor instance.
 *
 * @event pluginsLoaded
 * @param {CKEDITOR.editor} editor This editor instance.
 */

/**
 * Fired when styles set is loaded. During editor initialization
 * phase the {@link #getStylesSet} method returns only styles that
 * are already loaded, which may not include e.g. styles parsed
 * by `stylesheetparser` plugin. Thus, to be notified when all
 * styles are ready you can listen on this event.
 *
 * @since 4.1
 * @event stylesSet
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param {Array} styles Array of styles definitions.
 */

/**
 * Fired before the command execution when {@link #execCommand} is called.
 *
 * @event beforeCommandExec
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param data
 * @param {String} data.name The command name.
 * @param {Object} data.commandData The data to be sent to the command. This
 * can be manipulated by the event listener.
 * @param {CKEDITOR.command} data.command The command itself.
 */

/**
 * Fired after the command execution when {@link #execCommand} is called.
 *
 * @event afterCommandExec
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param data
 * @param {String} data.name The command name.
 * @param {Object} data.commandData The data sent to the command.
 * @param {CKEDITOR.command} data.command The command itself.
 * @param {Object} data.returnValue The value returned by the command execution.
 */

/**
 * Fired when the custom configuration file is loaded, before the final
 * configurations initialization.
 *
 * Custom configuration files can be loaded thorugh the
 * {@link CKEDITOR.config#customConfig} setting. Several files can be loaded
 * by changing this setting.
 *
 * @event customConfigLoaded
 * @param {CKEDITOR.editor} editor This editor instance.
 */

/**
 * Fired once the editor configuration is ready (loaded and processed).
 *
 * @event configLoaded
 * @param {CKEDITOR.editor} editor This editor instance.
 */

/**
 * Fired when this editor instance is destroyed. The editor at this
 * point is not usable and this event should be used to perform the clean-up
 * in any plugin.
 *
 * @event destroy
 * @param {CKEDITOR.editor} editor This editor instance.
 */

/**
 * Internal event to get the current data.
 *
 * @event beforeGetData
 * @param {CKEDITOR.editor} editor This editor instance.
 */

/**
 * Internal event to perform the {@link #method-getSnapshot} call.
 *
 * @event getSnapshot
 * @param {CKEDITOR.editor} editor This editor instance.
 */

/**
 * Internal event to perform the {@link #method-loadSnapshot} call.
 *
 * @event loadSnapshot
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param {String} data The data that will be used.
 */

/**
 * Event fired before the {@link #method-getData} call returns allowing additional manipulation.
 *
 * @event getData
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param data
 * @param {String} data.dataValue The data that will be returned.
 */

/**
 * Event fired before the {@link #method-setData} call is executed allowing additional manipulation.
 *
 * @event setData
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param data
 * @param {String} data.dataValue The data that will be used.
 */

/**
 * Event fired at the end of the {@link #method-setData} call execution. Usually it is better to use the
 * {@link #dataReady} event.
 *
 * @event afterSetData
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param data
 * @param {String} data.dataValue The data that has been set.
 */

/**
 * Fired as an indicator of the editor data loading. It may be the result of
 * calling {@link #method-setData} explicitly or an internal
 * editor function, like the editor editing mode switching (move to Source and back).
 *
 * @event dataReady
 * @param {CKEDITOR.editor} editor This editor instance.
 */

/**
 * Fired when the CKEDITOR instance is completely created, fully initialized
 * and ready for interaction.
 *
 * @event instanceReady
 * @param {CKEDITOR.editor} editor This editor instance.
 */

/**
 * Fired when editor's components (config, languages and plugins) are fully
 * loaded and initialized. However, the editor will be fully ready to for interaction
 * on {@link #instanceReady}.
 *
 * @event loaded
 * @param {CKEDITOR.editor} editor This editor instance.
 */

/**
 * Internal event to perform the {@link #method-insertHtml} call.
 *
 * @event insertHtml
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param data
 * @param {String} data.mode Mode in which data is inserted (see {@link #method-insertHtml}).
 * @param {String} data.dataValue The HTML to insert.
 */

/**
 * Internal event to perform the {@link #method-insertText} call.
 *
 * @event insertText
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param {String} data The text to insert.
 */

/**
 * Internal event to perform the {@link #method-insertElement} call.
 *
 * @event insertElement
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param {CKEDITOR.dom.element} data The element to insert.
 */

/**
 * Event fired after the {@link #property-readOnly} property changes.
 *
 * @since 3.6
 * @event readOnly
 * @param {CKEDITOR.editor} editor This editor instance.
 */

/**
 * Event fired when an UI template is added to the editor instance. It makes
 * it possible to bring customizations to the template source.
 *
 * @event template
 * @param {CKEDITOR.editor} editor This editor instance.
 * @param data
 * @param {String} data.name The template name.
 * @param {String} data.source The source data for this template.
 */

/**
 * Fired when content of the editor (its DOM structure) is ready.
 * It is similar to native DOMContentLoaded event, but it concerns
 * editor's content. It is also a first event fired after
 * {@link CKEDITOR.editable} is initialized.
 *
 * This event is particularly important for framed editor, because
 * on editor initialization and every time data are set
 * (by {@link CKEDITOR.editor#method-setData}) contents DOM structure
 * is rebuilt. Thus, e.g. you need to attach DOM events listeners
 * on editable one more time.
 *
 * On inline editor this event is fired only once - when editor
 * is initialized for the first time. That's because setting
 * editor's content doesn't cause editable destruction and creation.
 *
 * {@link #contentDom} goes along with {@link #contentDomUnload} which
 * is fired before contents DOM structure is destroyed. This is the
 * right moment to detach content DOM events listener. Otherwise
 * browsers like IE or Opera may throw exceptions when accessing
 * elements from detached document.
 *
 * **Note:** {@link CKEDITOR.editable#attachListener} is a convenient
 * way to attach listeners that will be detached on {@link #contentDomUnload}.
 *
 *		editor.on( 'contentDom', function() {
 *			var editable = editor.editable();
 *
 *			editable.attachListener( editable, 'click', function() {
 *				console.log( 'Editable has been clicked' );
 *			});
 *		});
 *
 * @event contentDom
 * @param {CKEDITOR.editor} editor This editor instance.
 */

/**
 * Fired before contents DOM structure is destroyed.
 * See {@link #contentDom} documentation for more details.
 *
 * @event contentDomUnload
 * @param {CKEDITOR.editor} editor This editor instance.
 */