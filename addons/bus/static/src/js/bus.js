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
    init: function(){
        var self = this;
        this._super();
        this.options = {};
        this.activated = false;
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
        $(window).on("focus", _.bind(this.focus_change, this, true));
        $(window).on("blur", _.bind(this.focus_change, this, false));
        $(window).on("unload", _.bind(this.focus_change, this, false));
        _.each('click,keydown,keyup'.split(','), function(evtype) {
            $(window).on(evtype, function() {
                self.last_presence = new Date().getTime();
            });
        });
    },
    start_polling: function(){
        if(!this.activated){
            this.poll();
            this.stop = false;
        }
    },
    stop_polling: function(){
        this.activated = false;
        this.stop = true;
        this.channels = [];
    },
    poll: function() {
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
        session.rpc('/longpolling/poll', data, {shadow : true}).then(function(result) {
            self.on_notification(result);
            if(!self.stop){
                self.poll();
            }
        }, function(unused, e) {
            // no error popup if request is interrupted or fails for any reason
            e.preventDefault();
            // random delay to avoid massive longpolling
            setTimeout(_.bind(self.poll, self), bus.ERROR_DELAY + (Math.floor((Math.random()*20)+1)*1000));
        });
    },
    on_notification: function(notifications) {
        var self = this;
        var notifs = _.map(notifications, function (notif) {
            if (notif.id > self.last) {
                self.last = notif.id;
            }
            return [notif.channel, notif.message];
        });
        this.trigger("notification", notifs);
    },
    add_channel: function(channel){
        this.channels.push(channel);
        this.channels = _.uniq(this.channels);
    },
    delete_channel: function(channel){
        this.channels = _.without(this.channels, channel);
    },
    // bus presence : window focus/unfocus
    focus_change: function(focus) {
        this.set("window_focus", focus);
    },
    is_odoo_focused: function () {
        return this.get("window_focus");
    },
    get_last_presence: function () {
        return this.last_presence;
    },
    update_option: function(key, value){
        this.options[key] = value;
    },
    delete_option: function(key){
        if(_.contains(_.keys(this.options), key)){
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
 * localStorage used keys are :
 *      - bus.channels : shared public channel list to listen during the poll
 *      - bus.options : shared options
 *      - bus.notification : the received notifications from the last poll
 *      - bus.tab_list : list of opened tab ids
 *      - bus.tab_master : generated id of the master tab
 */
var CrossTabBus = bus.Bus.extend({
    init: function(){
        this._super.apply(this, arguments);
        this.is_master = false;
        this.is_registered = false;
        if (parseInt(getItem('bus.last_ts', 0)) + 50000 < new Date().getTime()) {
            setItem('bus.last', -1);
        }

        on("storage", this.on_storage.bind(this));
    },
    start_polling: function(){
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
                    setItem('bus.last_presence', self.last_presence);
                }
            });
            if (this.is_master) {
                setItem('bus.channels', this.channels);
                setItem('bus.options', this.options);
            } else {
                this.channels = getItem('bus.channels', this.channels);
                this.options = getItem('bus.options', this.options);
            }
            return;  // start_polling will be called again on tab registration
        }

        if (this.is_master) {
            this._super.apply(this, arguments);
        }
     },
    on_notification: function(notifications){
        if(this.is_master) { // broadcast to other tabs
            var last = getItem('bus.last', -1);
            var max_id = Math.max(last, 0);
            var new_notifications = _.filter(notifications, function (notif) {
                max_id = Math.max(max_id, notif.id);
                return notif.id < 0 || notif.id > last;
            });
            this.last = max_id;
            if (new_notifications.length) {
                setItem('bus.last', max_id);
                setItem('bus.last_ts', new Date().getTime());
                setItem('bus.notification', new_notifications);
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
        if(e.key === 'bus.notification'){
            var notifs = JSON.parse(value);
            this.on_notification(notifs);
        }
        // update channels
        if(e.key === 'bus.channels'){
            this.channels = JSON.parse(value);
        }
        // update options
        if(e.key === 'bus.options'){
            this.options = JSON.parse(value);
        }
        // update focus
        if(e.key === 'bus.focus'){
            this.set('window_focus', JSON.parse(value));
        }
    },
    add_channel: function(){
        this._super.apply(this, arguments);
        setItem('bus.channels', this.channels);
    },
    delete_channel: function(){
        this._super.apply(this, arguments);
        setItem('bus.channels', this.channels);
    },
    get_last_presence: function () {
        return getItem('bus.last_presence') || new Date().getTime();
    },
    update_option: function(){
        this._super.apply(this, arguments);
        setItem('bus.options', this.options);
    },
    delete_option: function(){
        this._super.apply(this, arguments);
        setItem('bus.options', this.options);
    },
    focus_change: function(focus) {
        this._super.apply(this, arguments);
        setItem('bus.focus', focus);
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
    peersKey: 'bus.peers',
    masterKey: 'bus.master',
    heartbeatKey: 'bus.heartbeat',
    isMaster: false,
    id: new Date().getTime() + ':' + (Math.random() * 1000000000 | 0),

    register_tab: function (is_master_callback, is_no_longer_master, on_heartbeat_callback) {
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

        on('storage', function(e) {
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

        setTimeout(function(){
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
if(typeof Storage !== "undefined"){
    bus.bus = new CrossTabBus();
} else {
    bus.bus = new bus.Bus();
}

return bus;


});

