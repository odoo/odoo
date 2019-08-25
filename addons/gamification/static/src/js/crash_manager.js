odoo.define('gamification.CrashManager', function (require) {
"use strict";

const core = require('web.core');
const CrashManager = require('web.CrashManager').CrashManager;

const _lt = core._lt;

CrashManager.include({
    /**
     * @override
     */
    getMapTitle() {
        return {
            ...this._super(...arguments),
            karma_error: _lt("Karma Error"),
        };
    },
});
});
