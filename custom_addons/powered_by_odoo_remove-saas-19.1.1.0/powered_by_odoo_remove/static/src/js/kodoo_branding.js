/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

function sanitizeTitlePart(value) {
    const text = (value || "").toString();
    if (!text) {
        return "";
    }
    return text
        .replaceAll("Odoo", "Kodoo")
        .replaceAll("odoo", "kodoo")
        .replaceAll("My Odoo.com Account", "Kodoo Account");
}

const titleService = {
    start() {
        const titleCounters = {};
        const titleParts = {};

        function getParts() {
            return { ...titleParts };
        }

        function updateTitle() {
            const counter = Object.values(titleCounters).reduce((acc, count) => acc + count, 0);
            const name = Object.values(titleParts)
                .map(sanitizeTitlePart)
                .filter(Boolean)
                .join(" - ") || "Kodoo";
            document.title = counter ? `(${counter}) ${name}` : name;
        }

        function setCounters(counters) {
            for (const key in counters) {
                const value = counters[key];
                if (!value) {
                    delete titleCounters[key];
                } else {
                    titleCounters[key] = value;
                }
            }
            updateTitle();
        }

        function setParts(parts) {
            for (const key in parts) {
                const value = sanitizeTitlePart(parts[key]);
                if (!value) {
                    delete titleParts[key];
                } else {
                    titleParts[key] = value;
                }
            }
            updateTitle();
        }

        updateTitle();

        return {
            get current() {
                return document.title;
            },
            getParts,
            setCounters,
            setParts,
        };
    },
};

function kodooAccountItem() {
    return {
        type: "item",
        id: "account",
        description: _t("Kodoo Account"),
        callback: () => {
            browser.open(browser.location.origin, "_blank");
        },
        sequence: 60,
    };
}

registry.category("services").add("title", titleService, { force: true });
registry.category("user_menuitems").add("odoo_account", kodooAccountItem, { force: true });
