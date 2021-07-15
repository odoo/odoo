odoo.define('mail/static/src/components/activity/activity.js', function (require) {
'use strict';

const components = {
    ActivityMarkDonePopover: require('mail/static/src/components/activity_mark_done_popover/activity_mark_done_popover.js'),
    FileUploader: require('mail/static/src/components/file_uploader/file_uploader.js'),
    MailTemplate: require('mail/static/src/components/mail_template/mail_template.js'),
};
const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

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
        useShouldUpdateBasedOnProps();
        this.state = useState({
            areDetailsVisible: false,
        });
        useStore(props => {
            const activity = this.env.models['mail.activity'].get(props.activityLocalId);
            return {
                activity: activity ? activity.__state : undefined,
                assigneeNameOrDisplayName: (
                    activity &&
                    activity.assignee &&
                    activity.assignee.nameOrDisplayName
                ),
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
     * @returns {mail.activity}
     */
    get activity() {
        return this.env.models['mail.activity'].get(this.props.activityLocalId);
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
    get MARK_DONE() {
        return this.env._t("Mark Done");
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
     * @param {mail.attachment} ev.detail.attachment
     */
    _onAttachmentCreated(ev) {
        this.activity.markAsDone({ attachments: [ev.detail.attachment] });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        if (
            ev.target.tagName === 'A' &&
            ev.target.dataset.oeId &&
            ev.target.dataset.oeModel
        ) {
            this.env.messaging.openProfile({
                id: Number(ev.target.dataset.oeId),
                model: ev.target.dataset.oeModel,
            });
            // avoid following dummy href
            ev.preventDefault();
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickCancel(ev) {
        ev.preventDefault();
        await this.activity.deleteServerRecord();
        this.trigger('reload', { keepChanges: true });
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
        this.activity.edit();
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
    template: 'mail.Activity',
});

return Activity;

});
