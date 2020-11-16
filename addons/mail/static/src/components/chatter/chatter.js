odoo.define('mail/static/src/components/chatter/chatter.js', function (require) {
'use strict';

const components = {
    ActivityBox: require('mail/static/src/components/activity_box/activity_box.js'),
    AttachmentBox: require('mail/static/src/components/attachment_box/attachment_box.js'),
    ChatterTopbar: require('mail/static/src/components/chatter_topbar/chatter_topbar.js'),
    Composer: require('mail/static/src/components/composer/composer.js'),
    ThreadView: require('mail/static/src/components/thread_view/thread_view.js'),
};
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');
const useUpdate = require('mail/static/src/component_hooks/use_update/use_update.js');

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
        useUpdate({ func: () => this._update() });
        /**
         * Reference of the composer. Useful to focus it.
         */
        this._composerRef = useRef('composer');
        /**
         * Reference of the message list. Useful to trigger the scroll event on it.
         */
        this._threadRef = useRef('thread');
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

    /**
     * @private
     */
    _update() {
        if (!this.chatter) {
            return;
        }
        if (this.chatter.thread) {
            this._notifyRendered();
        }
        if (this.chatter.isDoFocus) {
            this.chatter.update({ isDoFocus: false });
            const composer = this._composerRef.comp;
            if (composer) {
                composer.focus();
            }
        }
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

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onScrollPanelScroll(ev) {
        if (!this._threadRef.comp) {
            return;
        }
        this._threadRef.comp.onScroll(ev);
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
