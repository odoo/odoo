/** @odoo-module **/

import CategoryTitle from '@mail/components/category_title/category_title';

import { patch } from 'web.utils';

const components = { CategoryTitle };

patch(components.CategoryTitle.prototype, 'im_livechat/static/src/components/category_title/category_title.js', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {Integer}
     */
    unreadCounter() {
        if (this.category.id === "livechat") {
            return this.env.messaging.discuss && this.env.messaging.discuss.categoryLivechatUnreadCounter;
        }
        return this._super();
    },

    /**
     * @overide
     */
    _useStoreSelector(props) {
        return Object.assign(this._super(...arguments), {
            categoryLivechatUnreadCounter: this.env.messaging.discuss && this.env.messaging.discuss.categoryLivechatUnreadCounter,
        });
    }
});
