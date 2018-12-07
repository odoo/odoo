odoo.define('mail.form_renderer', function (require) {
"use strict";

var Chatter = require('mail.Chatter');
var FormRenderer = require('web.FormRenderer');

/**
 * Include the FormRenderer to instanciate the chatter area containing (a
 * subset of) the mail widgets (mail_thread, mail_followers and mail_activity).
 */
FormRenderer.include({
    /**
     * @override
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.mailFields = params.mailFields;
        this.chatter = undefined;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Updates the chatter area with the new state if its fields has changed
     *
     * @override
     */
    confirmChange: function (state, id, fields) {
        if (this.chatter) {
            var chatterFields = ['message_attachment_count'].concat(_.values(this.mailFields));
            var updatedMailFields = _.intersection(fields, chatterFields);
            if (updatedMailFields.length) {
                this.chatter.update(state, updatedMailFields);
            }
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Overrides the function that renders the nodes to return the chatter's $el
     * for the 'oe_chatter' div node.
     *
     * @override
     * @private
     */
    _renderNode: function (node) {
        if (node.tag === 'div' && node.attrs.class === 'oe_chatter') {
            if (!this.chatter) {
                this.chatter = new Chatter(this, this.state, this.mailFields, {
                    isEditable: this.activeActions.edit,
                    viewType: 'form',
                });
                this.chatter.appendTo($('<div>'));
                this._handleAttributes(this.chatter.$el, node);
            } else {
                this.chatter.update(this.state);
            }
            return this.chatter.$el;
        } else {
            return this._super.apply(this, arguments);
        }
    },
});

});
