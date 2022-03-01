/** @odoo-module **/

const { Component, useEffect, useRef, useState } = owl;

export class CopyButton extends Component {
    setup() {
        this.copyRef = useRef("copyBtn");
        this.state = useState({
            isCopied: false,
        });
        useEffect(() => {
            if (!this.copyRef.el) return;
            this.clipboard = new ClipboardJS(this.copyRef.el);
            this.clipboard.on("success", () => {
                this.state.isCopied = true;
                this.timeoutId = setTimeout(() => (this.state.isCopied = false), 800);
            });
            return () => clearTimeout(this.timeoutId), () => [this.state.isCopied];
        });
    }
    get isInline() {
        return ["char", "url"].includes(this.props.type);
    }
}
CopyButton.template = "web.CopyButton";
CopyButton.props = {
    className: { type: String, optional: true },
    value: String,
};
