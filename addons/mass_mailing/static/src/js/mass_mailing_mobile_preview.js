/** @odoo-module **/

import { Component, markup, useEffect, useRef } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { escape } from "@web/core/utils/strings";
export class MassMailingMobilePreviewDialog extends Component {
    static components = {
        Dialog,
    };
    static template = "mass_mailing.MobilePreviewDialog";
    static props = {
        title: { type: String },
        preview: { type: String },
        close: Function,
    };

    appendPreview() {
        const iframe = this.iframeRef.el.contentDocument;
        const body = iframe.querySelector("body");
        const isMarkup = this.props.preview instanceof markup().constructor;
        const safePreview = isMarkup ? this.props.preview : escape(this.props.preview);
        body.innerHTML = safePreview;
    }

    setup() {
        this.iframeRef = useRef("iframeRef");
        useEffect(
            (modalEl) => {
                if (modalEl) {
                    this.modalBody = modalEl.querySelector(".modal-body");
                    modalEl.classList.add("o_mailing_mobile_preview");
                }
            },
            () => [document.querySelector(":not(.o_inactive_modal).o_dialog")]
        );
    }

    toggle() {
        this.modalBody.classList.toggle("o_invert_orientation");
    }
}

delete MassMailingMobilePreviewDialog.props.slots;
