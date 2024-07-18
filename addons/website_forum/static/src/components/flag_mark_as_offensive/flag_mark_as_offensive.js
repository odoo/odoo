/** @odoo-module **/

import { Component, useEffect } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { useChildRef } from "@web/core/utils/hooks";

export class FlagMarkAsOffensiveDialog extends Component {
    static template = "website_forum.FlagMarkAsOffensiveDialog";
    static components = { Dialog };
    static props = {
        title: String,
        body: String,
        close: Function,
    };

    setup() {
        this.modalRef = useChildRef();

        const onClickDiscard = (ev) => {
            ev.preventDefault();
            this.props.close();
        };

        useEffect(
            (discardButton) => {
                if (discardButton) {
                    discardButton.addEventListener("click", onClickDiscard);
                    return () => {
                        discardButton.removeEventListener("click", onClickDiscard);
                    };
                }
            },
            () => [this.modalRef.el?.querySelector(".btn-link")]
        );
    }
}
