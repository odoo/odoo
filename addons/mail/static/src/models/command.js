/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'Command',
    lifecycleHooks: {
        _created() {
            this.update({
                remove: this.env.services.command.add(
                    this.name,
                    this.action,
                    this.options,
                )
            });
        },
        _willDelete() {
            this.remove();
        }
    },
    fields: {
        action: attr(),
        channel: one('Channel', {
            identifying: true,
            inverse: 'command',
        }),
        name: attr(),
        options: attr(),
        remove: attr(),
    },
});
