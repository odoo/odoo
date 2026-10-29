import { Component, proxy, t, useProps } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { Dialog } from "@web/core/dialog/dialog";

/**
 * Asks which of the printers of a report to print to.
 */
export class PrinterDialog extends Component {
    static template = "printer.PrinterDialog";
    static components = { CheckBox, Dialog };
    props = useProps({
        close: t.function(),
        title: t.string(),
        // the printers of the report: { id, display_name }
        printers: t.array(),
        selectedIds: t.array(t.number()).optional(() => []),
        skipDialog: t.boolean().optional(false),
        onConfirm: t.function(),
    });

    setup() {
        this.state = proxy({
            selectedIds: [...this.props.selectedIds],
            skipDialog: this.props.skipDialog,
            showError: false,
        });
    }

    togglePrinter(printerId, checked) {
        const selectedIds = this.state.selectedIds.filter((id) => id !== printerId);
        this.state.selectedIds = checked ? [...selectedIds, printerId] : selectedIds;
        this.state.showError = false;
    }

    toggleSkipDialog(checked) {
        this.state.skipDialog = checked;
    }

    onConfirm() {
        if (!this.state.selectedIds.length) {
            this.state.showError = true;
            return;
        }
        this.props.onConfirm({
            printerIds: this.props.printers
                .map((printer) => printer.id)
                .filter((id) => this.state.selectedIds.includes(id)),
            skipDialog: this.state.skipDialog,
        });
        this.props.close();
    }
}
