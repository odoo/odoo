/** @odoo-module **/
/* mv_deal_footer.js
 *
 * Hides the deal form footer unless the record is "dirty" (has
 * unsaved changes), mirroring Odoo's own o_form_status_indicator
 * behavior into a class our SCSS can reveal.
 *
 * Strategy:
 *   - SCSS rule: `.mv-deal-redesign .mv-form-footer { display: none }`
 *     with `.mv-deal-redesign.mv-form--dirty .mv-form-footer { display: flex }`.
 *   - This script watches the page for `.o_form_status_indicator_buttons`
 *     elements (which Odoo renders only when the form is dirty) and
 *     mirrors that presence into a `mv-form--dirty` class on the
 *     surrounding `.mv-deal-redesign` form.
 *
 * Why a MutationObserver and not an OWL service:
 *   - Multiple form views may be open across tabs (kanban dialogs,
 *     breadcrumb-pushed views), so binding to a specific
 *     FormController instance is brittle.
 *   - Odoo's own indicator is the source of truth; we mirror it.
 */

(function () {
    "use strict";

    const DIRTY_CLASS = "mv-form--dirty";
    const FORM_SELECTOR = ".mv-deal-redesign";
    const INDICATOR_SELECTOR = ".o_form_status_indicator_buttons";

    function syncForm(form) {
        // The dirty indicator may live anywhere inside the form's
        // status bar / sheet header. If present and visible, mark
        // dirty; otherwise clear.
        const indicator = form.querySelector(INDICATOR_SELECTOR);
        const isDirty = !!indicator && indicator.offsetParent !== null;
        if (isDirty) {
            form.classList.add(DIRTY_CLASS);
        } else {
            form.classList.remove(DIRTY_CLASS);
        }
    }

    function syncAll() {
        document.querySelectorAll(FORM_SELECTOR).forEach(syncForm);
    }

    // Observe the entire document for subtree changes. The indicator
    // is added/removed by Odoo's own re-renders, which mutate the
    // DOM, so a subtree+attribute observer catches every transition.
    const observer = new MutationObserver(() => {
        // Debounce: coalesce bursts of mutations during a single
        // re-render into one sync call via microtask.
        if (observer._scheduled) return;
        observer._scheduled = true;
        queueMicrotask(() => {
            observer._scheduled = false;
            syncAll();
        });
    });

    function start() {
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ["class", "style"],
        });
        // Also listen to capture-phase input/change events on form
        // controls — Odoo's indicator render trails a few ticks
        // behind the actual edit, so syncing on input gives an
        // immediate response (the indicator will catch up shortly).
        ["input", "change"].forEach((evType) => {
            document.addEventListener(
                evType,
                (ev) => {
                    const form = ev.target && ev.target.closest
                        ? ev.target.closest(FORM_SELECTOR)
                        : null;
                    if (form) {
                        // Defer the read so Odoo has a chance to
                        // toggle its own indicator first.
                        setTimeout(() => syncForm(form), 0);
                    }
                },
                true,
            );
        });
        // Initial sync in case a form is already on screen at load.
        syncAll();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start, { once: true });
    } else {
        start();
    }
})();
