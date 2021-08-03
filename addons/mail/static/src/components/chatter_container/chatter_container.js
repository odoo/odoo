/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models/use_models';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { Chatter } from '@mail/components/chatter/chatter';
import { clear } from '@mail/model/model_field_command';

const { Component } = owl;

const components = { Chatter };

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
        useModels();
        useShouldUpdateBasedOnProps();
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
        await this.env.messagingCreatedPromise;
        await this.env.messaging.initializedPromise;
        if (this.__owl__.status === 5 /* destroyed */) {
            return;
        }
        const values = Object.assign({}, props);
        if (values.threadId === undefined) {
            values.threadId = clear();
        }
        if (!this.chatter) {
            this.chatter = this.env.models['mail.chatter'].create(values);
        } else {
            this.chatter.update(values);
        }
        this.chatter.refresh();
        this.render();
    }

}

Object.assign(ChatterContainer, {
    components,
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
