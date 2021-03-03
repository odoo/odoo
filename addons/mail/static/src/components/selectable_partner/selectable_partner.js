/** @odoo-module **/

import useStore from '@mail/component_hooks/use_store/use_store';

const { useRef } = owl.hooks;
const { Component } = owl;

class SelectablePartner extends Component {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.selectionStatusRef = useRef('selection-status');
        useStore(props => {
            const partner = this.env.models['mail.partner'].get(props.partnerLocalId);
            return {
                partner: partner && partner.__state,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get partner() {
        return this.env.models['mail.partner'].get(this.props.partnerLocalId);
    }

    get partner_name() {
        return this._getPartnerName(this.partner.nameOrDisplayName);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} partnerName
     *
     * @returns {string}
     */
    _getPartnerName(partnerName) {
        const commaIndex = partnerName.lastIndexOf(",");
        if (commaIndex !== -1) {
            return partnerName.substring(commaIndex + 2, partnerName.length);
        }
        return partnerName;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onChange() {
        this.trigger("o-selected-partner", {
            id: this.partner.id,
            selected: this.selectionStatusRef.el.checked,
        });
    }
}

Object.assign(SelectablePartner, {
    defaultProps: {
        isSelected: false,
    },
    props: {
        isSelected: {
            type: Boolean,
        },
        partnerLocalId: {
            type: String,
        }
    },
    template: 'mail.SelectablePartner',
});

export default SelectablePartner;
