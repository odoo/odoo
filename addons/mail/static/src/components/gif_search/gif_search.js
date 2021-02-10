/** @odoo-module **/

import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';
import GifCategory from '@mail/components/gif_category/gif_category';
import Gif from '@mail/components/gif/gif';

const components = {
    GifCategory,
    Gif,
};

const { Component } = owl;

class GifList extends Component {

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

    /**
     * @returns {mail.gif_manager}
     */
    get gifManager() {
        return this.env.models['mail.gif_manager'].get(this.props.gifManagerLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickGif(gif) {
        this.gifManager.gifAction(gif);
    }

    _onScroll(event) {
        if (
            (event.target.scrollHeight - event.target.clientHeight - 50) <= event.target.scrollTop
            && !this.gifManager.isLoadingMore
        ) {
            this.gifManager.searchMore();
        }
    }

}

Object.assign(GifList, {
    components,
    props: {
        gifManagerLocalId: String,
    },
    template: 'mail.GifList',
});

export default GifList;
