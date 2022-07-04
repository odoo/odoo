/** @odoo-module **/

import { ChatterContainer } from '@mail/components/chatter_container/chatter_container';
import { AttachmentViewer } from '@mail/widgets/attachment_viewer/attachment_viewer';

import dom from 'web.dom';
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
        this.isChatterInSheet = false;
        this.hasAttachmentViewerFeature = params.hasAttachmentViewerFeature;
        this.chatterFields = params.chatterFields;
        this.mailFields = params.mailFields;
        this.messaging = undefined;
        if (owl.Component.env.services.messaging) {
            owl.Component.env.services.messaging.get().then(messaging => this.messaging = messaging);
        }
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
        this.attachmentViewer = undefined;
        this.attachmentViewerTarget = undefined;
        if (this.hasAttachmentViewerFeature) {
            this.attachmentViewerTarget = document.createElement("div");
            this.attachmentViewerTarget.classList.add("o_attachment_preview");
        }
        this.attachmentViewerTargetPlaceholder = undefined;
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
        if (node.tag === 'div' && node.attrs.class === 'o_attachment_preview') {
            if (!this.hasAttachmentViewerFeature) {
                return document.createElement("div");
            }
            this._registerModifiers(node, this.state, $(this.attachmentViewerTarget)); // support for groups= on the node
            this.attachmentViewerTargetPlaceholder = this.attachmentViewerTarget.cloneNode(false);
            return this.attachmentViewerTargetPlaceholder;
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
        if (this.hasAttachmentViewerFeature) {
            this.attachmentViewerTarget.remove();
        }
        this._super(...arguments);
        if (this.hasAttachmentViewerFeature) {
            this.attachmentViewerTargetPlaceholder.replaceWith(this.attachmentViewerTarget);
        }
        if (this.hasChatter) {
            this.chatterContainerTargetPlaceholder.replaceWith(this._chatterContainerTarget);
            // isChatterInSheet can only be written from this specific life-cycle method because the
            // parentNode is not accessible before the target node is actually in DOM. Ideally this
            // should be determined statically in `_processNode` but the parent is not provided.
            this.isChatterInSheet = this._chatterContainerTarget.parentNode.classList.contains('o_form_sheet');
            this._interchangeChatter();
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
     * Interchange the position of the chatter and the attachment preview.
     *
     * @private
     */
    _interchangeChatter() {
        const $sheetBg = this.$('.o_form_sheet_bg');
        this._updateChatterContainerTarget();
        if (this._isChatterAside()) {
            $(this._chatterContainerTarget).insertAfter($sheetBg);
        } else if (this.isChatterInSheet) {
            const $sheet = this.$('.o_form_sheet');
            dom.append($sheet, $(this._chatterContainerTarget));
        } else {
            dom.append($sheetBg, $(this._chatterContainerTarget));
        }
        if (this.hasAttachmentViewer()) {
            $(this.attachmentViewerTarget).insertAfter($sheetBg);
        } else {
            dom.append($sheetBg, $(this.attachmentViewerTarget));
        }
        this._updateChatterContainerComponent();
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
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data
     * @param {Attachment[]} ev.data.attachments
     * @param {Thread} ev.data.thread
     */
    _onChatterRendered(ev) {
        if (!this.hasAttachmentViewer()) {
            if (this.attachmentViewer) {
                this.attachmentViewer.destroy();
                this.attachmentViewer = undefined;
                this._interchangeChatter();
            }
            return;
        }
        var self = this;
        const thread = this.messaging.models['Thread'].insert({
            id: this.state.res_id,
            model: this.state.model,
        });
        if (thread.attachmentsInWebClientView.length || this.attachmentViewer) {
            if (this.attachmentViewer) {
                // FIXME should be improved : what if somehow an attachment is replaced in a thread ?
                if (
                    this.attachmentViewer.thread !== thread ||
                    this.attachmentViewer.attachments.length !== thread.attachmentsInWebClientView.length
                ) {
                    if (thread.attachmentsInWebClientView.length) {
                        this.attachmentViewer.updateContents(thread);
                    }
                } else {
                    // The attachmentViewer lose its event listeners when it is reused,
                    // we just need to reregister them.
                    if (this.attachmentViewer.$el) {
                        this.attachmentViewer._undelegateEvents();
                        this.attachmentViewer._delegateEvents();
                    }
                }
                this.trigger_up('preview_attachment_validation');
                this._updateChatterContainerTarget();
            } else {
                this.attachmentViewer = new AttachmentViewer(this, thread);
                this.attachmentViewer.appendTo($(this.attachmentViewerTarget)).then(function () {
                    self.trigger_up('preview_attachment_validation');
                    self._interchangeChatter();
                });
            }
        }
    },
});
