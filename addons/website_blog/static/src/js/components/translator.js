/** @odoo-module **/

import { WebsiteTranslator } from '@website/components/translator/translator';
import { patch } from 'web.utils';

patch(WebsiteTranslator.prototype, 'website_blog_translator', {
    /**
     * @override
     */
    _beforeEditorActive() {
        this._super(...arguments);
        $(this.websiteService.pageDocument).find('[data-translate-error-tooltip]').tooltip({
            container: this.websiteService.pageDocument.body,
            trigger: 'click',
            delay: {'show': 0, 'hide': 0},
            title: function () {
                return $(this).data('translate-error-tooltip');
            },
        });
    }
});
