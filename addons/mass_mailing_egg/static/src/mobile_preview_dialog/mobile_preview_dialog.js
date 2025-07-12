import { Dialog } from "@web/core/dialog/dialog";

import { Component } from "@odoo/owl";
import { useChildRef } from "@web/core/utils/hooks";

export class MassMailingMobilePreviewDialog extends Component {
    static template = "mass_mailing_egg.MobilePreviewDialog";
    static components = {
        Dialog,
    }
    static props = {
        close: { type: Function },
        IframeComponent: { type: Object },
        title: { type: String },
        value: { type: String },
    }

    setup() {
        this.iframeRef = useChildRef();
    }

    toggle() {
        this.iframeRef.el?.closest(".modal-body").classList.toggle("o_invert_orientation");
    }

    get config() {
        return {
            value: this.props.value,
        }
    }
}
