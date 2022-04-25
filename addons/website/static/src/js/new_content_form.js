/** @odoo-module **/

import FormController from 'web.FormController';

export const NewContentFormController = FormController.extend({
    /**
     * @override
     */
    saveRecord() {
        return this._super.apply(this, arguments).then(() => {
            const state = this.model.get(this.handle);
            this.do_action({
                type: 'ir.actions.act_window_close',
                infos: {path: this._getPath(state)},
            });
        });
    },
    /**
     * @private
     */
    _getPath(state) {
        return state.data.website_url;
    }
});
