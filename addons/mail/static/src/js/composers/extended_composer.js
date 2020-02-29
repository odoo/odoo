odoo.define('mail.composer.Extended', function (require) {
"use strict";

var BasicComposer = require('mail.composer.Basic');

var core = require('web.core');

var QWeb = core.qweb;

var ExtendedComposer = BasicComposer.extend({
    events: _.extend({}, BasicComposer.prototype.events, {
        'click .o_composer_button_discard': '_onClickDiscard',
    }),
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
    /**
     * Show the button 'discard' next to the send button. This is useful while
     * replying to a message, when in the end we do not want to reply.
     */
    showDiscardButton: function () {
        var $discard = this.$('.o_composer_button_discard');
        $discard.removeClass('d-none');
        $discard.addClass('d-md-inline-block');
    },
    /**
     * Hide the button 'discard' next to the send button. This is useful when
     * we were replying to a message from a certain thread, then we discard it
     * with some other actions (i.e. switch thread). The discard button only
     * makes sense during the selection of a message.
     */
    hideDiscardButton: function () {
        var $discard = this.$('.o_composer_button_discard');
        $discard.removeClass('d-md-inline-block');
        $discard.addClass('d-none');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @returns {Promise}
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

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickDiscard: function () {
        this.trigger_up('discard_extended_composer');
    },
});

return ExtendedComposer;

});
