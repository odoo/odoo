/**
 * Copyright 2023 ACSONE SA/NV
 */

import {Dialog} from "@web/core/dialog/dialog";

import {Component, useRef} from "@odoo/owl";

export class AltTextDialog extends Component {
    setup() {
        this.altText = useRef("altText");
    }

    async onClose() {
        if (this.props.close) {
            this.props.close();
        }
    }

    async onConfirm() {
        try {
            await this.props.confirm(this.altText.el.value);
        } catch (e) {
            this.props.close();
            throw e;
        }
        this.onClose();
    }
}

AltTextDialog.components = {Dialog};
AltTextDialog.template = "fs_image.AltTextDialog";
AltTextDialog.props = {
    title: String,
    altText: String,
    confirm: Function,
    close: {type: Function, optional: true},
};
