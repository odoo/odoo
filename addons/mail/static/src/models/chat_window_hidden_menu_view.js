/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'ChatWindowHiddenMenuView',
    lifecycleHooks: {
        _created() {
            document.addEventListener('click', this._onClickCaptureGlobal, true);
        },
        _willDelete() {
            document.removeEventListener('click', this._onClickCaptureGlobal, true);
        },
    },
    recordMethods: {
        /**
         * Closes the menu when clicking outside.
         * Must be done as capture to avoid stop propagation.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onClickCaptureGlobal(ev) {
            if (!this.component || !this.component.root.el || this.component.root.el.contains(ev.target)) {
                return;
            }
            this.owner.closeHiddenMenu();
        }
    },
    fields: {
        component: attr(),
        owner: one('ChatWindowManager', {
            identifying: true,
            inverse: 'hiddenMenuView',
        }),
    },
});
