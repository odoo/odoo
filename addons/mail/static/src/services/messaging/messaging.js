/** @odoo-module **/

import AbstractService from 'web.AbstractService';

export default AbstractService.extend({
    dependencies: ['bus_service'],
    /**
     * @override {web.AbstractService}
     */
    start() {
        this._super(...arguments);
        this.env.messagingCreatedPromise.then(() => this.env.messaging.start());
    },
});
