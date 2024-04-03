/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { markEventHandled } from '@mail/utils/utils';

const { Component } = owl;

export class PersonaImStatusIcon extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {PersonaImStatusIconView}
     */
    get personaImStatusIconView() {
        return this.props.record;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        markEventHandled(ev, 'PersonaImStatusIcon.Click');
        if (!this.props.hasOpenChat || !this.personaImStatusIconView.persona.partner) {
            return;
        }
        this.personaImStatusIconView.persona.partner.openChat();
    }

}

Object.assign(PersonaImStatusIcon, {
    defaultProps: {
        hasBackground: true,
        hasOpenChat: false,
    },
    props: {
        hasBackground: { type: Boolean, optional: true },
        /**
         * Determines whether a click on `this` should open a chat with
         * `this.partner`.
         */
        hasOpenChat: { type: Boolean, optional: true },
        record: Object,
    },
    template: 'mail.PersonaImStatusIcon',
});

registerMessagingComponent(PersonaImStatusIcon);
