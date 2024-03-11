/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'Timer',
    identifyingMode: 'xor',
    lifecycleHooks: {
        _created() {
            this.update({ timeoutId: this.messaging.browser.setTimeout(this._onTimeout, this.duration) });
        },
        _willDelete() {
            this.messaging.browser.clearTimeout(this.timeoutId);
        },
    },
    recordMethods: {
        /**
         * @private
         */
        _onTimeout() {
            this.update({ timeoutId: clear() });
            this.onTimeout();
        },
        onTimeout() {},
        _onChangeDoReset() {
            if (!this.doReset) {
                return;
            }
            this.messaging.browser.clearTimeout(this.timeoutId);
            this.update({
                doReset: clear(),
                timeoutId: this.messaging.browser.setTimeout(this._onTimeout, this.duration),
            });
        },
    },
    fields: {
        doReset: attr({
            default: false,
        }),
        /**
         * Duration, in milliseconds, until timer times out and calls the
         * timeout function.
         */
        duration: attr({
            compute() {
                return clear();
            },
            required: true,
        }),
        /**
         * Internal reference of `setTimeout()` that is used to invoke function
         * when timer times out. Useful to clear it when timer is cleared/reset.
         */
        timeoutId: attr(),
    },
    onChanges: [
        {
            dependencies: ["doReset"],
            methodName: '_onChangeDoReset',
        },
    ],
});
