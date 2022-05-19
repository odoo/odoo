/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models';
import { useUpdate } from '@mail/component_hooks/use_update';
// ensure component is registered before-hand
import '@mail/components/discuss/discuss';
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component, onWillDestroy } = owl;

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
        onWillDestroy(() => this._willDestroy());
        /**
         * When executing the discuss action while it's already opened, the
         * action manager first mounts the newest DiscussContainer, then
         * unmounts the oldest one. The issue is that messaging.discussView is
         * updated on setup but is cleared during the unmount. This leads to
         * errors because there is no discussView anymore. In order to handle
         * this situation, let's keep a reference to the currentInstance so that
         * we can check we're deleting the discussView only when there is no
         * incoming DiscussContainer.
         */
        DiscussContainer.currentInstance = this;
    }

    _update() {
        if (!this.messaging || !this.messaging.discuss) {
            return;
        }
        this.messaging.discuss.open();
    }

    _willDestroy() {
        if (this.messaging && this.messaging.discuss && DiscussContainer.currentInstance === this) {
            this.messaging.discuss.close();
        }
    }

}

Object.assign(DiscussContainer, {
    components: { Discuss: getMessagingComponent('Discuss') },
    template: 'mail.DiscussContainer',
});
