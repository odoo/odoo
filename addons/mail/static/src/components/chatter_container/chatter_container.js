/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models';
// ensure components are registered beforehand.
import '@mail/components/chatter/chatter';
import { clear } from '@mail/model/model_field_command';
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component, onWillDestroy, onWillUpdateProps } = owl;

export const getChatterNextTemporaryId = (function () {
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
        this.localChatter = undefined;
        this._insertFromProps(this.props);
        onWillUpdateProps(nextProps => {
            this._insertFromProps(nextProps);
        });
        onWillDestroy(() => this.deleteLocalChatter());
    }

    get chatter() {
        return this.props.chatter || this.localChatter;
    }

    deleteLocalChatter() {
        if (this.localChatter && this.localChatter.exists()) {
            this.localChatter.delete();
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
        if (owl.status(this) === "destroyed") {
            return;
        }
        const values = { ...props };
        delete values.chatter;
        delete values.className;
        if (values.threadId === undefined) {
            values.threadId = clear();
        }
        const hasToCreateChatter = !props.chatter && !this.localChatter;
        if (hasToCreateChatter) {
            this.localChatter = messaging.models['Chatter'].insert({ id: getChatterNextTemporaryId(), ...values });
        }
        const chatter = props.chatter || this.localChatter;
        if (!hasToCreateChatter) {
            chatter.update(values);
        }
        if (owl.status(this) === "destroyed") {
            // insert might trigger a re-render which might destroy the current component
            this.deleteLocalChatter();
            return;
        }
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
        if (chatter.thread) {
            chatter.refresh();
        }
        this.render();
    }

}

Object.assign(ChatterContainer, {
    components: { Chatter: getMessagingComponent('Chatter') },
    props: {
        chatter: {
            type: Object,
            optional: true,
        },
        className: {
            type: String,
            optional: true,
        },
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
        hasParentReloadOnMessagePosted: {
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
        isInFormSheetBg: {
            type: Boolean,
            optional: true,
        },
        threadId: {
            type: Number,
            optional: true,
        },
        threadModel: String,
        webRecord: {
            type: Object,
            optional: true,
        },
        saveRecord: {
            type: Function,
            optional: true,
        }
    },
    template: 'mail.ChatterContainer',
});
