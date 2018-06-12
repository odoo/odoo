odoo.define('mail.composer.Extended', function (require) {
"use strict";

var BasicComposer = require('mail.composer.Basic');

var ExtendedComposer = BasicComposer.extend({
    /**
     * @override
     */
    init: function (parent, options) {
        options = _.defaults(options || {}, {
            inputMinHeight: 120,
        });
        this._super(parent, options);
        this.extended = true;
    },
    /**
     * @override
     */
    start: function () {
        this._$subjectInput = this.$('.o_composer_subject input');
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    clearComposer: function () {
        this._super.apply(this, arguments);
        this._$subjectInput.val('');
    },
    /**
     * @override
     * @param {string} target
     */
    focus: function (target) {
        if (target === 'body') {
            this.$input.focus();
        } else {
            this._$subjectInput.focus();
        }
    },
    /**
     * @override
     */
    getState: function () {
        var state = this._super.apply(this, arguments);
        state.subject = this._$subjectInput.val();
        return state;
    },
    /**
     * @override
     * @param {Object} state
     * @param {string} state.subject
     */
    setState: function (state) {
        this._super.apply(this, arguments);
        this.setSubject(state.subject);
    },
    /**
     * @param {string} subject
     */
    setSubject: function (subject) {
        this.$('.o_composer_subject input').val(subject);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @returns {$.Deferred}
     */
    _preprocessMessage: function () {
        var self = this;
        return this._super().then(function (message) {
            var subject = self._$subjectInput.val();
            self._$subjectInput.val("");
            message.subject = subject;
            return message;
        });
    },
    /**
     * @override
     * @private
     */
    _shouldSend: function () {
        return false;
    },
});

return ExtendedComposer;

});
