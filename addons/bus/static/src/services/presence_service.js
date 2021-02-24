export const userService = {
    name: "user",
    dependencies: ["router", "cookie"],
    deploy(env) {
        return {

        };
    },
};

odoo.define('bus/static/src/services/presence_service.js', function (require) {
'use strict';

const AbstractService = require('web.AbstractService');
const { serviceRegistry } = require('web.core');

const BusPresence = AbstractService.extend({
    /**
     * @override
     */
    init(...args) {
        this._super(...args);
        this._handleVisibilityChange = this._handleVisibilityChange.bind(this);
        this._visibilityState;
    },
    /**
     * @override
     */
    start(...args) {
        this._super(...args);
        document.addEventListener('visibilitychange', this._handleVisibilityChange);
        this._visibilityState = document.visibilityState;
    },
    /**
     * Cleans up listeners.
     */
    destroy() {
        document.removeEventListener('visibilitychange', this._handleVisibilityChange);
    },
    /**
     * @private
     */
    _handleVisibilityChange() {
        this._visibilityState = document.visibilityState;
        this.env.bus.trigger('bus.documentVisibilityChanged', this._visibilityState);
    }
});

serviceRegistry.add('bus.presence', BusPresence);

return BusPresence;

});
