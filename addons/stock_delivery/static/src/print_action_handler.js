import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

async function print(ip, job) {
    const printMethod = job.type === "epos"
        ? ePosPrint
        : zplPrint
    return printMethod(ip, job.report);
}

/**
 * Zebra printers host a web server that accepts print jobs
 * This server has not been updated to handle CORS preflight requests,
 * so we have to use "no-cors" mode and can't check the response status.
 */
async function zplPrint(ip, report) {
    const params = {
        method: "POST",
        body: report,
        signal: AbortSignal.timeout(15000),
        headers: {
            "Content-Length": report.length,
            "Content-Type": "text/plain; charset=utf-8",
        },
        mode: "no-cors",
    };

    try {
        await fetch(`http://${ip}/pstprnt`, params);
        return { result: true };
    } catch {
        return { result: false };
    }
}

async function ePosPrint(ip, report) {
    const params = {
        method: "POST",
        body: report,
        signal: AbortSignal.timeout(15000),
    };

    try {
        const res = await fetch(`http://${ip}/cgi-bin/epos/service.cgi?devid=local_printer`, params);
        const body = await res.text();
        const parser = new DOMParser();
        const parsedBody = parser.parseFromString(body, "application/xml");
        const response = parsedBody.querySelector("response");
        return {
            result: response.getAttribute("success") === "true",
            errorCode: response.getAttribute("code"),
        };
    } catch {
        return {
            result: false,
            errorCode: "",
        };
    }
}

async function printActionHandler(action, options, env) {
    const orm = env.services.orm;
    if (!action.printer_ip) {
        return false;
    }
    const jobs = action.jobs || await orm.call("ir.actions.report", "get_print_jobs", [
        action.report_name,
        action.context.active_ids,
    ]);

    // print jobs one by one and retry if the printers is waiting for the user to eject the paper
    while (jobs.length > 0) {
        const res = await print(action.printer_ip, jobs.at(-1));

        if (res.result) {
            jobs.pop();
            continue;
        }

        if (res.errorCode === "ERROR_WAIT_EJECT") {
            await new Promise(r => setTimeout(r, 1000));
            continue;
        }

        env.services.notification.add(_t(
            "Error occurred while printing the document. Please check the printer and try again: %s",
                res.errorCode
            ), {
                type: "danger",
            },
        );
        jobs.pop();
    }
    options.onClose?.();
    return true;
}

registry
    .category("ir.actions.report handlers")
    .add("print_action_andler", printActionHandler);
