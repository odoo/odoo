import { Component, props, proxy, signal, types as t } from "@odoo/owl";

export class WhiteboardPopover extends Component {
    static template = "html_editor.whiteboardPopover";
    props = props({
        close: t.function(),
        apply: t.function(),
        process: t.function(),
    });
    urlRef = signal(null);

    setup() {
        this.state = proxy({
            canBeApplied: false,
            error: undefined,
        });
    }

    processUrl() {
        const url = this.urlRef().value.trim();
        if (!url.startsWith("http")) {
            this.state.canBeApplied = false;
            this.state.error = false;
            return;
        }
        const embeddedProps = this.props.process(url);
        if (!embeddedProps || embeddedProps.error) {
            this.state.canBeApplied = false;
            this.state.error = true;
        } else {
            this.state.canBeApplied = true;
            this.state.error = false;
            return embeddedProps;
        }
    }

    onKeydown(ev) {
        if (ev.key === "Escape") {
            this.props.close();
        }
    }

    onKeydownEnter(ev) {
        if (ev.key === "Enter") {
            this.onClickApply();
        }
    }

    onChange(ev) {
        this.processUrl();
    }

    onInput(ev) {
        this.processUrl();
    }

    onClickApply() {
        if (!this.state.canBeApplied) {
            return;
        }
        const embeddedProps = this.processUrl();
        if (embeddedProps) {
            this.props.apply(embeddedProps);
            this.props.close();
        }
    }
}
