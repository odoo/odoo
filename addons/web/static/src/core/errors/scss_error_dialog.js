import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { _t, translationIsReady } from "@web/core/l10n/translation";
import { getOrigin } from "@web/core/utils/urls";

const scssErrorNotificationService = {
    dependencies: ["notification"],
    start(env, { notification }) {
        const origin = getOrigin();
        const assets = [...document.styleSheets].filter((sheet) => {
            return (
                sheet.href?.includes("/web") &&
                sheet.href?.includes("/assets/") &&
                // CORS security rules don't allow reading content in JS
                new URL(sheet.href, browser.location.origin).origin === origin
            );
        });
        translationIsReady.then(() => {
            for (const asset of assets) {
                let cssRules;
                try {
                    // The filter above isn't enough to protect against CORS errors when reading
                    // the cssRules property. Indeed, it seems that if the protocol is http, reading
                    // that property can also trigger a CORS error, even if the origin is the same.
                    // Anyway, we never want this line to crash, so we protect it.
                    // See opw 3746910.
                    cssRules = asset.cssRules;
                } catch {
                    continue;
                }
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
