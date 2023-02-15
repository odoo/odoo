/** @odoo-module **/

import { Patch } from '@mail/model';

import Dialog from 'web.Dialog';

Patch({
    name: 'ActivityView',
    recordMethods: {
        /**
         * @override
         */
        async onClickCancel(ev) {
            if (this.activity.calendar_event_id) {
                await new Promise(resolve => {
                    Dialog.confirm(
                        this,
                        this.env._t("The activity is linked to a meeting. Deleting it will remove the meeting as well. Do you want to proceed?"),
                        { confirm_callback: resolve },
                    );
                });
            }
            if (!this.exists()) {
                return;
            }
            await this._super();
        },
    },
});
