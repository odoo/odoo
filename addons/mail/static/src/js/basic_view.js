odoo.define('mail.BasicView', function (require) {
"use strict";

const BasicView = require('web.BasicView');

const mailWidgets = ['kanban_activity'];

BasicView.include({
    init: function () {
        this._super.apply(this, arguments);
        const post_refresh = this._getFieldOption('message_ids', 'post_refresh', false);
        const followers_post_refresh = this._getFieldOption('message_follower_ids', 'post_refresh', false);
        this.chatterFields = {
            hasActivityIds: this._hasField('activity_ids'),
            hasMessageFollowerIds: this._hasField('message_follower_ids'),
            hasMessageIds: this._hasField('message_ids'),
            hasRecordReloadOnAttachmentsChanged: post_refresh === 'always',
            hasRecordReloadOnMessagePosted: !!post_refresh,
            hasRecordReloadOnFollowersUpdate: !!followers_post_refresh,
            isAttachmentBoxVisibleInitially: (
                this._getFieldOption('message_ids', 'open_attachments', false) ||
                this._getFieldOption('message_follower_ids', 'open_attachments', false)
            ),
        };
        const fieldsInfo = this.fieldsInfo[this.viewType];
        this.rendererParams.chatterFields = this.chatterFields;

        // LEGACY for widget kanban_activity
        this.mailFields = {};
        for (const fieldName in fieldsInfo) {
            const fieldInfo = fieldsInfo[fieldName];
            if (_.contains(mailWidgets, fieldInfo.widget)) {
                this.mailFields[fieldInfo.widget] = fieldName;
                fieldInfo.__no_fetch = true;
            }
        }
        this.rendererParams.activeActions = this.controllerParams.activeActions;
        this.rendererParams.mailFields = this.mailFields;
    },
    /**
     * Gets the option value of a field if present.
     *
     * @private
     * @param {string} fieldName the desired field name
     * @param {string} optionName the desired option name
     * @param {*} defaultValue the default value if option or field is not found.
     * @returns {*}
     */
    _getFieldOption(fieldName, optionName, defaultValue) {
        const field = this.fieldsInfo[this.viewType][fieldName];
        if (field && field.options && field.options[optionName] !== undefined) {
            return field.options[optionName];
        }
        return defaultValue;
    },
    /**
     * Checks whether the view has a given field.
     *
     * @private
     * @param {string} fieldName the desired field name
     * @returns {boolean}
     */
    _hasField(fieldName) {
        return !!this.fieldsInfo[this.viewType][fieldName];
    },
});

});
