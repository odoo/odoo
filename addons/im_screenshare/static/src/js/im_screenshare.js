(function(){
    var instance = openerp;
    instance.im_screenshare = {};
    var _t = openerp._t;

    // Default class : it records the summary mutation (start, stop, and send must be override to use the mutations)
    // A mutation is a key-array :
    //      * f : string, it is the type of the mutation (initialize or applyChanged for TreeMirror, forwardData for cursorMirror)
    //      * args : array containing hte DOM mutations ([removed, addedOrMoved, attributes, text] for TreeMirror)
    //      * timestamp : the timestamp of the mutations
    instance.im_screenshare.RecordHandler = instance.Widget.extend({
        init: function(parent, mode) {
            this._super(parent);
            this.mode = mode || 'share';
            this.uuid = false;
            this.record_id = false;
            // filter nodes
            this.loading_node_id = false;
            this.loading_children_ids = [];
            // business
            this.treeMirrorClient = null;
            this.cursorMirrorClient = null;
            this.def = $.when();
            this.msgQueue = [];

            var cookie = openerp.session.get_cookie('odoo-screenshare-' + this.mode);
            if(cookie){
                // then import data from cookie
                this.record_id = cookie.record_id;
                this.uuid = cookie.uuid;
                this._start_record();
            }
        },
        // mutations filter
        _remove_empty_mutations: function(mutations){
            var self = this;
            var clean_mutations = [];
            _.each(mutations, function(m){
                if(m.f === 'initialize' || m.f === 'message' || m.base){
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
        is_recording: function(){
            return this.treeMirrorClient !== null;
        },
        start_record: function(){
            var self = this;
            return openerp.session.rpc("/im_screenshare/start", {mode : this.mode}).then(function(result){
                if(self.mode === 'share'){
                    self.uuid = result;
                }else{
                    self.record_id = result;
                }
                // create cookie for 1h
                var data = {uuid : self.uuid, record_id : self.record_id};
                openerp.session.set_cookie("odoo-screenshare-" + self.mode, data, 60*60*1000);
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
                openerp.webclient.loading.on_rpc_event = function(){};
            }

            this.queue({
                base: location.href.match(/^(.*\/)[^\/]*$/)[1],
                timestamp: Date.now(),
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
                    self.queue({
                        f: 'applyChanged',
                        args: [removed, addedOrMoved, attributes, text],
                        timestamp: Date.now(),
                    });
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
            // send notification to the player message zone
            this.send_record([{f: "message", message : _t("The sharing/recording is not now finished."), timestamp: Date.now()}])
            // erase cookie
            openerp.session.set_cookie("odoo-screenshare-" + this.mode, "", -1);
            // re-init data
            this.treeMirrorClient.disconnect();
            this.treeMirrorClient = null;
            this.cursorMirrorClient.disconnect();
            this.cursorMirrorClient = null;

            this.loading_node_id = false;
            this.loading_children_ids = [];
            this.uuid = false;
            this.record_id = false;
            // restore the initial on_rpc_event function
            if(openerp.webclient){
                openerp.webclient.loading.on_rpc_event = this._on_rpc_function;
            }
        },
        send_record: function(mutations){
            // remove the empty mutations
            mutations = this._remove_empty_mutations(mutations);
            if(mutations.length !== 0){
                console.log(JSON.stringify(mutations));
                return openerp.session.rpc("/im_screenshare/share", {uuid: this.uuid, record_id : this.record_id, mutations : mutations});
            }else{
                return $.Deferred().resolve();
            }
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
            this.handleMessage(current);
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
                        self.handleMessage(m);
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
                }
            });
            this.cursorMirror = new CursorMirror();
        },
        handleMessage: function(msg) {
            if (msg.base) {
                this.base = msg.base;
                this.clearPage();
                this._init_mirroirs();
            } else {
                if (msg.f === 'forwardData') {
                    this.cursorMirror[msg.f].apply(this.cursorMirror, msg.args);
                } else {
                    if(msg.f === 'message'){ // message to be display in the message zone
                        $('.oe_screenshare_message_zone').text(msg.message);
                    }else{
                        // DOM mutation (initialize, or applyChanged)
                        this.treeMirror[msg.f].apply(this.treeMirror, msg.args);
                        if(msg.f === 'initialize'){
                            var mzone = $("<div>", {class: "oe_screenshare_message_zone"}).text(_t("This the screensharing player."));
                            $("body").prepend(mzone);
                        }
                    }
                }
            }
        }
    });

    // Screen recording in the Database
    // Class recording the summary mutation of the current DOM and save them in the Database
    instance.im_screenshare.DbRecordHandler = instance.im_screenshare.RecordHandler.extend({
        init: function(parent){
            this._super(parent, 'record');
        },
        start: function() {
            this.$el.html(this.generate_button(this.is_recording()));
            this.$el.on('click','button',_.bind(this.click,this));
        },
        generate_button: function(is_recording) {
            return (is_recording ? '<button>Stop</button>' : '<button>Record</button>');
        },
        click: function(){
            var is_recording = this.is_recording();
            this.$el.html(this.generate_button(!is_recording));
            if(is_recording){
                this.stop_record();
            }else{
                this.start_record();
            }
        }
    });

    // add the button in the webclient menu bar
    instance.web.UserMenu.include({
        do_update: function(){
            var self = this;
            this.update_promise.then(function() {
                var button = new instance.im_screenshare.DbRecordHandler(this);
                button.appendTo(openerp.webclient.$el.find('.oe_systray'));
            });
            return this._super.apply(this, arguments);
        },
    });


    // IM Screenshare with other users, depends on im_chat
    // This is the button on the header of the conversation : it starts and stops the screensharing.
    instance.im_screenshare.IMSenderButton = openerp.im_screenshare.RecordHandler.extend({
        init: function(parent){
            this._super(parent, 'share');
            this.conv = parent;
        },
        start: function() {
            this.$el.html('<button class="oe_im_screenshare_button" title="Share your screen"><i class="fa fa-caret-square-o-right"></i></button>');//this.generate_button());
            this.$el.on('click','button',_.bind(this.click,this));
        },
        click: function(event){
            var self = this;
            event.stopPropagation();
            if(this.is_recording()){
                this.stop_record();
                this.$('.oe_im_screenshare_button').css('color','gray');
                this.$('.oe_im_screenshare_button').css('title','Share your screen');
            }else{
                self.start_record();
                self.$('.oe_im_screenshare_button').css('color','red');
                self.$('.oe_im_screenshare_button').css('title','Stop sharing screen');
            }
        },
        // override functions
        start_record: function(){
            var self = this;
            this._super().then(function(res){
                var invit = "Screensharing with you, follow the link : " + openerp.session.server + '/im_screenshare/player/' + self.uuid;
                self.conv.send_message(invit, 'meta');
            });
        }
    });

    // add the button to the header of the conversation
    instance.im_chat.Conversation.include({
        start: function() {
            this._super();
            var b = new instance.im_screenshare.IMSenderButton(this);
            b.prependTo(this.$('.oe_im_chatview_right'));
        },
        /* TODO : make it work with im_livechat (for saas6)
        add_options: function(){
            this._super();
            this._add_option('Screensharing', 'im_chat_option_screenshare', 'fa fa-desktop');
        }
        */
    });

    return instance.im_screenshare;
})();
