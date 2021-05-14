/** @odoo-module **/

import Dialog from 'web.Dialog';

Dialog.include({
    /**
     * @private
     * @override
     * @param {jQueryEvent} ev
     */
    _onFooterButtonKeyDown(ev) {
        switch(ev.key) {
            case 'TAB':
                const name = ev.target.getAttribute('name');
                if (['action_close_dialog', 'action_done', 'action_done_schedule_next'].includes(name)) {
                    return;
                }
                return this._super.apply(this, arguments);
        }
    },

});
