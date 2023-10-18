/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import dom from "@web/legacy/js/core/dom";
import publicWidget from "@web/legacy/js/public/public_widget";
import portalComposer from "@portal/js/portal_composer";
import { range } from "@web/core/utils/numbers";

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

        this.set('messages', []);
        this.set('message_count', this.options['message_count']);
        this.set('pager', {});
        this.set('domain', this.options['domain']);
        this._currentPage = this.options['pager_start'];

        this.rpc = this.bindService("rpc");
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
        // bind events
        this.on("change:messages", this, this._renderMessages);
        this.on("change:message_count", this, function () {
            this._renderMessageCount();
            this.set('pager', this._pager(this._currentPage));
        });
        this.on("change:pager", this, this._renderPager);
        this.on("change:domain", this, this._onChangeDomain);
        // set options and parameters
        this.set('message_count', this.options['message_count']);
        this.set('messages', this.preprocessMessages(this.result['messages']));
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
     * current page and current domain.
     *
     * @param {Array} domain
     * @returns {Promise}
     */
    messageFetch: function (domain) {
        var self = this;
        return this.rpc('/mail/chatter_fetch', self._messageFetchPrepareParams()).then(function (result) {
            self.set('messages', self.preprocessMessages(result['messages']));
            self.set('message_count', result['message_count']);
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
            'domain': [],
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
        return this.rpc('/mail/chatter_init', this._messageFetchPrepareParams()).then(function (result) {
            self.result = result;
            self.options = Object.assign(self.options, self.result['options'] || {});
            return result;
        });
    },
    /**
     * Change the current page by refreshing current domain
     *
     * @private
     * @param {Number} page
     * @param {Array} domain
     */
    _changeCurrentPage: function (page, domain) {
        this._currentPage = page;
        var d = domain ? domain : Object.assign({}, this.get("domain"));
        this.set('domain', d); // trigger fetch message
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
        // add domain
        if (this.get('domain')) {
            data['domain'] = this.get('domain');
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
        var total = this.get('message_count');
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
    _renderMessages: function () {
        this.$('.o_portal_chatter_messages').empty().append(renderToElement("portal.chatter_messages", {widget: this}));
    },
    _renderMessageCount: function () {
        this.$('.o_message_counter').replaceWith(renderToElement("portal.chatter_message_count", {widget: this}));
    },
    _renderPager: function () {
        this.$('.o_portal_chatter_pager').replaceWith(renderToElement("portal.pager", {widget: this}));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onChangeDomain: function () {
        var self = this;
        return this.messageFetch().then(function () {
            var p = self._currentPage;
            self.set('pager', self._pager(p));
        });
    },
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
        return this.rpc('/mail/update_is_internal', {
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
            dom.scrollTo(this.el, {duration: 0});
        }
    },
});

export default PortalChatter
