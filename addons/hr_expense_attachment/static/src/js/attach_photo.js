odoo.define('hr_expense_attachment.AttachPhoto', function (require) {
"use strict";

var config = require('web.config')
var Widget = require('web.Widget');

var AttachPhoto = Widget.extend({
    template: 'AttachPhoto',
    events: {
        'click .o_attach_photo': '_onClick',
    },
    /**
     * @constructor
     */
    init: function (parent, params) {
        this.formRender = parent;
        this.res_id = params.res_id;
        this.res_model = params.res_model;
        this.fileuploadId = _.uniqueId('oe_fileupload');
        return this._super.apply(this, arguments);
    },

    start: function () {
        var self = this;
        $(window).on(this.fileuploadId, function(event) {
            self.onAttachmentLoaded(Array.prototype.slice.call(arguments, 1));
        });
        return this._super.apply(this, arguments);
    },

    destroy: function () {
        $(window).off(this.fileuploadId);
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    
    /**
     * Attachment log on chatter
     *
     * @param {files} attachment_ids
     */
    onAttachmentLoaded: function (files) {
        var self = this;

        var att_ids = [];
        _.each(files, function(file){
            att_ids.push(file.id)
        });

        var message = {
            'attachment_ids': att_ids,
        };

        return this._rpc({
            model: self.res_model,
            method: 'message_post',
            args: [self.res_id],
            kwargs: message,
         }).then(function () {
            self.formRender.trigger_up('reload');
         });
    },

    /**
     * @private
     * @param {Event} event
     */
    _onClick: function (event) {
        var self = this;
        var $input = this.$('input.o_input_file');
        $input.on("change", function(event) {
            self.$('form.o_form_binary_form').submit();
        });
        $input.click();
    },
});

return AttachPhoto;

});
