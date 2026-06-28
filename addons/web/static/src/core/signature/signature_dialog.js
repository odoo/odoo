import { Dialog } from "@web/core/dialog/dialog";
import { NameAndSignature } from "./name_and_signature";

import { Component, props, proxy, t } from "@odoo/owl";

export class SignatureDialog extends Component {
    static template = "web.SignatureDialog";
    static components = { Dialog, NameAndSignature };
    props = props({
        defaultName: t.string().optional(""),
        nameAndSignatureProps: t.object(),
        uploadSignature: t.function(),
        close: t.function(),
    });

    setup() {
        this.signature = proxy({
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
