odoo.define('web.signature_widget', function (require) {
"use strict";

const framework = require('web.framework');
const SignatureDialog = require('web.signature_dialog');
const widgetRegistry = require('web.widget_registry');
const Widget = require('web.Widget');


const WidgetSignature = Widget.extend({
    custom_events: Object.assign({}, Widget.prototype.custom_events, {
        upload_signature: '_onUploadSignature',
    }),
    events: Object.assign({}, Widget.prototype.events, {
        'click .o_sign_label': '_onClickSignature',
    }),
    template: 'SignButton',
    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} record
     * @param {Object} nodeInfo
     */
    init: function (parent, record, nodeInfo) {
        this._super.apply(this, arguments);
        this.res_id = record.res_id;
        this.res_model = record.model;
        this.state = record;
        this.node = nodeInfo;
        // signature_field is the field on which the signature image will be
        // saved (`signature` by default).
        this.signature_field = this.node.attrs.signature_field || 'signature';
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Open a dialog to sign.
     *
     * @private
     */
    _onClickSignature: function () {
        const nameAndSignatureOptions = {
            displaySignatureRatio: 3,
            mode: 'draw',
            noInputName: true,
            signatureType: 'signature',
        };

        if (this.node.attrs.full_name) {
            let signName;
            const fieldFullName = this.state.data[this.node.attrs.full_name];
            if (fieldFullName && fieldFullName.type === 'record') {
                signName = fieldFullName.data.display_name;
            } else {
                signName = fieldFullName;
            }
            nameAndSignatureOptions.defaultName = signName || undefined;
        }

        nameAndSignatureOptions.defaultFont = this.node.attrs.default_font || '';
        this.signDialog = new SignatureDialog(this, {
            nameAndSignatureOptions: nameAndSignatureOptions,
        });
        this.signDialog.open();
    },
    /**
     * Upload the signature image (write it on the corresponding field) and
     * close the dialog.
     *
     * @returns {Promise}
     * @private
     */
    _onUploadSignature: function (ev) {
        const file = ev.data.signatureImage[1];
        const always = () => {
            this.trigger_up('reload');
            framework.unblockUI();
        };
        framework.blockUI();
        const rpcProm = this._rpc({
            model: this.res_model,
            method: 'write',
            args: [[this.res_id], {
                [this.signature_field]: file,
            }],
        });
        rpcProm.then(always).guardedCatch(always);
        return rpcProm;
    },
});

widgetRegistry.add('signature', WidgetSignature);

});
