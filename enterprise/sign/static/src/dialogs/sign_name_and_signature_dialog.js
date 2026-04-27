/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
/* global html2canvas */

import { Dialog } from "@web/core/dialog/dialog";
import { user } from "@web/core/user";
import { loadJS } from "@web/core/assets";
import { Component, onWillStart, useRef, useState } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { NameAndSignature } from "@web/core/signature/name_and_signature";

export class SignNameAndSignature extends NameAndSignature {
    static template = "sign.NameAndSignature";
    static props = {
        ...NameAndSignature.props,
        activeFrame: Boolean,
        defaultFrame: String,
        frame: { type: Object, optional: true },
        hash: String,
        onNameChange: Function,
        onSignatureChange: { type: Function, optional: true },
    };

    setup() {
        super.setup();
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
                        width: this.signatureRef.el.width,
                        height: this.signatureRef.el.height,
                        x: -this.signatureRef.el.width * xOffset,
                        y: -this.signatureRef.el.height * 0.09,
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
                    user.hasGroup("base.group_user").then((isSystemUser) => {
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
            this.props.onSignatureChange(this.state.signMode);
        }
    }

    onClickSignLoad() {
        super.onClickSignLoad();
        this.props.signature.signatureChanged = true;
    }

    async onClickSignAuto() {
        super.onClickSignAuto();
        this.props.signature.signatureChanged = true;
        if (this.fonts.length <= 1) {
            this.fonts = await rpc(`/web/sign/get_fonts/`);
        }
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
        this.props.onSignatureChange(this.state.signMode);
    }
}

export class SignNameAndSignatureDialog extends Component {
    static props = {
        signature: Object,
        frame: { type: Object, optional: true },
        signatureType: { type: String, optional: true },
        displaySignatureRatio: Number,
        activeFrame: Boolean,
        defaultFrame: { type: String, optional: true },
        mode: { type: String, optional: true },
        signatureImage: { type: String, optional: true },
        hash: String,
        onConfirm: Function,
        onConfirmAll: Function,
        onCancel: Function,
        close: Function,
    };
    static template = "sign.SignNameAndSignatureDialog";
    static components = {
        Dialog,
        SignNameAndSignature,
    };

    setup() {
        this.footerState = useState({
            signButtonDisabled: !this.props.signature.name || !this.props.signature.signatureChanged,
            signAllButtonsDisabled: !this.props.signature.name,
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
            defaultFont: "LaBelleAurore-Regular.ttf",
            onSignatureChange: this.onSignatureChange.bind(this),
        };
    }

    get dialogProps() {
        return {
            title: _t("Adopt Your Signature"),
            size: "md",
        };
    }

    onNameChange(name) {
        const isNameFilled = Boolean(name);
        this.footerState.signButtonDisabled = !isNameFilled;
        this.footerState.signAllButtonsDisabled = !isNameFilled;
    }

    onSignatureChange(signMode) {
        const { name, isSignatureEmpty, signatureChanged } = this.props.signature;
        const isAutoMode = signMode === "auto"
        // Disable Sign all button if:
        // - Name is missing or empty
        //   - In "auto" mode, the name is only whitespace
        //   - In any other mode, the signature is empty
        const buttonsDisabled = !name || isAutoMode ? !name.trim() : isSignatureEmpty
        if (this.footerState.signAllButtonsDisabled !== buttonsDisabled){
            this.footerState.signAllButtonsDisabled = buttonsDisabled;
        }
        // Disable Sign button if:
        // - signature is not changed
        // - name is missing
        this.footerState.signButtonDisabled = buttonsDisabled || !signatureChanged;
    }
}
