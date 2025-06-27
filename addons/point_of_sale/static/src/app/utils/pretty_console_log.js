export function logPosMessage(type, functionName, message, color = "#999999") {
    if (odoo.debug === "assets") {
        console.debug(
            `[%c${type}%c]: %c${functionName}%c - ${message}`,
            `color:${color};`,
            "",
            `font-weight:bold;`,
            ""
        );
    }
}
