odoo.define('portal.signature_form', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');
var NameAndSignature = require('web.name_and_signature').NameAndSignature;
var qweb = core.qweb;

var _t = core._t;

/**
 * This widget is a signature request form. It uses
 * @see NameAndSignature for the input fields, adds a submit
 * button, and handles the RPC to save the result.
 */
var SignatureForm = publicWidget.Widget.extend({
    template: 'portal.portal_signature',
    events: {
        'click .o_portal_sign_submit': 'async _onClickSignSubmit',
    },
    custom_events: {
        'signature_changed': '_onChangeSignature',
    },

    /**
     * Overridden to allow options.
     *
     * @constructor
     * @param {Widget} parent
     * @param {Object} options
     * @param {string} options.callUrl - make RPC to this url
     * @param {string} [options.sendLabel='Accept & Sign'] - label of the
     *  send button
     * @param {Object} [options.rpcParams={}] - params for the RPC
     * @param {Object} [options.nameAndSignatureOptions={}] - options for
     *  @see NameAndSignature.init()
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);

        this.csrf_token = odoo.csrf_token;

        this.callUrl = options.callUrl || '';
        this.rpcParams = options.rpcParams || {};
        this.sendLabel = options.sendLabel || _t("Accept & Sign");

        this.nameAndSignature = new NameAndSignature(this,
            options.nameAndSignatureOptions || {});
    },
    /**
     * Overridden to get the DOM elements
     * and to insert the name and signature.
     *
     * @override
     */
    start: function () {
        var self = this;
        this.$confirm_btn = this.$('.o_portal_sign_submit');
        this.$controls = this.$('.o_portal_sign_controls');
        var subWidgetStart = this.nameAndSignature.replace(this.$('.o_web_sign_name_and_signature'));
        return Promise.all([subWidgetStart, this._super.apply(this, arguments)]).then(function () {
            self.nameAndSignature.resetSignature();
        });
    },

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    /**
     * Focuses the name.
     *
     * @see NameAndSignature.focusName();
     */
    focusName: function () {
        this.nameAndSignature.focusName();
    },
    /**
     * Resets the signature.
     *
     * @see NameAndSignature.resetSignature();
     */
    resetSignature: function () {
        return this.nameAndSignature.resetSignature();
    },

    //----------------------------------------------------------------------
    // Handlers
    //----------------------------------------------------------------------

    /**
     * Handles click on the submit button.
     *
     * This will get the current name and signature and validate them.
     * If they are valid, they are sent to the server, and the reponse is
     * handled. If they are invalid, it will display the errors to the user.
     *
     * @private
     * @param {Event} ev
     * @returns {Deferred}
     */
    _onClickSignSubmit: function (ev) {
        var self = this;
        ev.preventDefault();

        if (!this.nameAndSignature.validateSignature()) {
            return;
        }

        var name = this.nameAndSignature.getName();
        var signature = this.nameAndSignature.getSignatureImage()[1];

        return this._rpc({
            route: this.callUrl,
            params: _.extend(this.rpcParams, {
                'name': name,
                'signature': signature,
            }),
        }).then(function (data) {
            if (data.error) {
                self.$('.o_portal_sign_error_msg').remove();
                self.$controls.prepend(qweb.render('portal.portal_signature_error', {widget: data}));
            } else if (data.success) {
                var $success = qweb.render('portal.portal_signature_success', {widget: data});
                self.$el.empty().append($success);
            }
            if (data.force_refresh) {
                if (data.redirect_url) {
                    window.location = data.redirect_url;
                } else {
                    window.location.reload();
                }
                // no resolve if we reload the page
                return new Promise(function () { });
            }
        });
    },
    /**
     * Toggles the submit button depending on the signature state.
     *
     * @private
     */
    _onChangeSignature: function () {
        var isEmpty = this.nameAndSignature.isSignatureEmpty();
        this.$confirm_btn.prop('disabled', isEmpty);
    },
});

publicWidget.registry.SignatureForm = publicWidget.Widget.extend({
    selector: '.o_portal_signature_form',

    /**
     * @private
     */
    start: function () {
        var hasBeenReset = false;

        var callUrl = this.$el.data('call-url');
        var nameAndSignatureOptions = {
            defaultName: this.$el.data('default-name'),
            mode: this.$el.data('mode'),
            displaySignatureRatio: this.$el.data('signature-ratio'),
            signatureType: this.$el.data('signature-type'),
            fontColor: this.$el.data('font-color')  || 'black',
        };
        var sendLabel = this.$el.data('send-label');

        var form = new SignatureForm(this, {
            callUrl: callUrl,
            nameAndSignatureOptions: nameAndSignatureOptions,
            sendLabel: sendLabel,
        });

        // Correctly set up the signature area if it is inside a modal
        this.$el.closest('.modal').on('shown.bs.modal', function (ev) {
            if (!hasBeenReset) {
                // Reset it only the first time it is open to get correct
                // size. After we want to keep its content on reopen.
                hasBeenReset = true;
                form.resetSignature();
            } else {
                form.focusName();
            }
        });

        return Promise.all([
            this._super.apply(this, arguments),
            form.appendTo(this.$el)
        ]);
    },
});

return {
    SignatureForm: SignatureForm,
};
});
