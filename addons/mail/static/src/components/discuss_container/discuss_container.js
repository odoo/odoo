/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models';
// ensure component is registered before-hand
import '@mail/components/discuss/discuss';
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component, onWillDestroy } = owl;

export class DiscussContainer extends Component {

    /**
     * @override
     */
    setup() {
        useModels();
        super.setup();
        onWillDestroy(() => this._willDestroy());
        this.env.services.messaging.modelManager.messagingCreatedPromise.then(async () => {
            const { action } = this.props;
            const initActiveId =
                (action.context && action.context.active_id) ||
                (action.params && action.params.default_active_id) ||
                'mail.box_inbox';
            this.discuss = this.messaging.discuss;
            this.discuss.update({
                discussView: {
                    actionId: action.id,
                },
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
        /**
         * When executing the discuss action while it's already opened, the
         * action manager first mounts the newest DiscussContainer, then
         * unmounts the oldest one. The issue is that messaging.discussView is
         * updated on setup but is cleared on destroy. This leads to
         * errors because there is no discussView anymore. In order to handle
         * this situation, let's keep a reference to the currentInstance so that
         * we can check we're deleting the discussView only when there is no
         * incoming DiscussContainer.
         */
        DiscussContainer.currentInstance = this;
    }

    get messaging() {
        return this.env.services.messaging.modelManager.messaging;
    }

    _willDestroy() {
        if (this.discuss && DiscussContainer.currentInstance === this) {
            this.discuss.close();
        }
    }

}

Object.assign(DiscussContainer, {
    props: {
        action: Object,
        actionId: { type: Number, optional: 1 },
        className: String,
        globalState: { type: Object, optional: 1 },
    },
    components: { Discuss: getMessagingComponent('Discuss') },
    template: 'mail.DiscussContainer',
});
