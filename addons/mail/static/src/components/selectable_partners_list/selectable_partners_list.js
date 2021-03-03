/** @odoo-module **/

import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import SelectablePartner from '@mail/components/selectable_partner/selectable_partner';

const components = { SelectablePartner };
const { Component } = owl;

class SelectablePartnersList extends Component {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        this.selectedPartners = [...this.props.initialMembers];
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------


    get partners() {
        const partners = this.env.messaging.selectablePartnersList.selectablePartners.map(partner => {
            return {
                avatarUrl: partner.avatarUrl,
                id: partner.id,
                isInitialMember: this.props.initialMembers.includes(partner.id),
                isSelected: this.selectedPartners.includes(partner.id),
                localId: partner.localId,
            }
        });
        return partners;
    }

    get thread() {
        return this.env.models['mail.thread'].get(this.props.threadLocalId);
    }
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _close() {
        this.trigger('o-popover-close');
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    async _onClickCreateGroupChat() {
        if (this.props.initialMembers.length > 2 && this.props.initialMembers.length !== this.selectedPartners.length) {
            await this.env.services.rpc(({
                model: 'mail.channel',
                method: 'channel_invite',
                args: [this.thread.id],
                kwargs: {
                    partner_ids: this.selectedPartners,
                },
            }));
            // Trigger rendu de la topbar
        } else if (this.props.initialMembers.length !== this.selectedPartners.length) {
            this.env.messaging.openGroupChat(this.selectedPartners);
        }

        this._close();
    }

    _onSelectedPartner(ev) {
        const selected = this.selectedPartners.includes(ev.detail.id);
        if (ev.detail.selected && !selected) {
            this.selectedPartners.push(ev.detail.id);
            return;
        }

        if (!ev.detail.selected && selected) {
            this.selectedPartners = this.selectedPartners.filter(partnerId => partnerId !== ev.detail.id);
        }
    }
}

Object.assign(SelectablePartnersList, {
    components,
    defaultProps: {
        inputSearch: "",
    },
    props: {
        initialMembers: {
            type: Array,
        },
        inputSearch: {
            type: String,
        },
        threadLocalId: {
            type: String,
        }
    },
    template: 'mail.SelectablePartnersList',
});

export default SelectablePartnersList;
