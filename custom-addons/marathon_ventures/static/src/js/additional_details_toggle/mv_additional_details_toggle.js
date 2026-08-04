/** @odoo-module **/
/*  mv_additional_details_toggle.js
 *  ---------------------------------------------------------
 *  The Deal form's "Additional details" collapse bar wires a
 *  <button name="action_toggle_additional_details" type="object">
 *  Odoo's default behaviour for type="object" buttons is:
 *      1. Save the record   (runs validation on every required field)
 *      2. Call the server method
 *      3. Reload
 *
 *  On a fresh deal with some required fields empty, step 1 fails
 *  and the toggle never fires - the collapse bar looks broken.
 *
 *  Also: even when it worked, we were paying a full server round-
 *  trip just to flip a UI-only boolean. This patch intercepts the
 *  button, toggles the field client-side via record.update(), and
 *  returns false so Odoo skips the save+server-call sequence.
 *
 *  Scope: strictly this one button name so no other type="object"
 *  action is affected.
 */

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

const TOGGLE_BUTTON_NAME = "action_toggle_additional_details";
const TOGGLE_FIELD = "show_additional_details";

patch(FormController.prototype, {
    async beforeExecuteActionButton(clickParams) {
        // Only intercept our exact toggle button. Every other
        // type="object" button flows through Odoo's default path.
        if (clickParams && clickParams.name === TOGGLE_BUTTON_NAME) {
            const record = this.model && this.model.root;
            if (record && record.data && TOGGLE_FIELD in record.data) {
                try {
                    const next = !record.data[TOGGLE_FIELD];
                    await record.update({ [TOGGLE_FIELD]: next });
                } catch (e) {
                    // eslint-disable-next-line no-console
                    console.warn(
                        "[mv additional-details] local toggle failed:", e,
                    );
                }
            }
            // Returning false tells the action executor that no
            // save happened and the server-side method should not
            // be called - the toggle already happened locally.
            return false;
        }
        return super.beforeExecuteActionButton(clickParams);
    },
});
