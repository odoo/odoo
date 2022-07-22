/** @odoo-module **/

import ViewRegistry from 'web.view_registry';
import { registry } from '@web/core/registry';
// FIXME: make sure the form and list views are define before we remove them below
import "@web/views/form/form_view";
import "@web/views/list/list_view";

import FormView from './form/view';
import ListView from './list/view';

// FIXME: remove new views to force the use of the overriden legacy views when
// project sharing form and list are converted to new views.
registry.category("views").remove("form");
registry.category("views").remove("list");

ViewRegistry
    .add('form', FormView)
    .add('list', ListView);
