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
}
