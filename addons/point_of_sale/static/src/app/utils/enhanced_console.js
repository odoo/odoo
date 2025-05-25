export default function enhancedConsole(type, tag, message, error = false) {
    if (odoo.debug !== "assets") {
        return;
    }

    const styles = {
        info: "color: skyblue",
        warn: "color: orange",
        error: "color: red",
        debug: "color: silver",
        success: "color: lime",
    };

    if (styles[type] === undefined) {
        console.info(`%c[ENHANCED_CONSOLE] Invalid type: ${type}`, "color: red; font-weight: bold");
        return;
    }

    console.info(`%c[${tag}]`, `font-weight: bold; ${styles[type]}`, message, error);
}
