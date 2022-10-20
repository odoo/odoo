/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'InlinePersonaView',
    template: 'mail.InlinePersonaView',
    templateGetter: 'inlinePersonaView',
    fields: {
        persona: one('Persona', { identifying: true }),
        personaListViewOwner: one('PersonaListView', { identifying: true, inverse: 'inlinePersonaViews' }),
    },
});
