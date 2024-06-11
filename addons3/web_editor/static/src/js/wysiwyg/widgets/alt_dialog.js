/** @odoo-module **/

import { Component, useRef, onMounted } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class AltDialog extends Component {
    static components = { Dialog };
    static props = {
        confirm: Function,
        close: Function,
        alt: String,
        tag_title: String,
    };
    static template = 'web_edior.AltDialog';
    altRef = useRef("alt");
    tagTitleRef = useRef("tag_title");

    setup() {
        this.isConfirmedOrCancelled = false; // ensures we do not confirm and/or cancel twice
        onMounted(() => {
            this.altRef.el.focus();
        });
    }
    async _cancel() {
        if (this.isConfirmedOrCancelled) {
            return;
        }
        this.isConfirmedOrCancelled = true;
        this.props.close();
    }
    async _confirm() {
        if (this.isConfirmedOrCancelled) {
            return;
        }
        this.isConfirmedOrCancelled = true;
        try {
            const allNonEscQuots = /"/g;
            const alt = this.altRef.el.value.replace(allNonEscQuots, "&quot;");
            const title = this.tagTitleRef.el.value.replace(allNonEscQuots, "&quot;");
            await this.props.confirm(alt, title);
        } catch (e) {
            this.props.close();
            throw e;
        }
        this.props.close();
    }
}
