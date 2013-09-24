/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

(function() {
	function placeholderDialog( editor, isEdit ) {

		var lang = editor.lang.placeholder,
			generalLabel = editor.lang.common.generalTab;
		return {
			title: lang.title,
			minWidth: 300,
			minHeight: 80,
			contents: [
				{
				id: 'info',
				label: generalLabel,
				title: generalLabel,
				elements: [
					{
					id: 'text',
					type: 'text',
					style: 'width: 100%;',
					label: lang.text,
					'default': '',
					required: true,
					validate: CKEDITOR.dialog.validate.notEmpty( lang.textMissing ),
					setup: function( element ) {
						if ( isEdit )
							this.setValue( element.getText().slice( 2, -2 ) );
					},
					commit: function( element ) {
						var text = '[[' + this.getValue() + ']]';
						// The placeholder must be recreated.
						CKEDITOR.plugins.placeholder.createPlaceholder( editor, element, text );
					}
				}
				]
			}
			],
			onShow: function() {
				if ( isEdit )
					this._element = CKEDITOR.plugins.placeholder.getSelectedPlaceHolder( editor );

				this.setupContent( this._element );
			},
			onOk: function() {
				this.commitContent( this._element );
				delete this._element;
			}
		};
	}

	CKEDITOR.dialog.add( 'createplaceholder', function( editor ) {
		return placeholderDialog( editor );
	});
	CKEDITOR.dialog.add( 'editplaceholder', function( editor ) {
		return placeholderDialog( editor, 1 );
	});
})();
