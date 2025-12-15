import { Logger } from "@bus/workers/bus_worker_utils";
import { downloadFile } from "@web/core/network/download";

const posLogger = new Logger(`point_of_sale_config_${odoo.pos_config_id}_logger`);

export function logPosMessage(type, functionName, message, color = "#A1A1A1", args = []) {
    if (odoo.debug === "assets") {
        console.groupCollapsed(
            `[%c${type}%c]: %c${functionName}%c - ${message}`,
            `color:${color};`,
            "",
            `font-weight:bold;`,
            ""
        );
        if (args.length) {
            console.debug(...args);
        }
        console.trace("Call stack:");
        console.groupEnd();
    }
    const timestamp = luxon.DateTime.now().toUTC().toFormat("yyyy-LL-dd HH:mm:ss");
    const log = {
        timestamp,
        type,
        functionName,
        message,
    };
    if (args.length) {
        try {
            log.args = JSON.parse(JSON.stringify(args));
        } catch {
            // In case the args are not serializable
            log.args = args.toString();
        }
    }
    posLogger.log(log);
}

export async function downloadPosLogs() {
    const logs = await posLogger.getLogs();
    const blob = new Blob([JSON.stringify(logs, null, 2)], {
        type: "application/json",
    });
    const filename = `pos_logs_${luxon.DateTime.now()
        .toUTC()
        .toFormat("yyyy-LL-dd-HH-mm-ss")}.json`;
    downloadFile(blob, filename);
}
