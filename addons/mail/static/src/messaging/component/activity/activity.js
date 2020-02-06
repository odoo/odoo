odoo.define('mail.messaging.component.Activity', function (require) {
'use strict';

const components = {
    ActivityMarkDoneButton: require('mail.messaging.component.ActivityMarkDoneButton'),
    FileUploader: require('mail.messaging.component.FileUploader'),
    MailTemplate: require('mail.messaging.component.MailTemplate'),
};
const useStore = require('mail.messaging.component_hook.useStore');

const {
    auto_str_to_date,
    getLangDateFormat,
    getLangDatetimeFormat,
} = require('web.time');

const { Component, useState } = owl;
const { useRef } = owl.hooks;

class Activity extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.state = useState({
            areDetailsVisible: false,
        });
        useStore(props => {
            return {
                activity: this.env.entities.Activity.get(props.activityLocalId),
            };
        });
        /**
         * Reference of the file uploader.
         * Useful to programmatically prompts the browser file uploader.
         */
        this._fileUploaderRef = useRef('fileUploader');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.messaging.entity.Activity}
     */
    get activity() {
        return this.env.entities.Activity.get(this.props.activityLocalId);
    }

    /**
     * @returns {string}
     */
    get assignedUserText() {
        return _.str.sprintf(this.env._t("for %s"), this.activity.assignee.nameOrDisplayName);
    }

    /**
     * @returns {string}
     */
    get delayLabel() {
        const today = moment().startOf('day');
        const momentDeadlineDate = moment(auto_str_to_date(this.activity.dateDeadline));
        // true means no rounding
        const diff = momentDeadlineDate.diff(today, 'days', true);
        if (diff === 0) {
            return this.env._t("Today:");
        } else if (diff === -1) {
            return this.env._t("Yesterday:");
        } else if (diff < 0) {
            return _.str.sprintf(this.env._t("%d days overdue:"), Math.abs(diff));
        } else if (diff === 1) {
            return this.env._t("Tomorrow:");
        } else {
            return _.str.sprintf(this.env._t("Due in %d days:"), Math.abs(diff));
        }
    }

    /**
     * @returns {string}
     */
    get formattedCreateDatetime() {
        const momentCreateDate = moment(auto_str_to_date(this.activity.dateCreate));
        const datetimeFormat = getLangDatetimeFormat();
        return momentCreateDate.format(datetimeFormat);
    }

    /**
     * @returns {string}
     */
    get formattedDeadlineDate() {
        const momentDeadlineDate = moment(auto_str_to_date(this.activity.dateDeadline));
        const datetimeFormat = getLangDateFormat();
        return momentDeadlineDate.format(datetimeFormat);
    }

    /**
     * @returns {string}
     */
    get summary() {
        return _.str.sprintf(this.env._t("“%s”"), this.activity.summary);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {mail.messaging.entity.Attachment} ev.detail.attachment
     */
    _onAttachmentCreated(ev) {
        this.activity.markAsDone({ attachments: [ev.detail.attachment] });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCancel(ev) {
        ev.preventDefault();
        this.activity.delete();
    }

    /**
     * @private
     */
    _onClickDetailsButton() {
        this.state.areDetailsVisible = !this.state.areDetailsVisible;
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickEdit(ev) {
        ev.preventDefault();
        const action = {
            type: 'ir.actions.act_window',
            name: this.env._t("Schedule Activity"),
            res_model: 'mail.activity',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_res_id: this.activity.res_id,
                default_res_model: this.activity.res_model,
            },
            res_id: this.activity.id,
        };
        return this.env.do_action(action, {
            on_close: () => this.activity.fetchAndUpdate(),
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickUploadDocument(ev) {
        this._fileUploaderRef.comp.openBrowserFileUploader();
    }

}

Object.assign(Activity, {
    components,
    props: {
        activityLocalId: String,
    },
    template: 'mail.messaging.component.Activity',
});

return Activity;

});
