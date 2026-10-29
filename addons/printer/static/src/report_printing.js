import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { getLinkedPrinters, setLinkedPrinters } from "./linked_printers";
import { PrinterDialog } from "./printer_dialog/printer_dialog";

const printerDrivers = registry.category("printer_drivers");

/**
 * Opens the printer dialog.
 *
 * @returns {Promise<{ printerIds: number[], skipDialog: boolean } | null>} the
 *   choice of the user, or null when they closed the dialog without choosing
 */
function askPrinters(dialog, props) {
    return new Promise((resolve) => {
        dialog.add(
            PrinterDialog,
            { ...props, onConfirm: resolve },
            { onClose: () => resolve(null) }
        );
    });
}

/**
 * Handler of the report actions sending the reports that have printers to the
 * printers, instead of downloading them.
 *
 * The first time a user prints a report in a browser, they choose the printers
 * to use; the choice is remembered in that browser.
 *
 * @returns {Promise<boolean>} whether the report was handled, i.e. it must not
 *   be downloaded
 */
export async function printReportOnPrinters(action) {
    if (!action.printer_ids?.length) {
        return false;
    }
    const orm = useService("orm");
    const dialog = useService("dialog");
    const notification = useService("notification");
    const ui = useService("ui");

    const printers = (
        await orm.read("printer.printer", action.printer_ids, ["display_name", "kind", "address"], {
            context: { printer_show_kind: true },
        })
    ).filter((printer) => printerDrivers.contains(printer.kind));
    if (!printers.length) {
        return false;
    }

    const linkedPrinters = getLinkedPrinters(action.report_name);
    let printerIds = (linkedPrinters?.printerIds || []).filter((id) =>
        printers.some((printer) => printer.id === id)
    );
    if (!linkedPrinters?.skipDialog || !printerIds.length) {
        const choice = await askPrinters(dialog, {
            title: _t("Print %s", action.name || action.display_name || ""),
            printers,
            selectedIds: printerIds,
            skipDialog: linkedPrinters?.skipDialog || false,
        });
        if (!choice) {
            return false;
        }
        setLinkedPrinters({
            reportName: action.report_name,
            displayName: action.name || action.display_name || action.report_name,
            ...choice,
        });
        printerIds = choice.printerIds;
    }
    const selectedPrinters = printers.filter((printer) => printerIds.includes(printer.id));

    let documents;
    ui.block();
    try {
        documents = await rpc("/printer/report_documents", {
            report_name: action.report_name,
            printer_ids: selectedPrinters.map((printer) => printer.id),
            res_ids: action.context?.active_ids || [],
            data: action.data || null,
            context: { ...user.context, ...action.context },
        });
    } finally {
        ui.unblock();
    }

    for (const printer of selectedPrinters) {
        const printerDocuments = documents[printer.kind] || [];
        if (!printerDocuments.length) {
            notification.add(_t("%s has nothing to print for this report.", printer.display_name), {
                type: "warning",
            });
        }
        for (const document of printerDocuments) {
            const { success, errorCode } = await printerDrivers
                .get(printer.kind)
                .print(printer, document);
            if (!success) {
                notification.add(
                    _t("The document could not be printed on %(printer)s. Error code: %(code)s", {
                        printer: printer.display_name,
                        code: errorCode || _t("unknown"),
                    }),
                    { type: "danger", title: _t("Printing failed") }
                );
            }
        }
    }
    return true;
}

registry.category("ir.actions.report handlers").add("printer", printReportOnPrinters);
