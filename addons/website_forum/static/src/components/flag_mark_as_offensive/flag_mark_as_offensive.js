import { useLayoutEffect } from "@web/owl2/utils";
import { Component, signal } from "@odoo/owl";
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

        const onClickDiscard = (ev) => {
            ev.preventDefault();
            this.props.close();
        };

        useLayoutEffect(
            (discardButton) => {
                if (discardButton) {
                    discardButton.addEventListener("click", onClickDiscard);
                    return () => {
                        discardButton.removeEventListener("click", onClickDiscard);
                    };
                }
            },
            () => [this.modalRef()?.querySelector(".btn-link")]
        );
    }
}
