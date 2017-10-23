odoo.define('hr_expense_attachment.FormRenderer', function (require) {
"use strict";

var FormRenderer = require('web.FormRenderer');

var AttachPhoto = require('hr_expense_attachment.AttachPhoto');


/**
 * Include the FormRenderer to instanciate widget AttachPhoto.
 * The method will be automatically called to replace the tag <attachphoto>.
 */
FormRenderer.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _renderTagAttachphoto: function () {
        var widget = new AttachPhoto(this, {
            res_id: this.state.res_id,
            res_model: this.state.model,
        });
        widget.appendTo($('<div>'));
        return widget.$el;
    },
});

});
