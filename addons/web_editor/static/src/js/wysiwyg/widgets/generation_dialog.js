/** @odoo-module **/

import {Component, useRef, onMounted} from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class GenerationDialog extends Component{
    static components = { Dialog };
    static props = {
        restore: Function,
        close: Function,
        confirm: Function,
        context: String,
        prompt: String,
    };
    static template = 'web_edior.GenerationDialog';
    promptRef = useRef("prompt");

    setup() {
        this.isConfirmedOrCancelled = false; // ensures we do not confirm and/or cancel twice
        onMounted(() => this.promptRef.el && this.promptRef.el.focus());
    }

    async _cancel() {
        if (this.isConfirmedOrCancelled) {
            return;
        }
        this.isConfirmedOrCancelled = true;
        this.props.restore();
        this.props.close();
    }

     _confirm() {
        if (this.isConfirmedOrCancelled) {
            return;
        }
        this.isConfirmedOrCancelled = true;

        try {
            this.props.restore();
            this.props.close();
            console.log("confirmed",this.promptRef.el.value,this.props);
            const prompt = this.promptRef.el.value;
            this.props.confirm(prompt, this.props.context);
        } catch (e) {
            this.props.restore();
            this.props.close();
            throw e;
        }
    }
}
