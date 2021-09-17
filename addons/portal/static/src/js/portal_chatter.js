odoo.define('portal.chatter', function (require) {
'use strict';

var core = require('web.core');
const dom = require('web.dom');
var publicWidget = require('web.public.widget');
var time = require('web.time');
var portalComposer = require('portal.composer');
const {Markup} = require('web.utils');

var qweb = core.qweb;
var _t = core._t;

/**
 * Widget PortalChatter
 *
 * - Fetch message fron controller
 * - Display chatter: pager, total message, composer (according to access right)
 * - Provider API to filter displayed messages
 */
var PortalChatter = publicWidget.Widget.extend({
    template: 'portal.Chatter',
    xmlDependencies: ['/portal/static/src/xml/portal_chatter.xml'],
    events: {
        'click .o_portal_chatter_pager_btn': '_onClickPager',
        'click .o_portal_chatter_attachments_link': '_onClickAttachmentsLink',
        'click .o_portal_chatter_js_is_internal': 'async _onClickUpdateIsInternal',
    },

    /**
     * @constructor
     */
    init: function (parent, options) {
        var self = this;
        this.options = {};
        this._super.apply(this, arguments);

        this._setOptions(options);

        this.set('messages', []);
        this.set('message_count', this.options['message_count']);
        this.set('attachment_ids', this.options['attachment_ids']);
        this.set('pager', {});
        this.set('domain', this.options['domain']);
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
        // bind events
        this.on("change:grouped_messages", this, this._renderMessages);
        this.on("change:attachment_ids", this, function () {
            this._renderAttachmentSummary();
            this.set('pager', this._pager(this._currentPage));
        });
        this.on("change:pager", this, this._renderPager);
        this.on("change:domain", this, this._onChangeDomain);
        // set options and parameters
        this.set('message_count', this.options['message_count']);
        this.set('attachment_ids', this.options['attachment_ids']);
        this.set('grouped_messages', this.preprocessMessages(this.result['grouped_messages']));
        // bind bus event: this (portal.chatter) and 'portal.rating.composer' in portal_rating
        // are separate and sibling widgets, this event is to be triggered from portal.rating.composer,
        // hence bus event is bound to achieve usage of the event in another widget.
        core.bus.on('reload_chatter_content', this, this._reloadChatterContent);

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
        return this._rpc({
            route: '/mail/chatter_fetch',
            params: self._messageFetchPrepareParams(),
        }).then(function (result) {
            self.set('grouped_messages', self.preprocessMessages(result['grouped_messages']));
            self.set('message_count', result['message_count']);
            self.set('attachment_ids', result['attachment_ids']);
            return result;
        });
    },
    /**
     * Update the messages format and store messages as a list
     *
     * @param {Array<Object>} grouped_messages each item is a group of messages sent the same day.
     *                                         accessible keys are 'label':{str}, 'date':{Date}, 'messages':{Array<Object>}
     * @returns {Array}
     */
    preprocessMessages: function (grouped_messages) {
        var messages = [];
        var index = 0;
        const self = this;
        grouped_messages.forEach(msg_group => {
            msg_group.date = moment(time.str_to_date(msg_group.date)).format('MMMM Do YYYY');
            messages.push(...msg_group.messages);
            msg_group.messages.forEach(function (m) {
                self._preprocessMessage(m, index++);
            });
        });
        this.messages = messages;
        return grouped_messages;
    },

    /**
     * @param {Object} message
     */
    _preprocessMessage: function (message) {
        message.author_avatar_url = _.str.sprintf('/web/image/%s/%s/author_avatar/50x50', 'mail.message', message.id);
        var published_date = moment(time.str_to_datetime(message.date));
        message.published_date_str = published_date.format('MMMM Do YYYY, h:mm:ss a');
        message.date_ago = published_date.fromNow();
        message.body = Markup(message.body);
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
            'attachment_ids': [],
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

        this.options = Object.entries(options).reduce(
            (acc, [key, value]) => {
                acc[_.str.underscored(key)] = value;
                return acc;
            },
            defaultOptions);
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
        return this._rpc({
            route: '/mail/chatter_init',
            params: this._messageFetchPrepareParams()
        }).then(function (result) {
            self.result = result;
            self.options = _.extend(self.options, self.result['options'] || {});
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
        var d = domain ? domain : _.clone(this.get('domain'));
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
        _.each(_.range(pmin, pmax + 1), function (index) {
            pages.push(index);
        });

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
        this.$('.o_portal_chatter_messages').html(qweb.render("portal.chatter_messages", {widget: this}));
    },
    _renderAttachmentSummary: function () {
        this.$('.o_attachment_summary').replaceWith(qweb.render("portal.chatter_attachment_summary", {widget: this}));
    },
    _renderPager: function () {
        this.$('.o_portal_chatter_pager').replaceWith(qweb.render("portal.pager", {widget: this}));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onChangeDomain: function () {
        var self = this;
        this.messageFetch().then(function () {
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
     *
     * @private
     * @param {MouseEvent} event
     */
    _onClickAttachmentsLink: function (ev) {
        ev.preventDefault();
        $(ev.currentTarget).closest('.o_attachment_counter').next('.o_portal_chatter_attachments').toggle();
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
        return this._rpc({
            route: '/mail/update_is_internal',
            params: {
                message_id: $elem.data('message-id'),
                is_internal: ! $elem.data('is-internal'),
            },
        }).then(function (result) {
            $elem.data('is-internal', result);
            if (result === true) {
                $elem.children('input').prop('checked', false);
            } else {
                $elem.children('input').prop('checked', true);
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

return {
    PortalChatter: PortalChatter,
};
});
