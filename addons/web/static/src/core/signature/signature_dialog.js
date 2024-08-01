import { Dialog } from "@web/core/dialog/dialog";
import { NameAndSignature } from "./name_and_signature";

import { Component, useState } from "@odoo/owl";

export class SignatureDialog extends Component {
    static template = "web.SignatureDialog";
    static components = { Dialog, NameAndSignature };
    static props = {
        defaultName: { type: String, optional: true },
        nameAndSignatureProps: Object,
        uploadSignature: Function,
        close: Function,
    };
    static defaultProps = {
        defaultName: "",
    };

    setup() {
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
