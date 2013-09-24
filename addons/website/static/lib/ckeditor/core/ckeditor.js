/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Contains the third and last part of the {@link CKEDITOR} object
 *		definition.
 */

/** @class CKEDITOR */

// Remove the CKEDITOR.loadFullCore reference defined on ckeditor_basic.
delete CKEDITOR.loadFullCore;

/**
 * Stores references to all editor instances created. The name of the properties
 * in this object correspond to instance names, and their values contain the
 * {@link CKEDITOR.editor} object representing them.
 *
 *		alert( CKEDITOR.instances.editor1.name ); // 'editor1'
 *
 * @property {Object}
 */
CKEDITOR.instances = {};

/**
 * The document of the window storing the CKEDITOR object.
 *
 *		alert( CKEDITOR.document.getBody().getName() ); // 'body'
 *
 * @property {CKEDITOR.dom.document}
 */
CKEDITOR.document = new CKEDITOR.dom.document( document );

/**
 * Adds an editor instance to the global {@link CKEDITOR} object. This function
 * is available for internal use mainly.
 *
 * @param {CKEDITOR.editor} editor The editor instance to be added.
 */
CKEDITOR.add = function( editor ) {
	CKEDITOR.instances[ editor.name ] = editor;

	editor.on( 'focus', function() {
		if ( CKEDITOR.currentInstance != editor ) {
			CKEDITOR.currentInstance = editor;
			CKEDITOR.fire( 'currentInstance' );
		}
	});

	editor.on( 'blur', function() {
		if ( CKEDITOR.currentInstance == editor ) {
			CKEDITOR.currentInstance = null;
			CKEDITOR.fire( 'currentInstance' );
		}
	});

	CKEDITOR.fire( 'instance', null, editor );
};

/**
 * Removes an editor instance from the global {@link CKEDITOR} object. This function
 * is available for internal use only. External code must use {@link CKEDITOR.editor#method-destroy}.
 *
 * @private
 * @param {CKEDITOR.editor} editor The editor instance to be removed.
 */
CKEDITOR.remove = function( editor ) {
	delete CKEDITOR.instances[ editor.name ];
};

(function() {
	var tpls = {};

	/**
	 * Adds a named {@link CKEDITOR.template} instance to be reused among all editors.
	 * This will return the existing one if a template with same name is already
	 * defined. Additionally, it fires the "template" event to allow template source customization.
	 *
	 * @param {String} name The name which identifies a UI template.
	 * @param {String} source The source string for constructing this template.
	 * @returns {CKEDITOR.template} The created template instance.
	 */
	CKEDITOR.addTemplate = function( name, source ) {
		var tpl = tpls[ name ];
		if ( tpl )
			return tpl;

		// Make it possible to customize the template through event.
		var params = { name: name, source: source };
		CKEDITOR.fire( 'template', params );

		return ( tpls[ name ] = new CKEDITOR.template( params.source ) );
	};

	/**
	 * Retrieves a defined template created with {@link CKEDITOR#addTemplate}.
	 *
	 * @param {String} name The template name.
	 */
	CKEDITOR.getTemplate = function( name ) {
		return tpls[ name ];
	};
})();

(function() {
	var styles = [];

	/**
	 * Adds CSS rules to be appended to the editor document.
	 * This method is mostly used by plugins to add custom styles to the editor
	 * document. For basic content styling the `contents.css` file should be
	 * used instead.
	 *
	 * **Note:** This function should be called before the creation of editor instances.
	 *
	 *		// Add styles for all headings inside editable contents.
	 *		CKEDITOR.addCss( '.cke_editable h1,.cke_editable h2,.cke_editable h3 { border-bottom: 1px dotted red }' );
	 *
	 * @param {String} css The style rules to be appended.
	 * @see CKEDITOR.config#contentsCss
	 */
	CKEDITOR.addCss = function( css ) {
		styles.push( css );
	};

	/**
	 * Returns a string will all CSS rules passed to the {@link CKEDITOR#addCss} method.
	 *
	 * @returns {String} A string containing CSS rules.
	 */
	CKEDITOR.getCss = function() {
		return styles.join( '\n' );
	};
})();

// Perform global clean up to free as much memory as possible
// when there are no instances left
CKEDITOR.on( 'instanceDestroyed', function() {
	if ( CKEDITOR.tools.isEmpty( this.instances ) )
		CKEDITOR.fire( 'reset' );
});

// Load the bootstrap script.
CKEDITOR.loader.load( '_bootstrap' ); // %REMOVE_LINE%

// Tri-state constants.
/**
 * Used to indicate the ON or ACTIVE state.
 *
 * @readonly
 * @property {Number} [=1]
 */
CKEDITOR.TRISTATE_ON = 1;

/**
 * Used to indicate the OFF or INACTIVE state.
 *
 * @readonly
 * @property {Number} [=2]
 */
CKEDITOR.TRISTATE_OFF = 2;

/**
 * Used to indicate the DISABLED state.
 *
 * @readonly
 * @property {Number} [=0]
 */
CKEDITOR.TRISTATE_DISABLED = 0;

/**
 * The editor which is currently active (has user focus).
 *
 *		function showCurrentEditorName() {
 *			if ( CKEDITOR.currentInstance )
 *				alert( CKEDITOR.currentInstance.name );
 *			else
 *				alert( 'Please focus an editor first.' );
 *		}
 *
 * @property {CKEDITOR.editor} currentInstance
 * @see CKEDITOR#event-currentInstance
 */

/**
 * Fired when the CKEDITOR.currentInstance object reference changes. This may
 * happen when setting the focus on different editor instances in the page.
 *
 *		var editor; // A variable to store a reference to the current editor.
 *		CKEDITOR.on( 'currentInstance', function() {
 *			editor = CKEDITOR.currentInstance;
 *		} );
 *
 * @event currentInstance
 */

/**
 * Fired when the last instance has been destroyed. This event is used to perform
 * global memory cleanup.
 *
 * @event reset
 */
