odoo.define('mail.form_renderer', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var Chatter = require('mail.Chatter');
var FormController = require('web.FormController');
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
            var updatedMailFields = _.intersection(fields, _.values(this.mailFields));
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
     * Overrides the function that renders the nodes to process the 'oe_chatter'
     * div node: we instantiate (or update if it already exists) the chatter,
     * and we return a fake node that we will use as a hook to insert the
     * chatter into the DOM when the whole view will be rendered.
     * In create mode returns an empty div instead of the fake hook node.
     *
     * @override
     * @private
     */
    _renderNode: function (node) {
        if (node.tag === 'div' && node.attrs.class === 'oe_chatter') {
            if (this.mode === 'edit' && !this.state.data.id) {
                // there is no chatter in create mode
                var $div = $('<div>');
                this._handleAttributes($div, node);
                return $div;
            } else {
                if (!this.chatter) {
                    this.chatter = new Chatter(this, this.state, this.mailFields, {
                        isEditable: this.activeActions.edit,
                    });
                    this.chatter.appendTo($('<div>'));
                    this._handleAttributes(this.chatter.$el, node);
                } else {
                    this.chatter.update(this.state);
                }
                return $('<div>', { class: 'oe_chatter', id: 'temp_chatter_hook' });
            }
        } else {
            return this._super.apply(this, arguments);
        }
    },
    /**
     * @override
     */
    _updateView: function () {
        // detach the chatter before calling _super, as we'll empty the html,
        // which would remove all handlers on the chatter
        if (this.chatter) {
            this.chatter.$el.detach();
        }
        this._super.apply(this, arguments);
        // replace our hook by the chatter's el once the view has been updated
        if (this.chatter && this.state.data.id) {
            this.$('#temp_chatter_hook').replaceWith(this.chatter.$el);
        }
    },
});

/**
 * Include the FormController and BasicModel to update the datapoint on the
 * model when a message is posted.
 */
FormController.include({
    custom_events: _.extend({}, FormController.prototype.custom_events, {
        new_message: '_onNewMessage',
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} event
     * @param {string} event.data.id datapointID
     * @param {integer[]} event.data.msgIDs list of message ids
     */
    _onNewMessage: function (event) {
        this.model.updateMessageIDs(event.data.id, event.data.msgIDs);
    },
});

BasicModel.include({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Update the message ids on a datapoint.
     *
     * Note that we directly update the res_ids on the datapoint as the message
     * has already been posted ; this change can't be handled 'normally' with
     * x2m commands because the change won't be saved as a normal field.
     *
     * @param {string} id
     * @param {integer[]} msgIDs
     */
    updateMessageIDs: function (id, msgIDs) {
        var element = this.localData[id];
        element.res_ids = msgIDs;
        element.count = msgIDs.length;
    },
});

});
