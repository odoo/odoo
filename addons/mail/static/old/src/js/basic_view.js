/** @odoo-module **/

import BasicView from 'web.BasicView';

const mailWidgets = ['kanban_activity'];

const chatterFields = ["message_ids", "message_follower_ids", "activity_ids"];

BasicView.include({
    init: function () {
        this.hasAttachmentViewerFeature = false;
        this.hasChatter = false;
        this._super.apply(this, arguments);
        this.rendererParams.hasChatter = this.hasChatter;
        this.rendererParams.hasAttachmentViewerFeature = this.hasAttachmentViewerFeature;
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
    /**
     * Override to mark chatter fields inside the "oe_chatter" div such that we
     * don't fetch their sub views, as we don't need them. Without this, those
     * subviews would be loaded as there is no "widget" set on those fields.
     *
     * @override
     */
    _processNode(node, fv) {
        if (node.tag === "div" && node.attrs.class && node.attrs.class.includes("oe_chatter")) {
            this.hasChatter = true;
            const viewType = fv.type;
            const fieldsInfo = fv.fieldsInfo[viewType];
            const fields = fv.viewFields;
            for (const child of node.children) {
                if (child.tag === 'field' && chatterFields.includes(child.attrs.name)) {
                    const attrs = { ...child.attrs, modifiers: {}, __no_fetch: true };
                    const fieldName = attrs.name;
                    fieldsInfo[fieldName] = this._processField(viewType, fields[fieldName], attrs);
                } else {
                    this._processNode(child, fv);
                }
            }
            return false;
        }
        if (node.tag === 'div' && node.attrs.class === 'o_attachment_preview') {
            this.hasAttachmentViewerFeature = true;
        }
        return this._super(...arguments);
    },
});
