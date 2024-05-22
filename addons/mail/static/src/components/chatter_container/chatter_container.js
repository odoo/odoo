odoo.define('mail/static/src/components/chatter_container/chatter_container.js', function (require) {
'use strict';

const components = {
    Chatter: require('mail/static/src/components/chatter/chatter.js'),
};
const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');
const useUpdate = require('mail/static/src/component_hooks/use_update/use_update.js');
const { clear } = require('mail/static/src/model/model_field_command.js');

const { Component } = owl;

/**
 * This component abstracts chatter component to its parent, so that it can be
 * mounted and receive chatter data even when a chatter component cannot be
 * created. Indeed, in order to create a chatter component, we must create
 * a chatter record, the latter requiring messaging to be initialized. The view
 * may attempt to create a chatter before messaging has been initialized, so
 * this component delays the mounting of chatter until it becomes initialized.
 */
class ChatterContainer extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.chatter = undefined;
        this._wasMessagingInitialized = false;
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const isMessagingInitialized = this.env.isMessagingInitialized();
            // Delay creation of chatter record until messaging is initialized.
            // Ideally should observe models directly to detect change instead
            // of using `useStore`.
            if (!this._wasMessagingInitialized && isMessagingInitialized) {
                this._wasMessagingInitialized = true;
                this._insertFromProps(props);
            }
            return { chatter: this.chatter };
        });
        useUpdate({ func: () => this._update() });
    }

    /**
     * @override
     */
    willUpdateProps(nextProps) {
        if (this.env.isMessagingInitialized()) {
            this._insertFromProps(nextProps);
        }
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
    _insertFromProps(props) {
        const values = Object.assign({}, props);
        if (values.threadId === undefined) {
            values.threadId = clear();
        }
        if (!this.chatter) {
            this.chatter = this.env.models['mail.chatter'].create(values);
        } else {
            this.chatter.update(values);
        }
    }

    /**
     * @private
     */
    _update() {
        if (this.chatter) {
            this.chatter.refresh();
        }
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


return ChatterContainer;

});
