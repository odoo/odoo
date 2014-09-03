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
        init: function(parent, mode) {
            this._super(parent);
            this.mode = mode || 'record';
            this.uuid = false;
            this.record_id = false;
            // business
            this.treeMirrorClient = null;
            this.cursorMirrorClient = null;
            this.def = $.when();
            this.msgQueue = [];
        },
        start: function(){
            var cookie = openerp.session.get_cookie(instance.im_screenshare.COOKIE_NAME);
            if(cookie && !this.is_recording()){
                if(this.check_cookie_auto_start(cookie)){
                    // then import data from cookie
                    this.record_id = cookie.record_id;
                    this.uuid = cookie.uuid;
                    this.mode = cookie.mode;
                    this._start_record();
                    return true;
                }
            }
            return false;
        },
        // override this function to set the condition determining if the current object is responsible for the recording (for auto start after refresh)
        check_cookie_auto_start: function(vals){
            return false;
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
            return !!(openerp.session.get_cookie(instance.im_screenshare.COOKIE_NAME));
        },
        start_record: function(extra_cookie_data){
            var self = this;
            if(this.is_screen_already_recording()){
                alert(_t("You are already sharing or recording your screen."));
                return new $.Deferred().resolve().then(function(){
                    return false;
                });
            }
            return openerp.session.rpc("/im_screenshare/start", {mode : this.mode}).then(function(result){
                if(self.mode === 'share'){
                    self.uuid = result;
                }else{
                    self.record_id = result;
                }
                // create cookie for 1h
                var cookie_values = _.extend({uuid : self.uuid, record_id : self.record_id, mode : self.mode}, extra_cookie_data || {});
                openerp.session.set_cookie(instance.im_screenshare.COOKIE_NAME, cookie_values, 60*60*1000);
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
            // send notification to the player message zone
            this.send_record([{
                f: "notificationMessage",
                args : [_t("The sharing/recording is not now finished.")],
                timestamp: Date.now()
            }]);
            // erase cookie
            openerp.session.set_cookie(instance.im_screenshare.COOKIE_NAME, "", -1);
            // reset data
            this.treeMirrorClient.disconnect();
            this.treeMirrorClient = null;
            this.cursorMirrorClient.disconnect();
            this.cursorMirrorClient = null;
            this.uuid = false;
            this.record_id = false;
            // restore the initial on_rpc_event function
            if(openerp.webclient){
                openerp.webclient.loading.on_rpc_event = this._on_rpc_function;
                openerp.webclient.loading.count = 0;
            }
        },
        send_record: function(mutations){
            // remove the empty mutations
            mutations = this._remove_empty_mutations(mutations);
            if(mutations.length !== 0){
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

    // Screen recording in the Database
    // Class recording the summary mutation of the current DOM and save them in the Database
    instance.im_screenshare.DbRecordHandler = instance.im_screenshare.RecordHandler.extend({
        init: function(parent){
            this._super(parent, 'record');
        },
        start: function(){
            var is_rec = this._super();
            this.$el.html(this.generate_button(is_rec));
            this.$el.on('click','button',_.bind(this.click,this));
        },
        check_cookie_auto_start: function(vals){
            return !!(vals["record_id"]);
        },
        generate_button: function(is_recording){
            return (is_recording ? '<button>Stop</button>' : '<button>Record</button>');
        },
        click: function(){
            var self = this;
            if(this.is_recording()){
                this.stop_record();
                this.$el.html(this.generate_button(false));
            }else{
                this.start_record().then(function(res){
                    self.$el.html(self.generate_button(res));
                });
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
    instance.im_screenshare.IMSenderButton = instance.im_screenshare.RecordHandler.extend({
        init: function(parent){
            this._super(parent, 'share');
            this.conv = parent;
        },
        start: function() {
            var is_rec = this._super();
            this.$el.html('<button class="oe_im_screenshare_button"><i class="fa fa-caret-square-o-right"></i></button>');
            this.color_button(is_rec);
            this.$el.on('click','button',_.bind(this.click,this));
        },
        check_cookie_auto_start: function(vals){
            return !!(vals["uuid"] && vals["conv_uuid"] === this.conv.get('session').uuid);
        },
        color_button: function(is_recording) {
            if(is_recording){
                this.$('.oe_im_screenshare_button').css('color','red');
                this.$('.oe_im_screenshare_button').css('title','Stop sharing screen');
            }else{
                this.$('.oe_im_screenshare_button').css('color','gray');
                this.$('.oe_im_screenshare_button').css('title','Share your screen');
            }
        },
        click: function(event){
            var self = this;
            event.stopPropagation();
            if(this.is_recording()){
                this.stop_record();
                this.color_button(false);
            }else{
                this.start_record({conv_uuid: this.conv.get('session').uuid}).then(function(res){
                    if(res){
                        var invit = "Screensharing with you, follow the link : " + openerp.session.server + '/im_screenshare/player/' + res;
                        self.conv.send_message(invit, 'meta');
                    }
                    self.color_button(res);
                });
            }
        },
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
