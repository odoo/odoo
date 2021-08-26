/** @odoo-module **/

import FormView from 'web.FormView';
import Controller from './controller';
import Renderer from './renderer';

export default FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller,
        Renderer,
    }),
});
