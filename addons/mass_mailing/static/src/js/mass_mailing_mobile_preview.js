/** @odoo-module **/

import { Component, onWillStart, useEffect } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class MassMailingMobilePreviewDialog extends Component {
    static components = {
        Dialog,
    };
    static template = "mass_mailing.MobilePreviewDialog";
    static props = {
        preview: { type: String },
        close: Function,
    };

    get title() {
        return _t("Mobile Preview");
    }

    setup() {
        this.rpc = useService("rpc");
        onWillStart(async () => {
            const result = await this.rpc("/mailing/preview/mobile/assets");
            this.links = result
                .filter((file) => file.type === "link")
                .map((file) => {
                    const link = document.createElement("link");
                    link.setAttribute("type", "text/css");
                    link.setAttribute("rel", "stylesheet");
                    link.setAttribute("href", file.src);
                    return link.outerHTML;
                });
        });
        useEffect(
            (modalEl) => {
                if (modalEl) {
                    this.modalBody = modalEl.querySelector(".modal-body");
                    modalEl.classList.add("o_mailing_mobile_preview");
                    const iframe = document.createElement("iframe");
                    iframe.srcdoc = `
                        <!DOCTYPE html>
                        <html>
                            <head>${this.links.join("")}</head>
                            <body>${this.props.preview}</body>
                        </html>
                    `;
                    this.modalBody.append(iframe);
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
