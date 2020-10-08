odoo.define('bus.AsyncJobStates', function (require) {
"use strict";

/**
 * 
 * Those states reflect the current processing status of an asynchronous task.
 *
 *                                  ---> FAILED
 *                                 / yes
 * CREATED -> PROCESSING -> error ?               ---> DONE
 *                                 \ no          / no (async function returned None)
 *                                  ---> result ?
 *                                               \ yes                                     
 *                                                ---> SUCCEEDED --result gathered/processed--> DONE
 *
 * @typedef jobstate
 * @enum {string}
 */
const CREATED = 'created';        // the task has been enqueued server-side for later processing
const PROCESSING = 'processing';  // a worker begins to process the task
const FAILED = 'failed';          // the task finished with an error
const SUCCEEDED = 'succeeded';    // the task finished with a result the user must process
const DONE = 'done';              // the task finished without result or the succeeded's state result was processed

return {CREATED, PROCESSING, FAILED, SUCCEEDED, DONE};

});
