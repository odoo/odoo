/** @odoo-module **/

import ViewRegistry from 'web.view_registry';

import FormView from './form/view';
import ListView from './list/view';

ViewRegistry
    .add('form', FormView)
    .add('list', ListView);
