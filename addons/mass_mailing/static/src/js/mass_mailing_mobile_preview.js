/** @odoo-module **/

import { Component, markup, useEffect, useRef, onMounted, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { escape } from "@web/core/utils/strings";
import { getBundle } from "@web/core/assets";
export class MassMailingMobilePreviewDialog extends Component {
    static components = {
        Dialog,
    };
    static template = "mass_mailing.MobilePreviewDialog";
    static props = {
        title: { type: String },
        preview: { type: Function },
        close: Function,
    };

    setup() {
        this.shadowRef = useRef("contentRef");
        useEffect(
            (modalEl) => {
                if (modalEl) {
                    this.modalBody = modalEl.querySelector(".modal-body");
                    modalEl.classList.add("o_mailing_mobile_preview");
                }
            },
            () => [document.querySelector(":not(.o_inactive_modal).o_dialog")]
        );
        onWillStart(async () => {
            this.bundle = await getBundle("mass_mailing.iframe_css_assets_edit");
        });
        onMounted(async () => {
            const shadow = this.shadowRef.el.attachShadow({ mode: "closed" });
            const div = document.createElement("div");
            //Load only css assets of bundle.
            for (const url of this.bundle.cssLibs) {
                const linkEl = document.createElement("link");
                linkEl.type = "text/css";
                linkEl.rel = "stylesheet";
                linkEl.href = url;
                div.appendChild(linkEl);
            }
            const isMarkup = this.props.preview instanceof markup().constructor;
            const safePreview = isMarkup ? this.props.preview : escape(this.props.preview);
            div.insertAdjacentHTML("beforeend", safePreview);
            shadow.appendChild(div);
        });
    }

    toggle() {
        this.modalBody.classList.toggle("o_invert_orientation");
    }
}

delete MassMailingMobilePreviewDialog.props.slots;
