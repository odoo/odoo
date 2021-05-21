/** @odoo-module **/

export const instancePatchMessagingInitializer = {
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    async _initializeOdooBot() {
        const data = await this.async(() => this.env.services.rpc({
            model: 'mail.channel',
            method: 'init_odoobot',
        }));
        if (!data) {
            return;
        }
        this.env.session.odoobot_initialized = true;
    },

    /**
     * @override
     */
    async start() {
        await this.async(() => this._super());

        if ('odoobot_initialized' in this.env.session && !this.env.session.odoobot_initialized) {
            this._initializeOdooBot();
        }
    },
};
