/** @odoo-module **/

import useStore from '@mail/component_hooks/use_store/use_store';

const { Component } = owl;

class CategoryTite extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore((...args) => this._useStoreSelector(...args));
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.category}
     */
    get category() {
        return this.env.models['mail.category'].get(this.props.categoryLocalId);
    }

    /**
     * @returns {String}
     */
    get title() {
        return this.env._t(this.category.displayName);
    }

    /**
     * @returns {Integer}
     */
    unreadCounter() {
        const discuss = this.env.messaging.discuss;
        if (this.category.id === 'channel') {
            return discuss && discuss.categoryChannelUnreadCounter;
        }
        else if (this.category.id === 'chat') {
            return discuss && discuss.categoryChatUnreadCounter;
        }
        return 0;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _toggleCategoryOpen() {
        this.category.toggleIsOpen();
    }

    /**
     * @private
     */
    _useStoreSelector(props) {
        const category = this.env.models['mail.category'].get(this.props.categoryLocalId);
        const discuss = this.env.messaging.discuss;
        return {
            category: category ? category.__state : undefined,
            categoryChannelUnreadCounter: discuss && discuss.categoryChannelUnreadCounter,
            categoryChatUnreadCounter: discuss && discuss.categoryChatUnreadCounter,
        };
    }

}

Object.assign(CategoryTite, {
    props: {
        categoryLocalId: String,
    },
    template: 'mail.CategoryTitle',
});

export default CategoryTite;
