/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
/* global html2canvas */

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { Component, onWillStart, useRef, useState } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { NameAndSignature } from "@web/core/signature/name_and_signature";

export class SignNameAndSignature extends NameAndSignature {
    setup() {
        super.setup();
        this.user = useService("user");
        this.props.signature.signatureChanged = this.state.signMode !== "draw";

        if (this.props.frame) {
            this.state.activeFrame = this.props.activeFrame || false;
            this.frame = this.props.defaultFrame;

            this.signFrame = useRef("signFrame");
            this.props.frame.updateFrame = () => {
                if (this.state.activeFrame) {
                    this.props.signature.signatureChanged = true;
                    const xOffset = localization.direction === "rtl" ? 0.75 : 0.06; // magic numbers
                    this.signFrame.el.classList.toggle("active", true);
                    return html2canvas(this.signFrame.el, {
                        backgroundColor: null,
                        width: this.$signatureField.width(),
                        height: this.$signatureField.height(),
                        x: -this.$signatureField.width() * xOffset,
                        y: -this.$signatureField.height() * 0.09,
                    }).then((canvas) => {
                        this.frame = canvas.toDataURL("image/png");
                    });
                }
                return Promise.resolve(false);
            };

            this.props.frame.getFrameImageSrc = () => {
                return this.state.activeFrame ? this.frame : false;
            };
        }

        onWillStart(() => {
            if (this.props.frame) {
                return Promise.all([
                    this.user.hasGroup("base.group_user").then((isSystemUser) => {
                        this.showFrameCheck = isSystemUser;
                    }),
                    loadJS("/web_editor/static/lib/html2canvas.js"),
                ]);
            }
        });
    }

    onFrameChange() {
        this.state.activeFrame = !this.state.activeFrame;
    }

    onSignatureAreaClick() {
        if (this.state.signMode === "draw") {
            this.props.signature.signatureChanged = true;
        }
    }

    onClickSignLoad() {
        super.onClickSignLoad();
        this.props.signature.signatureChanged = true;
    }

    onClickSignAuto() {
        super.onClickSignAuto();
        this.props.signature.signatureChanged = true;
    }

    onClickSignDrawClear() {
        super.onClickSignDrawClear();
        this.props.signature.signatureChanged = true;
    }

    get signFrameClass() {
        return this.state.activeFrame && this.state.signMode !== "draw" ? "active" : "";
    }

    /**
     * Override to enable/disable SignNameAndSignatureDialog's footer buttons
     * @param { Event } e
     */
    onInputSignName(e) {
        super.onInputSignName(e);
        this.props.onNameChange(this.props.signature.name);
    }
}

SignNameAndSignature.template = "sign.NameAndSignature";
SignNameAndSignature.props = {
    ...NameAndSignature.props,
    activeFrame: Boolean,
    defaultFrame: String,
    frame: { type: Object, optional: true },
    hash: String,
    onNameChange: Function,
};

export class SignNameAndSignatureDialog extends Component {
    setup() {
        this.footerState = useState({
            buttonsDisabled: !this.props.signature.name,
        });
    }

    get nameAndSignatureProps() {
        return {
            signature: this.props.signature || "signature",
            signatureType: this.props.signatureType,
            displaySignatureRatio: this.props.displaySignatureRatio,
            activeFrame: this.props.activeFrame,
            defaultFrame: this.props.defaultFrame || "",
            mode: this.props.mode || "auto",
            frame: this.props.frame || false,
            hash: this.props.hash,
            onNameChange: this.onNameChange.bind(this),
        };
    }

    get dialogProps() {
        return {
            title: _t("Adopt Your Signature"),
            size: "md",
        };
    }

    onNameChange(name) {
        if (this.footerState.buttonsDisabled !== !name) {
            this.footerState.buttonsDisabled = !name;
        }
    }
}

SignNameAndSignatureDialog.props = {
    signature: Object,
    frame: { type: Object, optional: true },
    signatureType: { type: String, optional: true },
    displaySignatureRatio: Number,
    activeFrame: Boolean,
    defaultFrame: { type: String, optional: true },
    mode: { type: String, optional: true },
    hash: String,
    onConfirm: Function,
    onConfirmAll: Function,
    onCancel: Function,
    close: Function,
};

SignNameAndSignatureDialog.components = {
    Dialog,
    SignNameAndSignature,
};

SignNameAndSignatureDialog.template = "sign.SignNameAndSignatureDialog";
