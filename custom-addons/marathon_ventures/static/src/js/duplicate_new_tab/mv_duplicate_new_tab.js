/** @odoo-module **/
/*  mv_duplicate_new_tab.js (Phase 21)
 *  ---------------------------------------------------------
 *  When the planner clicks Duplicate on any mv.* form, open
 *  the newly-created copy in a new browser tab instead of
 *  replacing the current form.
 *
 *  Rationale: duplicating a Deal often means the planner is
 *  building a similar Deal on the same page - the original is
 *  still open for reference. Odoo's default behaviour navigates
 *  away from the original, losing that context.
 *
 *  Scope: strictly mv.* models. Core Odoo forms (Partners,
 *  Users, Settings, ...) keep default same-tab duplicate.
 */

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

patch(FormController.prototype, {
    async duplicateRecord() {
        const resModel = this.props && this.props.resModel;

        // Non-mv.* models: default same-tab behaviour.
        if (!resModel || !resModel.startsWith("mv.")) {
            return super.duplicateRecord(...arguments);
        }
        const origId = this.model && this.model.root && this.model.root.resId;
        // New / unsaved record - nothing to copy yet, delegate.
        if (!origId) {
            return super.duplicateRecord(...arguments);
        }

        // Persist any in-flight edits before duplicating so the copy
        // reflects the current state. Odoo's default duplicate does
        // this implicitly; matching that behaviour here.
        try {
            if (this.model.root.dirty) {
                const saved = await this.model.root.save();
                if (!saved) {
                    // Save failed (validation etc.) - bail out. Odoo
                    // has already surfaced the failure via toast /
                    // invalid-field markers.
                    return;
                }
            }
        } catch (e) {
            // eslint-disable-next-line no-console
            console.warn("[mv duplicate] pre-save failed:", e);
            return;
        }

        // Call copy() via ORM. Returns either a single id or a
        // one-element list depending on Odoo version - handle both.
        try {
            const orm = this.env && this.env.services && this.env.services.orm;
            if (!orm) {
                return super.duplicateRecord(...arguments);
            }
            const result = await orm.call(resModel, "copy", [[origId]], {});
            const newId = Array.isArray(result) ? result[0] : result;
            if (!newId) {
                return super.duplicateRecord(...arguments);
            }
            // Modern Odoo route: /odoo/<model>/<id> opens the record's
            // form view. Works in Odoo 17+. window.open with _blank
            // triggers the browser's usual new-tab handling.
            const url = `/odoo/${encodeURIComponent(resModel)}/${newId}`;
            window.open(url, "_blank");
            // Toast so the planner knows the duplicate happened (the
            // current tab visibly doesn't change).
            const notif = this.env.services && this.env.services.notification;
            if (notif && notif.add) {
                notif.add(
                    "Record duplicated - opened in a new tab.",
                    { type: "success" },
                );
            }
        } catch (e) {
            // Any failure falls back to Odoo's default behaviour so
            // the user isn't stuck if something changes upstream.
            // eslint-disable-next-line no-console
            console.warn("[mv duplicate] new-tab open failed, falling back:", e);
            return super.duplicateRecord(...arguments);
        }
    },
});
