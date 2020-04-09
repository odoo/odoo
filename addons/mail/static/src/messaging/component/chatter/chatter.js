odoo.define('mail.messaging.component.Chatter', function (require) {
'use strict';

const components = {
    ActivityBox: require('mail.messaging.component.ActivityBox'),
    AttachmentBox: require('mail.messaging.component.AttachmentBox'),
    ChatterTopbar: require('mail.messaging.component.ChatterTopbar'),
    Composer: require('mail.messaging.component.Composer'),
    ThreadViewer: require('mail.messaging.component.ThreadViewer'),
};
const useStore = require('mail.messaging.component_hook.useStore');

const { Component } = owl;
const { useRef } = owl.hooks;

class Chatter extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const chatter = this.env.entities.Chatter.get(props.chatterLocalId);
            const thread = chatter ? chatter.thread : undefined;
            let attachments = [];
            if (thread) {
                attachments = thread.allAttachments;
            }
            return { attachments, chatter, thread };
        }, {
            compareDepth: {
                attachments: 1,
            },
        });
        this._threadRef = useRef('thread');
    }

    mounted() {
        if (this.chatter.thread) {
            this._notifyRendered();
        }
    }

    patched() {
        if (this.chatter.thread) {
            this._notifyRendered();
        }
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.messaging.entity.Chatter}
     */
    get chatter() {
        return this.env.entities.Chatter.get(this.props.chatterLocalId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _notifyRendered() {
        this.trigger('o-chatter-rendered', {
            attachments: this.chatter.thread.allAttachments,
            thread: this.chatter.thread.localId,
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onComposerMessagePosted() {
        this.chatter.update({ isComposerVisible: false });
    }

}

Object.assign(Chatter, {
    components,
    props: {
        chatterLocalId: String,
    },
    template: 'mail.messaging.component.Chatter',
});

return Chatter;

});
