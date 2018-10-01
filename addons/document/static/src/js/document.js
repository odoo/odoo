odoo.define('document.document', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var framework = require('web.framework');
var Sidebar = require('web.Sidebar');
var field_utils = require('web.field_utils');

var _t = core._t;

Sidebar.include({
    /**
     * @override
     */
    init : function (parent, options) {
        this._super.apply(this, arguments);
        this.hasAttachments = options.viewType === "form";
        if (this.hasAttachments) {
            this.sections.splice(1, 0, { 'name' : 'files', 'label' : _t('Attachment(s)'), });
            this.items.files = [];
            this.fileuploadId = _.uniqueId('oe_fileupload');
            $(window).on(this.fileuploadId, this._onFileUploaded.bind(this));
        }
    },
    /**
     * Get the attachment linked to the record when the toolbar started
     *
     * @override
     */
    start: function () {
        var _super = this._super.bind(this);
        var def = this.hasAttachments ? this._updateAttachments() : $.when();
        return def.then(_super);
    },
    /**
     * @override
     */
    destroy: function () {
        if (this.hasAttachments) {
            $(window).off(this.fileuploadId);
        }
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * @override
     */
    updateEnv: function (env) {
        this.env = env;
        var _super = _.bind(this._super, this, env);
        var def = this.hasAttachments ? this._updateAttachments() : $.when();
        def.then(_super);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Process the attachments then rerender the toolbar
     *
     * @private
     * @param  {Object} attachments
     */
    _processAttachments: function (attachments) {
        //to display number in name if more then one attachment which has same name.
        var self = this;
        _.chain(attachments)
            .groupBy(function (attachment) { return attachment.name; })
            .each(function (attachment) {
                 if (attachment.length > 1) {
                    _.map(attachment, function (attachment, i) {
                        attachment.name = _.str.sprintf(_t("%s (%s)"), attachment.name, i+1);
                    });
                }
            });
        _.each(attachments,function (a) {
            a.label = a.name;
            if (a.type === "binary") {
                a.url = '/web/content/'  + a.id + '?download=true';
            }
            a.create_date = field_utils.parse.datetime(a.create_date, 'create_date', {isUTC: true});
            a.create_date_string = field_utils.format.datetime(a.create_date, 'create_date', self.env.context.params);
            a.write_date = field_utils.parse.datetime(a.write_date, 'write_date', {isUTC: true});
            a.write_date_string = field_utils.format.datetime(a.write_date, 'write_date', self.env.context.params);
        });
        this.items.files = attachments;
    },
    /**
     * @private
     * @override
     */
    _redraw: function () {
        this._super.apply(this, arguments);
        if (this.hasAttachments) {
            this.$('.o_sidebar_add_attachment .o_form_binary_form')
                .change(this._onAddAttachment.bind(this));
            this.$('.o_sidebar_delete_attachment')
                .click(this._onDeleteAttachment.bind(this));
        }
    },
    /**
     * Update the attachments to be displayed in the attachment section
     * of the toolbar
     *
     * @private
     */
    _updateAttachments: function () {
        if (this.items.files === undefined) {
            return $.when();
        }
        var activeId = this.env.activeIds[0];
        if (!activeId) {
            this.items.files = [];
            return $.when();
        } else {
            var domain = [
                ['res_model', '=', this.env.model],
                ['res_id', '=', activeId],
                ['type', 'in', ['binary', 'url']]
            ];
            var fields = ['name', 'url', 'type',
                'create_uid', 'create_date', 'write_uid', 'write_date'];
            return this._rpc({
                model: 'ir.attachment',
                method: 'search_read',
                context: this.env.context,
                domain: domain,
                fields: fields,
            }).then(this._processAttachments.bind(this));
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Method triggered when user click on 'add attachment' and select a file
     *
     * @private
     * @param  {Event} event
     */
    _onAddAttachment: function (event) {
        var $event = $(event.target);
        if ($event.val() !== '') {
            var $binaryForm = this.$('form.o_form_binary_form');
            $binaryForm.submit();
            $binaryForm.find('input[type=file]').prop('disabled', true);
            $binaryForm.find('button').prop('disabled', true).find('img, span').toggle();
            this.$('.o_sidebar_add_attachment a').text(_t('Uploading...'));
            framework.blockUI();
        }
    },
    /**
     * Method triggered when user delete an attachment
     *
     * @private
     * @param  {Event} event
     */
    _onDeleteAttachment: function (event) {
        event.preventDefault();
        var self = this;
        var $event = $(event.currentTarget);
        var options = {
            confirm_callback: function () {
                self._rpc({
                    model: 'ir.attachment',
                    method: 'unlink',
                    args: [parseInt($event.attr('data-id'), 10)],
                })
                .then(self._updateAttachments.bind(self))
                .then(self._redraw.bind(self));
            }
        };
        Dialog.confirm(this, _t("Do you really want to delete this attachment ?"), options);
    },
    /**
     * Handler called when the upload is done
     *
     * @private
     */
    _onFileUploaded: function () {
        var attachments = Array.prototype.slice.call(arguments, 1);
        var uploadErrors = _.filter(attachments, function (attachment) {
            return attachment.error;
        });
        if (uploadErrors.length) {
            this.do_warn(_t('Uploading Error'), uploadErrors[0].error);
        }
        this._updateAttachments().then(this._redraw.bind(this));
        framework.unblockUI();
    }
});

});
