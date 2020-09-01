odoo.define('bus.systray.AsyncSpinner', function (require) {
"use strict";

const {bus, qweb, _lt, _t} = require('web.core');
const SystrayMenu = require('web.SystrayMenu');
const Widget = require('web.Widget');
const {AsyncJobService, asyncJobState} = require('bus.AsyncJobService');

const STATE_DATA = {
    [asyncJobState.CREATED]: {
        icon: 'fa fa-arrow-circle-right',
        tooltip: _lt('The task has been scheduled for processing and will start shortly.'),
    },
    [asyncJobState.PROCESSING]: {
        icon: 'fa fa-spinner fa-spin',
        tooltip: _lt('The task is processing.'),
    },
    [asyncJobState.SUCCEEDED]: {
        icon: 'fa fa-check-circle',
        tooltip: _lt('The task has been processed, click to resume the execution.'),
    },
    [asyncJobState.FAILED]: {
        icon: 'fa fa-exclamation-circle text-danger',
        tooltip: _lt('The task failed due to an error, click to reveal it.'),
    },
    [asyncJobState.DONE]: {
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
        this.isOpen = false;
        this.STATE_DATA = STATE_DATA;
        bus.on('async_job', this, this._onJobUpdate);
    },

    start() {
        document.addEventListener('click', this._onClickCaptureGlobal.bind(this), true);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @return {string} aggregated state from the current job list
     */
    aggreatedState() {
        const jobList = Object.values(this.call('async_job', 'getJobs'));
        if (jobList.some(job => job.state === asyncJobState.PROCESSING)) {
            return 'processing';
        } else if (jobList.some(job => job.state === asyncJobState.CREATED)) {
            return 'pending';
        } else {
            return 'finished';
        }
    },

    /**
     * @return {int} count of SUCCEEDED jobs waiting user action
     */
    actionNeededCount() {
        return Object.values(this.call('async_job', 'getJobs')).filter(job => {
            return job.state === asyncJobState.SUCCEEDED
                   && (job.payload.result["type"] || "").startsWith("ir.action")
        }).length;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Update the internal state and re-render the task list
     *
     * @param {AsyncJobService.Job} job
     */
    _onJobUpdate(job) {
        this.renderElement();
    },

    /**
     * Execution the action contained in a S_READY job or show the error
     * contained in a S_FAILED one.
     * 
     * @param {MouseEvent} ev
     */
    _onClickSucceededFailed(ev) {
        const jobId = $(ev.currentTarget).data("job-id");
        const job = this.call('async_job', 'getJobs')[jobId];
        if (job.state === asyncJobState.FAILED) {
            this.call('crash_manager', 'rpc_error', job.payload.error);
        } else if (job.state === asyncJobState.SUCCEEDED
                   && (job.payload.result.type || '').startsWith('ir.actions')) {
            this.do_action(job.payload.result).then(() => {
                this.call('async_job', 'complete', job.id);
            });
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
});

SystrayMenu.Items.push(AsyncJobSystrayMenu);
return AsyncJobSystrayMenu;
});
