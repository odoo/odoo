odoo.define('mail/static/src/components/chatter_container/chatter_container.js', function (require) {
'use strict';

const components = {
    Chatter: require('mail/static/src/components/chatter/chatter.js'),
};
const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

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
        useModels();
    }

    mounted() {
        this._update();
    }

    patched() {
        this._update();
    }

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
     * @param {Object} props
     * @returns {Object}
     */
    _convertPropsToChatterFields(props) {
        return {
            __mfield_activityIds: props.activityIds,
            __mfield_context: props.context,
            __mfield_followerIds: props.followerIds,
            __mfield_hasActivities: props.hasActivities,
            __mfield_hasFollowers: props.hasFollowers,
            __mfield_hasMessageList: props.hasMessageList,
            __mfield_isAttachmentBoxVisible: props.isAttachmentBoxVisible,
            __mfield_messageIds: props.messageIds,
            __mfield_threadAttachmentCount: props.threadAttachmentCount,
            __mfield_threadId: props.threadId,
            __mfield_threadModel: props.threadModel,
        };
    }

    /**
     * @private
     */
    _update() {
        if (this.chatter) {
            this.chatter.update(
                this._convertPropsToChatterFields(this.props)
            );
        }
    }

}

Object.assign(ChatterContainer, {
    components,
    /**
     * No props validation because this component simply forwards props to
     * chatter record as its data.
     */
    template: 'mail.ChatterContainer',
});


return ChatterContainer;

});
