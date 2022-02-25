/** @odoo-module */
import { registry } from "./registry";
import { ErrorHandler } from "./utils/components";

const { Component, xml } = owl;

export class MainComponentsContainer extends Component {
    setup() {
        this.Components = registry.category("main_components").getEntries();
    }

    handleComponentError(error, C) {
        // remove the faulty component and rerender without it
        this.Components.splice(this.Components.indexOf(C), 1);
        this.render();
        /**
         * we rethrow the error to notify the user something bad happened.
         * We do it after a tick to make sure owl can properly finish its
         * rendering
         */
        Promise.resolve().then(() => {
            throw error;
        });
    }
}

MainComponentsContainer.template = xml`
<div>
    <t t-foreach="Components" t-as="C" t-key="C[0]">
        <ErrorHandler onError="error => this.handleComponentError(error, C)">
            <t t-component="C[1].Component" t-props="C[1].props"/>
        </ErrorHandler>
    </t>
</div>
`;
MainComponentsContainer.components = { ErrorHandler };
