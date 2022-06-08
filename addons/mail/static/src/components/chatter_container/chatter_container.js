/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models';
// ensure components are registered beforehand.
import '@mail/components/chatter/chatter';
import { clear } from '@mail/model/model_field_command';
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component, onWillDestroy, onWillUpdateProps } = owl;

const getChatterNextTemporaryId = (function () {
    let tmpId = 0;
    return () => {
        tmpId += 1;
        return tmpId;
    };
})();

/**
 * This component abstracts chatter component to its parent, so that it can be
 * mounted and receive chatter data even when a chatter component cannot be
 * created. Indeed, in order to create a chatter component, we must create
 * a chatter record, the latter requiring messaging to be initialized. The view
 * may attempt to create a chatter before messaging has been initialized, so
 * this component delays the mounting of chatter until it becomes initialized.
 */
export class ChatterContainer extends Component {

    /**
     * @override
     */
    setup() {
        useModels();
        super.setup();
        this.chatter = undefined;
        this.chatterId = getChatterNextTemporaryId();
        this._insertFromProps(this.props);
        onWillUpdateProps(nextProps => this._willUpdateProps(nextProps));
        onWillDestroy(this._onWillDestroy);
    }

    _willUpdateProps(nextProps) {
        this._insertFromProps(nextProps);
    }

    /**
     * @override
     */
    _onWillDestroy() {
        if (this.chatter && this.chatter.exists()) {
            this.chatter.delete();
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    async _insertFromProps(props) {
        const messaging = await this.env.services.messaging.get();
        if (this.__owl__.status === 5 /* destroyed */) {
            return;
        }
        const values = { id: this.chatterId, ...props };
        if (values.threadId === undefined) {
            values.threadId = clear();
        }
        this.chatter = messaging.models['Chatter'].insert(values);
        /**
         * Refresh the chatter when the parent view is (re)loaded.
         * This serves mainly at loading initial data, but also on reload there
         * might be new message, new attachment, ...
         *
         * For example in approvals this is currently necessary to fetch the
         * newly added attachment when using the "Attach Document" button. And
         * in sales it is necessary to see the email when using the "Send email"
         * button.
         *
         * NOTE: this assumes props are actually changed when a reload of parent
         * happens which is true so far because of the OWL compatibility layer
         * calling the props change method but it is in general not a good
         * assumption to make.
         */
        this.chatter.refresh();
        this.render();
    }

}

Object.assign(ChatterContainer, {
    components: { Chatter: getMessagingComponent('Chatter') },
    props: {
        hasActivities: {
            type: Boolean,
            optional: true,
        },
        hasExternalBorder: {
            type: Boolean,
            optional: true,
        },
        hasFollowers: {
            type: Boolean,
            optional: true,
        },
        hasMessageList: {
            type: Boolean,
            optional: true,
        },
        hasMessageListScrollAdjust: {
            type: Boolean,
            optional: true,
        },
        hasParentReloadOnAttachmentsChanged: {
            type: Boolean,
            optional: true,
        },
        hasParentReloadOnFollowersUpdate: {
            type: Boolean,
            optional: true,
        },
        hasTopbarCloseButton: {
            type: Boolean,
            optional: true,
        },
        isAttachmentBoxVisibleInitially: {
            type: Boolean,
            optional: true,
        },
        threadId: {
            type: Number,
            optional: true,
        },
        threadModel: String,
    },
    template: 'mail.ChatterContainer',
});
