/** @odoo-module native */
import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { NameAndSignature } from "@web/components/signature";
import { rpc } from "@web/core/network";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { redirect } from "@web/core/utils/urls";

export class SignatureForm extends Component {
    static template = "portal.SignatureForm";
    static components = { NameAndSignature };
    static props = ["*"];

    setup() {
        this.rootRef = useRef("root");

        this.state = useState({
            submitting: false,
            error: false,
            success: false,
        });
        this.signature = useState({
            name: this.props.defaultName,
            getSignatureImage: () => "",
            resetSignature: () => {},
        });
        this.nameAndSignatureProps = {
            signature: this.signature,
            fontColor: this.props.fontColor || "black",
        };
        if (this.props.signatureRatio) {
            this.nameAndSignatureProps.displaySignatureRatio =
                this.props.signatureRatio;
        }
        if (this.props.signatureType) {
            this.nameAndSignatureProps.signatureType = this.props.signatureType;
        }
        if (this.props.mode) {
            this.nameAndSignatureProps.mode = this.props.mode;
        }

        this.onModalShown = () => {
            this.signature.resetSignature();
            this.toggleSignatureFormVisibility();
        };
        onMounted(() => {
            this.modalEl = this.rootRef.el.closest(".modal");
            this.modalEl?.addEventListener("shown.bs.modal", this.onModalShown);
        });
        onWillUnmount(() => {
            this.modalEl?.removeEventListener("shown.bs.modal", this.onModalShown);
        });
    }

    toggleSignatureFormVisibility() {
        this.rootRef.el?.classList.toggle(
            "d-none",
            document.querySelector(".editor_enable"),
        );
    }

    get sendLabel() {
        return this.props.sendLabel || _t("Accept & Sign");
    }

    /**
     * @returns {Promise}
     */
    async onClickSubmit() {
        if (
            this.state.submitting ||
            this.state.success ||
            this.signature.isSignatureEmpty
        ) {
            return;
        }
        this.state.submitting = true;
        let data;
        try {
            const name = this.signature.name;
            const signature = this.signature.getSignatureImage().split(",")[1];
            data = await rpc(this.props.callUrl, { name, signature });
        } finally {
            this.state.submitting = false;
        }
        if (data.force_refresh) {
            if (data.redirect_url) {
                redirect(data.redirect_url);
            } else {
                window.location.reload();
            }
            this.state.submitting = true;
            return;
        }
        this.state.error = data.error || false;
        this.state.success = !data.error && {
            message: data.message,
            redirect_url: data.redirect_url,
            redirect_message: data.redirect_message,
        };
    }
}

registry.category("public_components").add("portal.signature_form", SignatureForm);
