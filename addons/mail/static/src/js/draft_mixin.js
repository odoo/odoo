odoo.define('mail.DraftMixin', function (require) {
"use strict";

var DraftMixin = {
    /**
     * Auto-save the draft on any input change
     *
     * @private
     */
    _autosaveDraft: function () {
        this._saveDraft(); // input might be non-empty
        this._$draftInput.on('input', this._saveDraft.bind(this));
    },
    /**
     * Delete draft of a message
     *
     * @private
     */
    _dropDraft: function () {
        if (this._draft) {
            delete this._draft;
        }
    },
    /**
     * Return the content of the draft, empty string if no draft
     *
     * @private
     * @return {string}
     */
    _getDraft: function () {
        return this._draft || "";
    },
    /**
     * Tell whether there is a non-empty draft of a message or not
     *
     * @private
     * @return {boolean} true if there is an unempty-draft, false otherwise
     */
    _isDraft: function () {
        return this._draft && !_.isEmpty(this._draft);
    },
    /**
     * Save the text content as a draft
     *
     * @private
     */
    _saveDraft: function () {
        this._draft = this._$draftInput.html();
    },
    /**
     * Set jquery element `$element` as input for draft
     *
     * @param {jQuery} $element
     */
    _setDraftInput: function ($element) {
        this._$draftInput = $element;
    },
};

return DraftMixin;
});
