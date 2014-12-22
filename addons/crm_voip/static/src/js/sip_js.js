openerp.sip_js = function(instance) {

    var _t = openerp._t;

    this.init = function() {
        var self = this;
        self.in_automatic_mode = false;
        self.onCall = false;
        new openerp.web.Model("crm.phonecall").call("get_pbx_config").then(function(result){
            self.config = result;
            var ua_config = {};
            if(result.login && result.wsServer && result.pbx_ip && result.password){
                ua_config = {
                    uri: result.login +'@'+result.pbx_ip,
                    wsServers: result.wsServer,
                    authorizationUser: result.login,
                    password: result.password,
                    hackIpInContact: true,
                    log: {level: "debug"},
                    traceSip: true,
                    turnServers: {
                      urls:"turn:numb.viagenie.ca",
                      username:"renod2002@yahoo.fr",
                      password:"odoo"
                    }
                };
                self.always_transfert = result.always_transfert;
                self.physical_phone = result.physical_phone;
                self.ring_number = result.ring_number;
            }else{
                //TODO will open the error pop up on every page. maybe not the best way to do it
                //new openerp.web.Model("crm.phonecall").call("error_config");
            }

            self.ua = new SIP.UA(ua_config);
            //Audio element which will play the audio flux
            var audio = document.createElement("audio");
            audio.id = "remote_audio";
            audio.autoplay = "autoplay";
            document.body.appendChild(audio);
            audio = document.createElement("audio");
            audio.id = "ringbacktone";
            audio.loop = "true";
            audio.src = "/crm_voip/static/src/sounds/ringbacktone.wav";
            document.body.appendChild(audio);
        });
    };

    //success callback function of the getUserMedia function
    function getUserMediaSuccess(stream) {
        var self = this;
        self.mediaStream = stream;
        if(!self.session){
            var number;
            if(self.current_phonecall.partner_phone){
                number = self.current_phonecall.partner_phone;
            } else if (self.current_phonecall.partner_mobile){
                number = self.current_phonecall.partner_mobile;
            }else{
                //TODO what to do when no number?
                return {};
            }
            try{
                var call_options = {
                    media: {
                        stream: self.mediaStream,
                        render: {
                            remote: {
                                audio: document.getElementById('remote_audio')
                            },
                        }
                    }
                };    
                //Make the call
                self.session = self.ua.invite(number,call_options);

                //Select the current call if not already selected
                if($(".oe_dial_selected_phonecall").data('id') !== self.current_phonecall.id ){
                    openerp.client.action_manager.do_action({
                        type: 'ir.actions.client',
                        tag: 'select_call',
                        params: {'phonecall_id': self.current_phonecall.id}
                    });
                }
                //Add the microhpone icon next to the current call
                $(".oe_dial_phonecall_partner_name").filter(function(){return $(this).data('id') == self.current_phonecall.id;}).after("<i style='margin-left:5px;' class='fa fa-microphone oe_dial_icon_inCall'></i>");
                self.ua.on('invite', function (invite_session){
                    console.log(invite_session.remoteIdentity.displayName);
                    var confirmation = confirm("Incomming call from " + invite_session.remoteIdentity.displayName);
                    if(confirmation){
                        invite_session.accept(call_options);
                    }else{
                        invite_session.reject();
                    }
                });
                //Bind action when the call is answered
                self.session.on('accepted',function(result){
                    console.log("ACCEPTED");
                    console.log(result);
                    self.onCall = true;
                    clearTimeout(self.timer);
                    new openerp.web.Model("crm.phonecall").call("init_call", [self.current_phonecall.id]);
                    ringbacktone = document.getElementById("ringbacktone");
                    ringbacktone.pause();
                    $('.oe_dial_transferbutton').removeAttr('disabled');
                    if(self.always_transfert){
                        self.session.refer(self.physical_phone);
                    }
                });
                //Bind action when the call is in progress to catch the ringing phase
                self.session.on('progress', function (response) {
                    console.log("PROGRESS");console.log(response);
                    if(response.reason_phrase == "Ringing"){
                        ringbacktone = document.getElementById("ringbacktone");
                        ringbacktone.play();
                        $('.oe_dial_big_callbutton').html(_t("Calling..."));
                        $('.oe_dial_hangupbutton').removeAttr('disabled');
                        //set the timer to stop the call if ringing too long
                        self.timer = setTimeout(function(){
                            var phonecall_model = new openerp.web.Model("crm.phonecall");
                            phonecall_model.call("rejected_call",[self.current_phonecall.id]);
                            self.session.cancel();
                        },4000*self.ring_number);
                    }
                });
                //Bind action when the call is rejected by the customer
                self.session.on('rejected',function(){
                    console.log("REJECTED");
                    self.session = false;
                    clearTimeout(self.timer);
                    var phonecall_model = new openerp.web.Model("crm.phonecall");
                    phonecall_model.call("rejected_call",[self.current_phonecall.id]);
                    ringbacktone = document.getElementById("ringbacktone");
                    ringbacktone.pause();
                    var id = self.current_phonecall.id;
                    //Remove the microphone icon
                    $(".oe_dial_phonecall_partner_name").filter(function(){return $(this).data('id') == id;}).next(".oe_dial_icon_inCall").remove();
                    if(self.in_automatic_mode){
                        self.next_call();
                    }else{
                        self.stop_automatic_call();
                    }
                });
                //Bind action when the call is transfered
                self.session.on('refer',function(response){console.log("REFER");console.log(response);});
                //Bind action when the user hangup the call while ringing
                self.session.on('cancel',function(){
                    console.log("CANCEL");
                    self.session = false;
                    clearTimeout(self.timer);
                    ringbacktone = document.getElementById("ringbacktone");
                    ringbacktone.pause();
                    var id = self.current_phonecall.id;
                    $(".oe_dial_phonecall_partner_name").filter(function(){return $(this).data('id') == id;}).next(".oe_dial_icon_inCall").remove();
                    //TODO if the sale cancel one call, continue the automatic call or not ? 
                    self.stop_automatic_call();
                });
                //Bind action when the call is hanged up
                self.session.on('bye',function(){
                    console.log("BYE");
                    clearTimeout(self.timer);
                    var phonecall_model = new openerp.web.Model("crm.phonecall");
                    phonecall_model.call("hangup_call", [self.current_phonecall.id]).then(function(result){
                        openerp.web.bus.trigger('reload_panel');
                        self.session = false;
                        self.onCall = false;
                        duration = parseFloat(result.duration).toFixed(2);
                        self.logCall(duration);
                        var id = self.current_phonecall.id;
                        $(".oe_dial_phonecall_partner_name").filter(function(){return $(this).data('id') == id;}).next(".oe_dial_icon_inCall").remove();
                        if(!self.in_automatic_mode){
                            self.stop_automatic_call();
                        }
                    });    
                });
            }catch(err){
                $('.oe_dial_big_callbutton').html(_t("Call"));
                $(".oe_dial_transferbutton, .oe_dial_hangupbutton").attr('disabled','disabled');
                new openerp.web.Model("crm.phonecall").call("error_config");
            }
        }
    }

    function getUserMediaFailure(e) {
        console.error('getUserMedia failed:', e);
    }

    this.automatic_call = function(phonecalls_list){
        var self = this;
        if(!self.session){
            self.in_automatic_mode = true;
            self.phonecalls_ids = [];
            self.phonecalls = phonecalls_list;
            for (var phone in self.phonecalls){
                if(self.phonecalls[phone].state != "done"){
                    self.phonecalls_ids.push(phone);
                }
            }
            if(self.phonecalls_ids.length){
                var current_call = self.phonecalls[self.phonecalls_ids.shift()];
                self.call(current_call);
            }else{
                self.stop_automatic_call();
            }
        }
    };

    this.call = function(phonecall){
        var self = this;
        self.current_phonecall = phonecall;
        var mediaConstraints = {
            audio: true,
            video: false
        };
        //if there is already a mediaStream, it is reused
        if (self.mediaStream) {
            getUserMediaSuccess.call(self,self.mediaStream);
        } else {
            if (SIP.WebRTC.isSupported()) {
                /*      
                    WebRTC method to get a mediastream      
                    The callbacks functions are getUserMediaSuccess, when the function succeed      
                    and getUserMediaFailure when the function failed        
                */ 
                SIP.WebRTC.getUserMedia(mediaConstraints, _.bind(getUserMediaSuccess,self), _.bind(getUserMediaFailure,self));
            }
        }
    };

    this.next_call = function(){
        var self = this;
        if(self.phonecalls_ids.length){
            if(!self.session){
                var current_call = self.phonecalls[self.phonecalls_ids.shift()];
                self.call(current_call);
            }
        }else{
            self.stop_automatic_call();
        }
    }

    this.stop_automatic_call = function(){
        var self = this;
        self.in_automatic_mode = false;
        $(".oe_dial_split_callbutton").show();
        $(".oe_dial_stop_autocall_button").hide();
        if(!self.session){
            $('.oe_dial_big_callbutton').html(_t("Call"));
            $(".oe_dial_transferbutton, .oe_dial_hangupbutton").attr('disabled','disabled');
        }else{
            $('.oe_dial_big_callbutton').html(_t("Calling..."));
        }
    };

    this.hangup = function(){
        var self = this;
        if(self.session){
            if(self.onCall){
                self.session.bye();
            }else{
                self.session.cancel();
            }
        }
        return {};
    };

    this.transfer = function(number){
        var self = this;
        if(self.session){
            self.session.refer(number);
            stop_automatic_call();
        }
    };

    this.logCall = function(duration){
        var self = this;
        var value = duration;
        var pattern = '%02d:%02d';
        if (value < 0) {
            value = Math.abs(value);
            pattern = '-' + pattern;
        }
        var min = Math.floor(value);
        var sec = Math.round((value % 1) * 60);
        if (sec == 60){
            sec = 0;
            min = min + 1;
        }
        self.current_phonecall.duration = _.str.sprintf(pattern, min, sec);

        openerp.client.action_manager.do_action({
                name: 'Log a call',
                type: 'ir.actions.act_window',
                key2: 'client_action_multi',
                src_model: "crm.phonecall",
                res_model: "crm.phonecall.log.wizard",
                multi: "True",
                target: 'new',
                context: {'phonecall_id': self.current_phonecall.id,
                'default_opportunity_id': self.current_phonecall.opportunity_id,
                'default_name': self.current_phonecall.name,
                'default_duration': self.current_phonecall.duration,
                'default_description' : self.current_phonecall.description,
                'default_opportunity_name' : self.current_phonecall.opportunity_name,
                'default_opportunity_planned_revenue' : self.current_phonecall.opportunity_planned_revenue,
                'default_opportunity_title_action' : self.current_phonecall.opportunity_title_action,
                'default_opportunity_date_action' : self.current_phonecall.opportunity_date_action,
                'default_opportunity_probability' : self.current_phonecall.opportunity_probability,
                'default_partner_id': self.current_phonecall.partner_id,
                'default_partner_name' : self.current_phonecall.partner_name,
                'default_partner_phone' : self.current_phonecall.partner_phone,
                'default_partner_email' : self.current_phonecall.partner_email,
                'default_partner_image_small' : self.current_phonecall.partner_image_small,
                'default_in_automatic_mode': self.in_automatic_mode,},
                views: [[false, 'form']],
                flags: {
                    'headless': true,
                },
            });
    }
};