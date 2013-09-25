/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the "virtual" {@link CKEDITOR.pluginDefinition} class which
 *		contains the defintion of a plugin. This file is for documentation
 *		purposes only.
 */

/**
 * Virtual class which just illustrates the features of plugin objects to be
 * passed to the {@link CKEDITOR.plugins#add} method.
 *
 * This class is not really part of the API, so its constructor should not be called.
 *
 * @class CKEDITOR.pluginDefinition
 * @abstract
 */

/**
 * A list of plugins that are required by this plugin. Note that this property
 * does not determine the loading order of the plugins.
 *
 *		CKEDITOR.plugins.add( 'sample', {
 *			requires: [ 'button', 'selection' ]
 *		} );
 *
 * @property {Array} requires
 */

/**
 * A list of language files available for this plugin. These files are stored inside
 * the `lang` directory inside the plugin directory, follow the name
 * pattern of `langCode.js`, and contain the language definition created with
 * {@link CKEDITOR.plugins#setLang}.
 *
 * When the plugin is being loaded, the editor checks this list to see if
 * a language file of the current editor language ({@link CKEDITOR.editor#langCode})
 * is available, and if so, loads it. Otherwise, the file represented by the first item
 * in the list is loaded.
 *
 *		CKEDITOR.plugins.add( 'sample', {
 *			lang: [ 'en', 'fr' ]
 *		} );
 *
 * @property {Array} lang
 */

/**
 * A function called on initialization of every editor instance created in the
 * page before the {@link #init} call task. The `beforeInit` function will be called for
 * all plugins, after that the `init` function is called for all of them. This
 * feature makes it possible to initialize things that could be used in the
 * `init` function of other plugins.
 *
 *		CKEDITOR.plugins.add( 'sample', {
 *			beforeInit: function( editor ) {
 *				alert( 'Editor "' + editor.name + '" is to be initialized!' );
 *			}
 *		} );
 *
 * @method beforeInit
 * @param {CKEDITOR.editor} editor The editor instance being initialized.
 */

/**
 * Function called on initialization of every editor instance created in the page.
 *
 *		CKEDITOR.plugins.add( 'sample', {
 *			init: function( editor ) {
 *				alert( 'Editor "' + editor.name + '" is being initialized!' );
 *			}
 *		} );
 *
 * @method init
 * @param {CKEDITOR.editor} editor The editor instance being initialized.
 */

/**
 * Announces the plugin as HiDPI-ready (optimized for high pixel density screens, e.g. *Retina*)
 * by providing high-resolution icons and images. HiDPI icons must be twice as big
 * (defaults are `16px x 16px`) and stored under `plugin_name/icons/hidpi/` directory.
 *
 * The common place for additional HiDPI images used by the plugin (**but not icons**)
 * is `plugin_name/images/hidpi/` directory.
 *
 * This property is optional and only makes sense if `32px x 32px` icons
 * and high-resolution images actually exist. If this flag is set `true`, the editor
 * will automatically detect the HiDPI environment and attempt to load the
 * high-resolution resources.
 *
 * @since 4.2
 * @property {Boolean} hidpi
 */