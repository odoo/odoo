import { render } from "@web/owl2/utils";
import { Component, t, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useRegistry } from "@web/core/registry_hook";
import { ErrorHandler } from "@web/core/utils/components";
import { localization } from "@web/core/l10n/localization";
import { mainComponents } from "@web/core/main_components";

/**
 * @todo owl3 migration
 * temporary - to remove when all main components are registered on the
 * `mainComponents` resource instead of this registry
 */
const mainComponentsRegistry = registry.category("main_components");

mainComponentsRegistry.addValidation(
    t.object({
        Component: t.component(),
        props: t.object().optional(),
    })
);

export class MainComponentsContainer extends Component {
    static components = { ErrorHandler };
    static template = xml`
    <div class="o-main-components-container" t-att-class="{'o_rtl': this.isRTL}">
        <t t-foreach="this.Components.entries" t-as="C" t-key="C[0]">
            <ErrorHandler onError="error => this.handleRegistryComponentError(error, C)">
                <t t-component="C[1].Component" t-props="C[1].props"/>
            </ErrorHandler>
        </t>
        <t t-foreach="this.mainComponents.items()" t-as="C" t-key="C_index">
            <ErrorHandler onError="error => this.handleResourceComponentError(error, C)">
                <t t-component="C.Component" t-props="C.props"/>
            </ErrorHandler>
        </t>
    </div>
    `;

    setup() {
        this.Components = useRegistry(mainComponentsRegistry);
        this.mainComponents = mainComponents;
        this.isRTL = localization.direction === "rtl";
    }

    handleRegistryComponentError(error, C) {
        // remove the faulty component and rerender without it
        this.Components.entries.splice(this.Components.entries.indexOf(C), 1);
        render(this);
        /**
         * we rethrow the error to notify the user something bad happened.
         * We do it after a tick to make sure owl can properly finish its
         * rendering
         */
        Promise.resolve().then(() => {
            throw error;
        });
    }

    handleResourceComponentError(error, C) {
        // remove the faulty component and rerender without it
        this.mainComponents.delete(C);
        render(this);
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
