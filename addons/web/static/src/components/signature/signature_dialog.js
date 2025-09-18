// @ts-check

/** @module @web/components/signature/signature_dialog - Dialog wrapper for capturing and uploading a signature */

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/ui/dialog/dialog";

import { NameAndSignature } from "./name_and_signature";
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
     */
    async onClickConfirm() {
        await this.props.uploadSignature({
            name: this.signature.name,
            signatureImage: /** @type {any} */ (this.signature).getSignatureImage(),
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
