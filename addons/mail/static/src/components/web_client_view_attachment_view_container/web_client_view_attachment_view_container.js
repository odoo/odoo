/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models';
// ensure components are registered beforehand.
import '@mail/components/web_client_view_attachment_view/web_client_view_attachment_view';
import { getMessagingComponent } from '@mail/utils/messaging_component';

const { Component, onWillDestroy, onWillUpdateProps } = owl;

const getNextId = (function () {
    let tmpId = 0;
    return () => {
        tmpId += 1;
        return tmpId;
    };
})();

/**
 * This component abstracts attachment view component to its parent, so that it
 * can be mounted and receive messaging data even when an attachment view
 * component cannot be created. Indeed, in order to create an attachment view
 * component, we must create an attachment view record, the latter requiring
 * messaging to be initialized. The view may attempt to create an attachment
 * view before messaging has been initialized, so this component delays the
 * mounting of attachment view until it becomes initialized.
 */
export class WebClientViewAttachmentViewContainer extends Component {

    /**
     * @override
     */
    setup() {
        useModels();
        super.setup();
        this.webClientViewAttachmentView = undefined;
        this.webClientViewAttachmentViewId = getNextId();
        this._insertFromProps(this.props);
        onWillUpdateProps(nextProps => this._insertFromProps(nextProps));
        onWillDestroy(() => this._deleteRecord());
    }

    /**
     * @private
     */
    _deleteRecord() {
        if (this.webClientViewAttachmentView) {
            if (this.webClientViewAttachmentView.exists()) {
                this.webClientViewAttachmentView.delete();
            }
            this.webClientViewAttachmentView = undefined;
        }
    }

    /**
     * @private
     */
    async _insertFromProps(props) {
        const messaging = await this.env.services.messaging.get();
        if (owl.status(this) === "destroyed") {
            this._deleteRecord();
            return;
        }
        if (!props.threadId) {
            this._deleteRecord();
            return;
        }
        const thread = messaging.models['Thread'].insert({
            id: props.threadId,
            model: props.threadModel,
        });
        this.webClientViewAttachmentView = messaging.models['WebClientViewAttachmentView'].insert({
            id: this.webClientViewAttachmentViewId,
            thread,
        });
        this.render();
    }

}

Object.assign(WebClientViewAttachmentViewContainer, {
    components: { WebClientViewAttachmentView: getMessagingComponent('WebClientViewAttachmentView') },
    props: {
        threadId: {
            type: Number,
            optional: true,
        },
        threadModel: String,
    },
    template: 'mail.WebClientViewAttachmentViewContainer',
});
