odoo.define('website_mail.thread', function(require) {
    'use strict';

    var web_editor_base = require('web_editor.base');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var Widget = require('web.Widget');
    var rpc = require('web.rpc');

    var qweb = core.qweb;
    var _t = core._t;

    /**
     * Widget WebsiteMailThread
     *
     *  - Fetch message fron controller
     *  - Display chatter: pager, total message, composer (according to access right)
     *  - Provider API to filter displayed messages
     */
    var WebsiteMailThread = Widget.extend({
        template: 'website_mail.chatter',
        events: {
            "click .o_website_mail_pager_btn": '_onClickPager'
        },

        init: function(parent, options){
            this._super.apply(this, arguments);
            this.options = _.defaults(options || {}, {
                'allow_composer': true,
                'display_composer': false,
                'csrf_token': odoo.csrf_token,
                'message_count': 0,
                'pager_step': 10,
                'pager_scope': 5,
                'pager_start': 1,
                'is_user_public': true,
                'is_user_publisher': false,
                'domain': [],
            });
            this.set('messages', []);
            this.set('message_count', this.options['message_count']);
            this.set('pager', {});
            this.set('domain', this.options['domain']);
            this._current_page = this.options['pager_start'];
        },
        willStart: function(){
            var self = this;
            // load qweb template and init data
            return $.when(
                rpc.query({
                    route: '/website_mail/init',
                    params: this._messageFetchPrepareParams()
                }), this._loadTemplates()
            ).then(function(result){
                // bind events
                self.on("change:messages", self, self._renderMessages);
                self.on("change:message_count", self, function(){
                    self._renderMessageCount();
                    self.set('pager', self._pager(self._current_page));
                });
                self.on("change:pager", self, self._renderPager);
                self.on("change:domain", self, self._onChangeDomain);
                // set options and parameters
                self.options = _.extend(self.options, result['options'] || {});
                self.set('message_count', self.options['message_count']);
                self.set('messages', self.preprocessMessages(result['messages']));
                return result;
            });
        },

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * Fetch the messages and the message count from the server for the
         * current page and current domain.
         *
         * @param {Array}
         * @returns {Deferred}
         */
        messageFetch: function(domain){
            var self = this;
            return rpc.query({
                route: '/website_mail/fetch',
                params: self._messageFetchPrepareParams()
            }).then(function(result){
                self.set('messages', self.preprocessMessages(result['messages']));
                self.set('message_count', result['message_count']);
            });
        },
        /**
         * Update the messages format
         *
         * @param {Array<Object>}
         * @returns {Array}
         */
        preprocessMessages: function(messages){
            _.each(messages, function(m){
                m['author_avatar_url'] = _.str.sprintf('/web/image/%s/%s/author_avatar/50x50', 'mail.message', m.id);
                m['published_date_str'] = _.str.sprintf(_t('Published on %s'), moment(m.date).format('MMMM Do YYYY, h:mm:ss a'));
            });
            return messages;
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Change the current page by refreshing current domain
         *
         * @private
         * @param {Number} page
         * @param {Array} domain
         */
        _changeCurrentPage: function(page, domain){
            this._current_page = page;
            var d = domain ? domain : _.clone(this.get('domain'));
            this.set('domain', d); // trigger fetch message
        },
        /**
         * @private
         * @returns {Deferred}
         */
        _loadTemplates: function(){
            return ajax.loadXML('/website_mail/static/src/xml/website_mail.xml', qweb);
        },
        _messageFetchPrepareParams: function(){
            var self = this;
            var data = {
                'res_model': this.options['res_model'],
                'res_id': this.options['res_id'],
                'limit': this.options['pager_step'],
                'offset': (this._current_page-1) * this.options['pager_step'],
                'allow_composer': this.options['allow_composer'],
            };
            // add fields to allow to post comment without being logged
            _.each(['token', 'token_field'], function(field){
                if(self.options[field]){
                    data[field] = self.options[field];
                }
            });
            // add domain
            if(this.get('domain')){
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
        _pager: function(page){
            var page = page || 1;
            var total = this.get('message_count');
            var scope = this.options['pager_scope'];
            var step = this.options['pager_step'];

            // Compute Pager
            var page_count = Math.ceil(parseFloat(total) / step);

            var page = Math.max(1, Math.min(parseInt(page), page_count));
            scope -= 1;

            var pmin = Math.max(page - parseInt(Math.floor(scope/2)), 1);
            var pmax = Math.min(pmin + scope, page_count);

            if(pmax - scope > 0){
                pmin = pmax - scope;
            }else{
                pmin = 1;
            }

            var pages = [];
            _.each(_.range(pmin, pmax+1), function(index){
                pages.push(index);
            });

            return {
                "page_count": page_count,
                "offset": (page - 1) * step,
                "page": page,
                "page_start": pmin,
                "page_previous": Math.max(pmin, page - 1),
                "page_next": Math.min(pmax, page + 1),
                "page_end": pmax,
                "pages": pages
            };
        },
        _renderMessages: function(){
            this.$('.o_website_mail_messages').html(qweb.render("website_mail.chatter_messages", {widget: this}));
        },
        _renderMessageCount: function(){
            this.$('.o_message_counter').replaceWith(qweb.render("website_mail.chatter_message_count", {widget: this}));
        },
        _renderPager: function(){
            this.$('.o_website_mail_pager').replaceWith(qweb.render("website_mail.pager", {widget: this}));
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        _onChangeDomain: function(){
            var self = this;
            this.messageFetch().then(function(){
                var p = self.get('current_page');
                self.set('pager', self._pager(p));
            });
        },
        /**
         * @private
         * @param {MouseEvent} event
         */
        _onClickPager: function(ev){
            ev.preventDefault();
            var page = $(ev.currentTarget).data('page');
            this._changeCurrentPage(page);
        },
    });

    web_editor_base.ready().then(function(){
        $('.o_website_mail_thread').each(function(index){
            var $elem = $(this);
            var mail_thread = new WebsiteMailThread(null, $elem.data());
            mail_thread.appendTo($elem);
        });
    });

    return {
        WebsiteMailThread: WebsiteMailThread,
    };
});
