/** @odoo-module **/

export class CycleInfo {

    constructor(manager) {
        this.manager = manager;
        /**
         * Set of records that have been created during the current update
         * cycle and for which the compute/related methods still have to be
         * executed a first time.
         */
        this.newCompute = new Set();
        /**
         * Set of records that have been created during the current update
         * cycle and for which the _created method still has to be executed.
         */
        this.newCreated = new Set();
        /**
         * Set of records that have been created during the current update
         * cycle and for which the onChange methods still have to be executed
         * a first time.
         */
        this.newOnChange = new Set();
        /**
         * Map of listeners that should be notified as part of the current
         * update cycle. Value contains list of info to help for debug.
         */
        this.notifyNow = new Map();
        /**
         * Map of listeners that should be notified at the end of the current
         * update cycle. Value contains list of info to help for debug.
         */
        this.notifyAfter = new Map();
        /**
         * Set of records that have been updated during the current update cycle
         * and for which required fields check still has to be executed.
         */
        this.check = new Set();
    }

}
