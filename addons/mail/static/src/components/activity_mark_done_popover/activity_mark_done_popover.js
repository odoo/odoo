/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { useModels } from '@mail/component_hooks/use_models/use_models';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';

const { Component } = owl;
const { useRef } = owl.hooks;

export class ActivityMarkDonePopover extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useModels();
        useComponentToModel({ fieldName: 'componentPopOver', modelName: 'mail.activity', propNameAsRecordLocalId: 'activityLocalId' });
        this._feedbackTextareaRef = useRef('feedbackTextarea');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    mounted() {
        this._feedbackTextareaRef.el.focus();
        if (this.activity.feedbackBackup) {
            this._feedbackTextareaRef.el.value = this.activity.feedbackBackup;
        }
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

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onBlur() {
        this.activity.update({
            feedbackBackup: this._feedbackTextareaRef.el.value,
        });
    }

    /**
     * @private
     */
    async _onClickDone() {
        await this.activity.markAsDone({
            feedback: this._feedbackTextareaRef.el.value,
        });
        this.trigger('reload', { keepChanges: true });
    }

    /**
     * @private
     */
    _onClickDoneAndScheduleNext() {
        this.activity.markAsDoneAndScheduleNext({
            feedback: this._feedbackTextareaRef.el.value,
        });
    }

}

Object.assign(ActivityMarkDonePopover, {
    props: {
        activityLocalId: String,
    },
    template: 'mail.ActivityMarkDonePopover',
});
