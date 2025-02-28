/** @odoo-module **/

import { session } from '@web/session';
import { patch } from '@web/core/utils/patch';

import { Dialog } from '@web/core/dialog/dialog';

patch(Dialog.prototype, {
	setup() {
        super.setup();
        this.data.size = (
    		session.dialog_size !== 'maximize' ? this.props.size : 'fs'
        );
        this.data.initalSize = this.props?.size || 'lg';
    }
});
