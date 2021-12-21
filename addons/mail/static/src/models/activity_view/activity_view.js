/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many2one, one2one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'ActivityView',
    identifyingFields: ['activityBoxView', 'activity'],
    lifecycleHooks: {
        _created() {
            this.onClickActivity = this.onClickActivity.bind(this);
            this.onClickCancel = this.onClickCancel.bind(this);
            this.onClickDetailsButton = this.onClickDetailsButton.bind(this);
            this.onClickEdit = this.onClickEdit.bind(this);
            this.onClickUploadDocument = this.onClickUploadDocument.bind(this);
        }
    },
    recordMethods: {
        /**
         * Handles the click on a link inside the activity.
         *
         * @param {MouseEvent} ev
         */
        onClickActivity(ev) {
            if (
                ev.target.tagName === 'A' &&
                ev.target.dataset.oeId &&
                ev.target.dataset.oeModel
            ) {
                this.messaging.openProfile({
                    id: Number(ev.target.dataset.oeId),
                    model: ev.target.dataset.oeModel,
                });
                // avoid following dummy href
                ev.preventDefault();
            }
        },
        /**
         * Handles the click on the cancel button
         */
        async onClickCancel() {
            const { chatter } = this.activityBoxView; // save value before deleting activity
            await this.activity.deleteServerRecord();
            chatter.reloadParentView();
        },
        /**
         * Handles the click on the detail button
         */
        onClickDetailsButton() {
            this.update({ areDetailsVisible: !this.areDetailsVisible });
        },
        /**
         * Handles the click on the edit button
         */
        onClickEdit() {
            this.activity.edit();
        },
        /**
         * Handles the click on the upload document button. This open the file
         * explorer for upload.
         */
        onClickUploadDocument() {
            this.fileUploaderView.component.openBrowserFileUploader();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeFileUploaderView() {
            return this.activity.category === 'upload_file' ? insertAndReplace() : clear();
        },
    },
    fields: {
        activity: many2one('Activity', {
            inverse: 'activityViews',
            required: true,
            readonly: true,
        }),
        activityBoxView: many2one('ActivityBoxView', {
            inverse: 'activityViews',
            readonly: true,
            required: true,
        }),
        /**
         * Determines whether the details are visible.
         */
        areDetailsVisible: attr({
            default: false,
        }),
        fileUploaderView: one2one('FileUploaderView', {
            compute: '_computeFileUploaderView',
            inverse: 'activityView',
            isCausal: true,
        }),
    },
});
