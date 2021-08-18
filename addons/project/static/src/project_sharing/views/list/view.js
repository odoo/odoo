/** @odoo-module **/

import ListView from 'web.ListView';
import Controller from './controller';

export default ListView.extend({
    config: Object.assign({}, ListView.prototype.config, {
        Controller,
    }),
});
