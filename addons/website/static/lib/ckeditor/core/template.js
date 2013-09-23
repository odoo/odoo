/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the {@link CKEDITOR.template} class, which represents
 * an UI template for an editor instance.
 */

(function() {
	var cache = {};

	/**
	 * Lightweight template used to build the output string from variables.
	 *
	 *		// HTML template for presenting a label UI.
	 *		var tpl = new CKEDITOR.template( '<div class="{cls}">{label}</div>' );
	 *		alert( tpl.output( { cls: 'cke-label', label: 'foo'} ) ); // '<div class="cke-label">foo</div>'
	 *
	 * @class
	 * @constructor Creates a template class instance.
	 * @param {String} source The template source.
	 */
	CKEDITOR.template = function( source ) {
		// Builds an optimized function body for the output() method, focused on performance.
		// For example, if we have this "source":
		//	'<div style="{style}">{editorName}</div>'
		// ... the resulting function body will be (apart from the "buffer" handling):
		//	return [ '<div style="', data['style'] == undefined ? '{style}' : data['style'], '">', data['editorName'] == undefined ? '{editorName}' : data['editorName'], '</div>' ].join('');

		// Try to read from the cache.
		if ( cache[ source ] )
			this.output = cache[ source ];
		else {
			var fn = source
			// Escape all quotation marks (").
			.replace( /'/g, "\\'" )
			// Inject the template keys replacement.
			.replace( /{([^}]+)}/g, function( m, key ) {
				return "',data['" + key + "']==undefined?'{" + key + "}':data['" + key + "'],'";
			});

			fn = "return buffer?buffer.push('" + fn + "'):['" + fn + "'].join('');";
			this.output = cache[ source ] = Function( 'data', 'buffer', fn );
		}
	};
})();

/**
 * Processes the template, filling its variables with the provided data.
 *
 * @method output
 * @param {Object} data An object containing properties which values will be
 * used to fill the template variables. The property names must match the
 * template variables names. Variables without matching properties will be
 * kept untouched.
 * @param {Array} [buffer] An array into which the output data will be pushed into.
 * The number of entries appended to the array is unknown.
 * @returns {String/Number} If `buffer` has not been provided, the processed
 * template output data, otherwise the new length of `buffer`.
 */
