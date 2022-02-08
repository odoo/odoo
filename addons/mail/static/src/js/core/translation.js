/** @odoo-module **/

import { TranslationDataBase } from 'web.translation';

const { Component } = owl;

TranslationDataBase.include({
    /**
     * @override
     */
    set_bundle() {
        const res = this._super(...arguments);
        if (Component.env.services && Component.env.services.messaging) {
            // During boot `env.services` might not even be set yet, in this
            // case this can safely be ignored as messaging will then load
            // locale information during its initialization.
            Component.env.services.messaging.get().then(messaging => {
                // Update messaging locale whenever the translation bundle changes.
                // In particular if messaging is created before the end of the
                // `load_translations` RPC, the default values have to be
                // updated by the received ones.
                messaging.locale.update({
                    language: this.parameters.code,
                    textDirection: this.parameters.direction,
                });
            });
        }
        return res;
    },
});
