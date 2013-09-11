/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Defines the {@link CKEDITOR.lang} object, for the
 * English (United Kingdom) language.
 */

/**#@+
   @type String
   @example
*/

/**
 * Contains the dictionary of language entries.
 * @namespace
 */
CKEDITOR.lang[ 'en-gb' ] = {
	// ARIA description.
	editor: 'Rich Text Editor',

	// Common messages and labels.
	common: {
		// Screenreader titles. Please note that screenreaders are not always capable
		// of reading non-English words. So be careful while translating it.
		editorHelp: 'Press ALT 0 for help', // MISSING

		browseServer: 'Browse Server',
		url: 'URL',
		protocol: 'Protocol',
		upload: 'Upload',
		uploadSubmit: 'Send it to the Server',
		image: 'Image',
		flash: 'Flash',
		form: 'Form',
		checkbox: 'Checkbox',
		radio: 'Radio Button',
		textField: 'Text Field',
		textarea: 'Textarea',
		hiddenField: 'Hidden Field',
		button: 'Button',
		select: 'Selection Field',
		imageButton: 'Image Button',
		notSet: '<not set>',
		id: 'Id',
		name: 'Name',
		langDir: 'Language Direction',
		langDirLtr: 'Left to Right (LTR)',
		langDirRtl: 'Right to Left (RTL)',
		langCode: 'Language Code',
		longDescr: 'Long Description URL',
		cssClass: 'Stylesheet Classes',
		advisoryTitle: 'Advisory Title',
		cssStyle: 'Style',
		ok: 'OK',
		cancel: 'Cancel',
		close: 'Close',
		preview: 'Preview',
		resize: 'Drag to resize',
		generalTab: 'General',
		advancedTab: 'Advanced',
		validateNumberFailed: 'This value is not a number.',
		confirmNewPage: 'Any unsaved changes to this content will be lost. Are you sure you want to load new page?',
		confirmCancel: 'Some of the options have been changed. Are you sure to close the dialog?',
		options: 'Options',
		target: 'Target',
		targetNew: 'New Window (_blank)',
		targetTop: 'Topmost Window (_top)',
		targetSelf: 'Same Window (_self)',
		targetParent: 'Parent Window (_parent)',
		langDirLTR: 'Left to Right (LTR)',
		langDirRTL: 'Right to Left (RTL)',
		styles: 'Style',
		cssClasses: 'Stylesheet Classes',
		width: 'Width',
		height: 'Height',
		align: 'Align',
		alignLeft: 'Left',
		alignRight: 'Right',
		alignCenter: 'Centre',
		alignTop: 'Top',
		alignMiddle: 'Middle',
		alignBottom: 'Bottom',
		invalidValue	: 'Invalid value.', // MISSING
		invalidHeight: 'Height must be a number.',
		invalidWidth: 'Width must be a number.',
		invalidCssLength: 'Value specified for the "%1" field must be a positive number with or without a valid CSS measurement unit (px, %, in, cm, mm, em, ex, pt, or pc).', // MISSING
		invalidHtmlLength: 'Value specified for the "%1" field must be a positive number with or without a valid HTML measurement unit (px or %).', // MISSING
		invalidInlineStyle: 'Value specified for the inline style must consist of one or more tuples with the format of "name : value", separated by semi-colons.', // MISSING
		cssLengthTooltip: 'Enter a number for a value in pixels or a number with a valid CSS unit (px, %, in, cm, mm, em, ex, pt, or pc).', // MISSING

		// Put the voice-only part of the label in the span.
		unavailable: '%1<span class="cke_accessibility">, unavailable</span>'
	}
};
