/** @odoo-module **/
import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';
import { clear } from '@mail/model/model_field_command';

const components = {};

const { Component } = owl;

class GifSearchInput extends Component {

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

    _onClickBack() {
        this.gifManager.update({
            active: 'categories',
            searchInputContent: clear(),
        });
    }

    _onInputEvent(ev) {
        this.gifManager.search(ev.target.value.trim());
    }

}

Object.assign(GifSearchInput, {
    components,
    props: {
        gifManagerLocalId: String
    },
    template: 'mail.GifSearchInput',
});

export default GifSearchInput;
