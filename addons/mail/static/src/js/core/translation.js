/** @odoo-module **/

import { TranslationDataBase } from 'web.translation';

TranslationDataBase.include({
    /**
     * @override
     */
    set_bundle() {
        const res = this._super(...arguments);
        const { wowlEnv } = owl.Component.env;
        if (wowlEnv && wowlEnv.services && wowlEnv.services.messaging) {
            // During boot `env.services` might not even be set yet, in this
            // case this can safely be ignored as messaging will then load
            // locale information during its initialization.
            wowlEnv.services.messaging.get().then(messaging => {
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
