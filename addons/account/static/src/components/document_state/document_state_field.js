import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";

import { Component } from "@odoo/owl";

export class DocumentStatePopover extends Component {
    static template = "account.DocumentStatePopover";
    static props = {
        close: Function,
        onClose: Function,
        copyText: Function,
        message: String,
    };
}

export class DocumentState extends SelectionField {
    static template = "account.DocumentState";

    setup() {
        super.setup();
        this.popover = useService("popover");
        this.notification = useService("notification");
    }

    get message() {
        return this.props.record.data.message;
    }

    copyText() {
        navigator.clipboard.writeText(this.message);
        this.notification.add(_t("Text copied"), { type: "success" });
        this.popoverCloseFn();
        this.popoverCloseFn = null;
    }

    showMessagePopover(ev) {
        const close = () => {
            this.popoverCloseFn();
            this.popoverCloseFn = null;
        };

        if (this.popoverCloseFn) {
            close();
            return;
        }

        this.popoverCloseFn = this.popover.add(
            ev.currentTarget,
            DocumentStatePopover,
            {
                message: this.message,
                copyText: this.copyText.bind(this),
                onClose: close,
            },
            {
                closeOnClickAway: true,
                position: "top",
            },
        );
    }
}

registry.category("fields").add("account_document_state", {
    ...selectionField,
    component: DocumentState,
});
