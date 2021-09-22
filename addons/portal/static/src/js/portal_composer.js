odoo.define('portal.composer', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var publicWidget = require('web.public.widget');

var qweb = core.qweb;
var _t = core._t;

/**
 * Widget PortalComposer
 *
 * Display the composer (according to access right)
 *
 */
var PortalComposer = publicWidget.Widget.extend({
    template: 'portal.Composer',
    xmlDependencies: ['/portal/static/src/xml/portal_chatter.xml'],
    events: {
        'change .o_portal_chatter_file_input': '_onFileInputChange',
        'click .o_portal_chatter_attachment_btn': '_onAttachmentButtonClick',
        'click .o_portal_chatter_attachment_delete': 'async _onAttachmentDeleteClick',
        'click .o_portal_chatter_composer_btn': 'async _onSubmitButtonClick',
    },

    /**
     * @constructor
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.options = _.defaults(options || {}, {
            'allow_composer': true,
            'display_composer': false,
            'csrf_token': odoo.csrf_token,
            'token': false,
            'res_model': false,
            'res_id': false,
        });
        this.attachments = [];
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        this.$attachmentButton = this.$('.o_portal_chatter_attachment_btn');
        this.$fileInput = this.$('.o_portal_chatter_file_input');
        this.$sendButton = this.$('.o_portal_chatter_composer_btn');
        this.$attachments = this.$('.o_portal_chatter_composer_input .o_portal_chatter_attachments');
        this.$inputTextarea = this.$('.o_portal_chatter_composer_input textarea[name="message"]');

        return this._super.apply(this, arguments).then(function () {
            if (self.options.default_attachment_ids) {
                self.attachments = self.options.default_attachment_ids || [];
                _.each(self.attachments, function(attachment) {
                    attachment.state = 'done';
                });
                self._updateAttachments();
            }
            return Promise.resolve();
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAttachmentButtonClick: function () {
        this.$fileInput.click();
    },
    /**
     * @private
     * @param {Event} ev
     * @returns {Promise}
     */
    _onAttachmentDeleteClick: function (ev) {
        var self = this;
        var attachmentId = $(ev.currentTarget).closest('.o_portal_chatter_attachment').data('id');
        var accessToken = _.find(this.attachments, {'id': attachmentId}).access_token;
        ev.preventDefault();
        ev.stopPropagation();

        this.$sendButton.prop('disabled', true);

        return this._rpc({
            route: '/portal/attachment/remove',
            params: {
                'attachment_id': attachmentId,
                'access_token': accessToken,
            },
        }).then(function () {
            self.attachments = _.reject(self.attachments, {'id': attachmentId});
            self._updateAttachments();
            self.$sendButton.prop('disabled', false);
        });
    },
    _prepareAttachmentData: function (file) {
        return {
            'name': file.name,
            'file': file,
            'res_id': this.options.res_id,
            'res_model': this.options.res_model,
            'access_token': this.options.token,
        };
    },
    /**
     * @private
     * @returns {Promise}
     */
    _onFileInputChange: function () {
        var self = this;

        this.$sendButton.prop('disabled', true);

        return Promise.all(_.map(this.$fileInput[0].files, function (file) {
            return new Promise(function (resolve, reject) {
                var data = self._prepareAttachmentData(file);
                ajax.post('/portal/attachment/add', data).then(function (attachment) {
                    attachment.state = 'pending';
                    self.attachments.push(attachment);
                    self._updateAttachments();
                    resolve();
                }).guardedCatch(function (error) {
                    self.displayNotification({
                        message: _.str.sprintf(_t("Could not save file <strong>%s</strong>"),
                            _.escape(file.name)),
                        type: 'warning',
                        sticky: true,
                    });
                    resolve();
                });
            });
        })).then(function () {
            // ensures any selection triggers a change, even if the same files are selected again
            self.$fileInput[0].value = null;
            self.$sendButton.prop('disabled', false);
        });
    },
    /**
     * prepares data to send message
     *
     * @private
     */
    _prepareMessageData: function () {
        return Object.assign(this.options || {}, {
            'message': this.$('textarea[name="message"]').val(),
            'attachment_ids': _.pluck(this.attachments, 'id'),
            'attachment_tokens': _.pluck(this.attachments, 'access_token'),
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onSubmitButtonClick: function (ev) {
        ev.preventDefault();
        if (!this.$inputTextarea.val().trim() && !this.attachments.length) {
            this.$inputTextarea.addClass('border-danger');
            const error = _t('Some fields are required. Please make sure to write a message or attach a document');
            this.$(".o_portal_chatter_composer_error").text(error).removeClass('d-none');
            return Promise.reject();
        } else {
            return this._chatterPostMessage(ev.currentTarget.getAttribute('data-action'));
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _updateAttachments: function () {
        this.$attachments.html(qweb.render('portal.Chatter.Attachments', {
            attachments: this.attachments,
            showDelete: true,
        }));
    },
    /**
     * post message using rpc call and display new message and message count
     *
     * @private
     * @param {String} route
     * @returns {Promise}
     */
    _chatterPostMessage: async function (route) {
        const result = await this._rpc({
            route: route,
            params: this._prepareMessageData(),
        });
        core.bus.trigger('reload_chatter_content', result);
        return result;
    },
});

return {
    PortalComposer: PortalComposer,
};
});
