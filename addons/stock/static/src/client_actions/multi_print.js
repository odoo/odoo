import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

async function doMultiPrint(env, actionDescr) {
    const action = useService("action");
    const notification = useService("notification");
    for (const report of actionDescr.params.reports) {
        if (report.type != "ir.actions.report") {
            notification.add(
                _t("Incorrect type of action submitted as a report, skipping action"),
                {
                    title: _t("Report Printing Error"),
                }
            );
            continue;
        } else if (report.report_type === "qweb-html") {
            notification.add(
                _t("HTML reports cannot be auto-printed, skipping report: %s", report.name),
                { title: _t("Report Printing Error") }
            );
            continue;
        }
        // WARNING: potential issue if pdf generation fails, then action_service defaults
        // to HTML and rest of the action chain will break w/potentially never resolving promise
        await action.doAction({ type: "ir.actions.report", ...report });
    }
    if (actionDescr.params.anotherAction) {
        return action.doAction(actionDescr.params.anotherAction);
    } else if (actionDescr.params.onClose) {
        // handle special cases such as barcode
        actionDescr.params.onClose();
    } else {
        setTimeout(() => action.doAction("reload_context"), 66);
    }
}

registry.category("actions").add("do_multi_print", doMultiPrint);
