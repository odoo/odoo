odoo.define('bus.AsyncJobService', function (require) {
"use strict";

const AbstractService = require('web.AbstractService');
const { serviceRegistry, bus, _lt, _t } = require('web.core');
const { blockUI, unblockUI } = require("web.framework");
const session = require('web.session');

/**
 * @typedef jobstate
 * @enum {string}
 */
const CREATED = 'created';        // the task has been enqueued for later processing
const PROCESSING = 'processing';  // a worker begins to process the task
const SUCCEEDED = 'succeeded';    // the task succeeded with a result the user must process
const DONE = 'done';              // the task succeeded without result or the user processed it
const FAILED = 'failed';          // the task failed with an error
const STATE_ORDER = [CREATED, PROCESSING, SUCCEEDED, FAILED, DONE];


const TASK_CREATED_TITLE = _lt("Background task created");
const TASK_CREATED_CONTENT = _lt("The task %s has been scheduled for processing and will start shortly.");
const TASK_DONE_TITLE = _lt("Background task completed");
const TASK_PROCESSING_CONTENT = _lt("The task %s has been moved to the background.");
const TASK_SUCCEEDED_CONTENT = _lt("The task %s is ready, you can resume its execution via the task list.");
const TASK_FAILED_CONTENT = _lt("The task %s failed, you can show the error via the task list.");
const TASK_DONE_CONTENT = _lt("The task %s has been completed by the server.");

/**
 * Async service help, watch the longpolling bus for notifications sent
 * by ir.async upon job creation, processing and termination. Keep an
 * internal database of all known jobs plus send events on the ``async_job``
 * core bus.
 */
const AsyncJobService = AbstractService.extend({
    dependencies: ['bus_service', 'ajax', 'crash_manager'],

    /**
     * @override
     *
     * _jobs is a map jobid -> job object
     * _watchedJobs is a set containing all jobids we should automatically
     *     run when the job succeed or fail
     */
    init() {
        this._jobs = {};
        this._watchedJobs = {};
        return this._super(...arguments);
    },

    /**
     * @override
     */
    start() {
        this._super(...arguments);
        this.call('bus_service', 'onNotification', this, this._onNotification);
        this.dlJobs();
    },


    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Call an asynchronous capable endpoint, blocking the UI up to 5 seconds
     * for the asynchronous task to completes. Resolves when the asynchronous
     * background task completes.
     * 
     * @param {object} params ajax rpc params
     * @param {object} options ajac rpc options
     * @return {promise} resolved when the background task completes
     */
    asyncRpc(params, options) {
        // We take control of the blockUI
        options = options || {}
        options.shadow = true;
        blockUI();

        return new Promise((resolve, reject) => {

            // Call the async HTTP endpoint, he must return the asyncJobId
            this._rpc(params, options).then(({asyncJobId}) => {
                let UIBlocked = true;
                this._watchedJobs[asyncJobId] = {resolve, reject, UIBlocked};

                // We keep the UI blocked up to 5 seconds
                setTimeout(() => {
                    const job = this._jobs[asyncJobId];
                    const watchedJob = this._watchedJobs[asyncJobId];
                    if (watchedJob && watchedJob[2]) {
                        unblockUI();
                        this.do_notify(TASK_CREATED_TITLE, _.str.sprintf(TASK_PROCESSING_CONTENT.toString(), job.name));
                        this._watchedJobs[asyncJobId][2] = false;
                    }
                }, 5000);

                // In case the async job was so fast we got the response before
                // the HTTP result.
                if (asyncJobId in this._jobs) {
                    this._resumeWatchedJob(this._jobs[asyncJobId]);
                }
            }).catch(error => {
                unblockUI();
                this.call('crash_manager', 'rpc_error', error.error);
                reject(error);
            });
        });
    },


    /**
     * Update the internal job list
     */
    dlJobs() {
        this._rpc({
            model: 'ir.async',
            method: 'search_read',
            kwargs: {
                domain: [
                    ['user_id', '=', session.uid],
                    ['notify', '=', 1],
                    ['state', '!=', 'done'],
                ],
                fields: ['id', 'name', 'state', 'payload'],
            }
        }).then(jobs => {
            for (let job of jobs) {
                if (job.payload)
                    job.payload = JSON.parse(job.payload);
                this._jobs[job.id] = job;
            }
        })
    },

    /**
     * @return {object} job map id -> job
     */
    getJobs() {
        return this._jobs;
    },


    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Shows a notification for newly created jobs and when jobs are done
     * processing.
     *
     * @private
     * @param {Job} new job
     * @param {jobState} oldState
     */
    _notify(job, oldState) {
        if (job.state === CREATED) {
            this.do_notify(TASK_CREATED_TITLE, _.str.sprintf(TASK_CREATED_CONTENT.toString(), job.name));
        }

        if (oldState !== PROCESSING)
            return;

        switch (job.state) {
            case SUCCEEDED:
                this.do_notify(TASK_DONE_TITLE, _.str.sprintf(TASK_SUCCEEDED_CONTENT.toString(), job.name));
                break;
            case FAILED:
                this.do_warn(TASK_DONE_TITLE, _.str.sprintf(TASK_FAILED_CONTENT.toString(), job.name));
                break;
            case DONE:
                this.do_notify(TASK_DONE_TITLE, _.str.sprintf(TASK_DONE_CONTENT.toString(), job.name));
                break;
        }
    },

    /**
     * Resolve/reject the asyncRpc promise when 
     *
     * @private
     * @param {Job} new job
     * @param {jobState} oldState
     */
    _resumeWatchedJob(job) {
        if (STATE_ORDER.indexOf(job.state) < STATE_ORDER.indexOf(SUCCEEDED)) {
            return
        }

        const {resolve, reject, UIBlocked} = this._watchedJobs[job.id];
        delete this._watchedJobs[job.id];

        if (UIBlocked) {
            unblockUI();
        }
        if (job.state === FAILED) {
            this.call('crash_manager', 'rpc_error', job.payload.error);
            reject({message: job.payload.error, event: $.Event()});
        } else {
            resolve(job);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Dispatch a core bus event on async job update
     *
     * @private
     * @param {Object[]]} notifications
     * @param {string} notifications[i].type
     * @param {integer} notifications[i].id
     * @param {string} notifications[i].name
     * @param {jobstate} notifications[i].state
     * @param {Object} [notifications[i].payload]
     */
    _onNotification(notifications) {
        for (const notif of notifications) {
            if (notif[1].type !== 'ir.async')
                continue

            /**
             * @typedef Job
             * @type {object}
             * @property {number} id - record id
             * @property {string} name - description
             * @property {jobstate} state - current processing state
             * @property {?Object} payload - optionnal payload for succeeded and failed jobs
             */
            const job = {
                id: notif[1].id,
                name: notif[1].name,
                state: notif[1].state,
                payload: notif[1].payload,
            }

            // Discard jobs that are in a previous stage
            const oldJob = this._jobs[job.id] || {};
            if (STATE_ORDER.indexOf(job.state) < STATE_ORDER.indexOf(oldJob.state))
                continue;

            // Update internal jobs db and relay the event
            this._jobs[job.id] = job;
            if (job.id in this._watchedJobs) {
                this._resumeWatchedJob(job);
            } else if (job.name) {
                this._notify(job, oldJob.state);
            }
            bus.trigger('async_job', job);
        }
    },
});

serviceRegistry.add('async_job', AsyncJobService);
return {
    'AsyncJobService': AsyncJobService,
    'asyncJobState': {CREATED, PROCESSING, SUCCEEDED, FAILED, DONE}
};

});
