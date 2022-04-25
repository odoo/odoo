/** @odoo-module **/

import {NewContentFormController} from '@website/js/new_content_form';
import viewRegistry from 'web.view_registry';
import FormView from 'web.FormView';

const AddProductFormController = NewContentFormController.extend({
    /**
     * @override
     */
    _getPath(state) {
        return state.data.website_url.split('#')[0];
    },
});

const AddProductFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: AddProductFormController,
    }),
});

viewRegistry.add('product_product_add_form', AddProductFormView);

export default {
    AddProductFormController: AddProductFormController,
    AddProductFormView: AddProductFormView,
};
