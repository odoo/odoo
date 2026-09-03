import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

/**
 * Asked before deactivating the user linked to an employee. The chosen option is
 * handed back through `close`, the caller is the one doing the deactivation.
 */
export class UserDeactivationDialog extends Component {
    static template = "hr.UserDeactivationDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        canEndCollaboration: Boolean,
    };

    onDeactivate() {
        this.props.close("deactivate");
    }

    onDeactivateAndEndCollaboration() {
        this.props.close("end_collaboration");
    }

    onDiscard() {
        this.props.close("discard");
    }
}
