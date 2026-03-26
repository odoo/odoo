/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

const TEXT_REPLACEMENTS = [
    ["My Odoo.com Account", "Kodoo Account"],
    ["Powered by Odoo", "Powered by Kodoo"],
    ["Odoo Web Client", "Kodoo Web Client"],
    ["Odoo Session Expired", "Kodoo Session Expired"],
    ["Your Odoo session expired. The current page is about to be refreshed.", "Your Kodoo session expired. The current page is about to be refreshed."],
    ["Odoo Server Error", "Kodoo Server Error"],
    ["Odoo Client Error", "Kodoo Client Error"],
    ["Odoo Network Error", "Kodoo Network Error"],
    ["Odoo Warning", "Kodoo Warning"],
    ["Odoo Error", "Kodoo Error"],
    ["Manage Databases", "Kodoo Databases"],
];

function replaceText(value) {
    let next = value;
    for (const [from, to] of TEXT_REPLACEMENTS) {
        next = next.replaceAll(from, to);
    }
    return next;
}

function patchNode(node) {
    if (node.nodeType === Node.TEXT_NODE) {
        const next = replaceText(node.textContent || "");
        if (next !== node.textContent) {
            node.textContent = next;
        }
        return;
    }
    if (!(node instanceof Element)) {
        return;
    }

    for (const attr of ["title", "alt", "aria-label", "placeholder"]) {
        const value = node.getAttribute(attr);
        if (!value) {
            continue;
        }
        const next = replaceText(value);
        if (next !== value) {
            node.setAttribute(attr, next);
        }
    }

    if (node instanceof HTMLAnchorElement) {
        const href = node.getAttribute("href") || "";
        if (href.includes("odoo.com") || href.includes("accounts.odoo.com")) {
            const text = replaceText(node.textContent || "");
            node.textContent = text;
            if (/Kodoo/i.test(text) || /Powered by/i.test(text)) {
                node.setAttribute("href", browser.location.origin);
                node.removeAttribute("target");
            }
        }
    }

    for (const child of node.childNodes) {
        patchNode(child);
    }
}

function patchDocument() {
    if (document.title) {
        document.title = replaceText(document.title) || "Kodoo";
        if (document.title === "Odoo") {
            document.title = "Kodoo";
        }
    }
    patchNode(document.body);
}

const titleService = {
    start() {
        const titleCounters = {};
        const titleParts = {};

        function getParts() {
            return Object.assign({}, titleParts);
        }

        function setCounters(counters) {
            for (const key in counters) {
                const val = counters[key];
                if (!val) {
                    delete titleCounters[key];
                } else {
                    titleCounters[key] = val;
                }
            }
            updateTitle();
        }

        function setParts(parts) {
            for (const key in parts) {
                const val = parts[key];
                if (!val) {
                    delete titleParts[key];
                } else {
                    titleParts[key] = replaceText(val);
                }
            }
            updateTitle();
        }

        function updateTitle() {
            const counter = Object.values(titleCounters).reduce((acc, count) => acc + count, 0);
            const name = Object.values(titleParts).join(" - ") || "Kodoo";
            document.title = counter ? `(${counter}) ${name}` : name;
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

patchDocument();
const observer = new MutationObserver(() => patchDocument());
observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
    characterData: true,
});
