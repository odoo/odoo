/** @odoo-module **/
import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';
import Gif from '@mail/components/gif/gif';

const components = {
    Gif,
};

const { Component } = owl;

class GifFavorite extends Component {

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

    _onScroll(event) {
        if (
            (event.target.scrollHeight - event.target.clientHeight - 50) <= event.target.scrollTop
            && !this.gifManager.isLoadingMore
        ) {
            this.gifManager.favoriteMore();
        }
    }

}

Object.assign(GifFavorite, {
    components,
    props: {
        gifManagerLocalId: String
    },
    template: 'mail.GifFavorite',
});

export default GifFavorite;
