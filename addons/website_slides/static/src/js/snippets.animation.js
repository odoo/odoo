/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.WebsiteAnimate.include({
    /**
     * @override
     */
    getScrollingElement() {
        if ($('.o_wslide_fs_article_content').length) {
            return $('.o_wslide_fs_article_content:eq(0)');
        }
        return this._super.apply(this, arguments);
    }
});
