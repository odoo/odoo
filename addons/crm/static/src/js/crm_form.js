odoo.define("crm.crm_form", function (require) {
    "use strict";

    /**
     * This From Controller makes sure we display a rainbowman message
     * when the stage is won, even when we click on the statusbar.
     * When the stage of a lead is changed and data are saved, we check
     * if the lead is won and if a message should be displayed to the user
     * with a rainbowman like when the user click on the button "Mark Won".
     */

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');

    var CrmFormController = FormController.extend({
        /**
         * Main method used when saving the record hitting the "Save" button.
         * We check if the stage_id field was altered and if we need to display a rainbowman
         * message.
         *
         * @override
         */
        saveRecord: function () {
            return this._super(...arguments).then((modifiedFields) => {
                if (modifiedFields.indexOf('stage_id') !== -1) {
                    this._checkRainbowmanMessage(this.renderer.state.res_id)
                }
            });
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Apply change may be called with 'event.data.force_save' set to True.
         * This typically happens when directly clicking in the statusbar widget on a new stage.
         * If it's the case, we check for a modified stage_id field and if we need to display a
         * rainbowman message.
         *
         * @param {string} dataPointID
         * @param {Object} changes
         * @param {OdooEvent} event
         * @override
         * @private
         */
        _applyChanges: function (dataPointID, changes, event) {
            return this._super(...arguments).then(() => {
                if (event.data.force_save && 'stage_id' in changes) {
                    this._checkRainbowmanMessage(parseInt(event.target.res_id));
                }
            });
        },

        /**
         * When updating a crm.lead, through direct use of the status bar or when saving the
         * record, we check for a rainbowman message to display.
         *
         * (see Widget docstring for more information).
         *
         * @param {integer} recordId
         */
        _checkRainbowmanMessage: async function(recordId) {
            const message = await this._rpc({
                model: 'crm.lead',
                method : 'get_rainbowman_message',
                args: [[recordId]],
            });
            if (message) {
                this.trigger_up('show_effect', {
                    message: message,
                    type: 'rainbow_man',
                });
            }
        }
    });

    var CrmFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: CrmFormController,
        }),
    });

    viewRegistry.add('crm_form', CrmFormView);

    return {
        CrmFormController: CrmFormController,
        CrmFormView: CrmFormView,
    };
});
