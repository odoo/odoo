odoo.define('mail.messaging.component.ActivityMarkDonePopover', function (require) {
'use strict';

const useStore = require('mail.messaging.component_hook.useStore');

const { Component } = owl;
const { useRef } = owl.hooks;

class ActivityMarkDonePopover extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            return {
                activity: this.env.entities.Activity.get(props.activityLocalId),
            };
        });
        this._feedbackTextareaRef = useRef('feedbackTextarea');
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
    get DONE_AND_SCHEDULE_NEXT() {
        return this.env._t("Done & Schedule Next");
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickDiscard() {
        this.trigger('o-discard-clicked');
    }

    /**
     * @private
     */
    _onClickDone() {
        this.activity.markAsDone({
            feedback: this._feedbackTextareaRef.el.value,
        });
    }

    /**
     * @private
     */
    async _onClickDoneAndScheduleNext() {
        const action = await this.activity.markAsDoneAndScheduleNext({
            feedback: this._feedbackTextareaRef.el.value,
        });
        this.env.do_action(action, {
            on_close: () => this.activity.chatter.refreshActivities(),
        });
    }

}

Object.assign(ActivityMarkDonePopover, {
    props: {
        activityLocalId: String,
    },
    template: 'mail.messaging.component.ActivityMarkDonePopover',
});

return ActivityMarkDonePopover;

});
