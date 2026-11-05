import { Plugin, usePlugin, useScope } from "@odoo/owl";
import { location } from "@web/core/browser/browser";
import { _t, translationIsReady } from "@web/core/l10n/translation";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { services } from "@web/core/services";
import { getOrigin } from "@web/core/utils/urls";

export class ScssErrorDisplayPlugin extends Plugin {
    notification = usePlugin(NotificationPlugin);

    setup() {
        // Iframe with src "about:blank" origin isn't a valid base URL.
        if (location.origin === "null") {
            return;
        }
        const scope = useScope();
        translationIsReady.then(() => {
            if (!scope.isDestroyed()) {
                this._displayErrors();
            }
        });
    }

    /**
     * @private
     */
    _displayErrors() {
        const origin = getOrigin();
        for (const sheet of document.styleSheets) {
            if (
                !sheet.href?.includes("/web") ||
                !sheet.href?.includes("/assets/") ||
                // CORS security rules don't allow reading content in JS
                new URL(sheet.href, location.origin).origin !== origin
            ) {
                continue;
            }
            let cssRules;
            try {
                // The filter above isn't enough to protect against CORS errors when reading
                // the cssRules property. Indeed, it seems that if the protocol is http, reading
                // that property can also trigger a CORS error, even if the origin is the same.
                // Anyway, we never want this line to crash, so we protect it.
                // See opw 3746910.
                cssRules = sheet.cssRules;
            } catch {
                continue;
            }
            const lastRule = cssRules?.[cssRules?.length - 1];
            if (lastRule?.selectorText === "css_error_message") {
                const message = _t(
                    "The style compilation failed. This is an administrator or developer error that must be fixed for the entire database before continuing working. See browser console or server logs for details."
                );
                this.notification.add(message, {
                    title: _t("Style error"),
                    sticky: true,
                    type: "danger",
                    className: "o_line_clamp_3",
                });
                console.log(
                    lastRule.style.content
                        .replaceAll("\\a", "\n")
                        .replaceAll("\\*", "*")
                        .replaceAll(`\\"`, `"`)
                );
            }
        }
    }
}

services.add(ScssErrorDisplayPlugin);
