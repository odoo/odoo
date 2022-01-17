/** @odoo-module **/

import { NewContentModal, MODULE_STATUS } from '@website/systray_items/new_content';
import { patch } from 'web.utils';
import { WebsiteDialog } from '@website/components/dialog/dialog';

const { xml, useState } = owl;

export class AddProductDialog extends WebsiteDialog {
    setup() {
        super.setup();

        this.title = this.env._t("New Product");
        this.primaryTitle = this.env._t("Create");

        this.state = useState({
            name: '',
        });
    }

    async primaryClick() {
        await this.props.addProduct(this.state.name);
        this.close();
    }
}
AddProductDialog.bodyTemplate = xml`
<div>
    <div class="form-group row">
        <label class="col-form-label col-md-3">
            Product Name
        </label>
        <div class="col-md-9">
            <input type="text" t-model="state.name" class="form-control" required="required"/>
        </div>
    </div>
</div>
`;

patch(NewContentModal.prototype, 'website_sale_new_content', {
    setup() {
        this._super();
        this.state.newContentElements = this.state.newContentElements.map(element => {
            if (element.moduleXmlId === 'base.module_website_sale') {
                element.createNewContent = () => this.createNewProduct();
                element.status = MODULE_STATUS.INSTALLED;
            }
            return element;
        });
    },

    createNewProduct() {
        this.dialogs.add(AddProductDialog, {
            addProduct: async (name) => {
                const url = await this.rpc('/shop/add_product', {
                    name,
                });
                this.website.goToWebsite({ path: url });
            },
        });
    }
});
