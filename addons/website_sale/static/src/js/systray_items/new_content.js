/** @odoo-module **/

import { NewContentModal, MODULE_STATUS } from '@website/systray_items/new_content';
import { patch } from 'web.utils';

patch(NewContentModal.prototype, 'website_sale_new_content', {
    setup() {
        this._super();

        const newProductElement = this.state.newContentElements.find(element => element.moduleXmlId === 'base.module_website_sale');
        newProductElement.createNewContent = () => this.onAddContent('website_sale.product_product_action_add', true);
        newProductElement.status = MODULE_STATUS.INSTALLED;
        newProductElement.model = 'product.product';
    },
});
