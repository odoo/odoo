odoo.define('mail/static/src/js/core/translation.js', function (require) {
'use strict';

const { TranslationDataBase } = require('web.translation');

const { Component } = owl;

TranslationDataBase.include({
    /**
     * @override
     */
    set_bundle() {
        const res = this._super(...arguments);
        if (Component.env.messaging) {
            // Update messaging locale whenever the translation bundle changes.
            // In particular if messaging is created before the end of the
            // `load_translations` RPC, the default values have to be
            // updated by the received ones.
            Component.env.messaging.locale.update({
                language: this.parameters.code,
                textDirection: this.parameters.direction,
            });
        }
        return res;
    },
});

});
