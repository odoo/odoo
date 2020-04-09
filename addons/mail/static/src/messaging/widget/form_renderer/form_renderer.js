odoo.define('mail.messaging.widget.FormRenderer', function (require) {
"use strict";

const components = {
    ChatterContainer: require('mail.messaging.component.ChatterContainer'),
};

const FormRenderer = require('web.FormRenderer');
const { ComponentWrapper } = require('web.OwlCompatibility');

class ChatterContainerWrapperComponent extends ComponentWrapper {}

/**
 * Include the FormRenderer to instantiate the chatter area containing (a
 * subset of) the mail widgets (mail_thread, mail_followers and mail_activity).
 */
FormRenderer.include({
    /**
     * @override
     */
    init(parent, state, params) {
        this._super(...arguments);
        this.env = this.call('messaging', 'getEnv');
        this.mailFields = params.mailFields;
        this._chatterContainerComponent = undefined;
        /**
         * The target of chatter, if chatter has to be appended to the DOM.
         * This is set when arch contains `div.oe_chatter`.
         */
        this._chatterContainerTarget = undefined;
        // Do not load chatter in form view dialogs
        this._isFromFormViewDialog = params.isFromFormViewDialog;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Destroy the chatter component
     *
     * @private
     */
    _destroyChatterContainer() {
        if (this._chatterContainerComponent) {
            this._chatterContainerComponent.destroy();
            this._chatterContainerComponent.parentWidget.off('o_chatter_rendered', this);
            this._chatterContainerComponent = undefined;
        }
    },
    /**
     * Returns whether the form renderer has a chatter to display or not.
     * This is based on arch, which should have `div.oe_chatter`.
     *
     * @private
     * @returns {boolean}
     */
    _hasChatter() {
        return !!this._chatterContainerTarget;
    },
    /**
     * @private
     */
    _makeChatterContainerComponent() {
        const props = this._makeChatterContainerProps();
        this._chatterContainerComponent = new ChatterContainerWrapperComponent(
            this,
            components.ChatterContainer,
            props
        );
        // Not in custom_events because other modules may remove this listener
        // while attempting to extend them.
        this._chatterContainerComponent.parentWidget.on('o_chatter_rendered', this, ev => this._onChatterRendered(ev));
    },
    /**
     * @private
     * @returns {Object}
     */
    _makeChatterContainerProps() {
        const context = this.record ? this.record.getContext() : {};
        const activityIds = this.state.data.activity_ids
            ? this.state.data.activity_ids.res_ids
            : [];
        const followerIds = this.state.data.message_follower_ids
            ? this.state.data.message_follower_ids.res_ids
            : [];
        const messageIds = this.state.data.message_ids
            ? this.state.data.message_ids.res_ids
            : [];
        const threadAttachmentCount = this.state.data.message_attachment_count || 0;
        return {
            activityIds,
            context,
            followerIds,
            hasActivities: !!this.mailFields.mail_activity,
            hasFollowers: !!this.mailFields.mail_followers,
            hasThread: !!this.mailFields.mail_thread,
            messageIds,
            threadAttachmentCount,
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
        await this._chatterContainerComponent.mount(this._chatterContainerTarget);
    },
    /**
     * @override
     */
    _renderNode(node) {
        if (
            !this._isFromFormViewDialog &&
            node.tag === 'div' &&
            node.attrs.class === 'oe_chatter'
        ) {
            const $el = $('<div class="o_FormRenderer_chatterContainer"/>');
            this._chatterContainerTarget = $el[0];
            return $el;
        }
        return this._super(...arguments);
    },
    /**
     * Overrides the function to render the chatter once the form view is
     * rendered.
     *
     * @override
     */
    async _renderView() {
        await this._super(...arguments);
        if (this._hasChatter()) {
            ChatterContainerWrapperComponent.env = this.env;
            if (!this._chatterContainerComponent) {
                this._makeChatterContainerComponent();
            } else {
                this._updateChatterContainerComponent();
            }
            await this._mountChatterContainerComponent();
        }
    },
    /**
     * @private
     */
    _updateChatterContainerComponent() {
        const props = this._makeChatterContainerProps();
        this._chatterContainerComponent.update(props);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @abstract
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data
     * @param {mail.messaging.entity.Attachment[]} ev.data.attachments
     * @param {mail.messaging.entity.Thread} ev.data.thread
     */
    _onChatterRendered(ev) {},
});

});
