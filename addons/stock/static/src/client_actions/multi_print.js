import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

async function doMultiPrint(env, action) {
    for (const report of action.params.reports) {
        if (report.type != "ir.actions.report") {
            env.services.notification.add(_t("Incorrect type of action submitted as a report, skipping action"), {
                title: _t("Report Printing Error"),
            });
            continue
        } else if (report.report_type === "qweb-html") {
            env.services.notification.add(
                _t("HTML reports cannot be auto-printed, skipping report: %s", report.name),
                { title: _t("Report Printing Error") }
            );
            continue
        }
        // WARNING: potential issue if pdf generation fails, then action_service defaults
        // to HTML and rest of the action chain will break w/potentially never resolving promise
        await env.services.action.doAction({ type: "ir.actions.report", ...report });
    }
    if (action.params.anotherAction) {
        return env.services.action.doAction(action.params.anotherAction);
    } else if (action.params.onClose) {
        // handle special cases such as barcode
        action.params.onClose()
    } else {
        return env.services.action.doAction("reload_context");
    }
}

registry.category("actions").add("do_multi_print", doMultiPrint);
