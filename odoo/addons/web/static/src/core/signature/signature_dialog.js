/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { NameAndSignature } from "./name_and_signature";

import { Component, useState } from "@odoo/owl";

export class SignatureDialog extends Component {
    setup() {
        this.title = _t("Adopt Your Signature");
        this.signature = useState({
            name: this.props.defaultName,
            isSignatureEmpty: true,
        });
    }

    /**
     * Upload the signature image when confirm.
     *
     * @private
     */
    onClickConfirm() {
        this.props.uploadSignature({
            name: this.signature.name,
            signatureImage: this.signature.getSignatureImage(),
        });
        this.props.close();
    }

    get nameAndSignatureProps() {
        return {
            ...this.props.nameAndSignatureProps,
            signature: this.signature,
        };
    }
}

SignatureDialog.template = "web.SignatureDialog";
SignatureDialog.components = { Dialog, NameAndSignature };
SignatureDialog.defaultProps = {
    defaultName: "",
};
