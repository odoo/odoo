import { browser } from "@web/core/browser/browser";

export const lna = {
    fetch(url, options = {}) {
        return browser.fetch(url, options);
    },
};
