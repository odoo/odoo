import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";

class Alert extends Component {
    static template = xml`
        <div t-attf-class="alert navbar-height fixed-top p-1 rounded-0 alert-{{props.type}} fade show d-flex align-items-center justify-content-center" role="alert">
            <strong class="flex-grow-1 text-center" t-esc="props.message" />
        </div>
    `;
    static props = {
        message: String,
        type: {
            type: String,
            optional: true,
            validate: (type) => ["info", "warning", "danger", "success"].includes(type),
        },
    };
    static defaultProps = {
        type: "info",
    };
}

export const alertService = {
    dependencies: ["overlay"],
    start(env, { overlay }) {
        let dismiss = undefined;

        const add = (message, options = {}, overlayOptions = {}) => {
            dismiss?.();
            dismiss = overlay.add(
                Alert,
                {
                    message,
                    ...options,
                },
                overlayOptions
            );
        };

        return { add, dismiss: () => dismiss?.() };
    },
};

registry.category("services").add("alert", alertService);
