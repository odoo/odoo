/** @odoo-module */

import { isEmpty } from "../core/utils";
import { Plugin } from "../plugin";
import { Powerbox } from "./powerbox";

export class PowerboxPlugin extends Plugin {
    static name = "powerbox";
    static dependencies = ["hint", "overlay"];

    constructor() {
        super(...arguments);
        this.addDomListener(document, "selectionchange", this.handleCommandHint);

        /** @type {import("../core/overlay_plugin").Overlay} */
        this.powerbox = this.shared.createOverlay(Powerbox, "bottom", {
            dispatch: this.dispatch,
            el: this.el,
        });
        this.addDomListener(this.el, "keypress", (ev) => {
            if (ev.key === "/") {
                this.powerbox.open();
            }
        });
    }

    handleCommand(command, payload) {
        switch (command) {
            case "CONTENT_UPDATED":
                this.handleCommandHint();
                break;
        }
    }

    handleCommandHint() {
        const selection = window.getSelection();
        const range = selection.getRangeAt(0);
        if (selection.isCollapsed && this.el.contains(range.commonAncestorContainer)) {
            const node = selection.anchorNode;
            const el = node instanceof Element ? node : node.parentElement;
            if ((el.tagName === "DIV" || el.tagName === "P") && isEmpty(el)) {
                this.shared.createTempHint(el, 'Type "/" for commands');
            }
        }
    }
}
