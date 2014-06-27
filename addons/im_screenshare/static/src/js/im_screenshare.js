(function(){
    var instance = openerp;
    instance.im_screenshare = {};

    // Default class : it records the summary mutation (start, stop, and send must be override to use the mutations)
    instance.im_screenshare.RecordHandler = instance.Widget.extend({
        init: function() {
            this.treeMirrorClient = null;
           // this.cursorMirrorClient = null;
            this.def = $.when();
            this.msgQueue = [];
        },
        send_queue: function(msg) {
            var self = this;
            var msglist = JSON.stringify(self.msgQueue);
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
        is_recording: function(){
            return this.treeMirrorClient !== null;
        },
        start_record: function(){
            var self = this;
            this.queue({
                'base': location.href.match(/^(.*\/)[^\/]*$/)[1],
                'timestamp': Date.now(),
            });
            this.treeMirrorClient = new TreeMirrorClient(document.body, {
                initialize: function(rootId, children) {
                    self.queue({
                        f: 'initialize',
                        args: [rootId, children],
                        'timestamp': Date.now(),
                    });
                },
                applyChanged: function(removed, addedOrMoved, attributes, text) {
                    self.queue({
                        f: 'applyChanged',
                        args: [removed, addedOrMoved, attributes, text],
                        'timestamp': Date.now(),
                    });
                }
            });
            /*
            this.cursorMirrorClient = new CursorMirrorClient({
                forwardData: function(page, coords, elem) {
                    self.queue({
                        f: 'forwardData',
                        args: [page, coords, elem],
                        'timestamp': Date.now(),
                    });
                },
            });
            */
        },
        stop_record: function(){
            if(this.is_recording()){
                this.treeMirrorClient.disconnect();
                this.treeMirrorClient = null;
                //this.cursorMirrorClient.disconnect();
                //this.cursorMirrorClient = null;
            }
        },
        send_record: function(json_mutations){
            return $.Deferred().resolve();
        },
    });

    // Class which replay the recieved mutation on the current DOM
    instance.im_screenshare.Player = instance.Widget.extend({
        init: function(treeMirror){
            //this.cursorMirror = cursorMirror;
            this.treeMirror = treeMirror;
        },
        clearPage : function() {
            while (document.firstChild) {
                document.removeChild(document.firstChild);
            }
        },
        handleMessage: function(msg) {
            if (msg.clear) {
                //console.log("msg.clear");
                this.clearPage();
            } else if (msg.base) {
                //console.log("msg.base");
                base = msg.base;
            } else {
                //console.log(msg.f);
                if (msg.f === 'forwardData') {
                    //console.log("msg.f = forwardData");
                    this.cursorMirror[msg.f].apply(this.cursorMirror, msg.args);
                    //console.log(this.cursorMirror[msg.f]);
                } else {
                    //console.log("msg.f = applyChanged or initialize");
                    this.treeMirror[msg.f].apply(this.treeMirror, msg.args);
                }
            }
        }
    });

    //----------------------------------------------------------
    // Screenshare recoding in the Database
    //----------------------------------------------------------

    // Class recording the summary mutation of the current DOM and save them in the Database
    instance.im_screenshare.DbRecordHandler = instance.im_screenshare.RecordHandler.extend({
        init: function(parent){
            this._super();
        },
        start: function() {
            this.$el.html(this.generate_button());
            this.$el.on('click','button',_.bind(this.click,this));
        },
        generate_button: function() {
            return (this.is_recording() ? '<button>Stop</button>' : '<button>Record</button>');
        },
        click: function(){
            if(this.is_recording()){
                this.stop_record();
            }else{
                this.start_record();
            }
            this.$el.html(this.generate_button());
        },
        start_record: function(){
            //create the record
            var self =  this;
            var date = new Date();
            var screenRecord = new instance.web.Model('im_screenshare.record');
            screenRecord.call('create', [{
                'name': 'New Screen Recording Session: ' + date.toString(),
                'starttime': date.toISOString(),
            }]).then(function(result) {
                self.currentScreenRecord = result;
            });
            // start recording
            this._super();
        },
        stop_record: function(){
            // stop recording
            this._super();
            // save the end time
            var self = this;
            var date = new Date();
            var screenRecord = new instance.web.Model('im_screenshare.record');
            screenRecord.call('write', [this.currentScreenRecord, {
                    'endtime': date.toISOString(),
            }]).then(function(result) {
                console.log("Screen Record with id: " + self.currentScreenRecord + " modified");
            });
        },
        send_record: function(json_mutations){
            var date = new Date();
            var ts = this.msgQueue[0]['timestamp'];
            var screenRecordEvent = new instance.web.Model('im_screenshare.record.event');
            var def = screenRecordEvent.call('create', [{
                    'screen_record_id': this.currentScreenRecord,
                    'timestamp': ts,
                    'timestamp_date': date.toISOString(),
                    'msglist': json_mutations,
            }]);
            return def;
        }
    });

    // Class fetching the record and send the events to the player
    instance.im_screenshare.DbReceiver = instance.Widget.extend({
        init: function(id, dbname, player){
            var self = this;
            this.id = id;
            this.dbname = dbname;
            this.counter = 0;
            this.sre_msglist = [];
            this.player = player;
            instance.session.session_bind().done(function() {
                var screenRecord = new instance.web.Model('im_screenshare.record');
                var screenRecordEvent = new instance.web.Model('im_screenshare.record.event');
                screenRecord.query(['event_ids']).filter([['id', '=', self.id]]).all().then(function(r) {
                    var sre_ids = r[0].event_ids;
                    screenRecordEvent.query(['msglist']).filter([['id', 'in', sre_ids]]).all().done(function(sre_list) {
                        _.each(sre_list, function(sre) {
                            var list = JSON.parse(sre.msglist);
                            _.each(list, function(item) {
                                self.sre_msglist.push(item);
                            });
                        });
                        self.load();
                    });
                });
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
            this.player.handleMessage(current);
            this.counter++;
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


    //----------------------------------------------------------
    // IM Screenshare with other users, depends on im_chat
    //----------------------------------------------------------

    // Class sending the records to the server. This is the button on the header of the conversation
    instance.im_screenshare.IMSenderButton = openerp.im_screenshare.RecordHandler.extend({
        init: function(conv){
            this._super();
            this.conv = conv;
            this.count = 0;
        },
        start: function() {
            this.$el.html('<button class="oe_im_screenshare_button" title="Share your screen"><i class="fa fa-caret-square-o-right"></i></button>');//this.generate_button());
            this.$el.on('click','button',_.bind(this.click,this));
        },
        click: function(event){
            event.stopPropagation();
            if(this.is_recording()){
                this.stop_record();
                this.send_record("[]", "finish");
                this.$('.oe_im_screenshare_button').css('color','black');
                this.$('.oe_im_screenshare_button').css('title','Share your screen');
            }else{
                this.start_record();
                this.count = 0;
                this.$('.oe_im_screenshare_button').css('color','red');
                this.$('.oe_im_screenshare_button').css('title','Stop sharing screen');
            }
        },
        // override functions (stop_recording don't need to be)
        start_record: function(){
            // send the invitation
            var invit = "Screensharing with you, follow the link : "
            + openerp.session.server + '/im_screenshare/player/' + this.conv.get("session").uuid;

            this.conv.send_message(invit, 'meta');
            // start recording
            this._super();
        },
        send_record: function(json_mutations, type){
            var type = type || "base";
            var message = {
                "num" : this.count,
                "mutations" : JSON.parse(json_mutations),
                "type" : JSON.parse(json_mutations)[0] ? JSON.parse(json_mutations)[0].f : type,
                "session" : this.conv.get("session").uuid
            }
            this.count++;
            return openerp.session.rpc("/im_screenshare/share", {uuid: this.conv.get("session").uuid, message : message});
        },
    });

    // Class listening the bus, and keeping the im_screenshare messages to send them to the player
    instance.im_screenshare.BusListener = openerp.Class.extend({
        init: function(channel, player){
            this.player = player;
            this.channel = channel;
            this.bus = openerp.im.bus;
            this.bus.add_channel(channel);
            this.bus.on("notification", this, this.on_notification);
            this.bus.start_polling();
        },
        on_notification: function(notification){
            var self = this;
            var channel = notification[0];
            var message = notification[1];

            console.log("NUM : ", message);

            // Concern im_screenshare : only the im_screenshare message matters. It avoid messages send to the private "uuid" channel of the session
            if((Array.isArray(channel) && (channel[1] == 'im_screenshare'))){
                //console.log("RECEIVE : ", JSON.stringify(message));
                if(message.type === 'finish'){
                   // window.close();
                }else{
                    _.each(message.mutations, function(m){
                       //console.log(JSON.stringify(m));
                        try{
                            self.player.handleMessage(m);
                        }catch(e){
                            console.warn(e);
                        }
                    });
                }
            }
        }
    });

    // add the button to the header of the conversation
    instance.im_chat.Conversation.include({
        start: function() {
            this._super();
            var b = new instance.im_screenshare.IMSenderButton(this);
            b.appendTo(this.$('.oe_im_chatview_right'));
        },
    });

    return instance.im_screenshare;
})();