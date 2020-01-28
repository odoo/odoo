odoo.define('bus.CrossTab', function (require) {
"use strict";

var Longpolling = require('bus.Longpolling');

var session = require('web.session');

/**
 * CrossTab
 *
 * This is an extension of the longpolling bus with browser cross-tab synchronization.
 * It uses a Master/Slaves with Leader Election architecture:
 * - a single tab handles longpolling.
 * - tabs are synchronized by means of the local storage.
 *
 * localStorage used keys are:
 * - {LOCAL_STORAGE_PREFIX}.{sanitizedOrigin}.channels : shared public channel list to listen during the poll
 * - {LOCAL_STORAGE_PREFIX}.{sanitizedOrigin}.options : shared options
 * - {LOCAL_STORAGE_PREFIX}.{sanitizedOrigin}.notification : the received notifications from the last poll
 * - {LOCAL_STORAGE_PREFIX}.{sanitizedOrigin}.tab_list : list of opened tab ids
 * - {LOCAL_STORAGE_PREFIX}.{sanitizedOrigin}.tab_master : generated id of the master tab
 *
 * trigger:
 * - window_focus : when the window is focused
 * - notification : when a notification is receive from the long polling
 * - become_master : when this tab became the master
 * - no_longer_master : when this tab is not longer the master (the user swith tab)
 */

class CrossTabBus extends Longpolling {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        var now = new Date().getTime();
        // used to prefix localStorage keys
        this._sanitizedOrigin = session.origin.replace(/:\/{0,2}/g, '_');
        // prevents collisions between different tabs and in tests
        this._id = _.uniqueId(this.LOCAL_STORAGE_PREFIX) + ':' + now;
        if (this._callLocalStorage('getItem', 'last_ts', 0) + 50000 < now) {
            this._callLocalStorage('removeItem', 'last');
        }
        this._lastNotificationID = this._callLocalStorage('getItem', 'last', 0);
        this.env.services.local_storage.onStorage(this, this._onStorage);
    }

    /**
     * @override
     */
    destroy() {
        super.destroy();
        clearTimeout(this._heartbeatTimeout);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Share the bus channels with the others tab by the local storage
     *
     * @override
     * @param {...any} args
     */
    addChannel(...args) {
        super.addChannel(...args);
        this._callLocalStorage('setItem', 'channels', this._channels);
    }

    /**
     * Share the bus channels with the others tab by the local storage
     *
     * @override
     * @param {...any} args
     */
    deleteChannel(...args) {
        super.deleteChannel(...args);
        this._callLocalStorage('setItem', 'channels', this._channels);
    }

    /**
     * @return {string}
     */
    getTabId() {
        return this._id;
    }

    /**
     * Tells whether this bus is related to the master tab.
     *
     * @returns {boolean}
     */
    isMasterTab() {
        return this._isMasterTab;
    }

    /**
     * Use the local storage to share the long polling from the master tab.
     *
     * @override
     * @param {...any} args
     */
    startPolling(...args) {
        if (this._isActive === null) {
            this._heartbeat = this._heartbeat.bind(this);
        }
        if (!this._isRegistered) {
            this._isRegistered = true;

            var peers = this._callLocalStorage('getItem', 'peers', {});
            peers[this._id] = new Date().getTime();
            this._callLocalStorage('setItem', 'peers', peers);

            this._registerWindowUnload();

            if (!this._callLocalStorage('getItem', 'master')) {
                this._startElection();
            }

            this._heartbeat();

            if (this._isMasterTab) {
                this._callLocalStorage('setItem', 'channels', this._channels);
                this._callLocalStorage('setItem', 'options', this._options);
            } else {
                this._channels = this._callLocalStorage('getItem', 'channels', this._channels);
                this._options = this._callLocalStorage('getItem', 'options', this._options);
            }
            return;  // startPolling will be called again on tab registration
        }

        if (this._isMasterTab) {
            super.startPolling(...args);
        }
    }

    /**
     * Share the option with the local storage
     *
     * @override
     * @param {...any} args
     */
    updateOption(...args) {
        super.updateOption(...args);
        this._callLocalStorage('setItem', 'options', this._options);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Call local_storage service
     *
     * @private
     * @param {string} methodName (getItem, setItem, removeItem, on)
     * @param {string} key
     * @param {any} param
     * @returns service information
     */
    _callLocalStorage(methodName, key, param) {
        return this.env.services.local_storage[methodName](this._generateKey(key), param);
    }

    /**
     * Generates localStorage keys prefixed by bus. (LOCAL_STORAGE_PREFIX = the name
     * of this addon), and the sanitized origin, to prevent keys from
     * conflicting when several bus instances (polling different origins)
     * co-exist.
     *
     * @private
     * @param {string} key
     * @returns key prefixed with the origin
     */
    _generateKey(key) {
        return this.LOCAL_STORAGE_PREFIX + '.' + this._sanitizedOrigin + '.' + key;
    }

    /**
     * @override
     * @returns {integer} number of milliseconds since 1 January 1970 00:00:00
     */
    _getLastPresence() {
        return (
            this._callLocalStorage('getItem', 'lastPresence') ||
            super._getLastPresence()
        );
    }

    /**
     * Check all the time (according to the constants) if the tab is the master tab and
     * check if it is active. Use the local storage for this checks.
     *
     * @private
     * @see _startElection method
     */
    _heartbeat() {
        var now = new Date().getTime();
        var heartbeatValue = parseInt(this._callLocalStorage('getItem', 'heartbeat', 0));
        var peers = this._callLocalStorage('getItem', 'peers', {});

        if ((heartbeatValue + this.HEARTBEAT_OUT_OF_DATE_PERIOD) < now) {
            // Heartbeat is out of date. Electing new master
            this._startElection();
            heartbeatValue = parseInt(this._callLocalStorage('getItem', 'heartbeat', 0));
        }

        if (this._isMasterTab) {
            //walk through all peers and kill old
            var cleanedPeers = {};
            for (var peerName in peers) {
                if (peers[peerName] + this.HEARTBEAT_KILL_OLD_PERIOD > now) {
                    cleanedPeers[peerName] = peers[peerName];
                }
            }

            if (heartbeatValue !== this.lastHeartbeat) {
                // someone else is also master...
                // it should not happen, except in some race condition situation.
                this._isMasterTab = false;
                this.lastHeartbeat = 0;
                peers[this._id] = now;
                this._callLocalStorage('setItem', 'peers', peers);
                this.stopPolling();
                this.trigger('no_longer_master');
            } else {
                this.lastHeartbeat = now;
                this._callLocalStorage('setItem', 'heartbeat', now);
                this._callLocalStorage('setItem', 'peers', cleanedPeers);
            }
        } else {
            //update own heartbeat
            peers[this._id] = now;
            this._callLocalStorage('setItem', 'peers', peers);
        }

        // Write lastPresence in local storage if it has been updated since last heartbeat
        var hbPeriod = this._isMasterTab ? this.MASTER_TAB_HEARTBEAT_PERIOD : this.TAB_HEARTBEAT_PERIOD;
        if (this._lastPresenceTime + hbPeriod > now) {
            this._callLocalStorage('setItem', 'lastPresence', this._lastPresenceTime);
        }

        this._heartbeatTimeout = setTimeout(this._heartbeat.bind(this), hbPeriod);
    }

    /**
     * @private
     */
    _registerWindowUnload() {
        $(window).on('unload.' + this._id, this._onUnload.bind(this));
    }

    /**
     * Check with the local storage if the current tab is the master tab.
     * If this tab became the master, trigger 'become_master' event
     *
     * @private
     */
    _startElection() {
        if (this._isMasterTab) {
            return;
        }
        //check who's next
        var now = new Date().getTime();
        var peers = this._callLocalStorage('getItem', 'peers', {});
        var heartbeatKillOld = now - this.HEARTBEAT_KILL_OLD_PERIOD;
        var newMaster;
        for (var peerName in peers) {
            //check for dead peers
            if (peers[peerName] < heartbeatKillOld) {
                continue;
            }
            newMaster = peerName;
            break;
        }

        if (newMaster === this._id) {
            //we're next in queue. Electing as master
            this.lastHeartbeat = now;
            this._callLocalStorage('setItem', 'heartbeat', this.lastHeartbeat);
            this._callLocalStorage('setItem', 'master', true);
            this._isMasterTab = true;
            this.startPolling();
            this.trigger('become_master');

            //removing master peer from queue
            delete peers[newMaster];
            this._callLocalStorage('setItem', 'peers', peers);
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onFocusChange(params) {
        super._onFocusChange(...arguments);
        this._callLocalStorage('setItem', 'focus', params.focus);
    }

    /**
     * If it's the master tab, the notifications ares broadcasted to other tabs by the
     * local storage.
     *
     * @override
     */
    _onPoll(notifications) {
        var notifs = super._onPoll(notifications);
        if (this._isMasterTab && notifs.length) {
            this._callLocalStorage('setItem', 'last', this._lastNotificationID);
            this._callLocalStorage('setItem', 'last_ts', new Date().getTime());
            this._callLocalStorage('setItem', 'notification', notifs);
        }
    }

    /**
     * Handler when the local storage is updated
     *
     * @private
     * @param {OdooEvent} event
     * @param {string} event.key
     * @param {string} event.newValue
     */
    _onStorage(e) {
        var value = JSON.parse(e.newValue);
        var key = e.key;

        if (this._isRegistered && key === this._generateKey('master') && !value) {
            //master was unloaded
            this._startElection();
        }

        // last notification id changed
        if (key === this._generateKey('last')) {
            this._lastNotificationID = value || 0;
        }
        // notifications changed
        else if (key === this._generateKey('notification')) {
            if (!this._isMasterTab) {
                this.trigger("notification", value);
            }
        }
        // update channels
        else if (key === this._generateKey('channels')) {
            var channels = value;
            _.each(_.difference(this._channels, channels), this.deleteChannel.bind(this));
            _.each(_.difference(channels, this._channels), this.addChannel.bind(this));
        }
        // update options
        else if (key === this._generateKey('options')) {
            this._options = value;
        }
        // update focus
        else if (key === this._generateKey('focus')) {
            this._isOdooFocused = value;
            this.trigger('window_focus', this._isOdooFocused);
        }
    }

    /**
     * Handler when unload the window
     *
     * @private
     */
    _onUnload() {
        // unload peer
        var peers = this._callLocalStorage('getItem', 'peers') || {};
        delete peers[this._id];
        this._callLocalStorage('setItem', 'peers', peers);

        // unload master
        if (this._isMasterTab) {
            this._callLocalStorage('removeItem', 'master');
        }
    }
}

Object.assign(CrossTabBus, {
    // constants
    TAB_HEARTBEAT_PERIOD: 10000, // 10 seconds
    MASTER_TAB_HEARTBEAT_PERIOD: 1500, // 1.5 seconds
    HEARTBEAT_OUT_OF_DATE_PERIOD: 5000, // 5 seconds
    HEARTBEAT_KILL_OLD_PERIOD: 15000, // 15 seconds
    LOCAL_STORAGE_PREFIX: 'bus',

    // properties
    _isMasterTab: false,
    _isRegistered: false,
});

return CrossTabBus;

});

