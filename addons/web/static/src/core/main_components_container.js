import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useRegistry } from "@web/core/registry_hook";
import { ErrorHandler } from "@web/core/utils/components";

const mainComponents = registry.category("main_components");

mainComponents.addValidation({
    Component: { validate: (c) => c.prototype instanceof Component },
    props: { type: Object, optional: true }
});

export class MainComponentsContainer extends Component {
    static components = { ErrorHandler };
    static props = {};
    static template = xml`
    <div class="o-main-components-container">
        <t t-foreach="Components.entries" t-as="C" t-key="C[0]">
            <ErrorHandler onError="error => this.handleComponentError(error, C)">
                <t t-component="C[1].Component" t-props="C[1].props"/>
            </ErrorHandler>
        </t>
    </div>
    `;

    setup() {
        this.Components = useRegistry(mainComponents);
    }

    handleComponentError(error, C) {
        // remove the faulty component and rerender without it
        this.Components.entries.splice(this.Components.entries.indexOf(C), 1);
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
