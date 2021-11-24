/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { isEventHandled, markEventHandled } from '@mail/utils/utils';

import { _lt } from 'web.core';
import { format } from 'web.field_utils';
import { getLangDatetimeFormat } from 'web.time';

const { Component, useState } = owl;
const { useRef } = owl.hooks;

const READ_MORE = _lt("read more");
const READ_LESS = _lt("read less");

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
         * Value of the last rendered prettyBody. Useful to compare to new value
         * to decide if it has to be updated.
         */
        this._lastPrettyBody;
        /**
         * Reference to element containing the prettyBody. Useful to be able to
         * replace prettyBody with new value in JS (which is faster than t-raw).
         */
        this._prettyBodyRef = useRef('prettyBody');
        /**
         * Reference to the content of the message.
         */
        this._contentRef = useRef('content');
        /**
         * To get checkbox state.
         */
        this._checkboxRef = useRef('checkbox');
        /**
         * Id of setInterval used to auto-update time elapsed of message at
         * regular time.
         */
        this._intervalId = undefined;
        /**
         * States the index of the last "read more" that was inserted.
         * Useful to remember the state for each "read more" even if their DOM
         * is re-rendered.
         */
        this._lastReadMoreIndex = 0;
        /**
         * Determines whether each "read more" is opened or closed. The keys are
         * index, which is determined by their order of appearance in the DOM.
         * If body changes so that "read more" count is different, their default
         * value will be "wrong" at the next render but this is an acceptable
         * limitation. It's more important to save the state correctly in a
         * typical non-changing situation.
         */
        this._isReadMoreByIndex = new Map();
        this._constructor();
    }

    /**
     * Allows patching constructor.
     */
    _constructor() {}

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'mail.message_view', propNameAsRecordLocalId: 'messageViewLocalId' });
    }

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
        if (this.messageView.message.author && (!this.messageView.message.originThread || this.messageView.message.originThread.model !== 'mail.channel')) {
            // TODO FIXME for public user this might not be accessible. task-2223236
            // we should probably use the correspondig attachment id + access token
            // or create a dedicated route to get message image, checking the access right of the message
            return this.messageView.message.author.avatarUrl;
        } else if (this.messageView.message.author && this.messageView.message.originThread && this.messageView.message.originThread.model === 'mail.channel') {
            return `/mail/channel/${this.messageView.message.originThread.id}/partner/${this.messageView.message.author.id}/avatar_128`;
        } else if (this.messageView.message.guestAuthor && (!this.messageView.message.originThread || this.messageView.message.originThread.model !== 'mail.channel')) {
            return this.messageView.message.guestAuthor.avatarUrl;
        } else if (this.messageView.message.guestAuthor && this.messageView.message.originThread && this.messageView.message.originThread.model === 'mail.channel') {
            return `/mail/channel/${this.messageView.message.originThread.id}/guest/${this.messageView.message.guestAuthor.id}/avatar_128?unique=${this.messageView.message.guestAuthor.name}`;
        } else if (this.messageView.message.message_type === 'email') {
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
        return this.messageView.message.date.format(getLangDatetimeFormat());
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
        if (!this.messageView.message.author) {
            return false;
        }
        if (
            this.threadView &&
            this.threadView.thread &&
            this.threadView.thread.correspondent === this.messageView.message.author
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
            (
                this.messageView &&
                this.messageView.messageActionList &&
                (
                    this.messageView.messageActionList.isReactionPopoverOpened ||
                    this.messageView.messageActionList.showDeleteConfirm
                )
            )
        );
    }

    /**
     * Tell whether the bottom of this message is visible or not.
     *
     * @param {Object} param0
     * @param {integer} [offset=0]
     * @returns {boolean}
     */
    isBottomVisible({ offset = 0 } = {}) {
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
        if (!this.el) {
            return false;
        }
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
        return Boolean(
            this.threadView &&
            this.messageView &&
            this.threadView.replyingToMessageView === this.messageView
        );
    }

    /**
     * @returns {mail.message_view}
     */
    get messageView() {
        return this.messaging && this.messaging.models['mail.message_view'].get(this.props.messageViewLocalId);
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
        return this.messageView.message.date.format('hh:mm');
    }

    /**
     * @returns {mail.thread_view}
     */
    get threadView() {
        return this.messageView && this.messageView.threadView;
    }

    /**
     * @returns {Object}
     */
    get trackingValues() {
        return this.messageView.message.tracking_value_ids.map(trackingValue => {
            const value = Object.assign({}, trackingValue);
            value.changed_field = _.str.sprintf(this.env._t("%s:"), value.changed_field);
            /**
             * Maps tracked field type to a JS formatter. Tracking values are
             * not always stored in the same field type as their origin type.
             * Field types that are not listed here are not supported by
             * tracking in Python. Also see `create_tracking_values` in Python.
             */
            switch (value.field_type) {
                case 'boolean':
                    value.old_value = format.boolean(value.old_value, undefined, { forceString: true });
                    value.new_value = format.boolean(value.new_value, undefined, { forceString: true });
                    break;
                /**
                 * many2one formatter exists but is expecting id/name_get or data
                 * object but only the target record name is known in this context.
                 *
                 * Selection formatter exists but requires knowing all
                 * possibilities and they are not given in this context.
                 */
                case 'char':
                case 'many2one':
                case 'selection':
                    value.old_value = format.char(value.old_value);
                    value.new_value = format.char(value.new_value);
                    break;
                case 'date':
                    if (value.old_value) {
                        value.old_value = moment.utc(value.old_value);
                    }
                    if (value.new_value) {
                        value.new_value = moment.utc(value.new_value);
                    }
                    value.old_value = format.date(value.old_value);
                    value.new_value = format.date(value.new_value);
                    break;
                case 'datetime':
                    if (value.old_value) {
                        value.old_value = moment.utc(value.old_value);
                    }
                    if (value.new_value) {
                        value.new_value = moment.utc(value.new_value);
                    }
                    value.old_value = format.datetime(value.old_value);
                    value.new_value = format.datetime(value.new_value);
                    break;
                case 'float':
                    value.old_value = format.float(value.old_value);
                    value.new_value = format.float(value.new_value);
                    break;
                case 'integer':
                    value.old_value = format.integer(value.old_value);
                    value.new_value = format.integer(value.new_value);
                    break;
                case 'monetary':
                    value.old_value = format.monetary(value.old_value, undefined, {
                        currency: value.currency_id
                            ? this.env.session.currencies[value.currency_id]
                            : undefined,
                        forceString: true,
                    });
                    value.new_value = format.monetary(value.new_value, undefined, {
                        currency: value.currency_id
                            ? this.env.session.currencies[value.currency_id]
                            : undefined,
                        forceString: true,
                    });
                    break;
                case 'text':
                    value.old_value = format.text(value.old_value);
                    value.new_value = format.text(value.new_value);
                    break;
            }
            return value;
        });
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Modifies the message to add the 'read more/read less' functionality
     * All element nodes with 'data-o-mail-quote' attribute are concerned.
     * All text nodes after a ``#stopSpelling`` element are concerned.
     * Those text nodes need to be wrapped in a span (toggle functionality).
     * All consecutive elements are joined in one 'read more/read less'.
     *
     * FIXME This method should be rewritten (task-2308951)
     *
     * @private
     * @param {jQuery} $element
     */
    _insertReadMoreLess($element) {
        const groups = [];
        let readMoreNodes;

        // nodeType 1: element_node
        // nodeType 3: text_node
        const $children = $element.contents()
            .filter((index, content) =>
                content.nodeType === 1 || (content.nodeType === 3 && content.nodeValue.trim())
            );

        for (const child of $children) {
            let $child = $(child);

            // Hide Text nodes if "stopSpelling"
            if (
                child.nodeType === 3 &&
                $child.prevAll('[id*="stopSpelling"]').length > 0
            ) {
                // Convert Text nodes to Element nodes
                $child = $('<span>', {
                    text: child.textContent,
                    'data-o-mail-quote': '1',
                });
                child.parentNode.replaceChild($child[0], child);
            }

            // Create array for each 'read more' with nodes to toggle
            if (
                $child.attr('data-o-mail-quote') ||
                (
                    $child.get(0).nodeName === 'BR' &&
                    $child.prev('[data-o-mail-quote="1"]').length > 0
                )
            ) {
                if (!readMoreNodes) {
                    readMoreNodes = [];
                    groups.push(readMoreNodes);
                }
                $child.hide();
                readMoreNodes.push($child);
            } else {
                readMoreNodes = undefined;
                this._insertReadMoreLess($child);
            }
        }

        for (const group of groups) {
            const index = this._lastReadMoreIndex++;
            // Insert link just before the first node
            const $readMoreLess = $('<a>', {
                class: 'o_Message_readMoreLess',
                href: '#',
                text: READ_MORE,
            }).insertBefore(group[0]);

            // Toggle All next nodes
            if (!this._isReadMoreByIndex.has(index)) {
                this._isReadMoreByIndex.set(index, true);
            }
            const updateFromState = () => {
                const isReadMore = this._isReadMoreByIndex.get(index);
                for (const $child of group) {
                    $child.hide();
                    $child.toggle(!isReadMore);
                }
                $readMoreLess.text(isReadMore ? READ_MORE : READ_LESS);
            };
            $readMoreLess.click(e => {
                e.preventDefault();
                this._isReadMoreByIndex.set(index, !this._isReadMoreByIndex.get(index));
                updateFromState();
            });
            updateFromState();
        }
    }

    /**
     * @private
     */
    _update() {
        if (!this.messageView) {
            return;
        }
        if (this._prettyBodyRef.el && this.messageView.message.prettyBody !== this._lastPrettyBody) {
            this._prettyBodyRef.el.innerHTML = this.messageView.message.prettyBody;
            this._lastPrettyBody = this.messageView.message.prettyBody;
        }
        if (!this._prettyBodyRef.el) {
            this._lastPrettyBody = undefined;
        }
        // Remove all readmore before if any before reinsert them with _insertReadMoreLess.
        // This is needed because _insertReadMoreLess is working with direct DOM mutations
        // which are not sync with Owl.
        if (this._contentRef.el) {
            for (const el of [...this._contentRef.el.querySelectorAll(':scope .o_Message_readMoreLess')]) {
                el.remove();
            }
            this._lastReadMoreIndex = 0;
            this._insertReadMoreLess($(this._contentRef.el));
            this.messaging.messagingBus.trigger('o-component-message-read-more-less-inserted', {
                message: this.messageView.message,
            });
        }
        this.messageView.message.refreshDateFromNow();
        clearInterval(this._intervalId);
        this._intervalId = setInterval(() => {
            if (this.messageView) {
                this.messageView.message.refreshDateFromNow();
            }
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
            !isEventHandled(ev, 'MessageReactionGroup.Click') &&
            !isEventHandled(ev, 'MessageInReplyToView.ClickMessageInReplyTo')
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
        this.messageView.message.author.openChat();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAuthorName(ev) {
        markEventHandled(ev, 'Message.ClickAuthorName');
        if (!this.messageView.message.author) {
            return;
        }
        this.messageView.message.author.openProfile();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickFailure(ev) {
        markEventHandled(ev, 'Message.ClickFailure');
        this.messageView.message.openResendAction();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickOriginThread(ev) {
        // avoid following dummy href
        ev.preventDefault();
        this.messageView.message.originThread.open();
    }
}

Object.assign(Message, {
    props: {
        messageViewLocalId: String,
    },
    template: 'mail.Message',
});

registerMessagingComponent(Message);
