import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { FormOption } from "./form_option";
import { getModelName } from "./utils";
import { xml } from "@odoo/owl";

const formOptionRedrawProps = { ...FormOption.props };
delete formOptionRedrawProps.modelName;

export class FormOptionRedraw extends BaseOptionComponent {
    static template = xml`<FormOption t-props="getProps()"/>`;
    static props = formOptionRedrawProps;
    static components = { FormOption };

    setup() {
        super.setup();
        this.domState = useDomState((formEl) => {
            const modelName = getModelName(formEl);
            return {
                modelName,
            };
        });
    }

    getProps() {
        return {
            ...this.props,
            modelName: this.domState.modelName,
        };
    }
}
