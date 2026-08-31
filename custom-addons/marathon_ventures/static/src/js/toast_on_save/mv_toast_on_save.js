/** @odoo-module **/
/*  mv_toast_on_save.js  (Phase 20)
 *  ---------------------------------------------------------
 *  Shows an Odoo success toast on every successful save of an
 *  mv.* record. Fires for both create and update, using the
 *  model's ir.model.name as the display label.
 *
 *  Scope: strictly mv.* models so core Odoo forms (Users,
 *  Partners, Settings, product.template, ...) stay silent.
 *
 *  We patch Record.save() from the relational_model layer
 *  rather than FormController.save(). Record.save() is the
 *  shared low-level entry point that BOTH the top-right Save
 *  button AND our custom <button name="action_save_record"
 *  type="object"> "Save Deal" go through - Odoo auto-saves
 *  before calling the server-side action, using record.save()
 *  under the hood. Patching one level lower catches both
 *  paths + inline-list saves + save-on-navigate.
 */

import { patch } from "@web/core/utils/patch";
import { Record } from "@web/model/relational_model/record";
import { registry } from "@web/core/registry";

// Model-name -> human label cache. Populated on first save
// per model via a single-record search_read on ir.model.
const modelLabelCache = {};

async function getModelLabel(orm, modelName) {
    if (modelLabelCache[modelName]) return modelLabelCache[modelName];
    try {
        const rows = await orm.searchRead(
            "ir.model",
            [["model", "=", modelName]],
            ["name"],
            { limit: 1 },
        );
        const label = rows && rows[0] && rows[0].name
            ? rows[0].name : modelName;
        modelLabelCache[modelName] = label;
        return label;
    } catch (e) {
        return modelName;
    }
}

// Grab the running WebClient's env once, then reuse. Notification
// and orm services are attached to that env.
function getEnv() {
    try {
        const app = window.__OWL_APP__;
        if (app && app.env) return app.env;
    } catch (e) { /* swallow */ }
    return null;
}

patch(Record.prototype, {
    async save(...args) {
        // Capture "is this a new record?" AND "did the user actually
        // edit anything?" BEFORE saving. After a successful save the
        // record's isNew flips to false and dirty flips to false, so
        // we have to snapshot them first.
        //
        // The dirty guard is critical: Odoo silently calls Record.save()
        // on tab-visibility changes, breadcrumb navigation, and various
        // other lifecycle events - even when the user hasn't touched
        // anything. Without the guard, switching browser tabs on a
        // Deal detail page would fire an "Updated" toast on return.
        const wasNew = !!this.isNew;
        const wasDirty = !!this.dirty;
        const resModel = this.resModel;

        const result = await super.save(...args);

        try {
            // Only toast for real user-driven saves:
            //   * a brand-new record being persisted, OR
            //   * an existing record with pending edits.
            // No-op save() calls (tab switch, breadcrumb nav,
            // implicit refresh) get neither and stay silent.
            const shouldToast = result && (wasNew || wasDirty);
            if (
                shouldToast
                && resModel
                && typeof resModel === "string"
                && resModel.startsWith("mv.")
            ) {
                const env = this.model && this.model.env;
                const services = env && env.services;
                const notif = services && services.notification;
                const orm = services && services.orm;
                if (notif && notif.add && orm) {
                    const label = await getModelLabel(orm, resModel);
                    const verb = wasNew ? "Created" : "Updated";
                    notif.add(
                        `${label} Successfully ${verb}`,
                        { type: "success" },
                    );
                }
            }
        } catch (e) {
            // Guarantee the toast layer can never break a save.
            // eslint-disable-next-line no-console
            console.warn("[mv_toast_on_save] toast failed:", e);
        }
        return result;
    },
});

// No registry entry needed - patching Record.prototype takes effect
// the moment this module is imported by the asset bundle.
