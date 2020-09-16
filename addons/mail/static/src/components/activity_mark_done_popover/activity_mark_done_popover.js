odoo.define('mail/static/src/components/activity_mark_done_popover/activity_mark_done_popover.js', function (require) {
'use strict';

const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

const { Component } = owl;
const { useRef } = owl.hooks;

class ActivityMarkDonePopover extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
        this._feedbackTextareaRef = useRef('feedbackTextarea');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    mounted() {
        this._feedbackTextareaRef.el.focus();
    }

    /**
     * @returns {mail.activity}
     */
    get activity() {
        return this.env.models['mail.activity'].get(this.props.activityLocalId);
    }

    /**
     * @returns {string}
     */
    get DONE_AND_SCHEDULE_NEXT() {
        return this.env._t("Done & Schedule Next");
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _close() {
        this.trigger('o-popover-close');
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickDiscard() {
        this._close();
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
    _onClickDoneAndScheduleNext() {
        this.activity.markAsDoneAndScheduleNext({
            feedback: this._feedbackTextareaRef.el.value,
        });
    }

    /**
     * @private
     */
    _onKeydown(ev) {
        if (ev.key === 'Escape') {
            this._close();
        }
    }

}

Object.assign(ActivityMarkDonePopover, {
    props: {
        activityLocalId: String,
    },
    template: 'mail.ActivityMarkDonePopover',
});

return ActivityMarkDonePopover;

});
