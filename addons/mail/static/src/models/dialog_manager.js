/** @odoo-module **/

import { many, Model } from '@mail/model';

Model({
    name: 'DialogManager',
    template: 'mail.DialogManager',
    lifecycleHooks: {
        _componentUpdated() {
            if (this.dialogs.length > 0) {
                document.body.classList.add('modal-open');
            } else {
                document.body.classList.remove('modal-open');
            }
        },
    },
    fields: {
        // FIXME: dependent on implementation that uses insert order in relations!!
        dialogs: many('Dialog', { inverse: 'manager', isCausal: true }),
    },
});
