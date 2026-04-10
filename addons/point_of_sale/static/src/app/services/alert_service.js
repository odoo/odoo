import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class Alert extends Component {
    static template = xml`
        <div t-attf-class="alert pos-navbar-height fixed-top py-3 px-1 mt-2 lh-sm alert-{{this.props.type}} fade show d-flex align-items-center justify-content-center rounded {{this.ui.isSmall ? 'w-100': 'w-50 fs-5 m-auto'}}" role="alert">
            <strong class="flex-grow-1 text-center" t-out="this.props.message" />
            <button t-if="this.props.closable" t-on-click="this.props.onClose" class="btn btn-lg btn-close position-absolute end-0 me-2"/>
        </div>
    `;
    static props = {
        message: String,
        type: {
            type: String,
            optional: true,
            validate: (type) => ["info", "warning", "danger", "success"].includes(type),
        },
        onClose: {
            type: Function,
        },
        closable: {
            type: Boolean,
            optional: true,
        },
    };
    static defaultProps = {
        type: "info",
        closable: false,
    };
    setup() {
        super.setup(...arguments);
        this.ui = useService("ui");
    }
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
                    onClose: () => {
                        dismiss?.();
                        options.onClose?.();
                    },
                },
                overlayOptions
            );
        };

        return { add, dismiss: () => dismiss?.() };
    },
};

registry.category("services").add("alert", alertService);
