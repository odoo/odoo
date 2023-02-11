/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { clear } from '@mail/model/model_field_command';

const { Component } = owl;

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
    constructor(...args) {
        super(...args);
        this.chatter = undefined;
        this.chatterId = getChatterNextTemporaryId();
        this._insertFromProps(this.props);
    }

    /**
     * @override
     */
    willUpdateProps(nextProps) {
        this._insertFromProps(nextProps);
        return super.willUpdateProps(...arguments);
    }

    /**
     * @override
     */
    destroy() {
        super.destroy();
        if (this.chatter) {
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
        this.chatter = messaging.models['mail.chatter'].insert(values);
        this.chatter.refresh();
        this.render();
    }

}

Object.assign(ChatterContainer, {
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

registerMessagingComponent(ChatterContainer);
