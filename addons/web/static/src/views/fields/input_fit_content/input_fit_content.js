/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { useFitContent } from "../input_fit_content_field_hook";

const { Component, useRef, xml } = owl;

export class InputFitContent extends Component {
    setup() {
        useInputField({
            getValue: () => this.props.value || '',
            refName: "inputFitContent",
        });
        this.inputRef = useRef("inputFitContent");
        useFitContent({ component: this });
    }
}

InputFitContent.template = xml`<span t-if="props.readonly" t-esc="value" />
    <input t-else="" t-att-id="props.id" t-ref="inputFitContent" t-att-placeholder="props.placeholder" class="o_input" />
`;

InputFitContent.props = {
    ...standardFieldProps,
    placeholder: { type: String, optional: true },
    minSize: { type: Number, optional: true},
    maxSize: { type: Number, optional: true},
    sizesDefined: { type: Boolean }
};
InputFitContent.defaultProps = {
    minSize: 5,
    maxSize: 80,
};
InputFitContent.displayName = _lt("Input");
InputFitContent.supportedTypes = ["text"];

InputFitContent.isEmpty = () => false;
InputFitContent.extractProps = ({ attrs }) => {
    return {
        placeholder: attrs.placeholder,
        minSize: attrs.options.minSize,
        maxSize: attrs.options.maxSize,
        sizesDefined: 'minSize' in attrs.options || 'maxSize' in attrs.options
    };
};

registry.category("fields").add("input_fit_content", InputFitContent);
