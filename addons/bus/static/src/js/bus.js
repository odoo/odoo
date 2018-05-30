odoo.define('bus.bus', function (require) {
"use strict";

var local_storage = require('web.local_storage');
var session = require('web.session');
var Widget = require('web.Widget');

var bus = {};
var PARTNERS_PRESENCE_CHECK_PERIOD = 30000;  // don't check presence more than once every 30s

var TAB_HEARTBEAT_PERIOD = 10000;  // 10 seconds
var MASTER_TAB_HEARTBEAT_PERIOD = 1500;  // 1.5 second

bus.ERROR_DELAY = 10000;

bus.Bus = Widget.extend({
    /**
     * @override
     * @param {Object} params
     * @param {Object} params.session the session to use to perform the poll RPC
     * @param {string} params.pollRoute the longpolling route to use
     */
    init: function (params) {
        var self = this;
        this._super();
        this.pollRoute = params.pollRoute;
        this.session = params.session;
        this.options = {};
        this.activated = false;
        this.bus_id = _.uniqueId('bus');
        this.channels = [];
        this.last = 0;
        this.stop = false;
        this.is_master = true;

        // bus presence
        this.last_presence = new Date().getTime();
        this.last_partners_presence_check = this.last_presence;
        this.set("window_focus", true);
        this.on("change:window_focus", this, function () {
            if (this.get("window_focus")) {
                this.trigger('window_focus', this.is_master);
            }
        });
        $(window).on("focus." + this.bus_id, _.bind(this.focus_change, this, true));
        $(window).on("blur." + this.bus_id, _.bind(this.focus_change, this, false));
        $(window).on("unload." + this.bus_id, _.bind(this.focus_change, this, false));
        _.each('click,keydown,keyup'.split(','), function (evtype) {
            $(window).on(evtype + "." + self.bus_id, function () {
                self.last_presence = new Date().getTime();
            });
        });
    },
    destroy: function () {
        var self = this;
        $(window).off("focus." + this.bus_id);
        $(window).off("blur." + this.bus_id);
        $(window).off("unload." + this.bus_id);
        _.each('click,keydown,keyup'.split(','), function (evtype) {
            $(window).off(evtype + "." + self.bus_id);
        });
    },
    start_polling: function () {
        if (!this.activated) {
            this.poll();
            this.stop = false;
        }
    },
    stop_polling: function () {
        this.activated = false;
        this.stop = true;
        this.channels = [];
    },
    poll: function () {
        var self = this;
        self.activated = true;
        var now = new Date().getTime();
        var options = _.extend({}, this.options, {
            bus_inactivity: now - this.get_last_presence(),
        });
        if (this.last_partners_presence_check + PARTNERS_PRESENCE_CHECK_PERIOD > now) {
            options = _.omit(options, 'bus_presence_partner_ids');
        } else {
            this.last_partners_presence_check = now;
        }
        var data = {channels: self.channels, last: self.last, options: options};
        // The backend has a maximum cycle time of 50 seconds so give +10 seconds
        this._pollRpc = session.rpc(this.pollRoute, data, {shadow : true, timeout: 60000});
        this._pollRpc.then(function (result) {
            self._pollRpc = false;
            self.on_notification(result);
            if (!self.stop) {
                self.poll();
            }
        }, function (error, event) {
            self._pollRpc = false;
            // no error popup if request is interrupted or fails for any reason
            event.preventDefault();
            if (error && error.message === "XmlHttpRequestError abort") {
                if (!self.stop && self.activated) {
                    self.poll();
                }
            } else {
                // random delay to avoid massive longpolling
                setTimeout(_.bind(self.poll, self), bus.ERROR_DELAY + (Math.floor((Math.random()*20)+1)*1000));
            }
        });
    },
    on_notification: function (notifications) {
        var self = this;
        var notifs = _.map(notifications, function (notif) {
            if (notif.id > self.last) {
                self.last = notif.id;
            }
            return [notif.channel, notif.message];
        });
        this.trigger("notification", notifs);
    },
    add_channel: function (channel) {
        if (this.channels.indexOf(channel) === -1) {
            this.channels.push(channel);
            if (this._pollRpc) {
                this._pollRpc.abort();
            }
        }
    },
    delete_channel: function (channel) {
        var index = this.channels.indexOf(channel);
        if (index !== -1) {
            this.channels.splice(index, 1);
            if (this._pollRpc) {
                this._pollRpc.abort();
            }
        }
    },
    // bus presence : window focus/unfocus
    focus_change: function (focus) {
        this.set("window_focus", focus);
    },
    is_odoo_focused: function () {
        return this.get("window_focus");
    },
    get_last_presence: function () {
        return this.last_presence;
    },
    update_option: function (key, value) {
        this.options[key] = value;
    },
    delete_option: function (key) {
        if (_.contains(_.keys(this.options), key)) {
            delete this.options[key];
        }
    },
});



/**
 * CrossTabBus Widget
 *
 * Manage the communication before browser tab to allow only one tab polling for the others (performance improvement)
 * When a tab is opened, and the start_polling method is called, the tab is signaling through the localStorage to the
 * others. When a tab is closed, it signals its removing. If he was the master tab (the polling one), he choose another
 * one in the list of open tabs. This one start polling for the other. When a notification is recieved from the poll, it
 * is signaling through the localStorage too.
 *
 * localStorage used keys are:
 *
 * - bus.channels : shared public channel list to listen during the poll
 * - bus.options : shared options
 * - bus.notification : the received notifications from the last poll
 * - bus.tab_list : list of opened tab ids
 * - bus.tab_master : generated id of the master tab
 */
bus.CrossTabBus = bus.Bus.extend({
    init: function () {
        this._super.apply(this, arguments);

        // used to prefix localStorage keys
        this.sanitizedOrigin = this.session.origin.replace(/:\/{0,2}/g, '_');

        this.is_master = false;
        this.is_registered = false;
        if (parseInt(this._getItem('last_ts', 0)) + 50000 < new Date().getTime()) {
            this._setItem('last', -1);
        }

        on("storage", this.on_storage.bind(this));
    },
    start_polling: function () {
        var self = this;
        if (!this.is_registered) {
            this.is_registered = true;
            tab_manager.register_tab(function () {
                self.is_master = true;
                self.start_polling();
            }, function () {
                self.is_master = false;
                self.stop_polling();
            }, function () {
                // Write last_presence in local storage if it has been updated since last heartbeat
                var hb_period = this.is_master ? MASTER_TAB_HEARTBEAT_PERIOD : TAB_HEARTBEAT_PERIOD;
                if (self.last_presence + hb_period > new Date().getTime()) {
                    self._setItem('last_presence', self.last_presence);
                }
            }, this._generateKey.bind(this));
            if (this.is_master) {
                this._setItem('channels', this.channels);
                this._setItem('options', this.options);
            } else {
                this.channels = this._getItem('channels', this.channels);
                this.options = this._getItem('options', this.options);
            }
            return;  // start_polling will be called again on tab registration
        }

        if (this.is_master) {
            this._super.apply(this, arguments);
        }
     },
    on_notification: function (notifications) {
        if (this.is_master) { // broadcast to other tabs
            var last = this._getItem('last', -1);
            var max_id = Math.max(last, 0);
            var new_notifications = _.filter(notifications, function (notif) {
                max_id = Math.max(max_id, notif.id);
                return notif.id < 0 || notif.id > last;
            });
            this.last = max_id;
            if (new_notifications.length) {
                this._setItem('last', max_id);
                this._setItem('last_ts', new Date().getTime());
                this._setItem('notification', new_notifications);
                this._super(new_notifications);
            }
        } else {
            this._super.apply(this, arguments);
        }
    },
    on_storage: function (e) {
        // use the value of event to not read from
        // localStorage (avoid race condition)
        var value = e.newValue;
        // notifications changed
        if (e.key === this._generateKey('notification')) {
            var notifs = JSON.parse(value);
            this.on_notification(notifs);
        }
        // update channels
        if (e.key === this._generateKey('channels')) {
            this.channels = JSON.parse(value);
        }
        // update options
        if (e.key === this._generateKey('options')) {
            this.options = JSON.parse(value);
        }
        // update focus
        if (e.key === this._generateKey('focus')) {
            this.set('window_focus', JSON.parse(value));
        }
    },
    add_channel: function () {
        this._super.apply(this, arguments);
        this._setItem('channels', this.channels);
    },
    delete_channel: function () {
        this._super.apply(this, arguments);
        this._setItem('channels', this.channels);
    },
    get_last_presence: function () {
        return this._getItem('last_presence') || new Date().getTime();
    },
    update_option: function () {
        this._super.apply(this, arguments);
        this._setItem('options', this.options);
    },
    delete_option: function () {
        this._super.apply(this, arguments);
        this._setItem('options', this.options);
    },
    focus_change: function (focus) {
        this._super.apply(this, arguments);
        this._setItem('focus', focus);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Generates localStorage keys prefixed by bus. (the name of this addon),
     * and the sanitized origin, to prevent keys from conflicting when several
     * bus instances (polling different origins) co-exist.
     *
     * @private
     * @param {string} key
     * @returns key prefixed with the origin
     */
    _generateKey: function (key) {
        return 'bus.' + this.sanitizedOrigin + '.' + key;
    },
    /**
     * @private
     * @param {string} key
     * @param {*} defaultValue
     */
    _getItem: function (key, defaultValue) {
        return getItem(this._generateKey(key), defaultValue);
    },
    /**
     * @private
     * @param {string} key
     * @param {*} value
     */
    _setItem: function (key, value) {
        setItem(this._generateKey(key), value);
    },
});


//utility functions
function on(type, listener) {
    if (window.addEventListener) {
        window.addEventListener(type, listener);
    } else { //IE8
        window.attachEvent('on' + type, listener);
    }
}

function getItem(key, defaultValue) {
    var val = local_storage.getItem(key);
    return val ? JSON.parse(val) : defaultValue;
}

function setItem(key, value) {
    local_storage.setItem(key, JSON.stringify(value));
}


var tab_manager = {
    isMaster: false,
    id: new Date().getTime() + ':' + (Math.random() * 1000000000 | 0),

    register_tab: function (is_master_callback, is_no_longer_master, on_heartbeat_callback, generateKey) {
        this.heartbeatKey = generateKey('heartbeat');
        this.masterKey = generateKey('master');
        this.peersKey = generateKey('peers');

        this.is_master_callback = is_master_callback;
        this.is_no_longer_master = is_no_longer_master || function () {};
        this.on_heartbeat_callback = on_heartbeat_callback || function () {};

        var peers = getItem(tab_manager.peersKey, {});
        peers[tab_manager.id] = new Date().getTime();
        setItem(tab_manager.peersKey, peers);

        on('unload', function () {
            // unload peer
            var peers = getItem(tab_manager.peersKey, {});
            delete peers[tab_manager.id];
            setItem(tab_manager.peersKey, peers);

            // unload master
            if (tab_manager.isMaster) {
                local_storage.removeItem(tab_manager.masterKey);
            }
        });

        if (!local_storage.getItem(tab_manager.masterKey)) {
            tab_manager.start_election();
        }

        on('storage', function (e) {
            if (!e) { e = window.event;}
            if (e.key !== tab_manager.masterKey) {
                return;
            }

            if (e.newValue === null) { //master was unloaded
                tab_manager.start_election();
            }

        });
        tab_manager.heartbeat();
    },
    heartbeat: function () {
        var current = new Date().getTime();
        var heartbeatValue = local_storage.getItem(tab_manager.heartbeatKey) || 0;
        var peers = getItem(tab_manager.peersKey, {});

        if ((parseInt(heartbeatValue) + 5000) < current) {
            // Heartbeat is out of date. Electing new master
            tab_manager.start_election();
        }
        if (tab_manager.isMaster) {
            //walk through all peers and kill old
            var cleanedPeers = {};
            for (var peerName in peers) {
                if (peers[peerName] + 15000 > current) {
                    cleanedPeers[peerName] = peers[peerName];
                }
            }
            if (!tab_manager.is_last_heartbeat_mine()) {
                // someone else is also master...
                // it should not happen, except in some race condition situation.
                tab_manager.isMaster = false;
                tab_manager.last_heartbeat = 0;
                peers[tab_manager.id] = current;
                setItem(tab_manager.peersKey, peers);
                tab_manager.is_no_longer_master();
            } else {
                tab_manager.last_heartbeat = current;
                local_storage.setItem(tab_manager.heartbeatKey, current);
                setItem(tab_manager.peersKey, cleanedPeers);
            }
        } else {
            //update own heartbeat
            peers[tab_manager.id] = current;
            setItem(tab_manager.peersKey, peers);
        }
        this.on_heartbeat_callback();

        setTimeout(function () {
            tab_manager.heartbeat();
        }, tab_manager.isMaster ? MASTER_TAB_HEARTBEAT_PERIOD : TAB_HEARTBEAT_PERIOD);
    },
    is_last_heartbeat_mine: function () {
        var heartbeatValue = local_storage.getItem(tab_manager.heartbeatKey) || 0;
        return (parseInt(heartbeatValue) === tab_manager.last_heartbeat);
    },
    start_election: function () {
        if (tab_manager.isMaster) {
            return;
        }
        //check who's next
        var peers = getItem(tab_manager.peersKey, {});
        var now = new Date().getTime();
        var newMaster;

        for (var peerName in peers) {
            //check for dead peers
            if (peers[peerName] + 15000 < now) {
                continue;
            }

            newMaster = peerName;
            break;
        }
        if (newMaster === tab_manager.id) {
            //we're next in queue. Electing as master
            setItem(tab_manager.masterKey, tab_manager.id);
            tab_manager.last_heartbeat = new Date().getTime();
            setItem(tab_manager.heartbeatKey, tab_manager.last_heartbeat);
            tab_manager.isMaster = true;
            tab_manager.is_master_callback();

            //removing master peer from queue
            delete peers[newMaster];
            setItem(tab_manager.peersKey, peers);
        }
    },
};


// bus singleton, depending of the browser :
// if supporting LocalStorage, there will be only one tab polling
var params = {
    pollRoute: '/longpolling/poll',
    session: session,
};
if (typeof Storage !== "undefined") {
    bus.bus = new bus.CrossTabBus(params);
} else {
    bus.bus = new bus.Bus(params);
}

return bus;


});

