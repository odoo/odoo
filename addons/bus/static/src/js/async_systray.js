odoo.define('bus.systray.AsyncJobSystrayMenu', function (require) {
"use strict";

const {bus, qweb, _lt, _t} = require('web.core');
const SystrayMenu = require('web.SystrayMenu');
const Widget = require('web.Widget');
const AsyncJobService = require('bus.AsyncJobService');
const {CREATED, PROCESSING, FAILED, SUCCEEDED, DONE} = require('bus.AsyncJobStates')

const STATE_DATA = {
    [CREATED]: {
        icon: 'fa fa-arrow-circle-right',
        tooltip: _lt('The task has been scheduled for processing and will start shortly.'),
    },
    [PROCESSING]: {
        icon: 'fa fa-spinner fa-spin',
        tooltip: _lt('The task is processing.'),
    },
    [SUCCEEDED]: {
        icon: 'fa fa-check-circle',
        tooltip: _lt('The task has been processed, click to resume the execution.'),
    },
    [FAILED]: {
        icon: 'fa fa-exclamation-circle text-danger',
        tooltip: _lt('The task failed due to an error, click to reveal it.'),
    },
    [DONE]: {
        icon: 'fa fa-check-circle text-success',
        tooltip: _lt('The task has be completely executed, re-click to re-execute it.'),
    },
}

/**
 * Systray menu for asynchronous jobs, list async jobs and their state.
 */
const AsyncJobSystrayMenu = Widget.extend({
    name: 'async_job_systray_menu',
    template: 'bus.systray.AsyncJobSystrayMenu',
    events: {
        'click .o_async_job_succeeded': '_onClickSucceededFailed',
        'click .o_async_job_failed': '_onClickSucceededFailed',
        'click .o_async_toggler': '_onClickToggle',
    },

    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this.jobs = this.call('async_job', 'getJobs');
        this.isOpen = false;
        this.STATE_DATA = STATE_DATA;
        bus.on('async_job', this, this._onJobUpdate);
    },

    start() {
        const res = this._super.apply(this, arguments);
        document.addEventListener('click', this._onClickCaptureGlobal.bind(this), true);
        return res;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Used to select what spinner to show on the systray icon
     *
     * @return {string} aggregated state from the current job list
     */
    aggregatedState() {
        const jobList = Object.values(this.jobs);
        if (jobList.some(job => job.state === PROCESSING)) {
            return 'processing';
        } else if (jobList.some(job => job.state === CREATED)) {
            return 'pending';
        } else {
            return 'finished';
        }
    },

    /**
     * @return {int} count of SUCCEEDED jobs waiting user action
     */
    countTaskRequiringUserAttention() {
        return Object.values(this.jobs).filter(job => {
            return (
                job.state === SUCCEEDED &&
                (job.payload.result["type"] || "").startsWith("ir.action")
            );
        }).length;
    },

    /**
     * Close the menu if the user clicked away
     * 
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCaptureGlobal(ev) {
        if (!this.isOpen || this.el.contains(ev.target))
            return;
        this.isOpen = false;
        this.renderElement();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Execution the action contained in a S_READY job or show the error
     * contained in a S_FAILED one.
     * 
     * @param {MouseEvent} ev
     */
    async _onClickSucceededFailed(ev) {
        const jobId = $(ev.currentTarget).data("job-id");
        const job = this.jobs[jobId];

        switch (job.state) {
            case SUCCEEDED:
                if ((job.payload.result.type || '').startsWith('ir.actions')) {
                    await this.do_action(job.payload.result);
                    this._rpc({model: 'ir.async', method: 'complete', args: [job.id]});
                }
                break;

            case FAILED:
                this.call('crash_manager', 'rpc_error', job.payload.error);
                break;

        }
    },

    /**
     * Open/close the task list
     * 
     * @private
     * @param {MouseEvent} ev
     */
    _onClickToggle(ev) {
        this.isOpen = !this.isOpen;
        this.renderElement();
    },

    /**
     * Update the internal state and re-render the task list
     *
     * @param {AsyncJobService.Job} job
     */
    _onJobUpdate(job) {
        this.renderElement();
    },
});

SystrayMenu.Items.push(AsyncJobSystrayMenu);
return AsyncJobSystrayMenu;
});
