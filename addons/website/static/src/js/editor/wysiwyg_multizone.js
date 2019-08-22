odoo.define('web_editor.wysiwyg.multizone', function (require) {
'use strict';
var Wysiwyg = require('web_editor.wysiwyg');


/**
 * HtmlEditor
 * Intended to edit HTML content. This widget uses the Wysiwyg editor
 * improved by odoo.
 *
 * class editable: o_editable
 * class non editable: o_not_editable
 *
 */
var WysiwygMultizone = Wysiwyg.extend({

    /**
     * @override
     */
    start: function () {
        var self = this;
        this.options.toolbarHandler = $('#web_editor-top-edit');
        this.options.saveElement = function ($el, context, withLang) {
            var outerHTML = this._getEscapedElement($el).prop('outerHTML');
            return self._saveElement(outerHTML, self.options.recordInfo, $el[0]);
        };
        return this._super();
    },
    /**
     * @override
     * @returns {Promise}
     */
    save: function () {
        if (this.isDirty()) {
            return this.editor.save().then(function() {
                return {isDirty: true};
            });
        } else {
            return {isDirty: false};
        }
    },


    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getEditableArea: function() {
        return $(':o_editable');
    },
    /**
     * Saves one (dirty) element of the page.
     *
     * @private
     * @param {jQuery} $el - the element to save
     * @param {Object} context - the context to use for the saving rpc
     * @param {boolean} [withLang=false]
     *        false if the lang must be omitted in the context (saving "master"
     *        page element)
     */
    _saveElement: function (outerHTML, recordInfo, editable) {
        var $el = $(editable);
        return this._rpc({
            model: 'ir.ui.view',
            method: 'save',
            args: [
                $el.data('oe-id'),
                outerHTML,
                $el.data('oe-xpath') || null,
            ],
            context: recordInfo.context,
        });
    },
});

return WysiwygMultizone;
});
