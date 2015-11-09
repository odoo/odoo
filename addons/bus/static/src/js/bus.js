odoo.define('bus.bus', function (require) {
"use strict";

var session = require('web.session');
var Widget = require('web.Widget');

var bus = {};

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

        // bus presence
        this.set("window_focus", true);
        this.on("change:window_focus", self, function() {
            self.options.im_presence = self.get("window_focus");
        });
        $(window).on("focus", _.bind(this.window_focus, this));
        $(window).on("blur", _.bind(this.window_blur, this));
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
        var data = {channels: self.channels, last: self.last, options : self.options};
        session.rpc('/longpolling/poll', data, {shadow : true}).then(function(result) {
            self._notification_receive(result);
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
    _notification_receive: function(notifications){
        _.each(notifications, this.on_notification);
    },
    on_notification: function(notification) {
        if (notification.id > this.last) {
            this.last = notification.id;
        }
        this.trigger("notification", [notification.channel, notification.message]);
    },
    add_channel: function(channel){
        this.channels.push(channel);
        this.channels = _.uniq(this.channels);
    },
    delete_channel: function(channel){
        this.channels = _.without(this.channels, channel);
    },
    // bus presence : window focus/unfocus
    window_focus: function() {
        this.set("window_focus", true);
    },
    window_blur: function() {
        this.set("window_focus", false);
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
        var self = this;
        this._super.apply(this, arguments);
        this.is_master = false;
        tab_manager.register_tab(function () {
            self.is_master = true;
            self.start_polling();
        }, function () {
            self.is_master = false;
            self.stop_polling();
        });

        on("storage", this.on_storage.bind(this));
        if (this.is_master) {
            setItem('bus.channels', this.channels);
            setItem('bus.options', this.options);
        } else {
            this.channels = getItem('bus.channels', this.channels);
            this.options = getItem('bus.options', this.options);
        }

    },
    start_polling: function(){
        if (this.is_master) {
            this._super.apply(this, arguments);
        }
     },
    _notification_receive: function(notifications){
        if(this.is_master) { // broadcast to other tabs
            setItem('bus.notification', notifications);
        }
        this._super.apply(this, arguments);
    },
    on_storage: function (e) {
        // use the value of event to not read from
        // localStorage (avoid race condition)
        var value = e.newValue;
        // notifications changed
        if(e.key === 'bus.notification'){
            var notifs = JSON.parse(value);
            _.each(notifs, this.on_notification);
        }
        // update channels
        if(e.key === 'bus.channels'){
            this.channels = JSON.parse(value);
        }
        // update options
        if(e.key === 'bus.options'){
            this.options = JSON.parse(value);
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
    update_option: function(){
        this._super.apply(this, arguments);
        setItem('bus.options', this.options);
    },
    delete_option: function(){
        this._super.apply(this, arguments);
        setItem('bus.options', this.options);
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
    var val = localStorage.getItem(key);
    return val ? JSON.parse(val) : defaultValue;
}

function setItem(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
}

var tab_manager = {
    peersKey: 'bus.peers',
    masterKey: 'bus.master',
    heartbeatKey: 'bus.heartbeat',
    isMaster: false,
    id: new Date().getTime() + ':' + (Math.random() * 1000000000 | 0),

    register_tab: function (is_master_callback, is_no_longer_master) {
        this.is_master_callback = is_master_callback;
        this.is_no_longer_master = is_no_longer_master || function () {};

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
                localStorage.removeItem(tab_manager.masterKey);
            }
        });

        if (!localStorage[tab_manager.masterKey]) {
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
        var pollPeriod = 10000;
        var heartbeatValue = localStorage[tab_manager.heartbeatKey] || 0;
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

            if (parseInt(heartbeatValue) !== tab_manager.last_heartbeat) {
                // someone else is also master...
                // it should not happen, except in some race condition situation.
                tab_manager.isMaster = false;
                tab_manager.last_heartbeat = 0;
                peers[tab_manager.id] = current;
                setItem(tab_manager.peersKey, peers);
                tab_manager.is_no_longer_master();
            } else {
                tab_manager.last_heartbeat = current;
                localStorage[tab_manager.heartbeatKey] = current;
                setItem(tab_manager.peersKey, cleanedPeers);
                pollPeriod = 1500;
            }
        } else {
            //update own heartbeat
            peers[tab_manager.id] = current;
            setItem(tab_manager.peersKey, peers);
        }

        setTimeout(function(){
            tab_manager.heartbeat();
        }, pollPeriod);
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

