openerp.ari_client = function(instance) {

	var listeners = []
	var phone

	this.init = function() {
		var self = this;
		if(window.WebSocket) {
			var socket = new WebSocket("ws://localhost:8088/ari/events?api_key=asterisk:asterisk&app=bridge-dial");
			socket.onmessage = function(message) {
				data = JSON.parse(message.data);
				console.log("msg: ");
				console.log(data);
				for(id in listeners){
					self.checkListener(listeners[id],data);
				}
				if(data.type=="StasisStart"){
					if(data.args.indexOf("dialed") > -1){
						return [];
					}
					phone = data.args[0];
					self.answer(data.channel);
					self.playWaitSound(data.channel);
				}
			}			
		}
	}
	
	this.checkListener = function(listener, msg){
		if(msg.type == listener.type && msg.hasOwnProperty(listener.target)&& msg[listener.target].id == listener.obj.id){
			this[listener.callback](listener.obj, listener.param);
		}
		if(msg.type == listener.type && listener.type == "PlaybackFinished"){
			var target = msg.playback.target_uri;
			var id = target.substring(target.indexOf(':')+1);
			if(id == listener.obj.id){
				this[listener.callback](listener.obj);
			}
		}
	}

	this.answer = function(channel){
		$.ajax({
			type: "POST",
			url: "http://localhost:8088/ari/channels/" + channel.id + "/answer?api_key=asterisk:asterisk",
		})
	}

	this.playWaitSound = function(channel){
		$.ajax({
			type: "POST",
			url: "http://localhost:8088/ari/channels/" + channel.id + "/play?media=sound%3Apls-wait-connect-call&api_key=asterisk:asterisk",
		}).done(function(response){
			listener = {'type':'PlaybackFinished', 'obj':channel, 'callback':'findOrCreateHoldingBridge','target':'channel'};
			listeners.push(listener);
		})
	}

	this.findOrCreateHoldingBridge = function (channel) {
		var self = this;
		this.getBridges(function(bridges){
			var holdingBridge = bridges.filter(function(candidate) {
				return candidate.bridge_type === 'holding';
			})[0];
			if(holdingBridge){
				console.log('Using existing holding bridge ' + holdingBridge.id);
				self.originate(channel,holdingBridge);
			}else{
				self.createBridge("holding",function(holdingBridge){
					console.log('Creating a new bridge ' + holdingBridge.id);
					self.originate(channel,holdingBridge);
				});
			}
		});
	}

	this.originate = function(channel, holdingBridge){
		this.addChannel(holdingBridge, channel);
		$.ajax({
			type: "POST",
			url: "http://localhost:8088/ari/channels?app=bridge-dial&endpoint=" + phone + "&appArgs=dialed&api_key=asterisk:asterisk",
		}).done(function(dialed){
			listener = {'type':'StasisStart', 'obj':dialed, 'callback':'outgoingStart', 'target':'channel', 'param': [channel, dialed, holdingBridge]};
			listeners.push(listener);
			listener = {'type':'StasisEnd', 'obj':channel, 'callback':'incommingEnd', 'target':'channel', 'param':dialed.id};
			listeners.push(listener);
			listener = {'type':'ChannelDestroyed', 'obj':dialed, 'callback':'outgoingDestroyed', 'target':'channel', 'param':channel.id};
			listeners.push(listener);
		})
	}

	this.addChannel = function(bridge, channel){
		$.ajax({
			type: "POST",
			url: "http://localhost:8088/ari/bridges/"+bridge.id+"/addChannel?channel="+channel.id+"&api_key=asterisk:asterisk",
		})
	}

	this.removeChannel = function(bridge, channel){
		$.ajax({
			type: "POST",
			url: "http://localhost:8088/ari/bridges/"+bridge.id+"/removeChannel?channel="+channel.id+"&api_key=asterisk:asterisk",
		})
	}

	this.getBridges = function(callback){
		$.ajax({
			type: "GET",
			url: "http://localhost:8088/ari/bridges?api_key=asterisk:asterisk",
		}).done(function(response){
			console.log("Bridges: ");
			console.log(response);
			callback(response);
		})
	}

	this.createBridge = function(bridge_type,callback){
		$.ajax({
			type: "POST",
			url: "http://localhost:8088/ari/bridges?type=" + bridge_type + "&api_key=asterisk:asterisk",
		}).done(function(response){
			callback(response);
		});
	}

	this.getChannels = function(callback){
		$.ajax({
			type: "GET",
			url: "http://localhost:8088/ari/channels?api_key=asterisk:asterisk",
		}).done(function(response){
			console.log("Channels: ");
			console.log(response);
			callback(response);
		});
	}

	this.outgoingStart = function(channel, param){
		this.joinMixingBridge(param[0],param[1],param[2]);
	}

	this.joinMixingBridge = function(channel, dialed, holdingBridge){
		var self = this;
		var listener = {'type':'StasisEnd', 'obj':dialed, 'callback':'outgoingEnd', 'target':'channel'};
		listeners.push(listener);
		this.answer(dialed);
		self.createBridge("mixing",function(mixingBridge){
			self.moveToMixingBridge(channel, dialed, mixingBridge, holdingBridge);
		});
	}

	this.moveToMixingBridge = function(channel, dialed, mixingBridge, holdingBridge){
		this.removeChannel(holdingBridge,channel);
		this.addChannel(mixingBridge,channel);
		this.addChannel(mixingBridge,dialed);
	}

	this.incommingEnd = function(channel,param){
		console.log("INCOMMING END")
		$.ajax({
			type: "DELETE",
			url: "http://localhost:8088/ari/channels/" + param + "?api_key=asterisk:asterisk",
		})
		
	}

	this.outgoingEnd = function(channel,param){
		console.log("OUTGOING END")
		$.ajax({
			type: "DELETE",
			url: "http://localhost:8088/ari/channels/" + param + "?api_key=asterisk:asterisk",
		})
	}

	this.outgoingDestroyed = function(channel,param){
		console.log("OUTGOING DESTROYED")
		$.ajax({
			type: "DELETE",
			url: "http://localhost:8088/ari/channels/" + param + "?api_key=asterisk:asterisk",
		})
	}

	this.hangup = function(channel){
		console.log("HANGUP")
		$.ajax({
			type: "DELETE",
			url: "http://localhost:8088/ari/channels/" + channel.id + "?api_key=asterisk:asterisk",
		})
	}

	this.call = function(phonecall, callback){
		var number;
		console.log(phonecall);
		if(phonecall.partner_phone){
			number = phonecall.partner_phone;
		} else if (phonecall.partner_mobile){
			number = phonecall.partner_mobile;
		}
		$.ajax({
			type: "POST",
			url: "http://localhost:8088/ari/channels?app=bridge-dial&endpoint=SIP/" + number + "&app=bridge-dial&appArgs=SIP/2002&api_key=asterisk:asterisk",
		}).done(function(dialed){
			callback(dialed);
		});
	}
};