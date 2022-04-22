/** @odoo-module **/

import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useActiveElement } from "../ui/ui_service";

const { Component, useRef, useChildSubEnv, useState } = owl;
export class Dialog extends Component {
    setup() {
        this.modalRef = useRef("modal");
        useActiveElement("modal");
        this.data = useState(this.env.dialogData);
        useHotkey("escape", () => {
            this.data.close();
        });
        useChildSubEnv({ inDialog: true });
    }
}
Dialog.template = "web.Dialog";
Dialog.props = {
    contentClass: { type: String, optional: true },
    fullscreen: { type: Boolean, optional: true },
    footer: { type: Boolean, optional: true },
    header: { type: Boolean, optional: true },
    size: { type: String, optional: true, validate: (s) => ["sm", "md", "lg", "xl"].includes(s) },
    technical: { type: Boolean, optional: true },
    title: { type: String, optional: true },
    slots: {
        type: Object,
        shape: {
            default: Object, // Content is not optional
            footer: { type: Object, optional: true },
        },
    },
};
Dialog.defaultProps = {
    contentClass: "",
    fullscreen: false,
    footer: true,
    header: true,
    size: "lg",
    technical: true,
    title: "Odoo",
};
