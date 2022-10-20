/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one, many} from '@mail/model/model_field';

registerModel({
    name: 'PersonaListView',
    template: 'mail.PersonaListView',
    templateGetter: 'personaListView',
    identifyingMode: 'xor',
    fields: {
        inlinePersonaViews: many('InlinePersonaView', { inverse: 'personaListViewOwner',
            compute() {
                if (this.messageContextMenuOwner.reactionSelection) {
                    return this.messageContextMenuOwner.reactionSelection.personas.map(persona => {
                        return { persona: persona };
                   });
                } 
            },
        }),
        messageContextMenuOwner: one('MessageContextMenu', { identifying: true, inverse: 'personaListView' }),
    },
});
