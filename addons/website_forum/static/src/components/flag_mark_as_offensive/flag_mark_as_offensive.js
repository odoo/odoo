import { Component, signal, useListener } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class FlagMarkAsOffensiveDialog extends Component {
    static template = "website_forum.FlagMarkAsOffensiveDialog";
    static components = { Dialog };
    static props = {
        title: String,
        body: String,
        close: Function,
    };

    setup() {
        this.modalRef = signal.ref();

        useListener(() => this.modalRef()?.querySelector(".btn-link"), "click", (ev) => {
            ev.preventDefault();
            this.props.close();
        });
    }
}
