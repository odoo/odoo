// @ts-check

/** @module @web/views/widgets/signature/signature - Widget opening a signature drawing dialog and writing the captured image to a Binary field */

import { Component } from "@odoo/owl";
import { SignatureDialog } from "@web/components/signature/signature_dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

/** Widget that opens a signature drawing dialog and writes the captured image to a Binary field on the record. */
export class SignatureWidget extends Component {
    static template = "web.SignatureWidget";
    static props = {
        ...standardWidgetProps,
        fullName: { type: String, optional: true },
        highlight: { type: Boolean, optional: true },
        string: { type: String },
        signatureField: { type: String, optional: true },
    };

    setup() {
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
    }

    /** Open the SignatureDialog pre-filled with the record's full name field. */
    onClickSignature() {
        const nameAndSignatureProps = {
            mode: "draw",
            displaySignatureRatio: 3,
            signatureType: "signature",
            noInputName: true,
        };
        const { fullName, record } = this.props;
        let defaultName = "";
        if (fullName) {
            let signName;
            const fullNameData = record.data[fullName];
            if (record.fields[fullName].type === "many2one") {
                signName = fullNameData?.display_name;
            } else {
                signName = fullNameData;
            }
            defaultName = signName === "" ? undefined : signName;
        }

        nameAndSignatureProps.defaultFont = this.props.defaultFont;

        const dialogProps = {
            defaultName,
            nameAndSignatureProps,
            uploadSignature: (data) => this.uploadSignature(data),
        };
        this.dialogService.add(SignatureDialog, dialogProps);
    }

    /**
     * Write the base64 signature image to the record's signature field via ORM.
     * @param {{ signatureImage: string }} param0 - data URL from the signature pad
     */
    async uploadSignature({ signatureImage }) {
        const file = signatureImage.split(",")[1];
        const record = this.props.record;
        const { model, resModel, resId } = record;
        const signatureField = this.props.signatureField;
        // Use the raw ORM service — the protected wrapper from useService()
        // rejects or hangs when the widget is destroyed. On mobile the widget
        // lives inside a dropdown that closes on re-render, but the write
        // must still complete (the dialog outlives the widget).
        const orm = this.env.services.orm;

        await orm.write(resModel, [resId], { [signatureField]: file });
        await record.load();
        model.notify();
    }
}

export const signatureWidget = {
    component: SignatureWidget,
    extractProps: ({ attrs }) => {
        const { full_name: fullName, highlight, signature_field, string } = attrs;
        return {
            fullName,
            highlight: !!highlight,
            string,
            signatureField: signature_field || "signature",
        };
    },
};

registry.category("view_widgets").add("signature", signatureWidget);
