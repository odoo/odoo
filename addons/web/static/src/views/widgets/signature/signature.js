import { registry } from "@web/core/registry";
import { SignatureDialog } from "@web/core/signature/signature_dialog";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { Component } from "@odoo/owl";

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
                signName = fullNameData && fullNameData[1];
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

    async uploadSignature({ signatureImage }) {
        const file = signatureImage.split(",")[1];
        const { model, resModel, resId } = this.props.record;

        await this.env.services.orm.write(resModel, [resId], {
            [this.props.signatureField]: file,
        });
        await this.props.record.load();
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
