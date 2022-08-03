/** @odoo-module **/

import { browser } from '@web/core/browser/browser';

import { Longpolling } from '@bus/longpolling_bus';

/**
 * CrossTab
 *
 * This is an extension of the longpolling bus with browser cross-tab synchronization.
 * It uses the multi_tab service.
 * - only the main tab handles longpolling.
 * - tabs are synchronized by means of the multi_tab service.
 *
 * multi_tab shared values are:
 * - channels : shared public channel list to listen during the poll
 * - options : shared options
 * - notification : the received notifications from the last poll
 *
 * trigger:
 * - notification : when a notification is receive from the long polling
 */
export class CrossTab extends Longpolling {
    constructor(env, services) {
        super(env, services);

        // properties
        this._isRegistered = false;

        var now = new Date().getTime();
        this._currentTabChannels = new Set();
        if (this.env.services['multi_tab'].getSharedValue('last_ts', 0) + 50000 < now) {
            this.env.services['multi_tab'].removeSharedValue('last');
        }
        this._lastNotificationID = this.env.services['multi_tab'].getSharedValue('last', 0);

        const onSharedValueUpdated = (event) => this._onSharedValueUpdated(event);
        const stopPolling = () => this.stopPolling();
        const startPolling = () => this.startPolling();
        services['multi_tab'].bus.addEventListener('shared_value_updated', onSharedValueUpdated);
        services['multi_tab'].bus.addEventListener('no_longer_main_tab', stopPolling);
        services['multi_tab'].bus.addEventListener('become_main_tab', startPolling);

        browser.addEventListener('unload', () => {
            services['multi_tab'].bus.removeEventListener('shared_value_updated', onSharedValueUpdated);
            services['multi_tab'].bus.removeEventListener('no_longer_main_tab', stopPolling);
            services['multi_tab'].bus.removeEventListener('become_main_tab', startPolling);
            this._currentTabChannels.clear();
            this._updateChannels();
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Share the bus channels with the others tab by the local storage
     *
     * @override
     */
    addChannel(channel) {
        this._currentTabChannels.add(channel);
        super.addChannel(channel);
        this._updateChannels();
    }

    /**
     * Share the bus channels with the others tab by the local storage
     *
     * @override
     */
    deleteChannel(channel) {
        this._currentTabChannels.delete(channel);
        super.deleteChannel(channel);
        this._updateChannels();
    }

    /**
     * Use the local storage to share the long polling from the master tab.
     *
     * @override
     */
    startPolling() {
        if (!this._isRegistered) {
            this._isRegistered = true;

            if (this.env.services['multi_tab'].isOnMainTab()) {
                this.env.services['multi_tab'].setSharedValue('options', this._options);
            } else {
                this._options = this.env.services['multi_tab'].getSharedValue('options', this._options);
            }
            this._updateChannels();
        }

        if (this.env.services['multi_tab'].isOnMainTab()) {
            super.startPolling();
        }
    }

    /**
     * Share the option with the local storage
     *
     * @override
     */
    updateOption(key, value) {
        super.updateOption(key, value);
        this.env.services['multi_tab'].setSharedValue('options', this._options);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Update localstorage channels of with the channels of this tab.
     *
     * @private
     * @return {boolean} true if the aggregated channels has changed.
     */
    _updateChannels() {
        const currentPeerIds = new Set(Object.keys(this.env.services['multi_tab'].getSharedValue('lastPresenceByTab', {})));
        const peerChannels = this.env.services['multi_tab'].getSharedValue('channels', {});
        const peerChannelsBefore = JSON.stringify(peerChannels);
        peerChannels[this._id] = Array.from(this._currentTabChannels);

        // Clean outdated channels.
        for (const channelPeerId of Object.keys(peerChannels)) {
            if (!currentPeerIds.has(channelPeerId)) {
                delete peerChannels[channelPeerId];
            }
        }

        const peerChannelsAfter = JSON.stringify(peerChannels);
        if (peerChannelsBefore !== peerChannelsAfter) {
            this.env.services['multi_tab'].setSharedValue('channels', peerChannels);
        }

        const allChannels = new Set();
        for (const channels of Object.values(peerChannels)) {
            for (const channel of channels) {
                allChannels.add(channel);
            }
        }
        // Insure the current tab channels are always in the aggregated channels
        // in case this tab is not in the currentPeerIds nor peerChannels.
        for (const channel of this._currentTabChannels) {
            allChannels.add(channel);
        }
        const allChannelsSorted = Array.from(allChannels).sort();
        if (JSON.stringify(allChannelsSorted) === JSON.stringify(this._channels.sort())) {
            return false;
        } else {
            this._channels = allChannelsSorted;
            return true;
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * If it's the master tab, the notifications ares broadcasted to other tabs by the
     * local storage.
     *
     * @override
     */
    _onPoll(notifications) {
        var notifs = super._onPoll(notifications);
        if (this.env.services['multi_tab'].isOnMainTab() && notifs.length) {
            this.env.services['multi_tab'].setSharedValue('last', this._lastNotificationID);
            this.env.services['multi_tab'].setSharedValue('last_ts', new Date().getTime());
            this.env.services['multi_tab'].setSharedValue('notification', notifs);
        }
    }

    /**
     * Handler when a shared value is updated.
     *
     * @private
     * @param {CustomEvent} ev
     * @param {object} [ev.detail]
     * @param {string} [ev.detail.key] Key of the value that have changed.
     * @param {any} [ev.detail.newValue] New value associated to the key.
     */
    _onSharedValueUpdated({ detail }) {
        const { key, newValue } = detail;
        const value = JSON.parse(newValue);

        // last notification id changed
        if (key === 'last') {
            this._lastNotificationID = value || 0;
        }
        // notifications changed
        else if (key === 'notification') {
            if (!this.env.services['multi_tab'].isOnMainTab()) {
                this.trigger("notification", value);
            }
        }
        // update channels
        else if (key === 'channels') {
            if (this._updateChannels()) {
                this._restartPolling();
            };
        }
        // update options
        else if (key === 'options') {
            this._options = value;
        }
    }

}
