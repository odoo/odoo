odoo.define('bus.CrossTab2', function (require) {
"use strict";

const Longpolling = require('bus.Longpolling');

const CrossTabBus = Longpolling.extend({

    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this._unloadGlobalEventListener = ev => this._onUnloadGlobal(ev);
        this._heartbeatInterval = null;
        this._isMasterTab = false;
        this._isRegistered = false;
        this._tabId = `${_.uniqueId('crosstab-bus:')}:${Date.now()}`;
        this._worker = new window.SharedWorker('/bus/static/src/js/crosstab_bus_2_worker.js');

        this._worker.port.onmessage = ev => this._onMessage(ev);
        this._worker.port.postMessage(['tab:register', this._tabId]);

        window.addEventListener('unload', this._unloadGlobalEventListener);
    },
    /**
     * @override
     */
    destroy() {
        this._super();
        clearInterval(this._heartbeatInterval);
        this._worker.port.postMessage(['tab:unregister', this._tabId]);
        window.removeEventListener('unload', this._unloadGlobalEventListener);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Share the bus channels with the others tab by shared worker
     *
     * @override
     * @param {string} channel
     */
    addChannel(channel) {
        this._worker.port.postMessage(['tab:add-channel', channel]);
        if (!this._isRegistered) {
            return;
        }
        this._super(...arguments);
    },
    /**
     * Share the bus channels with the others tab by shared worker
     *
     * @override
     * @param {string} channel
     */
    deleteChannel(channel) {
        this._worker.port.postMessage('tab:delete-channel', channel);
        if (!this._isRegistered) {
            return;
        }
        this._super(...arguments);
    },
    /**
     * @return {string}
     */
    getTabId() {
        return this._tabId;
    },
    /**
     * Tells whether this bus is related to the master tab.
     *
     * @return {boolean}
     */
    isMasterTab() {
        return this._isMasterTab;
    },
    /**
     * Use the shared worker to share the long polling from the master tab.
     *
     * @override
     */
    startPolling() {
        this._heartbeat();
        this._heartbeatInterval = setInterval(() => this._heartbeat(), 5*1000);
        if (this._isMasterTab) {
            this._super(...arguments);
        }
    },
    /**
     * Share the option with the shared worker
     *
     * @override
     * @param {string} key
     * @param {any} value
     * @param {Object} [param2={}]
     * @param {boolean} [param2.isFromWorker=false]
     */
    updateOption(key, value, { isFromWorker=false }={}) {
        if (!isFromWorker) {
            this._worker.port.postMessage(['tab:update-option', key, value]);
        }
        if (!this._isRegistered) {
            return;
        }
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _heartbeat() {
        this._worker.port.postMessage(['tab:heartbeat', this._tabId]);
    },
    /**
     * @override
     * @private
     * @param {integer|null} [lastPresenceTime]
     * @param {Object} [param0={}]
     * @param {boolean} [param0.isFromWorker=false]
     */
    _updateLastPresenceTime(lastPresenceTime, { isFromWorker=false }={}) {
        this._super(...arguments);
        if (!isFromWorker && this._worker) {
            this._worker.port.postMessage(['tab:last-presence', this._getLastPresence()]);
        }
    },
    /**
     * @override
     * @private
     * @param {boolean} focus
     * @param {Object} [param1={}]
     * @param {boolean} [param1.isFromWorker=false]
     */
    _updateOdooFocus(focus, { isFromWorker=false }={}) {
        this._super(...arguments);
        if (!isFromWorker) {
            this._worker.port.postMessage(['tab:focus', this.isOdooFocused()]);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MessageEvent} ev
     * @param {Array} ev.data
     * @param {string} ev.data[0] name of event
     * @param {...any} [ev.data[1..n]]
     */
    _onMessage(ev) {
        const type = ev.data[0];
        const args = ev.data.slice(1);
        switch (type) {
            case 'worker:add-channel':
                this._onMessageWorkerAddChannel(...args);
                break;
            case 'worker:channels':
                this._onMessageWorkerChannels(...args);
                break;
            case 'worker:delete-channel':
                this._onMessageWorkerDeleteChannel(...args);
                break;
            case 'worker:focus':
                this._onMessageWorkerFocus(...args);
                break;
            case 'worker:last-presence':
                this._onMessageWorkerLastPresence(...args);
                break;
            case 'worker:master':
                this._onMessageWorkerMaster(...args);
                break;
            case 'worker:notifications':
                this._onMessageWorkerNotifications(...args);
                break;
            case 'worker:options':
                this._onMessageWorkerOptions(...args);
                break;
            case 'worker:update-option':
                this._onMessageWorkerUpdateOption(...args);
                break;
        }
    },
    /**
     * @private
     * @param {string} channel
     */
    _onMessageWorkerAddChannel(channel) {
        if (this._channels.includes(channel)) {
            return;
        }
        this.addChannel(channel);
    },
    /**
     * @private
     * @param {string[]} channels
     * @param {string} tabId
     */
    _onMessageWorkerChannels(channels, tabId) {
        if (this._tabId !== tabId) {
            return;
        }
        this._channels = channels;
    },
    /**
     * @private
     * @param {string} channel
     */
    _onMessageWorkerDeleteChannel(channel) {
        if (!this._channels.includes(channel)) {
            return;
        }
        this.deleteChannel(channel);
    },
    /**
     * @private
     * @param {boolean} focus
     */
    _onMessageWorkerFocus(focus) {
        this._updateOdooFocus(focus, { isFromWorker: true });
    },
    /**
     * @private
     */
    _onMessageWorkerLastPresence(lastPresenceTime) {
        this._updateLastPresenceTime(lastPresenceTime, { isFromWorker: true });
    },
    /**
     * @private
     * @param {string} tabId
     */
    _onMessageWorkerMaster(tabId) {
        if (
            this._isMasterTab &&
            this._tabId === tabId
        ) {
            return;
        }
        if (
            this._isMasterTab &&
            this._tabId !== tabId
        ) {
            console.warn('current master sees new elected master?!?');
            this._isMasterTab = false;
            this.stopPolling();
        }
        if (this._tabId === tabId) {
            this._isMasterTab = true;
            this.startPolling();
        }
    },
    /**
     * @private
     * @param {Object[]} notifications
     */
    _onMessageWorkerNotifications(notifications) {
        this._parseAndTriggerNotifications(notifications);
    },
    /**
     * @private
     * @param {Object} options
     * @param {string} tabId
     */
    _onMessageWorkerOptions(options, tabId) {
        if (this._tabId !== tabId) {
            return;
        }
        this._channels = options;
    },
    /**
     * @private
     * @param {string} key
     * @param {any} value
     */
    _onMessageWorkerUpdateOption(key, value) {
        this.updateOption(key, value, { isFromWorker: true });
    },
    /**
     * If it's the master tab, the notifications ares broadcasted to other tabs by the
     * local storage.
     *
     * @override
     * @private
     * @param {Object[]} notifications
     * @return {Array[]}
     */
    _onPoll: function (notifications) {
        this._worker.port.postMessage(['tab:notifications', notifications]);
        return this._super(...arguments);
    },
    /**
     * @private
     */
    _onUnloadGlobal() {
        this.destroy();
    },
});

return CrossTabBus;

});

