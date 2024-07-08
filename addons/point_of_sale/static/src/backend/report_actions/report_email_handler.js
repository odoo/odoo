import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

async function reportEmailHandler(action, options, env) {
    const canPrintByEmail = await user.hasGroup("point_of_sale.group_pos_email_printing");
    if (!action.printer_emails?.length || !canPrintByEmail) {
        return false;
    }

    // If there is also an IoT printer associated with this report, we abort.
    // Therefore IoT printing takes priority over email printing.
    // Otherwise whichever handler gets called first takes priority (not defined)
    if (action.device_ids && action.device_ids.length) {
        return false;
    }

    const args = [action.id, action.context.active_ids, action.data];
    if (action.printer_emails.length === 1) {
        await env.services.orm.call("ir.actions.report", "send_report_to_linked_emails", args);
        await env.services.action.doAction({ type: "ir.actions.act_window_close" });
    } else {
        const openPrinterSelection = await env.services.orm.call(
            "ir.actions.report",
            "get_email_selection_wizard",
            args
        );
        await env.services.action.doAction(openPrinterSelection);
    }

    if (options.onClose) {
        options.onClose();
    }

    return true;
}

registry.category("ir.actions.report handlers").add("pos_report_email_handler", reportEmailHandler);
