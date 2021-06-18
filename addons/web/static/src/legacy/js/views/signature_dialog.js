/** @odoo-module alias=web.signature_dialog **/

import core from 'web.core';
import Dialog from 'web.Dialog';
import { NameAndSignature } from 'web.name_and_signature';

var _t = core._t;

// The goal of this dialog is to ask the user a signature request.
// It uses @see SignNameAndSignature for the name and signature fields.
var SignatureDialog = Dialog.extend({
    template: 'web.signature_dialog',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/web/static/src/legacy/xml/name_and_signature.xml']
    ),
    custom_events: {
        'signature_changed': '_onChangeSignature',
    },

    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} options
     * @param {string} [options.title='Adopt Your Signature'] - modal title
     * @param {string} [options.size='medium'] - modal size
     * @param {Object} [options.nameAndSignatureOptions={}] - options for
     *  @see NameAndSignature.init()
     */
    init: function (parent, options) {
        var self = this;
        options = options || {};

        options.title = options.title || _t("Adopt Your Signature");
        options.size = options.size || 'medium';
        options.technical = false;

        if (!options.buttons) {
            options.buttons = [];
            options.buttons.push({text: _t("Adopt and Sign"), classes: "btn-primary", disabled: true, click: function (e) {
                self._onConfirm();
            }});
            options.buttons.push({text: _t("Cancel"), close: true});
        }

        this._super(parent, options);

        this.nameAndSignature = new NameAndSignature(this, options.nameAndSignatureOptions);
    },
    /**
     * Start the nameAndSignature widget and wait for it.
     *
     * @override
     */
    willStart: function () {
        return Promise.all([
            this.nameAndSignature.appendTo($('<div>')),
            this._super.apply(this, arguments)
        ]);
    },
    /**
     * Initialize the name and signature widget when the modal is opened.
     *
     * @override
     */
    start: function () {
        var self = this;
        this.$primaryButton = this.$footer.find('.btn-primary');

        this.opened().then(function () {
            self.$('.o_web_sign_name_and_signature').replaceWith(self.nameAndSignature.$el);
            // initialize the signature area
            self.nameAndSignature.resetSignature();
        });

        return this._super.apply(this, arguments);
    },

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    /**
     * Returns whether the drawing area is currently empty.
     *
     * @see NameAndSignature.isSignatureEmpty()
     * @returns {boolean} Whether the drawing area is currently empty.
     */
    isSignatureEmpty: function () {
        return this.nameAndSignature.isSignatureEmpty();
    },

    //----------------------------------------------------------------------
    // Handlers
    //----------------------------------------------------------------------

    /**
     * Toggles the submit button depending on the signature state.
     *
     * @private
     */
    _onChangeSignature: function () {
        var isEmpty = this.nameAndSignature.isSignatureEmpty();
        this.$primaryButton.prop('disabled', isEmpty);
    },
    /**
     * Upload the signature image when confirm.
     *
     * @private
     */
    _onConfirm: function (fct) {
        this.trigger_up('upload_signature', {
            name: this.nameAndSignature.getName(),
            signatureImage: this.nameAndSignature.getSignatureImage(),
        });
    },
});

export default SignatureDialog;
