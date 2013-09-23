/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the {@link CKEDITOR.config} object that stores the
 * default configuration settings.
 */

/**
 * Used in conjunction with {@link CKEDITOR.config#enterMode}
 * and {@link CKEDITOR.config#shiftEnterMode} configuration
 * settings to make the editor produce `<p>` tags when
 * using the *Enter* key.
 *
 * @readonly
 * @property {Number} [=1]
 * @member CKEDITOR
 */
CKEDITOR.ENTER_P = 1;

/**
 * Used in conjunction with {@link CKEDITOR.config#enterMode}
 * and {@link CKEDITOR.config#shiftEnterMode} configuration
 * settings to make the editor produce `<br>` tags when
 * using the *Enter* key.
 *
 * @readonly
 * @property {Number} [=2]
 * @member CKEDITOR
 */
CKEDITOR.ENTER_BR = 2;

/**
 * Used in conjunction with {@link CKEDITOR.config#enterMode}
 * and {@link CKEDITOR.config#shiftEnterMode} configuration
 * settings to make the editor produce `<div>` tags when
 * using the *Enter* key.
 *
 * @readonly
 * @property {Number} [=3]
 * @member CKEDITOR
 */
CKEDITOR.ENTER_DIV = 3;

/**
 * Stores default configuration settings. Changes to this object are
 * reflected in all editor instances, if not specified otherwise for a particular
 * instance.
 *
 * @class
 * @singleton
 */
