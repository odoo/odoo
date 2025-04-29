import { patch } from "@web/core/utils/patch";
import { NewContentModal } from '@website/client_actions/website_preview/new_content_modal';
import { MODULE_STATUS } from "@website/client_actions/website_preview/new_content_element";

patch(NewContentModal.prototype, {
    setup() {
        super.setup();

        const newProductElement = this.state.newContentElements.find(element => element.moduleXmlId === 'base.module_website_sale');
        newProductElement.createNewContent = () => this.onAddContent(
            'website_sale.product_product_action_add',
            true,
            {default_is_published: true});
        newProductElement.status = MODULE_STATUS.INSTALLED;
        newProductElement.model = 'product.product';
    },
});
