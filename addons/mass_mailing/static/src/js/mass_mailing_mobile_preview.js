/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { getBundle } from "@web/core/assets";
import { useEffect, onWillStart } from "@odoo/owl";

export class MassMailingMobilePreviewDialog extends Dialog {
    setup() {
        super.setup();
        onWillStart(async () => {
            this.bundle = await getBundle("mass_mailing.iframe_css_assets_edit");
        });
        useEffect((modalEl) => {
            if (modalEl) {
                const modalBody = modalEl.querySelector('.modal-body');
                const invertIcon = document.createElement("span");
                invertIcon.className = "fa fa-refresh";
                const iframe = document.createElement("iframe");
                iframe.srcdoc = this._getSourceDocument();

                modalEl.classList.add('o_mailing_mobile_preview');
                modalEl.querySelector('.modal-title').append(invertIcon);
                modalEl.querySelector('.modal-header').addEventListener('click', () => modalBody.classList.toggle('o_invert_orientation'));
                modalBody.append(iframe);
            }
        }, () => [document.querySelector(':not(.o_inactive_modal).o_dialog')]);
    }

    _getSourceDocument() {
        const links = this.bundle.cssLibs.map((src) => {
            const link = document.createElement("link");
            link.setAttribute("type", "text/css");
            link.setAttribute("rel", "stylesheet");
            link.setAttribute("href", src);
            return link.outerHTML;
        });
        return `
            <!DOCTYPE html><html>
                <head> ${links.join("")} </head>
                <body> ${this.props.preview} </body>
            </html>
        `;
    }
}

MassMailingMobilePreviewDialog.props = {
    ...Dialog.props,
    preview: { type: String },
    close: Function,
};
delete MassMailingMobilePreviewDialog.props.slots;
