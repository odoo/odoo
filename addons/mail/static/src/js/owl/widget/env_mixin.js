odoo.define('mail.widget.EnvMixin', function () {
"use strict";

const EnvMixin = {
    /**
     * @param {Object} [param0={}]
     * @param {boolean} [param0.withStore=true]
     * @throws {Error} in case the store service does not yet exist
     * @return {Promise<Object>} resolved with env
     */
    async getEnv({ withStore=true }={}) {
        const res = await this.call('env', 'get', { withStore });
        if (!res) {
            throw new Error("Cannot get env.");
        }
        this.env = res;
        return res;
    },
};

return EnvMixin;

});
