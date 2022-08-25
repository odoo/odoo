/** @odoo-module **/

const { Component, useEffect, useState } = owl;

export class CopyButton extends Component {
    setup() {
        this.state = useState({
            isCopied: false,
        });
        useEffect(
            () => {
                return () => clearTimeout(this.timeoutId);
            },
            () => [this.state.isCopied]
        );
    }

    async onClick() {
        // any kind of content can be copied into the clipboard using
        // the appropriate native methods
        if (typeof this.props.content === "string") {
            navigator.clipboard.writeText(this.props.content).then(() => {
                this.state.isCopied = true;
            });
        } else {
            navigator.clipboard.write(this.props.content).then(() => {
                this.state.isCopied = true;
            });
        }
        this.timeoutId = setTimeout(() => (this.state.isCopied = false), 800);
    }
}
CopyButton.template = "web.CopyButton";
CopyButton.props = {
    className: { type: String, optional: true },
    copyText: { type: String, optional: true },
    successText: { type: String, optional: true },
    content: { type: [String, Object], optional: true },
};
