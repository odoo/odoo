(function(){
    var instance = openerp;
    instance.im_screenshare = {};
    instance.im_screenshare.COOKIE_NAME = 'odoo-screenshare';
    var _t = openerp._t;

    // Default class : it records the summary mutation (start, stop, and send must be override to use the mutations)
    // A mutation is a key-array :
    //      * f : string, it is the type of the mutation (initialize or applyChanged for TreeMirror, forwardData for cursorMirror)
    //      * args : array containing hte DOM mutations ([removed, addedOrMoved, attributes, text] for TreeMirror)
    //      * timestamp : the timestamp of the mutations
    instance.im_screenshare.RecordHandler = instance.Widget.extend({
        init: function(parent) {
            this._super(parent);
            this.mode = false;
            this.uuid = false;
            this.record_id = false;
            this.cookie_data = {};
            this.activated = false;
            // business
            this.treeMirrorClient = null;
            this.cursorMirrorClient = null;
            this.def = $.when();
            this.msgQueue = [];
        },
        start: function(){
            if(!this.activated){
                this.activated = true;
                this.start_from_cookie();
            }
        },
        start_from_cookie: function(){
            var cookie = this.get_cookie(instance.im_screenshare.COOKIE_NAME);
            if(cookie && !this.is_recording()){
                this.record_id = cookie.record_id;
                this.uuid = cookie.uuid;
                this.mode = cookie.mode;
                this.cookie_data = cookie;
                this._start_record();
            }
        },
        // cookie functions
        create_cookie: function(extra){
            this.cookie_data = _.extend(extra, this.cookie_data);
            this.cookie_data = _.extend({uuid : this.uuid, record_id : this.record_id, mode : this.mode}, extra || {});
            this.set_cookie(instance.im_screenshare.COOKIE_NAME, this.cookie_data, 60*60*1000);
        },
        set_cookie: function(name,value,hours) {
            if (hours) {
                var date = new Date();
                date.setTime(date.getTime()+(hours*60*60*1000));
                var expires = "; expires="+date.toGMTString();
            }else{
                var expires = "";
            }
            document.cookie = name+"="+JSON.stringify(value)+expires+"; path=/";
        },
        get_cookie: function(name) {
            var nameEQ = name + '=';
            var cookies = document.cookie.split(';');
            for(var i=0; i<cookies.length; ++i) {
                var cookie = cookies[i].replace(/^\s*/, '');
                if(cookie.indexOf(nameEQ) === 0) {
                    try {
                        return JSON.parse(decodeURIComponent(cookie.substring(nameEQ.length)));
                    } catch(err) {
                        // wrong cookie, delete it
                        this.set_cookie(name, '', -1);
                    }
                }
            }
            return null;
        },
        // mutations utils
        _remove_empty_mutations: function(mutations){
            var self = this;
            var clean_mutations = [];
            _.each(mutations, function(m){
                if(m.base || _.contains(['initialize', 'notificationMessage', 'formData'], m.f)){
                    clean_mutations.push(m);
                }
                if(m.f === 'forwardData'){
                    if(m.args[1].x.length){
                       clean_mutations.push(m);
                    }
                }
                if(m.f === 'applyChanged'){
                    // remove mutation id=1 and attribute is empty key-array
                    m.args[2] = _.filter(m.args[2], function(item){
                        return !(item.id && item.id === 1 && item.attributes);
                    })
                    // filter the empty mutations
                    if(!(_.isEmpty(m.args[0]) && _.isEmpty(m.args[1]) && _.isEmpty(m.args[2]) && _.isEmpty(m.args[3]))){
                        clean_mutations.push(m);
                    }
                }
            });
            return clean_mutations;
        },
        _mutations_contain_tag: function(mutations, tag_name, search_values, args_index){
            var found = false;
            _.each(mutations, function(m){
                _.each(m.args[args_index], function(a){
                    if(!found && a[tag_name] && _.contains(search_values, a[tag_name])){
                        found = true;
                    }
                });
            });
            return found;
        },
        // mutations queue
        send_queue: function(msg) {
            var self = this;
            var msglist = self.msgQueue;
            this.def = this.send_record(msglist);
            this.msgQueue = [];
            this.def.then(function(result) {
                if (self.msgQueue.length) {
                    self.send_queue();
                }
            });
        },
        queue: function(msg) {
            this.msgQueue.push(msg);
            if (this.def.state() === "resolved") {
                this.send_queue();
            }
        },
        // recording functions
        is_recording: function(){ // is the current object recording for now
            return this.treeMirrorClient !== null;
        },
        is_screen_already_recording: function(){ // is the screen already recording or sharing
            return !!(this.get_cookie(instance.im_screenshare.COOKIE_NAME));
        },
        start_record: function(mode, extra_cookie_data){
            var self = this;
            this.mode = mode;
            return openerp.jsonRpc("/im_screenshare/start", 'call', {mode : this.mode}).then(function(result){
                if(self.mode === 'share'){
                    self.uuid = result;
                }else{
                    self.record_id = result;
                }
                // create cookie for 1h
                self.create_cookie(extra_cookie_data);
                // start sending mutations
                self._start_record();
                return result;
            });
        },
        _start_record: function(){
            var self = this;
            // disabled loading by replacing the on_rpc_event function
            if(openerp.webclient){
                this._on_rpc_function = openerp.webclient.loading.on_rpc_event;
                clearTimeout(openerp.webclient.loading.long_running_timer);
                openerp.webclient.loading.on_rpc_event = function(){};
                $('.oe_loading').hide();
            }
            // initialize the mirrorClients
            this.queue({
                base: location.href.match(/^(.*\/)[^\/]*$/)[1],
                timestamp: Date.now(),
            });
            this.formDataMirrorClient = new FormDataMirrorClient({
                setData: function(data){
                    self.queue({
                        f: 'formData',
                        args: [data],
                        timestamp: Date.now()
                    });
                }
            });
            this.treeMirrorClient = new TreeMirrorClient(document, {
                initialize: function(rootId, children) {
                    self.queue({
                        f: 'initialize',
                        args: [rootId, children],
                        timestamp: Date.now(),
                    });
                },
                applyChanged: function(removed, addedOrMoved, attributes, text) {
                    var mutation = {
                        f: 'applyChanged',
                        args: [removed, addedOrMoved, attributes, text],
                        timestamp: Date.now(),
                    };
                    self.queue(mutation);
                    // check if the mutation contains input elements
                    if(self._mutations_contain_tag([mutation], "tagName", ["INPUT", "TEXTEAREA", "SELECT"], 1)){
                        self.formDataMirrorClient.setData();
                    }
                }
            });
            this.cursorMirrorClient = new CursorMirrorClient({
                forwardData: function(page, coords, elem) {
                    self.queue({
                        f: 'forwardData',
                        args: [page, coords, elem],
                        timestamp: Date.now(),
                    });
                },
            });
        },
        stop_record: function(){
            // erase cookie
            this.set_cookie(instance.im_screenshare.COOKIE_NAME, "", -1);
            // reset data
            this.treeMirrorClient.disconnect();
            this.treeMirrorClient = null;
            this.cursorMirrorClient.disconnect();
            this.cursorMirrorClient = null;
            this.uuid = false;
            this.record_id = false;
            this.mode = false;
            this.cookie_data = {};
            // restore the initial on_rpc_event function
            if(openerp.webclient){
                openerp.webclient.loading.on_rpc_event = this._on_rpc_function;
                openerp.webclient.loading.count = 0;
            }
            // send notification to the player message zone
            return this.send_record([{
                f: "notificationMessage",
                args : [_t("The sharing/recording is not now finished.")],
                timestamp: Date.now()
            }]);
        },
        send_record: function(mutations){
            // remove the empty mutations
            mutations = this._remove_empty_mutations(mutations);
            if(mutations.length !== 0){
                return openerp.jsonRpc("/im_screenshare/share", 'call', {uuid: this.uuid, record_id : this.record_id, mutations : mutations});
            }
            return $.Deferred().resolve();
        }
    });

    // Unique Player for Screen recording and Screen sharing
    // Class which replay the recieved mutation on the current DOM.
    //      For the screensharing, it will listen to the bus, and replay the received mutations
    //      For the screenrecording, it will fetch the mutations, and replay them
    instance.im_screenshare.Player = instance.Class.extend({
        init: function(params){
            // common init
            this.clearPage();
            this._init_mirroirs();
            if(params.uuid){
                // screen sharing
                this.channel = params.uuid;
                this.bus = openerp.bus.bus;
                this.bus.add_channel(params.uuid);
                this.bus.on("notification", this, this.on_notification);
                this.bus.start_polling();
            }else{
                // screen record
                this.record_id = params.id;
                this.dbname = params.dbname;
                this.sre_msglist = [];
                this.counter = 0;
                this._init_screen_record();
            }
        },
        // screen recording
        _init_screen_record: function(){
            var self = this;
            var screenRecordEvent = new instance.web.Model('im_screenshare.record.event');
            screenRecordEvent.query(['mutations']).filter([['screen_record_id', '=', self.record_id]]).all().done(function(sre_list) {
                _.each(sre_list, function(sre) {
                    var list = JSON.parse(sre.mutations);
                    _.each(list, function(item) {
                        self.sre_msglist.push(item);
                    });
                });
                self.load();
            });
        },
        load: function(){
            var self = this;
            var next_event_delay = 0;
            var current = this.sre_msglist[this.counter];
            if (this.counter < this.sre_msglist.length-1) {
                var next = this.sre_msglist[this.counter+1];
                next_event_delay = next.timestamp - current.timestamp;
                window.setTimeout(function(){self.load();}, next_event_delay);
            }
            this.handleMutation(current);
            this.counter++;
        },
        // screen sharing (bus notifications)
        on_notification: function(notification){
            var self = this;
            var channel = notification[0];
            var mutations = notification[1];
            if(channel === this.channel){
                _.each(mutations, function(m){
                    try{
                        self.handleMutation(m);
                    }catch(e){
                        console.warn(e);
                    }
                });
            }
        },
        // common functions
        clearPage : function() {
            while (document.firstChild) {
                document.removeChild(document.firstChild);
            }
        },
        _init_mirroirs: function(){
            var self = this;
            // init the mirroirs
            this.treeMirror = new TreeMirror(document, {
                createElement: function(tagName) {
                    if (tagName == 'SCRIPT') {
                        var node = document.createElement('NO-SCRIPT');
                        node.style.display = 'none';
                        return node;
                    }
                    if (tagName == 'HEAD') {
                        var node = document.createElement('HEAD');
                        node.appendChild(document.createElement('BASE'));
                        node.firstChild.href = self.base;
                        return node;
                    }
                    // SVG Graph : add the NameSpace on each elem of the svg, otherwise they are not displayed.
                    if(['svg', 'g', 'rect', 'circle', 'text', 'line', 'path', 'tspan'].indexOf(tagName) > -1){
                        return document.createElementNS("http://www.w3.org/2000/svg", tagName);
                    }
                }
            });
            this.cursorMirror = new CursorMirror();
            this.formDataMirror = new FormDataMirror();
        },
        handleMutation: function(msg) {
            if (msg.base) {
                this.base = msg.base;
                this.clearPage();
                this._init_mirroirs();
            } else {
                if(msg.f){
                    if (msg.f === 'forwardData') {
                        this.cursorMirror[msg.f].apply(this.cursorMirror, msg.args);
                    }
                    if(msg.f === 'notificationMessage'){ // message to be display in the message zone
                        this.notificationMessage(msg.args);
                    }
                    if(msg.f === 'initialize' || msg.f === 'applyChanged'){
                        // DOM mutation (initialize, or applyChanged)
                        this.treeMirror[msg.f].apply(this.treeMirror, msg.args);
                        if(msg.f === 'initialize'){
                            var mzone = $("<div>", {class: "oe_screenshare_message_zone"}).text(_t("This the screensharing player."));
                            $("body").prepend(mzone);
                        }
                    }
                    if(msg.f === 'formData'){
                        this.formDataMirror[msg.f].apply(this.formDataMirror, msg.args);
                    }
                }
            }
        },
        notificationMessage: function(m){
            $('.oe_screenshare_message_zone').text(m);
        }
    });


    // Class managing the start and stop recording/sharing
    // The button widget must inherit this class. It restrict the sharing/recording to only on at a time.
    instance.im_screenshare.AbstractButton = instance.Widget.extend({
        init: function(parent){
            this._super(parent);
            this.mode = 'record';
            this.extra_cookie_data = {};
            this.record_handler = instance.im_screenshare.record_handler;
        },
        start: function(){
            this.record_handler.start();
            // bind events
            this.on("change:record_state", this, this.change_button);
            this.$el.on('click', _.bind(this.action_click, this));
            // set initial state
            var state = false;
            if(this.record_handler.is_screen_already_recording()){
                state = this.already_started_myself();
            }
            this.set('record_state', state);
        },
        action_click: function(){
            var self = this;
            if(this.record_handler.is_screen_already_recording()){
                if(this.already_started_myself()){
                    // stop recording
                    this.set('record_state', false);
                    return this.record_handler.stop_record().then(function(){
                        self.set('record_state', false);
                        return false;
                    });
                }else{
                    // alert the screen is already used.
                    alert(_t("You are already sharing or recording your screen. Please stop the current action, or clean your browser cookie."));
                    return new $.Deferred().resolve();
                }
            }else{
                // start recording
                return this.record_handler.start_record(this.mode, this.extra_cookie_data).then(function(res){
                    self.set('record_state', !!res);
                    return res;
                });
            }
        },
        // function to redefine in the real button implementation
        already_started_myself: function(){return false;},
        change_button: function(){},
    });

    // Screen recording in the Database
    // Implementation of the button to record the summary mutation of the current DOM and save them in the Database
    instance.im_screenshare.RecordButton = instance.im_screenshare.AbstractButton.extend({
        already_started_myself: function(){
            return !!(this.record_handler.cookie_data["record_id"]);
        },
        change_button: function(){
            if(this.get('record_state')){
                 this.$el.html('<button>Stop</button>');
            }else{
                 this.$el.html('<button>Record</button>');
            }
        },
    });

    // IM Screenshare with other users, depends on im_chat
    // Implementation of the conversation header button : it starts and stops the screensharing.
    instance.im_screenshare.ShareButton = instance.im_screenshare.AbstractButton.extend({
        init: function(parent){
            this._super(parent);
            this.conv = parent;
            this.mode = 'share';
            this.extra_cookie_data = {conv_uuid: this.conv.get('session').uuid};
        },
        start: function() {
            this.$el.html('<button class="oe_im_screenshare_button"><i class="fa fa-caret-square-o-right"></i></button>');
            this._super();
        },
        already_started_myself: function(){
            var vals = this.record_handler.cookie_data;
            return !!(vals["uuid"] && vals["conv_uuid"] === this.conv.get('session').uuid);
        },
        change_button: function() {
            if(this.get('record_state')){
                this.$('.oe_im_screenshare_button').css('color','red');
                this.$('.oe_im_screenshare_button').css('title','Stop sharing screen');
            }else{
                this.$('.oe_im_screenshare_button').css('color','gray');
                this.$('.oe_im_screenshare_button').css('title','Share your screen');
            }
        },
        action_click: function(e){
            var self = this;
            e.stopPropagation();
            this._super().then(function(res){
                if(res){
                    var url = openerp.session.server + '/im_screenshare/player/' + res;
                    self.conv.send_message(_.str.sprintf(_t("Invitation for screensharing. Click on this link : %s"), url), 'meta');
                }
            });
        },
    });

    // create the unique instance of the RecordHandler
    instance.im_screenshare.record_handler = new instance.im_screenshare.RecordHandler();


    // WEBSITE SCREENSHARE : This code allow the auto start on the Odoo Website. When the Website DOM is ready, we check if
    // the cookie exists (if yes, the recording start). This lib must be in the web.assets_common bundle to avoid dependency
    // with website module, but require the following EventListener.
    window.addEventListener('DOMContentLoaded', function() {
        if(openerp.website && openerp.website.ready){
            openerp.website.ready().then(function(){
                instance.im_screenshare.record_handler.start();
            });
        }
    });

    return instance.im_screenshare;

})();
