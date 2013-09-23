/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the "virtual" {@link CKEDITOR.dataProcessor} class, which
 *		defines the basic structure of data processor objects to be
 *		set to {@link CKEDITOR.editor.dataProcessor}.
 */

/**
 * If defined, points to the data processor which is responsible to translate
 * and transform the editor data on input and output.
 * Generaly it will point to an instance of {@link CKEDITOR.htmlDataProcessor},
 * which handles HTML data. The editor may also handle other data formats by
 * using different data processors provided by specific plugins.
 *
 * @property {CKEDITOR.dataProcessor} dataProcessor
 * @member CKEDITOR.editor
 */

/**
 * Represents a data processor, which is responsible to translate and
 * transform the editor data on input and output.
 *
 * This class is here for documentation purposes only and is not really part of
 * the API. It serves as the base ("interface") for data processors implementation.
 *
 * @class CKEDITOR.dataProcessor
 * @abstract
 */

/**
 * Transforms input data into HTML to be loaded in the editor.
 * While the editor is able to handle non HTML data (like BBCode), at runtime
 * it can handle HTML data only. The role of the data processor is transforming
 * the input data into HTML through this function.
 *
 *		// Tranforming BBCode data, having a custom BBCode data processor.
 *		var data = 'This is [b]an example[/b].';
 *		var html = editor.dataProcessor.toHtml( data ); // '<p>This is <b>an example</b>.</p>'
 *
 * @method toHtml
 * @param {String} data The input data to be transformed.
 * @param {String} [fixForBody] The tag name to be used if the data must be
 * fixed because it is supposed to be loaded direcly into the `<body>`
 * tag. This is generally not used by non-HTML data processors.
 * @todo fixForBody type - compare to htmlDataProcessor.
 */

/**
 * Transforms HTML into data to be outputted by the editor, in the format
 * expected by the data processor.
 *
 * While the editor is able to handle non HTML data (like BBCode), at runtime
 * it can handle HTML data only. The role of the data processor is transforming
 * the HTML data containined by the editor into a specific data format through
 * this function.
 *
 *		// Tranforming into BBCode data, having a custom BBCode data processor.
 *		var html = '<p>This is <b>an example</b>.</p>';
 *		var data = editor.dataProcessor.toDataFormat( html ); // 'This is [b]an example[/b].'
 *
 * @method toDataFormat
 * @param {String} html The HTML to be transformed.
 * @param {String} fixForBody The tag name to be used if the output data is
 * coming from `<body>` and may be eventually fixed for it. This is
 * generally not used by non-HTML data processors.
 */
