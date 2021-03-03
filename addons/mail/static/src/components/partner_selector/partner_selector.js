/** @odoo-module **/

import SelectablePartnersList from '@mail/components/selectable_partners_list/selectable_partners_list';

const components = { SelectablePartnersList };

const { Component } = owl;
const { useRef } = owl.hooks;
const { useState } = owl.hooks;

class PartnerSelector extends Component {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.inputRef = useRef('search-input');
        this.state = useState({ searchInput: "" });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get initial_members_id() {
        return this.props.initialMembers.map(element => element.id);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _onKeyUp() {
        this.env.messaging.selectablePartnersList.update({
            inputSearch: this.inputRef.el.value,
        });
        this.state.searchInput = this.inputRef.el.value;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------


}

Object.assign(PartnerSelector, {
    components,
    defaultProps: {

    },
    props: {
        initialMembers: {
            type: Object,
        },
        threadLocalId: {
            type: String,
        }
    },
    template: 'mail.PartnerSelector',
});

export default PartnerSelector;
