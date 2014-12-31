openerp.voip = function(openerp) {
    "use strict";

    var _t = openerp._t;

    openerp.voip.user_agent = openerp.Class.extend(openerp.PropertiesMixin,{
        init: function(parent,options){
            openerp.PropertiesMixin.init.call(this,parent);
            var self = this;
            self.in_automatic_mode = false;
            self.onCall = false;
            new openerp.web.Model("voip.configurator").call("get_pbx_config").then(function(result){
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
                var audio = document.createElement("audio");
                audio.id = "remote_audio";
                audio.autoplay = "autoplay";
                document.body.appendChild(audio);
                audio = document.createElement("audio");
                audio.id = "ringbacktone";
                audio.loop = "true";
                audio.src = "/voip/static/src/sounds/ringbacktone.mp3";
                document.body.appendChild(audio);
            });
        },

        //success callback function of the getUserMedia function
        getUserMediaSuccess: function(stream) {
            var self = this;
            self.mediaStream = stream;
            if(!self.session){
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
                    self.session = self.ua.invite(self.current_number,call_options);
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
                    self.session.on('accepted',_.bind(self.accepted,self));
                    //Bind action when the call is in progress to catch the ringing phase
                    self.session.on('progress', _.bind(self.progress,self));
                    //Bind action when the call is rejected by the customer
                    self.session.on('rejected',_.bind(self.rejected,self));
                    //Bind action when the call is transfered
                    self.session.on('refer',function(response){console.log("REFER");console.log(response);});
                    //Bind action when the user hangup the call while ringing
                    self.session.on('cancel',_.bind(self.cancel,self));
                    //Bind action when the call is hanged up
                    self.session.on('bye',_.bind(self.bye,self));
                }catch(err){
                    self.trigger('sip_error');
                }
            }
        },

        getUserMediaFailure: function(e) {
            console.error('getUserMedia failed:', e);
        },

        rejected: function(){
            console.log("REJECTED");
            this.session = false;
            clearTimeout(this.timer);
            this.trigger('sip_rejected');
            this.ringbacktone = document.getElementById("ringbacktone");
            ringbacktone.pause();
        },

        bye: function(){
            console.log("BYE");
            clearTimeout(this.timer);
            this.trigger('sip_bye');
            this.session = false;
            this.onCall = false;
        },

        progress: function(response){
            console.log("PROGRESS");console.log(response);
            var self = this;
            if(response.reason_phrase == "Ringing"){
                this.trigger('sip_ringing');
                var ringbacktone = document.getElementById("ringbacktone");
                ringbacktone.play();
                //set the timer to stop the call if ringing too long
                this.timer = setTimeout(function(){
                    self.trigger('sip_rejected');
                    self.session.cancel();
                },4000*self.ring_number);
            }
        },

        accepted: function(result){
            console.log("ACCEPTED");
            console.log(result);
            this.onCall = true;
            clearTimeout(this.timer);
            var ringbacktone = document.getElementById("ringbacktone");
            ringbacktone.pause();
            this.trigger('sip_accepted');
            if(this.always_transfert){
                this.session.refer(this.physical_phone);
            }
        },

        cancel: function(){
            console.log("CANCEL");
            this.session = false;
            clearTimeout(this.timer);
            var ringbacktone = document.getElementById("ringbacktone");
            ringbacktone.pause();
            this.trigger('sip_cancel');
        },

        make_call: function(number){
            var self = this;
            self.current_number = number;
            var mediaConstraints = {
                audio: true,
                video: false
            };
            //if there is already a mediaStream, it is reused
            if (self.mediaStream) {
                self.getUserMediaSuccess.call(self,self.mediaStream);
            } else {
                if (SIP.WebRTC.isSupported()) {
                    /*      
                        WebRTC method to get a mediastream      
                        The callbacks functions are getUserMediaSuccess, when the function succeed      
                        and getUserMediaFailure when the function failed
                        The _.bind is used to be ensure that the "this" in the callback function will still be the same
                        and not become the object "window"        
                    */ 
                    SIP.WebRTC.getUserMedia(mediaConstraints, _.bind(self.getUserMediaSuccess,self), _.bind(self.getUserMediaFailure,self));
                }
            }
        },

        hangup: function(){
            var self = this;
            if(self.session){
                if(self.onCall){
                    self.session.bye();
                }else{
                    self.session.cancel();
                }
            }
            return {};
        },

        transfer: function(number){
            var self = this;
            if(self.session){
                self.session.refer(number);
                self.stop_automatic_call();
            }
        },
    });
};