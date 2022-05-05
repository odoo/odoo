/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models';
import { useUpdate } from '@mail/component_hooks/use_update';
import { insertAndReplace } from '@mail/model/model_field_command';
import { getMessagingComponent } from "@mail/utils/messaging_component";
// ensure child component is registered first.
import '@mail/components/discuss/discuss';

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
        this.env.services.messaging.modelManager.messagingCreatedPromise.then(async () => {
            const { action } = this.props;
            const initActiveId =
                (action.context && action.context.active_id) ||
                (action.params && action.params.default_active_id) ||
                'mail.box_inbox';
            this.discuss = this.messaging.discuss;
            this.discuss.update({
                discussView: insertAndReplace({ actionId: action.id }),
                initActiveId,
            });
            // Wait for messaging to be initialized to make sure the system
            // knows of the "init thread" if it exists.
            await this.messaging.initializedPromise;
            if (!this.discuss.isInitThreadHandled) {
                this.discuss.update({ isInitThreadHandled: true });
                if (!this.discuss.thread) {
                    this.discuss.openInitThread();
                }
            }
        });
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
