odoo.define('bus.CrossTab', function (require) {
"use strict";

const Longpolling = require('bus.Longpolling');

const PREFIX = "crosstab-bus";

/**
 * CrossTab
 *
 * This is an extension of the longpolling bus with browser cross-tab synchronization.
 * It uses a Master/Slaves with Leader Election architecture:
 * - a single tab handles longpolling.
 * - tabs are synchronized by means of the local storage.
 */
const CrossTabBus = Longpolling.extend({
    PING_TIMEOUT: 50,
    TAB_TIMEOUT: 5*1000,

    /**
     * @override
     */
    init() {
        this._super(...arguments);
        const now = Date.now();
        const tabId = `${_.uniqueId(`${PREFIX}:`)}:${now}`;
        const tab = {
            id: tabId,
            timestamp: now,
        };
        const masterTabTimestamp = this
            ._getFromStorage('master-timestamp', { data: 0 })
            .data;
        const masterTabId = (now - masterTabTimestamp < this.TAB_TIMEOUT)
            ? this
                ._getFromStorage('master-id', { data: null })
                .data
            : null;
        this._beforeunloadGlobalListener = ev => this._onBeforeunload(ev);
        this._heartbeatTimeout = null;
        this._isSelfPromotingMasterTab = false;
        this._masterTabId = masterTabId;
        this._tab = tab;
        this._tabId = tabId;
        this._tabs = Object.assign(
            {},
            this
                ._getFromStorage('tabs', { data: {} })
                .data,
            { [tabId]: tab }
        );
        window.addEventListener('beforeunload', this._beforeunloadGlobalListener);
        this.call('local_storage', 'onStorage', this, this._onStorage);
    },
    /**
     * @override
     */
    destroy() {
        window.removeEventListener('beforeunload', this._beforeunloadGlobalListener);
        this._clearTimeout(this._heartbeatTimeout);
        if (Object.keys(this._tabs).length === 1) {
            this._broadcast('tabs', {});
        } else {
            this._broadcast('tab-close', this._tabId);
        }
        if (this._masterTabId === this._tabId) {
            this._broadcast('master-id', null);
            this._broadcast('master-timestamp', null);
        }
        this._super();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    addChannel(channel) {
        if (this._channels.includes(channel)) {
            return;
        }
        this._super(...arguments);
        if (this._masterTabId === this._tabId) {
            this._broadcast('channels', this._channels);
        } else {
            this._broadcast('add-channel', channel, this._masterTabId);
        }
    },
    /**
     * @override
     */
    deleteChannel(channel) {
        if (!this._channels.includes(channel)) {
            return;
        }
        this._super(...arguments);
        if (this._masterTabId === this._tabId) {
            this._broadcast('channels', this._channels);
        } else {
            this._broadcast('delete-channel', channel, this._masterTabId);
        }
    },
    /**
     * @return {string}
     */
    getTabId() {
        return this._tabId;
    },
    /**
     * Use the local storage to share the long polling from the master tab.
     *
     * @override
     */
    startPolling() {
        this._heartbeat();
        if (this._masterTabId !== this._tabId) {
            return;
        }
        this._super(...arguments);
    },
    /**
     * @override
     */
    updateOptions(key, value) {
        this._super(...arguments);
        if (this._masterTabId === this._tabId) {
            this._broadcast('options', this._options);
        } else {
            this._broadcast('update-option', { key, value }, this._masterTabId);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} name
     * @param {any} [data]
     * @param {string} [to] tab id
     */
    _broadcast(name, data, to) {
        const message = {
            data,
            from: this._tabId,
            name,
            timestamp: Date.now(),
            to,
        };
        if (
            name === 'channels' ||
            name === 'master-id' ||
            name === 'master-timestamp' ||
            name === 'options' ||
            name === 'tabs'
        ) {
            this.call('local_storage', 'setItem', `${PREFIX}:${name}`, message);
            if (!data) {
                this.call('local_storage', 'removeItem', `${PREFIX}:${name}`);
            }
        } else {
            this.call('local_storage', 'setItem', `${PREFIX}:${name}`, message);
            this.call('local_storage', 'removeItem', `${PREFIX}:${name}`);
        }
        const ev = new Event('storage');
        Object.assign(ev, {
            key: `${PREFIX}:${name}`,
            newValue: message,
        });
        window.dispatchEvent(ev);
    },
    /**
     * Useful for mocking timeouts in tests
     *
     * @private
     * @param {integer} timeoutId
     */
    _clearTimeout(timeoutId) {
        clearTimeout(timeoutId);
    },
    /**
     * @private
     */
    _electMasterTab() {
        const mostRecentTab = Object
            .values(this._tabs)
            .sort((tab1, tab2) => tab1.timestamp < tab2.timestamp ? -1 : 1)
            .shift();
        if (this._tabId === mostRecentTab.id) {
            if (this._isSelfPromotingMasterTab) {
                return;
            }
            this._isSelfPromotingMasterTab = true;
            this._broadcast('master-id', this._tabId);
            this._broadcast('tab-promote');
            this._setTimeout(
                () => {
                    if (this.isDestroyed()) {
                        return;
                    }
                    this._isSelfPromotingMasterTab = false;
                    this._masterTabId = this
                        ._getFromStorage('master-id', { data: null })
                        .data;
                    if (this._masterTabId === this._tabId) {
                        this.startPolling();
                    }
                }, this.PING_TIMEOUT);
        }
    },
    /**
     * @private
     * @param {string} key
     * @param {any} [defaultValue]
     * @return {any}
     */
    _getFromStorage(key, defaultValue) {
        return this.call('local_storage', 'getItem', `${PREFIX}:${key}`, defaultValue);
    },
    /**
     * @private
     */
    _heartbeat() {
        if (this.isDestroyed()) {
            return;
        }
        const now = Date.now();
        this._clearTimeout(this._heartbeatTimeout);
        this._heartbeatTimeout = this._setTimeout(
            () => this._heartbeat(),
            500 + Math.round(Math.random()*500));
        if (!this._tabs[this._masterTabId]) {
            this._electMasterTab();
        }
        this._tab.lastUpdated = now;
        if (this._masterTabId === this._tabId) {
            this._broadcast('master-timestamp', now);
        }
        this._broadcast('ping', this._tab);
        for (const tab of Object.values(this._tabs)) {
            if (now - tab.lastUpdated > this.TAB_TIMEOUT) {
                this._broadcast('tab-close', tab.id);
            }
        }
    },
    /**
     * Useful to mock timeouts in tests
     *
     * @private
     * @param {Function} func
     * @param {integer} duration
     * @return {integer}
     */
    _setTimeout(func, duration) {
        return setTimeout(func, duration);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onBeforeunload() {
        this.destroy();
    },
    /**
     * @private
     * @param {Object} message
     * @param {string} message.data channel to add
     */
    _onCrosstabAddChannel(message) {
        if (this._channels.includes(message.data)) {
            return;
        }
        this.addChannel(message.data);
    },
    /**
     * @private
     * @param {Object} message
     * @param {string[]} message.data
     */
    _onCrosstabChannels(message) {
        this._channels = message.data;
    },
    /**
     * @private
     * @param {Object} message
     * @param {string} message.data channel to delete
     */
    _onCrosstabDeleteChannel(message) {
        if (!this._channels.includes(message.data)) {
            return;
        }
        this.deleteChannel(message.data);
    },
    /**
     * @private
     * @param {Object} message
     * @param {string|null} message.data
     */
    _onCrosstabMasterId(message) {
        this._masterTabId = message.data;
    },
    /**
     * @private
     * @param {Object} message
     * @param {Object[]} message.data
     */
    _onCrosstabNotifications(message) {
        this._parseAndTriggerNotifications(message.data);
    },
    /**
     * @private
     * @param {Object} message
     * @param {Object} message.data
     * @param {string} message.data.id tab id
     * @param {integer} message.data.timestamp datetime
     */
    _onCrosstabPing(message) {
        if (Date.now() - message.data.timestamp > this.PING_TIMEOUT) {
            return;
        }
        this._tabs[message.data.id] = message.data;
        this._setTimeout(
            () => {
                if (this.isDestroyed()) {
                    return;
                }
                if (!this._tabs[this._masterTabId]) {
                    this._electMasterTab();
                } else if (this._masterTabId === this._tabId) {
                    this._broadcast('tabs', this._tabs);
                }
            },
            this.PING_TIMEOUT);
        this._tab.lastUpdated = Date.now();
        this._broadcast('pong', this._tab);
    },
    /**
     * @private
     * @param {Object} message
     * @param {Object} message.data
     * @param {string} message.data.id tab id
     * @param {integer} message.data.timestamp datetime
     */
    _onCrosstabPong(message) {
        if (Date.now() - message.data.timestamp > this.PING_TIMEOUT) {
            return;
        }
        this._tabs[message.data.id] = message.data;
    },
    /**
     * @private
     * @param {Object} message
     * @param {string} message.data tab id
     */
    _onCrosstabTabClose(message) {
        const tabId = message.data;
        delete this._tabs[tabId];
        if (!this._masterTabId || this._masterTabId === tabId) {
            this._masterTabId = null;
            this._electMasterTab();
        } else if (this._masterTabId === this._tabId) {
            this._broadcast('tabs', this._tabs);
        }
    },
    /**
     * @private
     */
    _onCrosstabTabPromote() {
        this._masterTabId = this
            ._getFromStorage('master-id', { data: null })
            .data;
    },
    /**
     * @private
     * @param {Object} message
     * @param {Object} message.data
     * @param {string} message.data.key
     * @param {any} message.data.value
     */
    _onCrosstabUpdateOption(message) {
        this.updateOptions(message.data.key, message.data.value);
    },
    /**
     * @private
     * @param {Object} message
     * @param {Object} message.data
     */
    _onCrosstabOptions(message) {
        this._options = message.data;
    },
    /**
     * @private
     * @param {Object} ev
     * @param {Object[]} message.data
     */
    _onCrosstabTabs(message) {
        const selfTab = {};
        selfTab[this._tabId] = this._tab;
        this._tabs = Object.assign(
            {},
            message.data,
            selfTab
        );
    },
    /**
     * @override
     * @private
     */
    _onPoll(notifications) {
        this._broadcast('notifications', notifications);
        return this._super(...arguments);
    },
    /**
     * Handler when the local storage is updated
     *
     * @private
     * @param {StorageEvent} ev
     */
    _onStorage(ev) {
        if (!ev.newValue) {
            return;
        }
        if (!ev.key.startsWith(PREFIX)) {
            return;
        }
        const type = ev.key.substr(PREFIX.length + 1); // ':'
        let message;
        try {
            message = JSON.parse(ev.newValue);
        } catch (error) {
            return;
        }
        if (!message) {
            return;
        }
        if (message.from && message.from === this._tabId) {
            return;
        }
        if (message.to && message.to !== this._tabId) {
            return;
        }
        switch (type) {
            case 'add-channel':
                this._onCrosstabAddChannel(message);
                break;
            case 'channels':
                this._onCrosstabChannels(message);
                break;
            case 'delete-channel':
                this._onCrosstabDeleteChannel(message);
                break;
            case 'master-id':
                this._onCrosstabMasterId(message);
                break;
            case 'notifications':
                this._onCrosstabNotifications(message);
                break;
            case 'options':
                this._onCrosstabOptions(message);
                break;
            case 'ping':
                this._onCrosstabPing(message);
                break;
            case 'pong':
                this._onCrosstabPong(message);
                break;
            case 'tabs':
                this._onCrosstabTabs(message);
                break;
            case 'tab-close':
                this._onCrosstabTabClose(message);
                break;
            case 'tab-promote':
                this._onCrosstabTabPromote(message);
                break;
            case 'update-option':
                this._onCrosstabUpdateOption(message);
                break;
        }
    },
});

return CrossTabBus;

});

