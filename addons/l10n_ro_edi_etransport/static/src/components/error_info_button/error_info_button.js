/** @odoo-module */

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";
import { useService } from "@web/core/utils/hooks";

export class ErrorInfoPopover extends Component {
    static template = "l10n_ro_edi_etransport.ErrorInfoPopover";
    static props = {
        close: Function,
        onClose: Function,
        errors: Array,
    };
}

export class ErrorInfoButton extends SelectionField {
    static template = "l10n_ro_edi_etransport.ErrorInfoButton";

    setup() {
        super.setup();
        this.popover = useService("popover");
    }

    shouldShow() {
        return this.props.record.data.l10n_ro_edi_etransport_status == "sending_failed" && getErrors()?.length > 0;
    }

    getErrors() {
        return this.props.record.data.l10n_ro_edi_etransport_message
            ?.split("\n")
            ?.filter((error) => error?.trim()?.length > 0);
    }

    showPopover(ev) {
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
            ErrorInfoPopover,
            {
                errors: this.getErrors(),
                onClose: close,
            },
            {
                closeOnClickAway: true,
                position: "right",
            },
        );
    }
}

export const errorInfoButton = {
    ...selectionField,
    component: ErrorInfoButton,
};

registry.category("fields").add("l10n_ro_edi_etransport_error_button", errorInfoButton);
