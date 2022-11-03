/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'DiscussSidebarView',
    template: 'mail.DiscussSidebarView',
    componentSetup() {
        useRefToModel({ fieldName: 'quickSearchInputRef', refName: 'quickSearchInput' });
        useUpdateToModel({ methodName: 'onComponentUpdate' });
    },
    recordMethods: {
        onComponentUpdate() {
            if (this.quickSearchInputRef.el) {
                this.quickSearchInputRef.el.value = this.owner.discuss.sidebarQuickSearchValue;
            }
        },
    },
    fields: {
        owner: one('DiscussView', { identifying: true, inverse: 'sidebar' }),
        /**
         * Reference to the quick search input. Useful to filter channels and
         * chats based on the content of the input.
         */
        quickSearchInputRef: attr(),
    },
});
