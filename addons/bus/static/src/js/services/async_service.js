odoo.define('bus.AsyncJobService', function (require) {
"use strict";

const AbstractService = require('web.AbstractService');
const { serviceRegistry, bus, _lt, _t } = require('web.core');
const framework = require('web.framework');
const session = require('web.session');
const {CREATED, PROCESSING, FAILED, SUCCEEDED, DONE} = require('bus.AsyncJobStates')

/* A status change should always go torward DONE, this list helps ensuring it. */
const STATE_ORDER = [CREATED, PROCESSING, FAILED, SUCCEEDED, DONE];

/* A few notification template messages */
const TASK_CREATED_TITLE = _lt("Background task created");
const TASK_CREATED_CONTENT = _lt("The task %s has been scheduled for processing and will start shortly.");
const TASK_DONE_TITLE = _lt("Background task completed");
const TASK_PROCESSING_CONTENT = _lt("The task %s has been moved to the background.");
const TASK_SUCCEEDED_CONTENT = _lt("The task %s is ready, you can resume its execution via the task list.");
const TASK_FAILED_CONTENT = _lt("The task %s failed, you can show the error via the task list.");
const TASK_DONE_CONTENT = _lt("The task %s has been completed by the server.");


/**
 * The AsyncJobService is the frontend service companion to the backend ir.async model. It keeps
 * track of the backend asynchronous jobs created for this user by listening for web notifications
 * and relay those notifications to the core bus.
 *
 * This service also offers the asyncRpc function that acts like _rpc but resolves when the
 * background asynchronous task finishes instead of when the initial HTTP request responses.
 */
const AsyncJobService = AbstractService.extend({
    dependencies: ['ajax', 'bus_service', 'crash_manager'],

    /**
     * @override
     */
    init() {
        this._super(...arguments);

        /**
         * Internal map listing all known asynchronous background job, indexed by jobid.
         */
        this._jobs = {};

        /**
         * Internal map linking jobs created via asyncRpc to an object triple {resolve, reject,
         * UIBlocked}. The two first elements are used to resolve or reject the promise returned,
         * by asyncRpc, the third element describe the framework.blockUI() status (whether it is
         * block or unblock as-per this service).
         */
        this._watchedJobs = {};
    },

    /**
     * @override
     */
    start() {
        this._super(...arguments);
        this.call('bus_service', 'onNotification', this, this._onNotification);
        this._fetchJobs();
    },


    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Call an asynchronous capable endpoint, blocking the UI up to 5 seconds
     * to give a chance fast async task to complete like if they were executed
     * the normal "_rpc"-like way. Resolves when the asynchronous background
     * task succeed. Rejects when the asynchronous background task fails.
     * 
     * @param {Object} params ajax rpc params
     * @param {Object} options ajac rpc options
     * @return {promise} resolved when the background task completes
     */
    asyncRpc(params, options) {
        options = options || {}

        // We take control of the blockUI unless options.shadow is set
        let UIBlocked = false;
        if (!options.shadow) {
            UIBlocked = true;
            framework.blockUI()
        }
        options.shadow = true;

        return new Promise((resolve, reject) => {

            // Call an async HTTP endpoint, he must return an asyncJobId
            this._rpc(params, options).then(({asyncJobId}) => {

                if (asyncJobId === undefined) {
                    framework.unblockUI();
                    console.error("Missing asyncJobId");
                    reject();
                    return;
                }
                this._watchedJobs[asyncJobId] = {resolve, reject, UIBlocked};

                // We keep the UI blocked maximum 5 seconds
                if (UIBlocked) {
                    setTimeout(() => {
                        const job = this._jobs[asyncJobId];
                        const watchedJob = this._watchedJobs[asyncJobId];
                        if (watchedJob && watchedJob.UIBlocked) {
                            framework.unblockUI();
                            this.do_notify(TASK_CREATED_TITLE, _.str.sprintf(TASK_PROCESSING_CONTENT.toString(), job.name));
                            watchedJob.UIBlocked = false;
                        }
                    }, 5000);
                }

                /* The _jobs mapping is populated and updated in _onNotification for every job
                   update. There is a chance the asynchronous job finished before the HTTP
                   request. In such case we should resume the job right now. */
                const job = this._jobs[asyncJobId];
                if (job && STATE_ORDER.indexOf(job.state) > STATE_ORDER.indexOf(PROCESSING)) {
                    this._resumeWatchedJob(job);
                }

            }).catch(error => {
                framework.unblockUI();
                if (error.error) {
                    this.call('crash_manager', 'rpc_error', error.error);
                }
                reject(error);
            });
        });
    },

    /**
     * @return {object} map listing all known asynchronous background job, indexed by jobid
     */
    getJobs() {
        return this._jobs;
    },


    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Fetch the async jobs of current user.
     */
    async _fetchJobs() {
        const jobs = await this._rpc({
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
        })
        for (let job of jobs) {
            if (job.payload)
                job.payload = JSON.parse(job.payload);
            this._jobs[job.id] = job;
        }
    },

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

        if (oldState !== PROCESSING) {
            return;
        }

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
     * @param {job} job that is either failed, succeeded, or done
     */
    _resumeWatchedJob(job) {
        const {resolve, reject, UIBlocked} = this._watchedJobs[job.id];
        delete this._watchedJobs[job.id];

        if (UIBlocked) {
            framework.unblockUI();
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
            if (STATE_ORDER.indexOf(job.state) < STATE_ORDER.indexOf(oldJob.state)) {
                continue;
            }

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
return AsyncJobService;

});
