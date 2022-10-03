/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class PersonaImStatusIcon extends Component {

    /**
     * @returns {PersonaImStatusIconView}
     */
    get personaImStatusIconView() {
        return this.props.record;
    }

}

Object.assign(PersonaImStatusIcon, {
    props: { record: Object },
    template: 'mail.PersonaImStatusIcon',
});

registerMessagingComponent(PersonaImStatusIcon);
