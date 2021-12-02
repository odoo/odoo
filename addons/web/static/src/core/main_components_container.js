/** @odoo-module */
import { registry } from "./registry";
import { NotUpdatable, ErrorHandler } from "./utils/components";

const { Component, tags } = owl;

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

MainComponentsContainer.template = tags.xml`
<div>
    <t t-foreach="Components" t-as="C" t-key="C[0]">
        <NotUpdatable>
            <ErrorHandler onError="error => handleComponentError(error, C)">
                <t t-component="C[1].Component" t-props="C[1].props"/>
            </ErrorHandler>
        </NotUpdatable>
    </t>
</div>
`;
MainComponentsContainer.components = { NotUpdatable, ErrorHandler };
