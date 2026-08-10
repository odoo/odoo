/** @odoo-module **/

/*  Deal footer Cancel button.
 *
 *  Behavior:
 *    * NEW deal (never saved)      -> discard + navigate back to the
 *                                     previous action (Odoo does this
 *                                     natively when Discard is clicked
 *                                     on an unsaved record).
 *    * EXISTING deal (has an id)   -> discard local edits and STAY on
 *                                     the same deal in read mode.
 *
 *  Both paths go through Odoo's built-in Discard control so we avoid
 *  the dirty-form / required-field validation guard that fires on
 *  window.history.back() when the record has unsaved changes. That
 *  guard was the reason a new deal previously needed two Cancel
 *  clicks (first click showed a validation dialog, second navigated).
 */

function _isNewRecordUrl() {
    const path = window.location.pathname || "";
    const hash = window.location.hash || "";
    if (/\/new(\/|\?|#|$)/.test(path)) {
        return true;
    }
    if (/[?&#]id=new(&|$)/.test(hash)) {
        return true;
    }
    const hasNumericId = /\/\d+(\/|\?|#|$)/.test(path)
                         || /[?&#]id=\d+/.test(hash);
    return !hasNumericId;
}

function _findDiscardButton() {
    return document.querySelector(
        ".o_form_button_cancel, "
        + ".o_form_status_indicator button[title='Discard'], "
        + ".o_cp_action_menus .fa-times"
    );
}

document.addEventListener("click", (ev) => {
    const btn = ev.target.closest(".mv_cancel_deal");
    if (!btn) {
        return;
    }
    ev.preventDefault();
    ev.stopPropagation();

    // Preferred path for BOTH new and existing records: click Odoo's
    // Discard control. Discard does not validate, so a new record
    // with missing required fields is dropped cleanly on the first
    // click. Odoo also handles the follow-up navigation:
    //   * new record   -> pops back to the previous action / list
    //   * existing rec -> stays on the record in read mode
    const discardBtn = _findDiscardButton();
    if (discardBtn) {
        discardBtn.click();
        return;
    }

    // Fallback (discard button not rendered - typically means the
    // record is CLEAN, no pending edits). Use the simpler branch:
    //   * new but somehow clean -> history.back()
    //   * existing + clean       -> reload to force a fresh read view
    if (_isNewRecordUrl()) {
        window.history.back();
    } else {
        window.location.reload();
    }
});
