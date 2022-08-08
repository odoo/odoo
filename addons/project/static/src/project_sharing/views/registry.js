/** @odoo-module **/

import ViewRegistry from 'web.view_registry';
import { registry } from '@web/core/registry';
// FIXME: make sure the form view are define before we remove them below
import "@web/views/form/form_view";

import FormView from './form/view';

// FIXME: remove new views to force the use of the overriden legacy views when
// project sharing form is converted to new views.
registry.category("views").remove("form");

ViewRegistry
    .add('form', FormView);
