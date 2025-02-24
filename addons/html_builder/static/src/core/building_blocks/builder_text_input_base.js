import { Component } from "@odoo/owl";
import { useForwardRefToParent } from "@web/core/utils/hooks";

export const textInputBasePassthroughProps = {
    action: { type: String, optional: true },
    placeholder: { type: String, optional: true },
    title: { type: String, optional: true },
    style: { type: String, optional: true },
};

// TODO: rename BuilderInputBase if compatible with type=range
export class BuilderTextInputBase extends Component {
    static template = "html_builder.BuilderTextInputBase";
    static props = {
        slots: { type: Object, optional: true },
        inputRef: { type: Function, optional: true },
        ...textInputBasePassthroughProps,
        commit: { type: Function },
        preview: { type: Function },
        onFocus: { type: Function, optional: true },
        value: { type: [String, { value: null }], optional: true },
    };

    setup() {
        this.inputRef = useForwardRefToParent("inputRef");
    }

    onChange() {
        const normalizedDisplayValue = this.props.commit(this.inputRef.el.value);
        this.inputRef.el.value = normalizedDisplayValue;
    }

    onInput() {
        this.props.preview(this.inputRef.el.value);
    }

    onFocus() {
        this.props.onFocus?.();
    }
}
