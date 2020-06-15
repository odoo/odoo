odoo.define('mail/static/src/components/chatter/chatter.js', function (require) {
'use strict';

const components = {
    ActivityBox: require('mail/static/src/components/activity_box/activity_box.js'),
    AttachmentBox: require('mail/static/src/components/attachment_box/attachment_box.js'),
    ChatterTopbar: require('mail/static/src/components/chatter_topbar/chatter_topbar.js'),
    Composer: require('mail/static/src/components/composer/composer.js'),
    ThreadViewer: require('mail/static/src/components/thread_viewer/thread_viewer.js'),
};
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;
const { useRef } = owl.hooks;

class Chatter extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const chatter = this.env.models['mail.chatter'].get(props.chatterLocalId);
            const thread = chatter ? chatter.thread : undefined;
            let attachments = [];
            if (thread) {
                attachments = thread.allAttachments;
            }
            return {
                attachments: attachments.map(attachment => attachment.__state),
                chatter: chatter ? chatter.__state : undefined,
                thread: thread ? thread.__state : undefined,
            };
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
     * @returns {mail.chatter}
     */
    get chatter() {
        return this.env.models['mail.chatter'].get(this.props.chatterLocalId);
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
    template: 'mail.Chatter',
});

return Chatter;

});
