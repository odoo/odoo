/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessagingMenu extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'MessagingMenu' });
        /**
         * global JS generated ID for this component. Useful to provide a
         * custom class to autocomplete input, so that click in an autocomplete
         * item is not considered as a click away from messaging menu in mobile.
         */
        this.id = _.uniqueId('o_messagingMenu_');
        // bind since passed as props
        this._onMobileNewMessageInputSelect = this._onMobileNewMessageInputSelect.bind(this);
        this._onMobileNewMessageInputSource = this._onMobileNewMessageInputSource.bind(this);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {MessagingMenu}
     */
    get messagingMenu() {
        return this.messaging && this.messaging.models['MessagingMenu'].get(this.props.localId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     * @param {Object} ui
     * @param {Object} ui.item
     * @param {integer} ui.item.id
     */
    _onMobileNewMessageInputSelect(ev, ui) {
        this.messaging.openChat({ partnerId: ui.item.id });
    }

    /**
     * @private
     * @param {Object} req
     * @param {string} req.term
     * @param {function} res
     */
    _onMobileNewMessageInputSource(req, res) {
        const value = _.escape(req.term);
        this.messaging.models['Partner'].imSearch({
            callback: partners => {
                const suggestions = partners.map(partner => {
                    return {
                        id: partner.id,
                        value: partner.nameOrDisplayName,
                        label: partner.nameOrDisplayName,
                    };
                });
                res(_.sortBy(suggestions, 'label'));
            },
            keyword: value,
            limit: 10,
        });
    }

}

Object.assign(MessagingMenu, {
    props: { localId: String },
    template: 'mail.MessagingMenu',
});

registerMessagingComponent(MessagingMenu);
