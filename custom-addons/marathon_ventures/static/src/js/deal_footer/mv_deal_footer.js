/** @odoo-module **/
/* mv_deal_footer.js
 *
 * Hides the deal form footer unless the record is "dirty" (has
 * unsaved changes). Mirrors Odoo's own o_form_status_indicator
 * presence into a `mv-form--dirty` class on `.mv-deal-redesign`
 * forms so our SCSS can toggle the footer's display.
 *
 * All callbacks are try/catch-wrapped. This script runs page-wide;
 * any uncaught exception could stop later listeners (including
 * Odoo's own row-click handler on the list view). Defensive
 * isolation is required.
 */

(function () {
    "use strict";

    // Prevent re-registration if the bundle reloads.
    if (window.__mvDealFooterInstalled) return;
    window.__mvDealFooterInstalled = true;

    const DIRTY_CLASS = "mv-form--dirty";
    const FORM_SELECTOR = ".mv-deal-redesign";
    const INDICATOR_SELECTOR = ".o_form_status_indicator_buttons";

    function syncForm(form) {
        try {
            if (!form.isConnected) return;
            const indicator = form.querySelector(INDICATOR_SELECTOR);
            const isDirty = !!indicator && indicator.offsetParent !== null;
            if (isDirty) form.classList.add(DIRTY_CLASS);
            else form.classList.remove(DIRTY_CLASS);
        } catch (e) { /* swallow */ }
    }

    function syncAll() {
        try {
            const forms = document.querySelectorAll(FORM_SELECTOR);
            if (forms.length === 0) return;
            forms.forEach(syncForm);
        } catch (e) { /* swallow */ }
    }

    const observer = new MutationObserver(() => {
        try {
            if (observer._scheduled) return;
            observer._scheduled = true;
            queueMicrotask(() => {
                observer._scheduled = false;
                syncAll();
            });
        } catch (e) { /* swallow */ }
    });

    function start() {
        try {
            observer.observe(document.body, {
                childList: true, subtree: true,
                attributes: true, attributeFilter: ["class", "style"],
            });
        } catch (e) { /* swallow */ }

        ["input", "change"].forEach((evType) => {
            try {
                document.addEventListener(evType, (ev) => {
                    try {
                        const t = ev.target;
                        if (!t || !t.closest) return;
                        const form = t.closest(FORM_SELECTOR);
                        if (form) setTimeout(() => syncForm(form), 0);
                    } catch (e) { /* swallow */ }
                }, true);
            } catch (e) { /* swallow */ }
        });

        syncAll();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start, { once: true });
    } else {
        start();
    }
})();
