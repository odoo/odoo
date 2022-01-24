/** @odoo-module **/

import { useModels } from "@mail/component_hooks/use_models/use_models";
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component, onWillUnmount } = owl;

export class DiscussContainer extends Component {

    /**
     * @override
     */
    setup() {
        // for now, the legacy env is needed for internal functions such as
        // `useModels` to work
        this.env = Component.env;
        useModels();
        super.setup();
        useUpdate({ func: () => this._update() });
        onWillUnmount(() => this._willUnmount());
    }

    _update() {
        if (!this.messaging || !this.messaging.discuss) {
            return;
        }
        this.messaging.discuss.open();
    }

    _willUnmount() {
        if (this.messaging && this.messaging.discuss) {
            this.messaging.discuss.close();
        }
    }

}

Object.assign(DiscussContainer, {
    components: { Discuss: getMessagingComponent('Discuss') },
    template: 'mail.DiscussContainer',
});
