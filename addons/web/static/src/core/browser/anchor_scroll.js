// @ts-check

/** @module @web/core/browser/anchor_scroll - Prevents default scroll on bare "#" anchor clicks */

import { browser } from "./browser";

browser.addEventListener("click", (ev) => {
    const href = /** @type {Element} */ (ev.target).closest("a")?.getAttribute("href");
    if (href && href === "#") {
        ev.preventDefault(); // single hash in href are just a way to activate A-tags node
        return;
    }
});
