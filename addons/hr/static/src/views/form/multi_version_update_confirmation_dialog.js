import { Component, props, signal, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useAutofocus } from "@web/core/utils/hooks";

export class MultiVersionUpdateConfirmationDialog extends Component {
    static template = "hr.FormView.MultiVersionUpdateConfirmation";
    static components = { Dialog };
    props = props({
        close: t.function().optional(),
        title: t.string().optional(),
        change_current: t.function().optional(),
        change_multi: t.function().optional(),
        cancel: t.function().optional(),
        version_changes: t.object().optional(),
    });

    currentButtonRef = signal.ref(HTMLButtonElement);

    setup() {
        useAutofocus({ ref: this.currentButtonRef });
    }

    _cancel() {
        if (this.props.cancel) {
            this.props.cancel();
        }
        this.props.close();
    }

    async _change_current() {
        if (this.props.change_current) {
            await this.props.change_current();
        }
        this.props.close();
    }

    async _change_multi() {
        if (this.props.change_multi) {
            await this.props.change_multi();
        }
        this.props.close();
    }
}
