import { Component, onWillUpdateProps, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { SignatureDialog } from "@web/core/signature/signature_dialog";
import { useService } from "@web/core/utils/hooks";

const PLACEHOLDER = "/web/static/img/placeholder.png";

export class SignatureViewer extends Component {
    static template = "web.SignatureViewer";
    static props = {
        defaultFont: { type: String, optional: true },
        defaultName: { type: String, optional: true },
        height: { type: Number, optional: true },
        readonly: { type: Boolean, optional: true },
        type: { validate: (t) => ["initial", "signature"].includes(t), optional: true },
        update: { type: Function, optional: true },
        url: { type: String, optional: true },
        width: { type: Number, optional: true },
    };
    static defaultProps = {
        type: "signature",
    };

    static displaySignatureRatio = 3;

    setup() {
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.state = useState({
            isValid: true,
        });
        onWillUpdateProps((np) => {
            if (this.props.url !== np.url) {
                this.state.isValid = true;
            }
        });
    }

    get src() {
        return this.state.isValid && this.props.url || PLACEHOLDER;
    }

    get size() {
        let { width, height } = this.props;
        if (!this.props.url) {
            const ratio = this.constructor.displaySignatureRatio;
            if (width && height) {
                width = Math.min(width, ratio * height);
                height = width / ratio;
            } else if (width) {
                height = width / ratio;
            } else if (height) {
                width = height * ratio;
            }
        }
        return { height, width };
    }

    get sizeStyle() {
        const { height, width } = this.size;
        let style = "";
        if (width) {
            style += `width:${width}px; max-width:${width}px;`;
        }
        if (height) {
            style += `height:${height}px; max-height:${height}px;`;
        }
        return style;
    }

    onClickSignature() {
        if (this.props.readonly) {
            return;
        }
        this.dialog.add(SignatureDialog, {
            defaultName: this.props.defaultName || "",
            nameAndSignatureProps: {
                defaultFont: this.props.defaultFont,
                displaySignatureRatio: 3,
                noInputName: true,
                signatureType: this.props.type,
            },
            uploadSignature: (signature) => this.props.update?.(signature),
        });
    }

    onLoadFailed() {
        this.state.isValid = false;
        this.notification.add(_t("Could not display the selected image"), {
            type: "danger",
        });
    }
}
