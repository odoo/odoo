/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class ChatWindowHiddenMenu extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'listRef', refName: 'list' });
        useUpdateToModel({ methodName: 'onComponentUpdate' });
    }

    /**
     * @returns {ChatWindowHiddenMenuView}
     */
    get chatWindowHiddenMenuView() {
        return this.props.record;
    }

}

Object.assign(ChatWindowHiddenMenu, {
    props: { record: Object },
    template: 'mail.ChatWindowHiddenMenu',
});

registerMessagingComponent(ChatWindowHiddenMenu);
