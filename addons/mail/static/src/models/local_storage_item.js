/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'LocalStorageItem',
    identifyingMode: 'xor',
    lifecyclesHooks: {
        _created() {
            this.update({ value: this.messaging.browser.localStorage.getItem(this.key) });
        },
    },
    recordMethods: {
        _onChangeValue() {
            this.messaging.browser.localStorage.setItem(this.key, this.value);
        },
    },
    fields: {
        emojiRegistryAsFrequentlyUsed: one('EmojiRegistry', {
            identifying: true,
            inverse: 'frequentlyUsedLocalStorageItem',
        }),
        key: attr({
            compute() {
                if (this.emojiRegistryAsFrequentlyUsed) {
                    return 'mail.frequentlyUsedEmojis';
                }
                return clear();
            },
            default: '',
        }),
        value: attr(),
    },
    onChanges: [
        {
            dependencies: ['value'],
            methodName: '_onChangeValue',
        },
    ],
});
