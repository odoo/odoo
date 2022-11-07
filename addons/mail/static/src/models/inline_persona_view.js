/** @odoo-module **/

import { one, Model } from '@mail/model';

Model({
    name: 'InlinePersonaView',
    template: 'mail.InlinePersonaView',
    fields: {
        persona: one('Persona', { identifying: true }),
        personaListViewOwner: one('PersonaListView', { identifying: true, inverse: 'inlinePersonaViews' }),
    },
});
