/** @odoo-module **/

import { one, many, Model} from '@mail/model';

Model({
    name: 'PersonaListView',
    template: 'mail.PersonaListView',
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
