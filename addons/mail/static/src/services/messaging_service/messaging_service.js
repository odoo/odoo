/** @odoo-module **/

import { ModelManager } from '@mail/model/model_manager';

export const messagingValues = {};

export const messagingService = {
    async: true,
    dependencies: ['effect', 'localization', 'notification', 'orm', 'router', 'rpc'],
    start(env) {
        this.modelManager = new ModelManager(env);
        env.bus.on("WEB_CLIENT_READY", null, async () => {
            this._startModelManager();
        });
        return {
            /**
             * Returns the messaging record once it is initialized. This method
             * should be considered the main entry point to the messaging system
             * for outside code.
             *
             * @returns {mail.messaging}
             **/
            async get() {
                return this.modelManager.getMessaging();
            },
            /**
             * Returns the messaging record or undefined if it is not yet
             * created. Useful to manually handle messaging not being created
             * or initialized for example to display a loading spinner.
             *
             * @returns {mail.messaging|undefined}
             **/
            get messaging() {
                return this.modelManager.messaging;
            },
            /**
             * Returns the modelManager. It should only be used by technical
             * code, not by business code.
             *
             * @returns {ModelManager}
             */
            modelManager: this.modelManager,
        };
    },
    /**
     * Separate method to control creation delay in tests.
     *
     * @private
     */
    _startModelManager() {
        this.modelManager.start(messagingValues);
    },
};
