/** @odoo-module **/
import { session } from "@web/session";
import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
const {onMounted} = owl;

/**
 * Patched function to toggle record selection and add a CSS class to selected records.
 *
 * @param {Object} record - The record to toggle selection for.
 */
patch(ListRenderer.prototype, 'custom_list_view/static/src/js/list_renderer.js', {
    toggleRecordSelection(record) {
        var self = this;
        this._super.apply(this, arguments);
        var selectedRecord = $(event.target).closest('tr')
        if ($(event.target).prop('checked')) {
            selectedRecord.addClass('selected_record');
        } else {
            selectedRecord.removeClass('selected_record')
        }
    }
});
