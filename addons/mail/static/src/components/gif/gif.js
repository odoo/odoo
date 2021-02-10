/** @odoo-module **/
import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';

const components = {};

const { Component } = owl;

class Gif extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const gif = this.env.models['mail.gif'].get(props.gifLocalId);
            return {
                gif: gif ? gif.__state : undefined,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.attachment}
     */
    get gif() {
        return this.env.models['mail.gif'].get(this.props.gifLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickGif() {
        this.gif.insertGif();
    }

    _onClickFav() {
        this.gif.favorite();
    }

    _onClickUnfav() {
        this.gif.unfavorite();
    }

    _onLoadedGif() {
        this.trigger('o-popover-compute');
    }

}

Object.assign(Gif, {
    components,
    props: {
        gifLocalId: String
    },
    template: 'mail.Gif',
});

export default Gif;
