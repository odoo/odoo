import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";

class Alert extends Component {
    static template = xml`
        <div t-attf-class="alert fixed-top p-1 rounded-0 alert-{{props.type}} fade show d-flex align-items-center justify-content-center" role="alert" style="height:48px">
            <strong class="flex-grow-1 text-center" t-esc="props.message" />
            <button class="ms-auto text-center d-flex align-items-center btn btn-light text-uppercase" t-on-click.stop="props.close">
                <i class="fa fa-times" role="img" aria-label="Close" title="Close" />
                <span t-if="props.closeMessage" t-esc="props.closeMessage" class="mt-1 ms-1" />
            </button>
        </div>
    `;
    static defaultProps = {
        type: "info",
    };
}

export const alertService = {
    dependencies: ["overlay"],
    start(env, { overlay }) {
        let currentNotificationCloser = null;
        const dismiss = () => currentNotificationCloser?.();

        const add = (message, onDismiss, closeMessage) => {
            const close = () => remove();
            dismiss();
            const remove = overlay.add(Alert, {
                message,
                closeMessage,
                close: () => {
                    close();
                    onDismiss();
                },
            });
            currentNotificationCloser = remove;
            return remove;
        };

        return { add, dismiss };
    },
};

registry.category("services").add("alert", alertService);
