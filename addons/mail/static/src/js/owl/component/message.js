odoo.define('mail.component.Message', function (require) {
'use strict';

const mailUtils = require('mail.utils');
const AttachmentList = require('mail.component.AttachmentList');
const PartnerImStatusIcon = require('mail.component.PartnerImStatusIcon');

const core = require('web.core');
const time = require('web.time');

const _lt = core._lt;
const READ_MORE = _lt("read more");
const READ_LESS = _lt("read less");

class Message extends owl.store.ConnectedComponent {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.state = owl.useState({
            isClicked: false,
            timeElapsed: null,
        });
        this._contentRef = owl.hooks.useRef('content');
        this._intervalId = undefined;
    }

    mounted() {
        this.state.timeElapsed = mailUtils.timeFromNow(this.storeProps.message.date);
        this._insertReadMoreLess($(this._contentRef.el));
    }

    willUnmount() {
        clearInterval(this._intervalId);
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @return {string}
     */
    get avatar() {
        if (
            this.storeProps.author &&
            this.storeProps.author === this.storeProps.odoobot
        ) {
            return '/mail/static/src/img/odoobot.png';
        } else if (this.storeProps.author) {
            return `/web/image/res.partner/${this.storeProps.author.id}/image_128`;
        } else if (this.storeProps.message.message_type === 'email') {
            return '/mail/static/src/img/email_icon.png';
        }
        return '/mail/static/src/img/smiley/avatar.jpg';
    }

    /**
     * @return {string}
     */
    get datetime() {
        return this.storeProps.message.date.format(time.getLangDatetimeFormat());
    }

    /**
     * @return {string}
     */
    get displayedAuthorName() {
        if (this.storeProps.author) {
            return this.env.store.getters.partnerName(this.storeProps.author.localId);
        }
        return this.storeProps.message.email_from || this.env._t("Anonymous");
    }

    /**
     * @return {boolean}
     */
    get hasAuthorRedirect() {
        if (!this.props.hasAuthorRedirect) {
            return false;
        }
        if (!this.storeProps.author) {
            return false;
        }
        if (this.storeProps.author.id === this.env.session.partner_id) {
            return false;
        }
        return true;
    }

    /**
     * @return {boolean}
     */
    get hasDifferentOriginThread() {
        return (
            this.storeProps.originThread &&
            this.storeProps.originThread !== this.storeProps.thread
        );
    }

    /**
     * @return {boolean}
     */
    get isStarred() {
        return this.storeProps.message.threadLocalIds.includes('mail.box_starred');
    }

    /**
     * @return {string}
     */
    get shortTime() {
        return this.storeProps.message.date.format('hh:mm');
    }

    /**
     * @return {string}
     */
    get timeElapsed() {
        clearInterval(this._intervalId);
        this._intervalId = setInterval(() => {
            this.state.timeElapsed = mailUtils.timeFromNow(this.storeProps.message.date);
        }, 60 * 1000);
        return this.state.timeElapsed;
    }

    /**
     * @return {Object}
     */
    get trackingValues() {
        if (!this.props.tracking_value_ids) {
            // might happen in tests
            return [];
        }
        return this.storeProps.message.tracking_value_ids.map(trackingValue => {
            let value = {
                changed_field: trackingValue.changed_field,
                old_value: trackingValue.old_value,
                new_value: trackingValue.new_value,
                field_type: trackingValue.field_type,
            };
            if (value.field_type === 'datetime') {
                if (value.old_value) {
                    value.old_value =
                        moment
                            .utc(value.old_value)
                            .local()
                            .format('LLL');
                }
                if (value.new_value) {
                    value.new_value =
                        moment
                            .utc(value.new_value)
                            .local()
                            .format('LLL');
                }
            } else if (value.field_type === 'date') {
                if (value.old_value) {
                    value.old_value =
                        moment(value.old_value)
                            .local()
                            .format('LL');
                }
                if (value.new_value) {
                    value.new_value =
                        moment(value.new_value)
                            .local()
                            .format('LL');
                }
            }
            return value;
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Object} param0
     * @param {integer} [offset=0]
     * @return {boolean}
     */
    isBottomVisible({ offset=0 }={}) {
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
     * @return {boolean}
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
     * @param {Object} [param0={}]
     * @param {string} [param0.behavior='auto']
     * @param {string} [param0.block='end']
     * @return {Promise}
     */
    async scrollIntoView({ behavior='auto', block='end' }={}) {
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
                content.nodeType === 1 ||
                content.nodeType === 3 &&
                content.nodeValue.trim());

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
            // Insert link just before the first node
            const $readMoreLess = $('<a>', {
                class: 'o_Message_readMore',
                href: '#',
                text: READ_MORE,
            }).insertBefore(group[0]);

            // Toggle All next nodes
            let isReadMore = true;
            $readMoreLess.click(e => {
                e.preventDefault();
                isReadMore = !isReadMore;
                for (const $child of group) {
                    $child.hide();
                    $child.toggle(!isReadMore);
                }
                $readMoreLess.text(isReadMore ? READ_MORE : READ_LESS);
            });
        }
    }
    /**
     * @private
     * @param {Object} param0
     * @param {integer} param0.id
     * @param {string} param0.model
     */
    _redirect({ id, model }) {
        this.trigger('o-redirect', { id, model });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        if (ev.target.closest('.o_mention')) {
            this.trigger('o-redirect', {
                id: Number(ev.target.dataset.oeId),
                model: ev.target.dataset.oeModel,
            });
            ev.preventDefault();
            return;
        }
        if (ev.target.closest('.o_mail_redirect')) {
            this.trigger('o-redirect', {
                id: Number(ev.target.dataset.oeId),
                model: ev.target.dataset.oeModel,
            });
            ev.preventDefault();
            return;
        }
        ev.stopPropagation();
        this.state.isClicked = !this.state.isClicked;
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAuthor(ev) {
        if (!this.hasAuthorRedirect) {
            return;
        }
        if (!this.storeProps.author) {
            return;
        }
        this._redirect({
            id: this.storeProps.author.id,
            model: this.storeProps.author._model,
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickOriginThread(ev) {
        ev.preventDefault();
        this.trigger('o-redirect', {
            id: this.storeProps.originThread.id,
            model: this.storeProps.originThread._model,
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickStar(ev) {
        return this.dispatch('toggleStarMessage', this.props.messageLocalId);
    }

    /**
     * @private
     */
    _onClickMarkAsRead() {
        return this.dispatch('markMessagesAsRead', [this.props.messageLocalId]);
    }

    /**
     * @private
     */
    _onClickReply() {
        this.trigger('o-reply-message', {
            messageLocalId: this.props.messageLocalId,
        });
    }
}

Message.components = {
    AttachmentList,
    PartnerImStatusIcon,
};

Message.defaultProps = {
    hasAuthorRedirect: false,
    hasMarkAsReadIcon: false,
    hasReplyIcon: false,
    isSelected: false,
    isSquashed: false,
};

/**
 * @param {Object} state
 * @param {Object} ownProps
 * @param {string} ownProps.messageLocalId
 * @param {string} ownProps.threadLocalId
 * @return {Object}
 */
Message.mapStoreToProps = function (state, ownProps) {
    const message = state.messages[ownProps.messageLocalId];
    const attachmentLocalIds = message.attachmentLocalIds;
    const author = state.partners[message.authorLocalId];
    const odoobot = state.partners['res.partner_odoobot'];
    const originThread = state.threads[message.originThreadLocalId];
    const thread = state.threads[ownProps.threadLocalId];
    return {
        attachmentLocalIds,
        author,
        isMobile: state.isMobile,
        message,
        odoobot,
        originThread,
        thread,
    };
};

Message.props = {
    hasAuthorRedirect: Boolean,
    hasMarkAsReadIcon: Boolean,
    hasReplyIcon: Boolean,
    isSelected: Boolean,
    isSquashed: Boolean,
    messageLocalId: String,
    threadLocalId: String,
};

Message.template = 'mail.component.Message';

return Message;

});