CKEDITOR.config = {
	/**
	 * The URL path for the custom configuration file to be loaded. If not
	 * overloaded with inline configuration, it defaults to the `config.js`
	 * file present in the root of the CKEditor installation directory.
	 *
	 * CKEditor will recursively load custom configuration files defined inside
	 * other custom configuration files.
	 *
	 *		// Load a specific configuration file.
	 *		CKEDITOR.replace( 'myfield', { customConfig: '/myconfig.js' } );
	 *
	 *		// Do not load any custom configuration file.
	 *		CKEDITOR.replace( 'myfield', { customConfig: '' } );
	 *
	 * @cfg {String} [="<CKEditor folder>/config.js"]
	 */
	customConfig: 'config.js',

	/**
	 * Whether the replaced element (usually a `<textarea>`)
	 * is to be updated automatically when posting the form containing the editor.
	 *
	 * @cfg
	 */
	autoUpdateElement: true,

	/**
	 * The user interface language localization to use. If left empty, the editor
	 * will automatically be localized to the user language. If the user language is not supported,
	 * the language specified in the {@link CKEDITOR.config#defaultLanguage}
	 * configuration setting is used.
	 *
	 *		// Load the German interface.
	 *		config.language = 'de';
	 *
	 * @cfg
	 */
	language: '',

	/**
	 * The language to be used if the {@link CKEDITOR.config#language}
	 * setting is left empty and it is not possible to localize the editor to the user language.
	 *
	 *		config.defaultLanguage = 'it';
	 *
	 * @cfg
	 */
	defaultLanguage: 'en',

	/**
	 * The writting direction of the language used to write the editor
	 * contents. Allowed values are:
	 *
	 * * `''` (empty string) - indicate content direction will be the same with either the editor
	 *     UI direction or page element direction depending on the creators:
	 *     * Themed UI: The same with user interface language direction;
	 *     * Inline: The same with the editable element text direction;
	 * * `'ltr'` - for Left-To-Right language (like English);
	 * * `'rtl'` - for Right-To-Left languages (like Arabic).
	 *
	 * Example:
	 *
	 *		config.contentsLangDirection = 'rtl';
	 *
	 * @cfg
	 */
	contentsLangDirection: '',

	/**
	 * Sets the behavior of the *Enter* key. It also determines other behavior
	 * rules of the editor, like whether the `<br>` element is to be used
	 * as a paragraph separator when indenting text.
	 * The allowed values are the following constants that cause the behavior outlined below:
	 *
	 * * {@link CKEDITOR#ENTER_P} (1) &ndash; new `<p>` paragraphs are created;
	 * * {@link CKEDITOR#ENTER_BR} (2) &ndash; lines are broken with `<br>` elements;
	 * * {@link CKEDITOR#ENTER_DIV} (3) &ndash; new `<div>` blocks are created.
	 *
	 * **Note**: It is recommended to use the {@link CKEDITOR#ENTER_P} setting because of
	 * its semantic value and correctness. The editor is optimized for this setting.
	 *
	 *		// Not recommended.
	 *		config.enterMode = CKEDITOR.ENTER_BR;
	 *
	 * @cfg {Number} [=CKEDITOR.ENTER_P]
	 */
	enterMode: CKEDITOR.ENTER_P,

	/**
	 * Force the use of {@link CKEDITOR.config#enterMode} as line break regardless
	 * of the context. If, for example, {@link CKEDITOR.config#enterMode} is set
	 * to {@link CKEDITOR#ENTER_P}, pressing the *Enter* key inside a
	 * `<div>` element will create a new paragraph with `<p>`
	 * instead of a `<div>`.
	 *
	 *		// Not recommended.
	 *		config.forceEnterMode = true;
	 *
	 * @since 3.2.1
	 * @cfg
	 */
	forceEnterMode: false,

	/**
	 * Similarly to the {@link CKEDITOR.config#enterMode} setting, it defines the behavior
	 * of the *Shift+Enter* key combination.
	 *
	 * The allowed values are the following constants the behavior outlined below:
	 *
	 * * {@link CKEDITOR#ENTER_P} (1) &ndash; new `<p>` paragraphs are created;
	 * * {@link CKEDITOR#ENTER_BR} (2) &ndash; lines are broken with `<br>` elements;
	 * * {@link CKEDITOR#ENTER_DIV} (3) &ndash; new `<div>` blocks are created.
	 *
	 * Example:
	 *
	 *		config.shiftEnterMode = CKEDITOR.ENTER_P;
	 *
	 * @cfg {Number} [=CKEDITOR.ENTER_BR]
	 */
	shiftEnterMode: CKEDITOR.ENTER_BR,

	/**
	 * Sets the `DOCTYPE` to be used when loading the editor content as HTML.
	 *
	 *		// Set the DOCTYPE to the HTML 4 (Quirks) mode.
	 *		config.docType = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">';
	 *
	 * @cfg
	 */
	docType: '<!DOCTYPE html>',

	/**
	 * Sets the `id` attribute to be used on the `body` element
	 * of the editing area. This can be useful when you intend to reuse the original CSS
	 * file you are using on your live website and want to assign the editor the same ID
	 * as the section that will include the contents. In this way ID-specific CSS rules will
	 * be enabled.
	 *
	 *		config.bodyId = 'contents_id';
	 *
	 * @since 3.1
	 * @cfg
	 */
	bodyId: '',

	/**
	 * Sets the `class` attribute to be used on the `body` element
	 * of the editing area. This can be useful when you intend to reuse the original CSS
	 * file you are using on your live website and want to assign the editor the same class
	 * as the section that will include the contents. In this way class-specific CSS rules will
	 * be enabled.
	 *
	 *		config.bodyClass = 'contents';
	 *
	 * @since 3.1
	 * @cfg
	 */
	bodyClass: '',

	/**
	 * Indicates whether the contents to be edited are being input as a full HTML page.
	 * A full page includes the `<html>`, `<head>`, and `<body>` elements.
	 * The final output will also reflect this setting, including the
	 * `<body>` contents only if this setting is disabled.
	 *
	 *		config.fullPage = true;
	 *
	 * @since 3.1
	 * @cfg
	 */
	fullPage: false,

	/**
	 * The height of the editing area (that includes the editor content). This
	 * can be an integer, for pixel sizes, or any CSS-defined length unit.
	 *
	 * **Note:** Percent units (%) are not supported.
	 *
	 *		config.height = 500;		// 500 pixels.
	 *		config.height = '25em';		// CSS length.
	 *		config.height = '300px';	// CSS length.
	 *
	 * @cfg {Number/String}
	 */
	height: 200,

	/**
	 * Comma separated list of plugins to be used for an editor instance,
	 * besides, the actual plugins that to be loaded could be still affected by two other settings:
	 * {@link CKEDITOR.config#extraPlugins} and {@link CKEDITOR.config#removePlugins}.
	 *
	 * @cfg {String} [="<default list of plugins>"]
	 */
	plugins: '', // %REMOVE_LINE%

	/**
	 * A list of additional plugins to be loaded. This setting makes it easier
	 * to add new plugins without having to touch {@link CKEDITOR.config#plugins} setting.
	 *
	 *		config.extraPlugins = 'myplugin,anotherplugin';
	 *
	 * @cfg
	 */
	extraPlugins: '',

	/**
	 * A list of plugins that must not be loaded. This setting makes it possible
	 * to avoid loading some plugins defined in the {@link CKEDITOR.config#plugins}
	 * setting, without having to touch it.
	 *
	 * **Note:** Plugin required by other plugin cannot be removed (error will be thrown).
	 * So e.g. if `contextmenu` is required by `tabletools`, then it can be removed
	 * only if `tabletools` isn't loaded.
	 *
	 *		config.removePlugins = 'elementspath,save,font';
	 *
	 * @cfg
	 */
	removePlugins: '',

	/**
	 * List of regular expressions to be executed on input HTML,
	 * indicating HTML source code that when matched, must **not** be available in the WYSIWYG
	 * mode for editing.
	 *
	 *		config.protectedSource.push( /<\?[\s\S]*?\?>/g );											// PHP code
	 *		config.protectedSource.push( /<%[\s\S]*?%>/g );												// ASP code
	 *		config.protectedSource.push( /(<asp:[^\>]+>[\s|\S]*?<\/asp:[^\>]+>)|(<asp:[^\>]+\/>)/gi );	// ASP.Net code
	 *
	 * @cfg
	 */
	protectedSource: [],

	/**
	 * The editor `tabindex` value.
	 *
	 *		config.tabIndex = 1;
	 *
	 * @cfg
	 */
	tabIndex: 0,

	/**
	 * The editor UI outer width. This can be an integer, for pixel sizes, or
	 * any CSS-defined unit.
	 *
	 * Unlike the {@link CKEDITOR.config#height} setting, this
	 * one will set the outer width of the entire editor UI, not for the
	 * editing area only.
	 *
	 *		config.width = 850;		// 850 pixels wide.
	 *		config.width = '75%';	// CSS unit.
	 *
	 * @cfg {String/Number}
	 */
	width: '',

	/**
	 * The base Z-index for floating dialog windows and popups.
	 *
	 *		config.baseFloatZIndex = 2000;
	 *
	 * @cfg
	 */
	baseFloatZIndex: 10000,

	/**
	 * The keystrokes that are blocked by default as the browser implementation
	 * is buggy. These default keystrokes are handled by the editor.
	 *
	 * @cfg {Array} [=[ CKEDITOR.CTRL + 66, CKEDITOR.CTRL + 73, CKEDITOR.CTRL + 85 ] // CTRL+B,I,U]
	 */
	blockedKeystrokes: [
		CKEDITOR.CTRL + 66, // CTRL+B
		CKEDITOR.CTRL + 73, // CTRL+I
		CKEDITOR.CTRL + 85 // CTRL+U
	]
};

/**
 * Indicates that some of the editor features, like alignment and text
 * direction, should use the "computed value" of the feature to indicate its
 * on/off state instead of using the "real value".
 *
 * If enabled in a Left-To-Right written document, the "Left Justify"
 * alignment button will be shown as active, even if the alignment style is not
 * explicitly applied to the current paragraph in the editor.
 *
 *		config.useComputedState = false;
 *
 * @since 3.4
 * @cfg {Boolean} [useComputedState=true]
 */

/**
 * The base user interface color to be used by the editor. Not all skins are
 * compatible with this setting.
 *
 *		// Using a color code.
 *		config.uiColor = '#AADC6E';
 *
 *		// Using an HTML color name.
 *		config.uiColor = 'Gold';
 *
 * @cfg {String} uiColor
 */

// PACKAGER_RENAME( CKEDITOR.config )
