/** @odoo-module **/

import { WysiwygAdapterComponent } from '@website/components/wysiwyg_adapter/wysiwyg_adapter';
import { patch } from 'web.utils';

patch(WysiwygAdapterComponent.prototype, 'website_sale_wysiwyg_adapter', {
    /**
     * @override
     */
     _getContentEditableAreas() {
        return $(this.websiteService.pageDocument).find(this.savableSelector).not('input, [data-oe-readonly],[data-oe-type="monetary"],[data-oe-many2one-id], [data-oe-field="arch"]:empty').filter((_, el) => {
            return !$(el).closest('.o_not_editable, .oe_website_sale .products_header').length;
        }).toArray();
    },
    /**
     * @override
     */
    _getReadOnlyAreas() {
        return $(this.websiteService.pageDocument).find("#wrapwrap").find('.oe_website_sale .products_header, .oe_website_sale .products_header a').toArray();
    },
});
