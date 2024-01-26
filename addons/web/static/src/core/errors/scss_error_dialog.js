/** @odoo-module */

import { registry } from "@web/core/registry";
import { _t, translationIsReady } from "@web/core/l10n/translation";

const scssErrorNotificationService = {
    dependencies: ["notification"],
    start(env, { notification }) {
        const assets = [...document.styleSheets].filter(
            (sheet) => sheet.href?.includes("/web") && sheet.href?.includes("/assets/")
        );
        translationIsReady.then(() => {
            for (const { cssRules } of assets) {
                const lastRule = cssRules?.[cssRules?.length - 1];
                if (lastRule?.selectorText === "css_error_message") {
                    const message = _t(
                        "The style compilation failed. This is an administrator or developer error that must be fixed for the entire database before continuing working. See browser console or server logs for details."
                    );
                    notification.add(message, {
                        title: _t("Style error"),
                        sticky: true,
                        type: "danger",
                    });
                    console.log(
                        lastRule.style.content
                            .replaceAll("\\a", "\n")
                            .replaceAll("\\*", "*")
                            .replaceAll(`\\"`, `"`)
                    );
                }
            }
        });
    },
};
registry.category("services").add("scss_error_display", scssErrorNotificationService);
