openerp.sip_js = function(instance) {

    var mediaStream;
    var session;
    var current_phonecall;
    var ua;
    var call_options;
    var in_automatic_mode;
    var phonecalls_ids;
    var phonecalls;
    var onCall = false;
    var always_transfert;
    var physical_phone;
    var ring_number;
    var timer;

    this.init = function() {
        var self = this;
        in_automatic_mode = false;
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
                    log: {level: "error"},
                };
                always_transfert = result.always_transfert;
                physical_phone = result.physical_phone;
                ring_number = result.ring_number;

            }else{
                //new openerp.web.Model("crm.phonecall").call("error_config");
            }

            ua = new SIP.UA(ua_config);

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

    function getUserMediaSuccess(stream) {
        console.log('getUserMedia succeeded', stream);
        mediaStream = stream;
        if(!session){
            var number;
            if(current_phonecall.partner_phone){
                number = current_phonecall.partner_phone;
            } else if (current_phonecall.partner_mobile){
                number = current_phonecall.partner_mobile;
            }else{
                //TODO what to do when no number? 
                console.log("NO NUMBER");
                return {};
            }
            try{
                call_options = {
                    media: {
                        stream: mediaStream,
                        render: {
                            remote: {
                                audio: document.getElementById('remote_audio')
                            },
                        }
                    }
                };    
                //Make the call
                session = ua.invite(number,call_options);
                openerp.client.action_manager.do_action({
                    type: 'ir.actions.client',
                    tag: 'select_call',
                    params: {'phonecall_id': current_phonecall.id}
                });

                $(".oe_dial_phonecall_partner_name").filter(function(){return $(this)[0].dataset.id == current_phonecall.id;}).after("<i style='margin-left:5px;' class='fa fa-microphone oe_dial_icon_inCall'></i>");
                ua.on('invite', function (invite_session){
                    console.log(invite_session.remoteIdentity.displayName);
                    var confirmation = confirm("Incomming call from " + invite_session.remoteIdentity.displayName);
                    if(confirmation){
                        invite_session.accept(call_options);
                    }else{
                        invite_session.reject();
                    }
                });
                //Bind action when the call is answered
                session.on('accepted',function(result){
                    console.log("ACCEPTED");
                    console.log(result);
                    console.log(this.remoteIdentity.toString());
                    onCall = true;
                    clearTimeout(timer);
                    new openerp.web.Model("crm.phonecall").call("init_call", [current_phonecall.id]);
                    ringbacktone = document.getElementById("ringbacktone");
                    ringbacktone.pause();
                    $('.oe_dial_transferbutton').removeAttr('disabled');
                    if(always_transfert){
                        session.refer(physical_phone);
                    }
                });
                session.on('progress', function (response) {
                    console.log("PROGRESS");console.log(response);
                    if(response.reason_phrase == "Ringing"){
                        ringbacktone = document.getElementById("ringbacktone");
                        ringbacktone.play();
                        $('.oe_dial_big_callbutton').html("Calling...");
                        $('.oe_dial_hangupbutton').removeAttr('disabled');
                        timer = setTimeout(function(){
                            console.log("TIMER FUNCTION");
                            var phonecall_model = new openerp.web.Model("crm.phonecall");
                            phonecall_model.call("rejected_call",[current_phonecall.id]);
                            session.cancel();
                        },4000*ring_number);
                    }
                });
                session.on('rejected',function(){
                    console.log("REJECTED");
                    session = false;
                    clearTimeout(timer);
                    var phonecall_model = new openerp.web.Model("crm.phonecall");
                    phonecall_model.call("rejected_call",[current_phonecall.id]);
                    ringbacktone = document.getElementById("ringbacktone");
                    ringbacktone.pause();
                    var id = current_phonecall.id;
                    $(".oe_dial_phonecall_partner_name").filter(function(){return $(this)[0].dataset.id == id;}).next(".oe_dial_icon_inCall").remove();
                    if(in_automatic_mode === true){
                        next_call();
                    }else{
                        $('.oe_dial_big_callbutton').html("Call");
                        $(".oe_dial_transferbutton").attr('disabled','disabled');
                        $(".oe_dial_hangupbutton").attr('disabled','disabled');
                    }
                });
                session.on('refer',function(response){console.log("REFER");console.log(response);});
                session.on('cancel',function(){
                    console.log("CANCEL");
                    session = false;
                    clearTimeout(timer);
                    ringbacktone = document.getElementById("ringbacktone");
                    ringbacktone.pause();
                    var id = current_phonecall.id;
                    console.log(current_phonecall);
                    console.log($(".oe_dial_phonecall_partner_name").filter(function(){return $(this)[0].dataset.id == id;}).next(".oe_dial_icon_inCall"));
                    $(".oe_dial_phonecall_partner_name").filter(function(){return $(this)[0].dataset.id == id;}).next(".oe_dial_icon_inCall").remove();
                    //TODO if the sale cancel one call, continue the automatic call or not ? 
                    if(in_automatic_mode === true){
                        next_call();
                    }else{
                        $('.oe_dial_big_callbutton').html("Call");
                        $(".oe_dial_transferbutton").attr('disabled','disabled');
                        $(".oe_dial_hangupbutton").attr('disabled','disabled');
                    }
                });
                session.on('bye',function(){
                    console.log("BYE");
                    clearTimeout(timer);
                    var phonecall_model = new openerp.web.Model("crm.phonecall");
                    phonecall_model.call("hangup_call", [current_phonecall.id]).then(function(result){
                        openerp.web.bus.trigger('reload_panel');
                        session = false;
                        onCall = false;
                        duration = parseFloat(result.duration).toFixed(2);
                        loggedCallOption(duration);
                        var id = current_phonecall.id;
                        $(".oe_dial_phonecall_partner_name").filter(function(){return $(this)[0].dataset.id == id;}).next(".oe_dial_icon_inCall").remove();
                        if(in_automatic_mode === true){
                            next_call();
                        }else{
                            $('.oe_dial_big_callbutton').html("Call");
                            $(".oe_dial_transferbutton").attr('disabled','disabled');
                            $(".oe_dial_hangupbutton").attr('disabled','disabled');
                        }
                    });    
                });
            }catch(err){
                $('.oe_dial_big_callbutton').html("Call");
                $(".oe_dial_transferbutton").attr('disabled','disabled');
                $(".oe_dial_hangupbutton").attr('disabled','disabled');
                new openerp.web.Model("crm.phonecall").call("error_config");
            }
        }
    }

    function getUserMediaFailure(e) {
        console.error('getUserMedia failed:', e);
    }

    this.automatic_call = function(phonecalls_list){
        if(!session){
            in_automatic_mode = true;
            phonecalls_ids = [];
            phonecalls = phonecalls_list;
            for (var phone in phonecalls){
                console.log(phonecalls[phone]);
                if(phonecalls[phone].state != "done"){
                    phonecalls_ids.push(phone);
                }
            }
            if(phonecalls_ids.length){
                current_call = phonecalls[phonecalls_ids.shift()];
                call(current_call);
            }else{
                stop_automatic_call();
            }
        }
    };

    this.call = function(phonecall){
        call(phonecall);
    };

    function next_call(){
        if(phonecalls_ids.length){
            if(!session){
                console.log("NEXT CALL");
                current_call = phonecalls[phonecalls_ids.shift()];
                call(current_call);
            }
        }else{
            console.log("END OF LIST");
            stop_automatic_call();
        }
    }

    this.stop_automatic_call = function(){
        stop_automatic_call();
    };

    stop_automatic_call = function(){
        in_automatic_mode = false;
        $(".oe_dial_split_callbutton").css("display","inline-block");
        $(".oe_dial_stop_autocall_button").css("display","none");
        if(!session){
            $('.oe_dial_big_callbutton').html("Call");
            $(".oe_dial_transferbutton").attr('disabled','disabled');
            $(".oe_dial_hangupbutton").attr('disabled','disabled');
        }else{
            $('.oe_dial_big_callbutton').html("Calling...");
        }
    };

    function call(phonecall){
        console.log("CALL FUNCTION");
        current_phonecall = phonecall;
        var mediaConstraints = {
            audio: true,
            video: false
        };
        if (mediaStream) {
            console.log("MEDIA STREAM ALREADY");
            getUserMediaSuccess(mediaStream);
        } else {
            if (SIP.WebRTC.isSupported()) {
                console.log("GET USER MEDIA");
                SIP.WebRTC.getUserMedia(mediaConstraints, getUserMediaSuccess, getUserMediaFailure);
            }
        }
        /*
        if(!this.session){
            var self = this;
            this.phonecall = phonecall;
            var number;
            if(phonecall.partner_phone){
                number = phonecall.partner_phone;
            } else if (phonecall.partner_mobile){
                number = phonecall.partner_mobile;
            }else{
                //TODO what to do when no number? 
                console.log("NO NUMBER");
                return {};
            }
            try{
                //Make the call
                this.session = this.ua.invite(number,this.call_options);
                //Bind action when the call is answered
                this.session.on('accepted',function(result){
                    console.log("ACCEPTED");
                    console.log(result);
                    self.onCall = true;
                    new openerp.web.Model("crm.phonecall").call("init_call", [self.phonecall.id]);
                    ringbacktone = document.getElementById("ringbacktone");
                    ringbacktone.pause();
                });
                this.session.on('progress', function (response) {
                    console.log("PROGRESS");console.log(response);
                    if(response.reason_phrase == "Ringing"){
                        ringbacktone = document.getElementById("ringbacktone");
                        ringbacktone.play();
                        $('.oe_dial_big_callbutton').html("Calling...");
                        $('.oe_dial_inCallButton').removeAttr('disabled');
                    }
                });
                this.session.on('rejected',function(){
                    console.log("REJECTED");
                    self.session = false;
                    var phonecall_model = new openerp.web.Model("crm.phonecall");
                    phonecall_model.call("rejected_call",[self.phonecall.id]);
                    ringbacktone = document.getElementById("ringbacktone");
                    ringbacktone.pause();
                    if(self.in_automatic_mode === true){
                        self.next_call();
                    }else{
                        $('.oe_dial_big_callbutton').html("Call");
                        $(".oe_dial_inCallButton").attr('disabled','disabled');
                    }
                });
                this.session.on('refer',function(response){console.log("REFER");console.log(response);});
                this.session.on('cancel',function(){
                    console.log("CANCEL");
                    self.session = false;
                    ringbacktone = document.getElementById("ringbacktone");
                    ringbacktone.pause();
                    //TODO if the sale cancel one call, continue the automatic call or not ? 
                    if(self.in_automatic_mode === true){
                        self.next_call();
                    }else{
                        $('.oe_dial_big_callbutton').html("Call");
                        $(".oe_dial_inCallButton").attr('disabled','disabled');
                    }
                });
                this.session.on('bye',function(){
                    console.log("BYE");
                    var phonecall_model = new openerp.web.Model("crm.phonecall");
                    phonecall_model.call("hangup_call", [self.phonecall.id]).then(function(result){
                        openerp.web.bus.trigger('reload_panel');
                        self.session = false;
                        self.onCall = false;
                        self.phonecall.duration = parseFloat(result.duration).toFixed(2);
                        self.loggedCallOption();
                        if(self.in_automatic_mode === true){
                            self.next_call();
                        }else{
                            $('.oe_dial_big_callbutton').html("Call");
                            $(".oe_dial_inCallButton").attr('disabled','disabled');
                        }
                    });    
                });
            }catch(err){
                $('.oe_dial_big_callbutton').html("Call");
                $(".oe_dial_inCallButton").attr('disabled','disabled');
                new openerp.web.Model("crm.phonecall").call("error_config");
            }
        }*/
    }

    this.hangup = function(){
        if(session){
            if(onCall){
                session.bye();
            }else{
                session.cancel();
            }
        }
        return {};
    };

    this.transfer = function(number){
        if(session){
            session.refer(number);
            stop_automatic_call();
        }
    };

    function loggedCallOption(duration){
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
        current_phonecall.duration = _.str.sprintf(pattern, min, sec);

        openerp.client.action_manager.do_action({
                name: 'Log a call',
                type: 'ir.actions.act_window',
                key2: 'client_action_multi',
                src_model: "crm.phonecall",
                res_model: "crm.phonecall.log.wizard",
                multi: "True",
                target: 'new',
                context: {'phonecall_id': current_phonecall.id,
                'default_opportunity_id': current_phonecall.opportunity_id,
                'default_name': current_phonecall.name,
                'default_duration': current_phonecall.duration,
                'default_description' : current_phonecall.description,
                'default_opportunity_name' : current_phonecall.opportunity_name,
                'default_opportunity_planned_revenue' : current_phonecall.opportunity_planned_revenue,
                'default_opportunity_title_action' : current_phonecall.opportunity_title_action,
                'default_opportunity_date_action' : current_phonecall.opportunity_date_action,
                'default_opportunity_probability' : current_phonecall.opportunity_probability,
                'default_partner_id': current_phonecall.partner_id,
                'default_partner_name' : current_phonecall.partner_name,
                'default_partner_phone' : current_phonecall.partner_phone,
                'default_partner_email' : current_phonecall.partner_email,
                'default_partner_image_small' : current_phonecall.partner_image_small,},
                views: [[false, 'form']],
                flags: {
                    'headless': true,
                },
            });
    }
};