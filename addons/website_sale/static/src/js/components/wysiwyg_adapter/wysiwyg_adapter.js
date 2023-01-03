/** @odoo-module **/

import { WysiwygAdapterComponent } from '@website/components/wysiwyg_adapter/wysiwyg_adapter';
import { patch } from 'web.utils';

// TODO this whole patch actually seems unnecessary. The bug it solved seems
// to stay solved if this is removed. To investigate.
patch(WysiwygAdapterComponent.prototype, 'website_sale_wysiwyg_adapter', {
    /**
     * @override
     */
     _getContentEditableAreas() {
        const array = this._super(...arguments);
        return array.filter(el => {
            // TODO should really review this system of "ContentEditableAreas +
            // ReadOnlyAreas", here the "products_header" stuff is duplicated in
            // both but this system is also duplicated with o_not_editable and
            // maybe even other systems (like preserving contenteditable="false"
            // with oe-keep-contenteditable).
            return !el.closest('.oe_website_sale .products_header');
        });
    },
    /**
     * @override
     */
    _getReadOnlyAreas() {
        return $(this.websiteService.pageDocument).find("#wrapwrap").find('.oe_website_sale .products_header, .oe_website_sale .products_header a').toArray();
    },
});
