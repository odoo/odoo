odoo.define('portal.composer', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var publicWidget = require('web.public.widget');
var DocumentViewer = require('mail.DocumentViewer');

var qweb = core.qweb;
var _t = core._t;

ajax.loadXML('/mail/static/src/xml/thread.xml', qweb);

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
        'click .o_attachment_delete': 'async _onAttachmentDeleteClick',
        'click .o_portal_chatter_composer_btn': 'async _onSubmitButtonClick',
        "click .o_attachment_view": "_onAttachmentView",
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
        this.$attachments = this.$('.o_portal_chatter_composer_form .o_portal_chatter_attachments');
        this.$attachmentIds = this.$('.o_portal_chatter_attachment_ids');
        this.$attachmentTokens = this.$('.o_portal_chatter_attachment_tokens');

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
     * @param {MouseEvent} ev
     */
    _onAttachmentView: function (ev) {
        ev.stopPropagation();
        var activeAttachmentID = $(ev.currentTarget).data('id');
        if (activeAttachmentID) {
            var attachmentViewer = new DocumentViewer(this, this.attachments, activeAttachmentID);
            attachmentViewer.appendTo($('body'));
        }
    },
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
        var attachmentId = $(ev.currentTarget).data('id');
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
    /**
     * @private
     * @returns {Promise}
     */
    _onFileInputChange: function () {
        var self = this;

        this.$sendButton.prop('disabled', true);

        return Promise.all(_.map(this.$fileInput[0].files, function (file) {
            return new Promise(function (resolve, reject) {
                var data = {
                    'name': file.name,
                    'file': file,
                    'res_id': self.options.res_id,
                    'res_model': self.options.res_model,
                    'access_token': self.options.token,
                };
                ajax.post('/portal/attachment/add', data).then(function (attachment) {
                    attachment.state = 'pending';
                    self.attachments.push(attachment);
                    self._updateAttachments();
                    resolve();
                }).guardedCatch(function (error) {
                    self.displayNotification({
                        title: _t("Something went wrong."),
                        message: _.str.sprintf(_t("The file <strong>%s</strong> could not be saved."),
                            _.escape(file.name)),
                        type: 'warning',
                        sticky: true,
                    });
                    resolve();
                });
            });
        })).then(function () {
            self.$sendButton.prop('disabled', false);
        });
    },
    /**
     * Returns a Promise that is never resolved to prevent sending the form
     * twice when clicking twice on the button, in combination with the `async`
     * in the event definition.
     *
     * @private
     * @returns {Promise}
     */
    _onSubmitButtonClick: function (ev) {
        var self = this,
            $form = this.$el.find('form.o_portal_chatter_composer_form'),
            route = $form.attr('action');
        return new Promise(function (resolve, reject) {
            if (route === '/mail/chatter_post') {
                ev.preventDefault();
                var data = $form.serializeArray();
                self._rpc({
                    route: route,
                    params: _.object(_.pluck(data, 'name'), _.pluck(data, 'value')),
                }).then(function (url) {
                    var $parent = self.getParent();
                    if (self.options.is_portal_chatter) {
                        $parent._chatterInit().then(function (result) {
                            // reset chatter widget
                            if (self.options['display_composer']) {
                                $parent._composer.destroy();
                                $parent.start();
                                $parent.renderElement();
                                $parent._composer.replace($parent.$('.o_portal_chatter_composer'));
                            }
                        });
                    }
                    // for if chatter/composer open inside the BS modal
                    if ($parent.$el.is('.modal.fade.modal_shown')) {
                        window.location.reload();
                    }
                });
            }
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _updateAttachments: function () {
        this.$attachmentIds.val(_.pluck(this.attachments, 'id'));
        this.$attachmentTokens.val(_.pluck(this.attachments, 'access_token'));
        this.$attachments.html(qweb.render('portal.Chatter.Attachments', {
            attachments: this.attachments,
            showDelete: true,
        }));
    },
});

return {
    PortalComposer: PortalComposer,
};
});
