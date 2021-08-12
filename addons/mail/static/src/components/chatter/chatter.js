/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models/use_models';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { ActivityBox } from '@mail/components/activity_box/activity_box';
import { AttachmentBox } from '@mail/components/attachment_box/attachment_box';
import { ChatterTopbar } from '@mail/components/chatter_topbar/chatter_topbar';
import { Composer } from '@mail/components/composer/composer';
import { ThreadView } from '@mail/components/thread_view/thread_view';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';

const { Component } = owl;
const { useRef } = owl.hooks;

const components = {
    ActivityBox,
    AttachmentBox,
    ChatterTopbar,
    Composer,
    ThreadView,
};

export class Chatter extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useModels();
        useUpdate({ func: () => this._update() });
        useRefToModel({ fieldName: 'threadRef', modelName: 'mail.chatter', propNameAsRecordLocalId: 'chatterLocalId', refName: 'thread' });
        /**
         * Reference of the composer. Useful to focus it.
         */
        this._composerRef = useRef('composer');
        /**
         * Reference of the scroll Panel (Real scroll element). Useful to pass the Scroll element to
         * child component to handle proper scrollable element.
         */
        this._scrollPanelRef = useRef('scrollPanel');
        /**
         * Reference of the message list. Useful to trigger the scroll event on it.
         */
        this._threadRef = useRef('thread');
        this.getScrollableElement = this.getScrollableElement.bind(this);
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

    /**
     * @returns {Element|undefined} Scrollable Element
     */
    getScrollableElement() {
        if (!this._scrollPanelRef.el) {
            return;
        }
        return this._scrollPanelRef.el;
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

}

Object.assign(Chatter, {
    components,
    props: {
        chatterLocalId: String,
    },
    template: 'mail.Chatter',
});
