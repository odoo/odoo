/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { isEventHandled, markEventHandled } from '@mail/utils/utils';
import { processDomTransformation } from '@mail/js/utils';
import { useRefs } from '@mail/component_hooks/use_refs/use_refs';

import { useListener } from 'web.custom_hooks';
import { getLangDatetimeFormat } from 'web.time';

const { Component, useState } = owl;
const { useRef } = owl.hooks;

export class Message extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.state = useState({
            /**
             * Determine whether the message is hovered. When message is hovered
             * it displays message actions.
             */
             isHovered: false,
            /**
             * Determine whether the message is clicked. When message is in
             * clicked state, it keeps displaying actions even if not hovered.
             */
            isClicked: false,
        });
        useUpdate({ func: () => this._update() });
        
        /**
         * References to the contents of the message.
         */
        this._authorRef = useRef('author');
        this._prettyBodyRef = useRef('prettyBody');
        this._subjectRef = useRef('subject')
        this._subtypeDescriptionRef = useRef('subtype_description')
        this._trackingValuesRef = useRef('tracking_values');

        /**
         * All refs to handle the dynamic tracking value refs.
         */
        this._getRefs = useRefs();

        /**
         * Keeps a cache of all the content to display to know if it needs to be 
         * updated or not. 
         */
        this._contentCache = {}

        /**
         * To get checkbox state.
         */
        this._checkboxRef = useRef('checkbox');
        /**
         * Id of setInterval used to auto-update time elapsed of message at
         * regular time.
         */
        this._intervalId = undefined;

        useListener("click", "[data-read-more-hash]", this._onReadMoreClicked);
        useListener("click", "[data-read-less-hash]", this._onReadLessClicked);

        this._constructor();
    }

    /**
     * Allows patching constructor.
     */
    _constructor() {}

    willUnmount() {
        clearInterval(this._intervalId);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {string}
     */
    get avatar() {
        if (this.message.author && (!this.message.originThread || this.message.originThread.model !== 'mail.channel')) {
            // TODO FIXME for public user this might not be accessible. task-2223236
            // we should probably use the correspondig attachment id + access token
            // or create a dedicated route to get message image, checking the access right of the message
            return this.message.author.avatarUrl;
        } else if (this.message.author && this.message.originThread && this.message.originThread.model === 'mail.channel') {
            return `/mail/channel/${this.message.originThread.id}/partner/${this.message.author.id}/avatar_128`;
        } else if (this.message.guestAuthor && (!this.message.originThread || this.message.originThread.model !== 'mail.channel')) {
            return this.message.guestAuthor.avatarUrl;
        } else if (this.message.guestAuthor && this.message.originThread && this.message.originThread.model === 'mail.channel') {
            return `/mail/channel/${this.message.originThread.id}/guest/${this.message.guestAuthor.id}/avatar_128`;
        } else if (this.message.message_type === 'email') {
            return '/mail/static/src/img/email_icon.png';
        }
        return '/mail/static/src/img/smiley/avatar.jpg';
    }

    /**
     * Get the date time of the message at current user locale time.
     *
     * @returns {string}
     */
    get datetime() {
        return this.message.date.format(getLangDatetimeFormat());
    }

    /**
     * Determines whether author open chat feature is enabled on message.
     *
     * @returns {boolean}
     */
    get hasAuthorOpenChat() {
        if (this.messaging.currentGuest) {
            return false;
        }
        if (!this.message.author) {
            return false;
        }
        if (
            this.threadView &&
            this.threadView.thread &&
            this.threadView.thread.correspondent === this.message.author
        ) {
            return false;
        }
        return true;
    }

    /**
     * Whether the message is "active", ie: hovered or clicked, and should
     * display additional things (date in sidebar, message actions, etc.)
     *
     * @returns {boolean}
     */
    get isActive() {
        return Boolean(
            this.state.isHovered ||
            this.state.isClicked ||
            (this.message && this.message.actionList.isReactionPopoverOpened)
        );
    }

    /**
     * Tell whether the bottom of this message is visible or not.
     *
     * @param {Object} param0
     * @param {integer} [offset=0]
     * @returns {boolean}
     */
    isBottomVisible({ offset=0 } = {}) {
        if (!this.el) {
            return false;
        }
        const elRect = this.el.getBoundingClientRect();
        if (!this.el.parentNode) {
            return false;
        }
        const parentRect = this.el.parentNode.getBoundingClientRect();
        // bottom with (double) 10px offset
        return (
            elRect.bottom < parentRect.bottom + offset &&
            parentRect.top < elRect.bottom + offset
        );
    }

    /**
     * Tell whether the message is partially visible on browser window or not.
     *
     * @returns {boolean}
     */
    isPartiallyVisible() {
        const elRect = this.el.getBoundingClientRect();
        if (!this.el.parentNode) {
            return false;
        }
        const parentRect = this.el.parentNode.getBoundingClientRect();
        // intersection with 5px offset
        return (
            elRect.top < parentRect.bottom + 5 &&
            parentRect.top < elRect.bottom + 5
        );
    }

    /**
     * Tell whether the message is selected in the current thread viewer.
     *
     * @returns {boolean}
     */
    get isSelected() {
        return (
            this.threadView &&
            this.threadView.threadViewer &&
            this.threadView.threadViewer.selectedMessage === this.message
        );
    }

    /**
     * @returns {mail.message}
     */
    get message() {
        return this.messaging && this.messaging.models['mail.message'].get(this.props.messageLocalId);
    }
    /**
     * @returns {string}
     */
    get OPEN_CHAT() {
        return this.env._t("Open chat");
    }

    /**
     * Make this message viewable in its enclosing scroll environment (usually
     * message list).
     *
     * @param {Object} [param0={}]
     * @param {string} [param0.behavior='auto']
     * @param {string} [param0.block='end']
     * @returns {Promise}
     */
    async scrollIntoView({ behavior = 'auto', block = 'end' } = {}) {
        this.el.scrollIntoView({
            behavior,
            block,
            inline: 'nearest',
        });
        if (behavior === 'smooth') {
            return new Promise(resolve => setTimeout(resolve, 500));
        } else {
            return Promise.resolve();
        }
    }

    /**
     * Get the shorttime format of the message date.
     *
     * @returns {string}
     */
    get shortTime() {
        return this.message.date.format('hh:mm');
    }

    /**
     * @returns {mail.thread_view}
     */
    get threadView() {
        return this.messaging && this.messaging.models['mail.thread_view'].get(this.props.threadViewLocalId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _onReadLessClicked(ev) {
        const hash = ev.target.dataset.readLessHash;
        this.message.collapseCollapsableContentByHash(hash);
    }

    _onReadMoreClicked(ev) {
        const hash = ev.target.dataset.readMoreHash;
        this.message.expandCollapsableContentByHash(hash);
    }

    /**
     * @private
     */
    _update() {
        if (!this.message) {
            return;
        }
        
        if (this._authorRef.el) {
            if (this._contentCache["author"] !== this.message.prettyAuthor) {
                this._contentCache["author"] = this.message.prettyAuthor
                this._authorRef.el.innerHTML = this.message.prettyAuthor;
            }
        }
        if (!this._authorRef.el) {
            this._contentCache["author"] = undefined;
        }
        if (this._prettyBodyRef.el) {
            if (this._contentCache["body"] !== this.message.prettyBody) {
                this._contentCache["body"] = this.message.prettyBody
                this._prettyBodyRef.el.innerHTML = this.message.prettyBody;
            }
        }
        if (!this._prettyBodyRef.el) {
            this._contentCache["body"] = undefined;
        }
        if (this._subjectRef.el) {
            if (this._contentCache["subject"] !== this.message.prettySubject) {
                this._contentCache["subject"] = this.message.prettySubject
                this._subjectRef.el.innerHTML = this.message.prettySubject;
            }
        }
        if (!this._subjectRef.el) {
            this._contentCache["subject"] = undefined;
        }
        if (this._subtypeDescriptionRef.el) {
            if (this._contentCache["subtype-description"] !== this.message.prettySubtypeDescription) {
                this._contentCache["subtype-description"] = this.message.prettySubtypeDescription
                this._subtypeDescriptionRef.el.innerHTML = this.message.prettySubtypeDescription;
            }
        }
        if (!this._subtypeDescriptionRef.el) {
            this._contentCache["subtype-description"] = undefined;
        }
     
        const refs = this._getRefs();
        for (const key in refs) {
            if (key.startsWith("tracking_value_")) {
                const trackingValueId = key.split("_").slice(-1).pop(); // keep only last item, which is the id
                const trackingValueIdType = key.includes('new_value') ? 'new' : (key.includes('old_value') ? 'old' : 'changed_field');
                const valueToDisplay = this.message.prettyTrackingValues[trackingValueId][trackingValueIdType];
                if (this._contentCache[key] !== valueToDisplay) {
                    this._contentCache[key] = valueToDisplay;
                    refs[key].innerHTML = valueToDisplay;
                }
            }
        }

        this.message.refreshDateFromNow();
        clearInterval(this._intervalId);
        this._intervalId = setInterval(() => {
            this.message.refreshDateFromNow();
        }, 60 * 1000);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        if (ev.target.closest('.o_channel_redirect')) {
            this.messaging.openProfile({
                id: Number(ev.target.dataset.oeId),
                model: 'mail.channel',
            });
            // avoid following dummy href
            ev.preventDefault();
            return;
        }
        if (ev.target.tagName === 'A') {
            if (ev.target.dataset.oeId && ev.target.dataset.oeModel) {
                this.messaging.openProfile({
                    id: Number(ev.target.dataset.oeId),
                    model: ev.target.dataset.oeModel,
                });
                // avoid following dummy href
                ev.preventDefault();
            }
            return;
        }
        if (
            !isEventHandled(ev, 'Message.ClickAuthorAvatar') &&
            !isEventHandled(ev, 'Message.ClickAuthorName') &&
            !isEventHandled(ev, 'Message.ClickFailure') &&
            !isEventHandled(ev, 'MessageActionList.Click') &&
            !isEventHandled(ev, 'MessageReactionGroup.Click')
        ) {
            this.state.isClicked = !this.state.isClicked;
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAuthorAvatar(ev) {
        markEventHandled(ev, 'Message.ClickAuthorAvatar');
        if (!this.hasAuthorOpenChat) {
            return;
        }
        this.message.author.openChat();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAuthorName(ev) {
        markEventHandled(ev, 'Message.ClickAuthorName');
        if (!this.message.author) {
            return;
        }
        this.message.author.openProfile();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickFailure(ev) {
        markEventHandled(ev, 'Message.ClickFailure');
        this.message.openResendAction();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickOriginThread(ev) {
        // avoid following dummy href
        ev.preventDefault();
        this.message.originThread.open();
    }
}

Object.assign(Message, {
    defaultProps: {
        hasMarkAsReadIcon: false,
        hasReplyIcon: false,
        isSquashed: false,
        showActions: true,
    },
    props: {
        attachmentsDetailsMode: {
            type: String,
            optional: true,
            validate: prop => ['auto', 'card', 'hover', 'none'].includes(prop),
        },
        hasMarkAsReadIcon: Boolean,
        hasReplyIcon: Boolean,
        isSquashed: Boolean,
        messageLocalId: String,
        threadViewLocalId: {
            type: String,
            optional: true,
        },
        showActions: Boolean,
    },
    template: 'mail.Message',
});

registerMessagingComponent(Message);
