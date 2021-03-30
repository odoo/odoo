/** @odoo-module **/

import AbstractService from 'web.AbstractService';

require('@bus/js/main');

export default AbstractService.extend({
    /**
     * @override {web.AbstractService}
     */
    start() {
        this._super(...arguments);
        this.env.messagingCreatedPromise.then(() => this.env.messaging.start());
    },
});
