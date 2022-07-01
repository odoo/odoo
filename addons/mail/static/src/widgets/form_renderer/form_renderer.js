/** @odoo-module **/

import { ChatterContainer } from '@mail/components/chatter_container/chatter_container';

import FormRenderer from 'web.FormRenderer';
import { ComponentWrapper } from 'web.OwlCompatibility';

class ChatterContainerWrapperComponent extends ComponentWrapper {}

/**
 * Include the FormRenderer to instantiate the chatter area containing (a
 * subset of) the mail widgets (mail_thread, mail_followers and mail_activity).
 */
FormRenderer.include({
    //--------------------------------------------------------------------------
    // Form Overrides
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    init(parent, state, params) {
        this._super(...arguments);
        this.hasChatter = params.hasChatter && !params.isFromFormViewDialog;
        this.chatterFields = params.chatterFields;
        this.mailFields = params.mailFields;
        this._chatterContainerComponent = undefined;
        /**
         * The target of chatter, if chatter has to be appended to the DOM.
         * This is set when arch contains `div.oe_chatter`.
         */
        this._chatterContainerTarget = undefined;
        if (this.hasChatter) {
            this._chatterContainerTarget = document.createElement("div");
            this._chatterContainerTarget.classList.add("o_FormRenderer_chatterContainer");
            this.initChatter();
        }
        /**
         * This element will be set when rendering the form view, and
         * used as a hook to insert the ChatterContainer in the right place,
         * when applying the rendering into the DOM.
         */
        this.chatterContainerTargetPlaceholder = undefined;
        this.on('o_chatter_rendered', this, ev => this._onChatterRendered(ev));
    },
    async initChatter() {
        this._chatterContainerComponent = new ChatterContainerWrapperComponent(
            this,
            ChatterContainer,
            this._makeChatterContainerProps(),
        );
        await this._chatterContainerComponent.mount(this._chatterContainerTarget);
    },
    /**
     * @override
     */
    _renderNode(node) {
        if (node.tag === 'div' && node.attrs.class === 'oe_chatter') {
            if (!this.hasChatter) {
                return document.createElement("div");
            }
            this.chatterContainerTargetPlaceholder = this._chatterContainerTarget.cloneNode(false);
            return this.chatterContainerTargetPlaceholder;
        }
        return this._super(...arguments);
    },
    /**
     * Overrides to re-render the chatter container with potentially new props.
     * This is done in `__renderView` specifically to wait for this render to
     * be complete before updating the form view, which prevents flickering.
     *
     * @override
     */
    async __renderView() {
        await this._super(...arguments);
        if (this.hasChatter) {
            await this._updateChatterContainerComponent();
        }
    },
    /**
     * The last rendering of the form view has just been applied into the DOM,
     * so we replace our chatter container hook by the actual chatter container.
     *
     * @override
     */
    _updateView() {
        /**
         * The chatter is detached before it's removed on the super._updateView function,
         * this is done to avoid losing the event handlers.
         */
        if (this.hasChatter) {
            this._chatterContainerTarget.remove();
        }
        this._super(...arguments);
        if (this.hasChatter) {
            this.chatterContainerTargetPlaceholder.replaceWith(this._chatterContainerTarget);
            this._updateChatterContainerTarget();
        }
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        this._chatterContainerComponent = undefined;
        this.off('o_chatter_rendered', this);
    },

    //--------------------------------------------------------------------------
    // Mail Methods
    //--------------------------------------------------------------------------

    /**
     * @returns {boolean}
     */
    hasAttachmentViewer() {
        return false;
    },
    /**
     * @private
     * @returns {boolean}
     */
    _isChatterAside() {
        return false;
    },
    /**
     * @private
     * @returns {Object}
     */
    _makeChatterContainerProps() {
        const isChatterAside = this._isChatterAside();
        return {
            hasActivities: this.chatterFields.hasActivityIds,
            hasExternalBorder: !isChatterAside,
            hasFollowers: this.chatterFields.hasMessageFollowerIds,
            hasMessageList: this.chatterFields.hasMessageIds,
            hasMessageListScrollAdjust: isChatterAside,
            hasParentReloadOnAttachmentsChanged: this.chatterFields.hasRecordReloadOnAttachmentsChanged,
            hasParentReloadOnFollowersUpdate: this.chatterFields.hasRecordReloadOnFollowersUpdate,
            hasParentReloadOnMessagePosted: this.chatterFields.hasRecordReloadOnMessagePosted,
            isAttachmentBoxVisibleInitially: this.chatterFields.isAttachmentBoxVisibleInitially,
            isInFormSheetBg: this.hasAttachmentViewer(),
            threadId: this.state.res_id,
            threadModel: this.state.model,
        };
    },
    /**
     * @private
     */
    async _updateChatterContainerComponent() {
        const props = this._makeChatterContainerProps();
        try {
            await this._chatterContainerComponent.update(props);
        } catch (error) {
            if (error.message !== "Mounting operation cancelled") {
                throw error;
            }
        }
    },
    /**
     * Add a class to allow styling of chatter depending on the fact is is
     * printed aside or underneath the form sheet.
     *
     * @private
     */
    _updateChatterContainerTarget() {
        if (this._isChatterAside()) {
            this._chatterContainerTarget.classList.add('o-aside');
        } else {
            this._chatterContainerTarget.classList.remove('o-aside');
        }
        if (this.hasAttachmentViewer()) {
            this._chatterContainerTarget.classList.add('o-isInFormSheetBg');
        } else {
            this._chatterContainerTarget.classList.remove('o-isInFormSheetBg');
        }
    },
    /**
     * @abstract
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data
     * @param {Attachment[]} ev.data.attachments
     * @param {Thread} ev.data.thread
     */
    _onChatterRendered(ev) {},
});
