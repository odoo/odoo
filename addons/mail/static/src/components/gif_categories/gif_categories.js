/** @odoo-module **/
import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';
import GifCategory from '@mail/components/gif_category/gif_category';

const components = {
    GifCategory,
};

const { Component } = owl;

class GifCategories extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const gifManager = this.env.models['mail.gif_manager'].get(props.gifManagerLocalId);
            return {
                gifManager: gifManager ? gifManager.__state : undefined,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.attachment}
     */
    get gifManager() {
        return this.env.models['mail.gif_manager'].get(this.props.gifManagerLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickFavoriteCategory() {
        this.gifManager.update({
            active: 'favorites',
        });
    }

}

Object.assign(GifCategories, {
    components,
    props: {
        gifManagerLocalId: String
    },
    template: 'mail.GifCategories',
});

export default GifCategories;
