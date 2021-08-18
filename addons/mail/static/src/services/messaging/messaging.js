/** @odoo-module **/

import { ModelManager } from '@mail/model/model_manager';

import AbstractService from 'web.AbstractService';

export default AbstractService.extend({
    dependencies: ['bus_service'],
    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this.messaging = undefined;
        this._modelManager = new ModelManager(this.env);
        this.env.modelManager = this._modelManager;
    },
    /**
     * @override
     */
    async start() {
        this._super(...arguments);
        if (document.readyState === 'loading') {
            await new Promise(resolve => {
                /**
                 * Called when all JS resources are loaded. This is useful in order
                 * to do some processing after other JS files have been parsed, for
                 * example new models or patched models that are coming from
                 * other modules, because some of those patches might need to be
                 * applied before messaging initialization.
                 */
                window.addEventListener('load', resolve);
            });
        }
        /**
         * All JS resources are loaded, but not necessarily processed.
         * We assume no messaging-related modules return any Promise,
         * therefore they should be processed *at most* asynchronously at
         * "Promise time".
         */
        await new Promise(resolve => setTimeout(resolve));
        /**
         * Some models require session data, like locale text direction (depends on
         * fully loaded translation).
         */
        await this.env.session.is_bound;
        await this.startModelManager();
        this.messaging = this._modelManager.messaging;
        this.env.messagingCreatedPromise.resolve();
        await this.messaging.start();
    },
    /**
     * Starts the model manager.
     */
    async startModelManager() {
        await this._modelManager.start();
    },
});
