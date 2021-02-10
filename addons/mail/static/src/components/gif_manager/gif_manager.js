/** @odoo-module **/

import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';
import GifCategories from '@mail/components/gif_categories/gif_categories';
import GifSearch from '@mail/components/gif_search/gif_search';
import GifSearchInput from '@mail/components/gif_search_input/gif_search_input';
import GifFavorite from '@mail/components/gif_favorite/gif_favorite';

const components = {
    GifCategories,
    GifSearch,
    GifSearchInput,
    GifFavorite,
};

const { Component } = owl;

class GifManager extends Component {

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

}

Object.assign(GifManager, {
    components,
    props: {
        gifManagerLocalId: String
    },
    template: 'mail.GifManager',
});

export default GifManager;
