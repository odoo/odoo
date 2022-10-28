/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class PersonaImStatusIconView extends Component {

    /**
     * @returns {PersonaImStatusIconView}
     */
    get personaImStatusIconView() {
        return this.props.record;
    }

}

Object.assign(PersonaImStatusIconView, {
    props: { record: Object },
    template: 'mail.PersonaImStatusIconView',
});

registerMessagingComponent(PersonaImStatusIconView);
