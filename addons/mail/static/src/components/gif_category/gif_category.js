/** @odoo-module **/

import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';

const components = {};

const { Component } = owl;

class GifCategory extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const gifCategory = this.env.models['mail.gif_category'].get(props.gifCategoryLocalId);
            return {
                gifCategory: gifCategory ? gifCategory.__state : undefined,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.attachment}
     */
    get gifCategory() {
        return this.env.models['mail.gif_category'].get(this.props.gifCategoryLocalId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickGifCategory() {
        this.gifCategory.openCategory();
    }

    _onLoadCategory() {
        this.trigger('o-popover-compute');
    }
}

Object.assign(GifCategory, {
    components,
    props: {
        gifCategoryLocalId: String
    },
    template: 'mail.GifCategory',
});

export default GifCategory;
