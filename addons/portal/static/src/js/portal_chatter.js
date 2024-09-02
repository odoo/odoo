/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import { scrollTo } from "@web/core/utils/scrolling";
import publicWidget from "@web/legacy/js/public/public_widget";
import portalComposer from "@portal/js/portal_composer";
import { range } from "@web/core/utils/numbers";
import { rpc } from "@web/core/network/rpc";

import { Component, markup } from "@odoo/owl";

/**
 * Widget PortalChatter
 *
 * - Fetch message fron controller
 * - Display chatter: pager, total message, composer (according to access right)
 * - Provider API to filter displayed messages
 */
var PortalChatter = publicWidget.Widget.extend({
    template: 'portal.Chatter',
    events: {
        'click .o_portal_chatter_pager_btn': '_onClickPager',
        'click .o_portal_chatter_js_is_internal': 'async _onClickUpdateIsInternal',
    },

    /**
     * @constructor
     */
    init: function (parent, options) {
        this.options = {};
        this._super.apply(this, arguments);

        this._setOptions(options);

        this._messages = [];
        this._messageCount = this.options['message_count'];
        this._pagerData = {};
        this._currentPage = this.options['pager_start'];
    },
    /**
     * @override
     */
    willStart: function () {
        return Promise.all([
            this._super.apply(this, arguments),
            this._chatterInit()
        ]);
    },
    /**
     * @override
     */
    start: function () {
        // set options and parameters
        this._updateMessageCount(this.options['message_count']);
        this._updateMessages(this.preprocessMessages(this.result['messages']));
        // bind bus event: this (portal.chatter) and 'portal.rating.composer' in portal_rating
        // are separate and sibling widgets, this event is to be triggered from portal.rating.composer,
        // hence bus event is bound to achieve usage of the event in another widget.
        Component.env.bus.addEventListener('reload_chatter_content', (ev) => this._reloadChatterContent(ev.detail));

        return Promise.all([this._super.apply(this, arguments), this._reloadComposer()]);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Fetch the messages and the message count from the server for the
     * current page.
     *
     * @returns {Promise}
     */
    messageFetch: function () {
        var self = this;
        return rpc('/mail/chatter_fetch', self._messageFetchPrepareParams()).then(function (result) {
            self._updateMessages(self.preprocessMessages(result['messages']));
            self._updateMessageCount(result['message_count']);
            return result;
        });
    },
    /**
     * Update the messages format
     *
     * @param {Array<Object>} messages
     * @returns {Array}
     */
    preprocessMessages(messages) {
        messages.forEach((m) => {
            m['body'] = markup(m.body);
            m.author = m.author_id ? m.author_id : m.author_guest_id;
        });
        return messages;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Set options
     *
     * @param {Array<string>} options: new options to set
     */
    _setOptions: function (options) {
        // underscorize the camelcased option keys
        const defaultOptions = Object.assign({
            'allow_composer': true,
            'display_composer': false,
            'csrf_token': odoo.csrf_token,
            'message_count': 0,
            'pager_step': 10,
            'pager_scope': 5,
            'pager_start': 1,
            'is_user_public': true,
            'is_user_employee': false,
            'is_user_publisher': false,
            'hash': false,
            'pid': false,
            'two_columns': false,
        }, this.options || {});

        this.options = Object.entries(options).reduce((acc, [key, value]) => {
            acc[
                //Camelized to Underscored key
                key
                    .split(/\.?(?=[A-Z])/)
                    .join("_")
                    .toLowerCase()
            ] = value;
            return acc;
        }, defaultOptions);
    },

    /**
     * Reloads chatter and message count after posting message
     *
     * @private
     */
    _reloadChatterContent: function (data) {
        this.messageFetch();
        this._reloadComposer();
    },
    _createComposerWidget: function () {
        return new portalComposer.PortalComposer(this, this.options);
    },
    /**
     * Destroy current composer widget and initialize and insert new widget
     *
     * @private
     */
    _reloadComposer: async function () {
        if (this._composer) {
            this._composer.destroy();
        }
        if (this.options.display_composer) {
            this._composer = this._createComposerWidget();
            await this._composer.appendTo(this.$('.o_portal_chatter_composer'));
        }
    },
    /**
     * @private
     * @returns {Deferred}
     */
    _chatterInit: function () {
        var self = this;
        return rpc('/mail/chatter_init', this._messageFetchPrepareParams()).then(function (result) {
            self.result = result;
            self.options = Object.assign(self.options, self.result['options'] || {});
            return result;
        });
    },
    /**
     * Changes the current page.
     *
     * @private
     * @param {Number} page
     */
    _changeCurrentPage: function (page) {
        this._currentPage = page;
        var self = this;
        return this.messageFetch().then(function () {
            var p = self._currentPage;
            self._updatePager(self._pager(p));
        });
    },
    _messageFetchPrepareParams: function () {
        var self = this;
        var data = {
            'res_model': this.options['res_model'],
            'res_id': this.options['res_id'],
            'limit': this.options['pager_step'],
            'offset': (this._currentPage - 1) * this.options['pager_step'],
            'allow_composer': this.options['allow_composer'],
        };
        // add token field to allow to post comment without being logged
        if (self.options['token']) {
            data['token'] = self.options['token'];
        }
        if (self.options['hash'] && self.options['pid']) {
            Object.assign(data, {
                'hash': self.options['hash'],
                'pid': self.options['pid'],
            });
        }
        return data;
    },
    /**
     * Generate the pager data for the given page number
     *
     * @private
     * @param {Number} page
     * @returns {Object}
     */
    _pager: function (page) {
        page = page || 1;
        var total = this._messageCount;
        var scope = this.options['pager_scope'];
        var step = this.options['pager_step'];

        // Compute Pager
        var pageCount = Math.ceil(parseFloat(total) / step);

        page = Math.max(1, Math.min(parseInt(page), pageCount));
        scope -= 1;

        var pmin = Math.max(page - parseInt(Math.floor(scope / 2)), 1);
        var pmax = Math.min(pmin + scope, pageCount);

        if (pmax - scope > 0) {
            pmin = pmax - scope;
        } else {
            pmin = 1;
        }

        var pages = [];
        range(pmin, pmax + 1).forEach(index => pages.push(index));

        return {
            "page_count": pageCount,
            "offset": (page - 1) * step,
            "page": page,
            "page_start": pmin,
            "page_previous": Math.max(pmin, page - 1),
            "page_next": Math.min(pmax, page + 1),
            "page_end": pmax,
            "pages": pages
        };
    },

    _updateMessages: function (messages) {
        this._messages = messages;
        this.$('.o_portal_chatter_messages').empty().append(renderToElement("portal.chatter_messages", {widget: this}));
    },
    _updateMessageCount: function (messageCount) {
        this._messageCount = messageCount;
        this.$('.o_message_counter').replaceWith(renderToElement("portal.chatter_message_count", {widget: this}));
        this._updatePager(this._pager(this._currentPage));
    },
    _updatePager: function (pager) {
        this._pagerData = pager;
        this.$('.o_portal_chatter_pager').replaceWith(renderToElement("portal.pager", {widget: this}));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClickPager: function (ev) {
        ev.preventDefault();
        var page = $(ev.currentTarget).data('page');
        this._changeCurrentPage(page);
    },

    /**
     * Toggle is_internal state of message. Update both node data and
     * classes to ensure DOM is updated accordingly to RPC call result.
     * @private
     * @returns {Promise}
     */
    _onClickUpdateIsInternal: function (ev) {
        ev.preventDefault();

        var $elem = $(ev.currentTarget);
        return rpc('/mail/update_is_internal', {
            message_id: $elem.data('message-id'),
            is_internal: ! $elem.data('is-internal'),
        }).then(function (result) {
            $elem.data('is-internal', result);
            if (result === true) {
                $elem.addClass('o_portal_message_internal_on');
                $elem.removeClass('o_portal_message_internal_off');
            } else {
                $elem.addClass('o_portal_message_internal_off');
                $elem.removeClass('o_portal_message_internal_on');
            }
        });
    },
});

publicWidget.registry.portalChatter = publicWidget.Widget.extend({
    selector: '.o_portal_chatter',

    /**
     * @override
     */
    async start() {
        const proms = [this._super.apply(this, arguments)];
        const chatter = new PortalChatter(this, this.$el.data());
        proms.push(chatter.appendTo(this.$el));
        await Promise.all(proms);
        // scroll to the right place after chatter loaded
        if (window.location.hash === `#${this.el.id}`) {
            scrollTo(this.el, { behavior: "instant" });
        }
    },
});

export default PortalChatter;
