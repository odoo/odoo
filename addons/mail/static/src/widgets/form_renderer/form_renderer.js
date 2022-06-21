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
        }
        /**
         * This element will be set when rendering the form view, and
         * used as a hook to insert the ChatterContainer in the right place,
         * when applying the rendering into the DOM.
         */
        this.chatterContainerTargetPlaceholder = undefined;
    },
    /**
     * @override
     */
    _renderNode(node) {
        if (node.tag === 'div' && node.attrs.class === 'oe_chatter') {
            if (!this.hasChatter) {
                return $('<div/>');
            }
            this.chatterContainerTargetPlaceholder = this._chatterContainerTarget.cloneNode(false);
            return this.chatterContainerTargetPlaceholder;
        }
        return this._super(...arguments);
    },
    /**
     * Overrides the function to render the chatter once the form view is
     * rendered.
     *
     * @override
     */
    async __renderView() {
        await this._super(...arguments);
        if (this.hasChatter) {
            if (!this._chatterContainerComponent) {
                this._makeChatterContainerComponent();
            } else {
                return this._updateChatterContainerComponent();
            }
            await this._mountChatterContainerComponent();
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
     * @private
     * @returns {boolean}
     */
    _isChatterAside() {
        return false;
    },
    /**
     * @private
     */
    _makeChatterContainerComponent() {
        const props = this._makeChatterContainerProps();
        this._chatterContainerComponent = new ChatterContainerWrapperComponent(
            this,
            ChatterContainer,
            props
        );
        // Not in custom_events because other modules may remove this listener
        // while attempting to extend them.
        this.on('o_chatter_rendered', this, ev => this._onChatterRendered(ev));
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
            threadId: this.state.res_id,
            threadModel: this.state.model,
        };
    },
    /**
     * Mount the chatter
     *
     * Force re-mounting chatter component in DOM. This is necessary
     * because each time `_renderView` is called, it puts old content
     * in a fragment.
     *
     * @private
     */
    async _mountChatterContainerComponent() {
        try {
            await this._chatterContainerComponent.mount(this._chatterContainerTarget);
        } catch (error) {
            if (error.message !== "Mounting operation cancelled") {
                throw error;
            }
        }
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
            $(this._chatterContainerTarget).addClass('o-aside');
        } else {
            $(this._chatterContainerTarget).removeClass('o-aside');
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
