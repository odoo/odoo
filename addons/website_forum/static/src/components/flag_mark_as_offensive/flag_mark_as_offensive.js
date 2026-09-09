import { Component, signal, t, useListener, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class FlagMarkAsOffensiveDialog extends Component {
    static template = "website_forum.FlagMarkAsOffensiveDialog";
    static components = { Dialog };
    props = useProps({
        title: t.string(),
        body: t.string(),
        close: t.function(),
    });

    setup() {
        this.modalRef = signal.ref();

        useListener(() => this.modalRef()?.querySelector(".btn-link"), "click", (ev) => {
            ev.preventDefault();
            this.props.close();
        });
    }
}
