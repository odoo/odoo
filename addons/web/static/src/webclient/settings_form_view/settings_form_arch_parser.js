/** @odoo-module */

import { evaluateExpr } from "@web/core/py_js/py";
import { formView } from "@web/views/form/form_view";

export class SettingsArchParser extends formView.ArchParser {
    parseXML() {
        const result = super.parseXML(...arguments);
        Array.from(result.querySelectorAll(".app_settings_header field")).forEach((el) => {
            const options = evaluateExpr(el.getAttribute("options") || "{}");
            options.isHeaderField = true;
            el.setAttribute("options", JSON.stringify(options));
        });
        return result;
    }
}
