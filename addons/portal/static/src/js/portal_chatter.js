odoo.define('portal.chatter', function(require) {
'use strict';

var base = require('web_editor.base');
var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');
var rpc = require('web.rpc');
var session = require('web.session');
var time = require('web.time');

var qweb = core.qweb;
var _t = core._t;

/**
 * Widget PortalChatter
 *
 * - Fetch message fron controller
 * - Display chatter: pager, total message, composer (according to access right)
 * - Provider API to filter displayed messages
 */
var PortalChatter = Widget.extend({
    template: 'portal.chatter',
    events: {
        'change input[type=file]': "_onAttachmentChange",
        "click .o_attachment_delete": "_onAttachmentDelete",
        "click .o_portal_chatter_pager_btn": '_onClickPager',
        "click .o_portal_chatter_attachment_btn": '_onClickFilePicker',
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
        this.set('attachmentIDs', []);
        this.fileuploadID = _.uniqueId('o_chat_fileupload');
    },
    willStart: function(){
        var self = this;
        // load qweb template and init data
        return $.when(
            rpc.query({
                route: '/mail/chatter_init',
                params: this._messageFetchPrepareParams()
            }), this._loadTemplates()
        ).then(function(result){
            self.result = result;
            self.options = _.extend(self.options, self.result['options'] || {});
            return result;
        });
    },
    /**
     * @override
     */
    start: function () {
        // bind events
        this.on("change:messages", this, this._renderMessages);
        this.on("change:message_count", this, function(){
            this._renderMessageCount();
            this.set('pager', this._pager(this._current_page));
        });
        this.on("change:pager", this, this._renderPager);
        this.on("change:domain", this, this._onChangeDomain);
        // set options and parameters
        this.set('message_count', this.options['message_count']);
        this.set('messages', this.preprocessMessages(this.result['messages']));
        //portal chatter
        this.$attachmentButton = this.$(".o_portal_chatter_attachment_btn");
        this.$composerSendButton = this.$(".o_portal_chatter_composer_btn");
        $(window).on(this.fileuploadID, this._onAttachmentLoaded.bind(this));
        this.on("change:attachmentIDs", this, this._renderAttachments);
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Fetch the messages and the message count from the server for the
     * current page and current domain.
     *
     * @param {Array} domain
     * @returns {Deferred}
     */
    messageFetch: function(domain){
        var self = this;
        return rpc.query({
            route: '/mail/chatter_fetch',
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
            m['published_date_str'] = _.str.sprintf(_t('Published on %s'), moment(time.str_to_datetime(m.date)).format('MMMM Do YYYY, h:mm:ss a'));
        });
        return messages;
    },
    /**
     * Display error message on file upload
     *
     * @param {string<message>}
     */
    display_alert: function (message) {
        this.$('.o_portal_chatter_warning').remove();
        $('<div>', {
            class: 'alert alert-warning o_portal_chatter_warning',
            text: message,
        }).insertBefore(this.$('.o_portal_chatter_attachment'));
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
        var def1 = ajax.loadXML('/portal/static/src/xml/portal_chatter.xml', qweb);
        var def2 = ajax.loadXML('/mail/static/src/xml/attachment.xml', qweb);
        return $.when(def1, def2);
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
        // add token field to allow to post comment without being logged
        if(self.options['token']){
            data['token'] = self.options['token'];
        }
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
    /**
     * @private
     */
    _renderAttachments: function () {
        this.$('.o_portal_chatter_attachment').html(qweb.render('portal.Chatter.Attachments', {attachments: this.get('attachmentIDs')}));
    },
    _renderMessages: function(){
        this.$('.o_portal_chatter_messages').html(qweb.render("portal.chatter_messages", {widget: this}));
    },
    _renderMessageCount: function(){
        this.$('.o_message_counter').replaceWith(qweb.render("portal.chatter_message_count", {widget: this}));
    },
    _renderPager: function(){
        this.$('.o_portal_chatter_pager').replaceWith(qweb.render("portal.pager", {widget: this}));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAttachmentChange: function (ev) {
        var files = ev.target.files,
            attachments = this.get('attachmentIDs');

        if (attachments.length + files.length > 10) {
            this.display_alert("Oops! You can not upload more than 10 files.");
        }
        else if (!_.isEmpty(_.filter(files, function (file) {return (file.size / 1024 / 1024) > 50;}))) {
            this.display_alert("Oops! You can not upload a file larger than 50MB.");
        }
        else {
            this.$('form.o_form_binary_form').submit();
            this.$attachmentButton.prop('disabled', true);
            this.$composerSendButton.prop('disabled', true);
            var uploadAttachments = _.map(files, function (file) {
                return {
                    'id': 0,
                    'name': file.name,
                    'filename': file.name,
                    'url': '',
                    'upload': true,
                    'mimetype': '',
                };
            });
            attachments = attachments.concat(uploadAttachments);
            this.set('attachmentIDs', attachments);
            this.$('.o_portal_chatter_warning').remove();
        }
    },
    /**
     * @private
     */
    _onAttachmentDelete: function (ev) {
        ev.stopPropagation();
        var attachmentID = $(ev.target).data("id");

        if (attachmentID) {
            var attachments = this.get('attachmentIDs');
            this._rpc({
                model: 'ir.attachment',
                method: 'unlink',
                args: [attachmentID],
            });
            attachments = _.reject(attachments, {'id': attachmentID});
            this.set('attachmentIDs', attachments);
            document.getElementById('attachments').setAttribute("value", _.pluck(attachments, 'id'));
            this.$('.o_portal_chatter_warning').remove();
        }
    },
    /**
     * @private
     */
    _onAttachmentLoaded: function (ev) {
        var attachments = this.get('attachmentIDs'),
            files = Array.prototype.slice.call(arguments, 1);

        _.each(files, function (file) {
            if (file.error || !file.id) {
                this.do_warn(file.error);
                attachments = _.filter(attachments, function (attachment) { return !attachment.upload; });
            } else {
                var attachment = _.findWhere(attachments, {filename: file.filename, upload: true});
                if (attachment) {
                    attachments = _.without(attachments, attachment);
                    attachments.push({
                        'id': file.id,
                        'name': file.name || file.filename,
                        'filename': file.filename,
                        'mimetype': file.mimetype,
                        'url': session.url('/web/content', {'id': file.id, download: true}),
                    });
                }
            }
        }.bind(this));

        this.set('attachmentIDs', attachments);
        document.getElementById('attachments').setAttribute("value", _.pluck(attachments, 'id'));
        this.$attachmentButton.prop('disabled', false);
        this.$composerSendButton.prop('disabled', false);
    },
    _onChangeDomain: function(){
        var self = this;
        this.messageFetch().then(function(){
            var p = self._current_page;
            self.set('pager', self._pager(p));
        });
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClickFilePicker: function (ev) {
        var filePicker = this.$('input[type=file]');
        if (this.get('attachmentIDs').length >= 10) {
            this.display_alert("Oops! You can not upload more than 10 files.");
            return;
        }
        if (!_.isEmpty(filePicker)) {
            filePicker[0].click();
        }
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

base.ready().then(function () {
    $('.o_portal_chatter').each(function (index) {
        var $elem = $(this);
        var mail_thread = new PortalChatter(null, $elem.data());
        mail_thread.appendTo($elem);
    });
});

return {
    PortalChatter: PortalChatter,
};

});
