/** @odoo-module */

import KanbanController from 'web.KanbanController';
import KanbanView from 'web.KanbanView';
import viewRegistry from 'web.view_registry';
import { qweb } from 'web.core';
import config from 'web.config'

const HRFleetKanbanController = KanbanController.extend({
    buttons_template: 'HRFleetKanbanView.buttons',
    events: _.extend({}, KanbanController.prototype.events, {
        'click .o_button_upload_fleet_attachment': '_onUpload',
        'change .o_fleet_documents_upload .o_form_binary_form': '_onAddAttachment',
    }),
    /**
     * @override
     */
        init: function () {
        this._super.apply(this, arguments);
        this.isMobile = config.device.isMobileDevice;
    },

    start: function () {
        // define a unique uploadId and a callback method
        this.fileUploadID = _.uniqueId('hr_fleet_document_upload');
        $(window).on(this.fileUploadID, () => this.trigger_up('reload'));
        return this._super.apply(this, arguments);
    },

    _onUpload: function (event) {
        // If hidden upload form doesn't exist, create it
        var $formContainer = this.$('.o_content').find('.o_fleet_documents_upload');
        if (!$formContainer.length) {
            $formContainer = $(qweb.render('HRFleet.DocumentsHiddenUploadForm', {widget: this}));
            $formContainer.appendTo(this.$('.o_content'));
        }
        // Trigger the input to select a file
        this.$('.o_fleet_documents_upload .o_input_file').click();
    },

    _onAddAttachment: function(ev) {
        // Auto submit form once we've selected an attachment
        const $input = $(ev.currentTarget).find('input.o_input_file');
        if ($input.val() !== '') {
            const $binaryForm = this.$('.o_fleet_documents_upload form.o_form_binary_form');
            $binaryForm.submit();
        }
    }
});

const HRFleetKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: HRFleetKanbanController,
    }),
})

viewRegistry.add('hr_fleet_kanban_view', HRFleetKanbanView);
