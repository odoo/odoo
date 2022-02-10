/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component, useEffect, useRef, useState } = owl;

class CopyClipboard extends Component {
    setup() {
        this.copyRef = useRef("copyBtn");
        this.state = useState({
            isCopied: false,
        });
        this.timeout = undefined;
        useEffect(() => {
            if (!this.copyRef.el) return;
            this.clipboard = new ClipboardJS(this.copyRef.el);
            this.clipboard.on("success", () => {
                this.state.isCopied = true;
                setTimeout(() => {
                    this.timeout = this.state.isCopied = false;
                }, 800);
            });
            return clearTimeout(this.timeout);
        });
    }
}
Object.assign(CopyClipboard, {
    props: {
        isInline: { type: Boolean, optional: true },
        type: String,
        value: String | null,
    },
    template: "web.CopyClipboard",
});

export class CopyClipboardCharField extends Component {}
Object.assign(CopyClipboardCharField, {
    components: { CopyClipboard },
    props: {
        ...standardFieldProps,
    },
    template: "web.CopyClipboardCharField",
});
registry.category("fields").add("CopyClipboardChar", CopyClipboardCharField);

export class CopyClipboardTextField extends Component {}
Object.assign(CopyClipboardTextField, {
    components: { CopyClipboard },
    props: {
        ...standardFieldProps,
    },
    template: "web.CopyClipboardTextField",
});
registry.category("fields").add("CopyClipboardText", CopyClipboardTextField);

export class CopyClipboardURLField extends Component {}
Object.assign(CopyClipboardURLField, {
    components: { CopyClipboard },
    props: {
        ...standardFieldProps,
    },
    template: "web.CopyClipboardURLField",
});
registry.category("fields").add("CopyClipboardURL", CopyClipboardURLField);
