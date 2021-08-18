/** @odoo-module **/

import FormView from 'web.FormView';
import Controller from './controller';

export default FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller,
    }),
});
