import { Component, useRef } from "@odoo/owl";

export const textInputBasePassthroughProps = {
    action: { type: String, optional: true },
    placeholder: { type: String, optional: true },
    title: { type: String, optional: true },
};

export class BuilderTextInputBase extends Component {
    static template = "html_builder.BuilderTextInputBase";
    static props = {
        ...textInputBasePassthroughProps,
        onChange: { type: Function, optional: true },
        onInput: { type: Function, optional: true },
        onFocus: { type: Function, optional: true },
        value: { type: [String, { value: null }], optional: true },
        inputRefCallback: { type: Function, optional: true },
    };

    setup() {
        this.inputRef = useRef("input");
        if (this.props.inputRefCallback) {
            this.props.inputRefCallback(this.inputRef);
        }
    }

    onFocus() {
        this.props.onFocus?.();
    }
}
