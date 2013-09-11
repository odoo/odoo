/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the {@link CKEDITOR.plugins} object, which is used to
 *		manage plugins registration and loading.
 */

/**
 * Manages plugins registration and loading.
 *
 * @class
 * @extends CKEDITOR.resourceManager
 * @singleton
 */
CKEDITOR.plugins = new CKEDITOR.resourceManager( 'plugins/', 'plugin' );

// PACKAGER_RENAME( CKEDITOR.plugins )

CKEDITOR.plugins.load = CKEDITOR.tools.override( CKEDITOR.plugins.load, function( originalLoad ) {
	var initialized = {};

	return function( name, callback, scope ) {
		var allPlugins = {};

		var loadPlugins = function( names ) {
				originalLoad.call( this, names, function( plugins ) {
					CKEDITOR.tools.extend( allPlugins, plugins );

					var requiredPlugins = [];
					for ( var pluginName in plugins ) {
						var plugin = plugins[ pluginName ],
							requires = plugin && plugin.requires;

						if ( !initialized[ pluginName ] ) {
							// Register all icons eventually defined by this plugin.
							if ( plugin.icons ) {
								var icons = plugin.icons.split( ',' );
								for ( var ic = icons.length; ic--; ) {
									CKEDITOR.skin.addIcon( icons[ ic ],
										plugin.path +
										'icons/' +
										( CKEDITOR.env.hidpi && plugin.hidpi ? 'hidpi/' : '' ) +
										icons[ ic ] +
										'.png' );
								}
							}
							initialized[ pluginName ] = 1;
						}

						if ( requires ) {
							// Trasnform it into an array, if it's not one.
							if ( requires.split )
								requires = requires.split( ',' );

							for ( var i = 0; i < requires.length; i++ ) {
								if ( !allPlugins[ requires[ i ] ] )
									requiredPlugins.push( requires[ i ] );
							}
						}
					}

					if ( requiredPlugins.length )
						loadPlugins.call( this, requiredPlugins );
					else {
						// Call the "onLoad" function for all plugins.
						for ( pluginName in allPlugins ) {
							plugin = allPlugins[ pluginName ];
							if ( plugin.onLoad && !plugin.onLoad._called ) {
								// Make it possible to return false from plugin::onLoad to disable it.
								if ( plugin.onLoad() === false )
									delete allPlugins[ pluginName ];

								plugin.onLoad._called = 1;
							}
						}

						// Call the callback.
						if ( callback )
							callback.call( scope || window, allPlugins );
					}
				}, this );

			};

		loadPlugins.call( this, name );
	};
});

/**
 * Loads a specific language file, or auto detect it. A callback is
 * then called when the file gets loaded.
 *
 *		CKEDITOR.plugins.setLang( 'myPlugin', 'en', {
 *			title: 'My plugin',
 *			selectOption: 'Please select an option'
 *		} );
 *
 * @param {String} pluginName The name of the plugin to which the provided translation
 * should be attached.
 * @param {String} languageCode The code of the language translation provided.
 * @param {Object} languageEntries An object that contains pairs of label and
 * the respective translation.
 */
CKEDITOR.plugins.setLang = function( pluginName, languageCode, languageEntries ) {
	var plugin = this.get( pluginName ),
		pluginLangEntries = plugin.langEntries || ( plugin.langEntries = {} ),
		pluginLang = plugin.lang || ( plugin.lang = [] );

	if ( pluginLang.split )
		pluginLang = pluginLang.split( ',' );

	if ( CKEDITOR.tools.indexOf( pluginLang, languageCode ) == -1 )
		pluginLang.push( languageCode );

	pluginLangEntries[ languageCode ] = languageEntries;
};
