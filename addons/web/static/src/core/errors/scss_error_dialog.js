/** @odoo-module */

import { registry } from "@web/core/registry";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";

class ScssErrorDialog extends Component {}
ScssErrorDialog.template = "web.ScssErrorDialog";
ScssErrorDialog.components = { Dialog };
ScssErrorDialog.title = _t("Style error");

const scssErrorDisplayService = {
    dependencies: ["dialog"],
    start(env, { dialog }) {
        const assets = [...document.styleSheets].filter((sheet) => sheet.href?.includes("/web") && sheet.href?.includes("/assets/"));
        for (const { cssRules } of assets) {
            const lastRule = cssRules?.[cssRules?.length - 1];
            if (lastRule?.selectorText === "css_error_message") {
                dialog.add(ScssErrorDialog, {
                    message: lastRule.style.content.replaceAll("\\a", "\n").replaceAll("\\*", "*").replaceAll(`\\"`, `"`),
                });
            }
        }

    },
};
registry.category("services").add("scss_error_display", scssErrorDisplayService);
