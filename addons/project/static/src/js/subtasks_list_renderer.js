/** @odoo-module **/

import ListRenderer from 'web.ListRenderer';
import Dialog from 'web.Dialog';
import { _t } from 'web.core';

export const SubTasksListRenderer = ListRenderer.extend({
    events: Object.assign({}, ListRenderer.prototype.events, {
        'click tr .o_list_record_remove': '_onClickOpenDialog',
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
    * Confirmation dialog is opened when deleted any record from list.
    *
    * @private
    * @param {MouseEvent} ev
    */
    _onClickOpenDialog(ev) {
        ev.stopPropagation();
        Dialog.confirm(this, _t("Are you sure you want to delete this record ?"), {
            confirm_callback: () => {
                this._onRemoveIconClick(ev);
            },
            cancel_callback: () => {
                return false;
            },
        });
    },

});
