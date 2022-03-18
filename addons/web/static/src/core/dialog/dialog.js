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
        //WOWL: To discuss
        if (this.props.parent) {
            const parent = owl.toRaw(this.props.parent);
            parent.__owl__.willDestroy.push(() => {
                this.close();
            });
        }
    }
}
Dialog.template = "web.Dialog";
Dialog.props = {
    parent: { type: Object, optional: true }, // WOWL: To discuss
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

export class SimpleDialog extends Component {
    setup() {
        useActiveElement("modal");
        useHotkey("escape", () => {
            this.props.close();
        });
        useChildSubEnv({ inDialog: true });
    }
}
SimpleDialog.template = "web.SimpleDialog";
SimpleDialog.props = {
    close: Function,
    isActive: { optional: true },
    "*": true,
};
