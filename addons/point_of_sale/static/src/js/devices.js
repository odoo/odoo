odoo.define('point_of_sale.devices', function (require) {
"use strict";

var core = require('web.core');
var mixins = require('web.mixins');
var Session = require('web.Session');
var Printer = require('point_of_sale.Printer').Printer;

// the JobQueue schedules a sequence of 'jobs'. each job is
// a function returning a promise. The queue waits for each job to finish
// before launching the next. Each job can also be scheduled with a delay.
// the  is used to prevent parallel requests to the proxy.

var JobQueue = function(){
    var queue = [];
    var running = false;
    var scheduled_end_time = 0;
    var end_of_queue = Promise.resolve();
    var stoprepeat = false;

    var run = function () {
        var runNextJob = function () {
            if (queue.length === 0) {
                running = false;
                scheduled_end_time = 0;
                return Promise.resolve();
            }
            running = true;
            var job = queue[0];
            if (!job.opts.repeat || stoprepeat) {
                queue.shift();
                stoprepeat = false;
            }

            // the time scheduled for this job
            scheduled_end_time = (new Date()).getTime() + (job.opts.duration || 0);

            // we run the job and put in prom when it finishes
            var prom = job.fun() || Promise.resolve();

            var always = function () {
                // we run the next job after the scheduled_end_time, even if it finishes before
                return new Promise(function (resolve, reject) {
                    setTimeout(
                        resolve,
                        Math.max(0, scheduled_end_time - (new Date()).getTime())
                    );
                });
            };
            // we don't care if a job fails ...
            return prom.then(always, always).then(runNextJob);
        };

        if (!running) {
            end_of_queue = runNextJob();
        }
    };

    /**
     * Adds a job to the schedule.
     *
     * @param {function} fun must return a promise
     * @param {object} [opts]
     * @param {number} [opts.duration] the job is guaranteed to finish no quicker than this (milisec)
     * @param {boolean} [opts.repeat] if true, the job will be endlessly repeated
     * @param {boolean} [opts.important] if true, the scheduled job cannot be canceled by a queue.clear()
     */
    this.schedule  = function (fun, opts) {
        queue.push({fun:fun, opts:opts || {}});
        if(!running){
            run();
        }
    };

    // remove all jobs from the schedule (except the ones marked as important)
    this.clear = function(){
        queue = _.filter(queue,function(job){return job.opts.important === true;});
    };

    // end the repetition of the current job
    this.stoprepeat = function(){
        stoprepeat = true;
    };

    /**
     * Returns a promise that resolves when all scheduled jobs have been run.
     * (jobs added after the call to this method are considered as well)
     *
     * @returns {Promise}
     */
    this.finished = function () {
        return end_of_queue;
    };

};


// this object interfaces with the local proxy to communicate to the various hardware devices
// connected to the Point of Sale. As the communication only goes from the POS to the proxy,
// methods are used both to signal an event, and to fetch information.

var ProxyDevice  = core.Class.extend(mixins.PropertiesMixin,{
    init: function(options){
        mixins.PropertiesMixin.init.call(this);
        var self = this;
        options = options || {};

        this.env = options.env;

        this.weighing = false;
        this.debug_weight = 0;
        this.use_debug_weight = false;

        this.paying = false;
        this.default_payment_status = {
            status: 'waiting',
            message: '',
            payment_method: undefined,
            receipt_client: undefined,
            receipt_shop:   undefined,
        };
        this.custom_payment_status = this.default_payment_status;

        this.notifications = {};
        this.bypass_proxy = false;

        this.connection = null;
        this.host       = '';
        this.keptalive  = false;

        this.set('status',{});

        this.set_connection_status('disconnected');

        this.on('change:status',this,function(eh,status){
            status = status.newValue;
            if(status.status === 'connected' && self.printer) {
                self.printer.print_receipt();
            }
        });

        this.posbox_supports_display = true;

        window.hw_proxy = this;
    },
    set_pos: function(pos) {
        this.setParent(pos);
        this.pos = pos;
    },
    set_connection_status: function(status, drivers, msg=''){
        var oldstatus = this.get('status');
        var newstatus = {};
        newstatus.status = status;
        newstatus.drivers = status === 'disconnected' ? {} : oldstatus.drivers;
        newstatus.drivers = drivers ? drivers : newstatus.drivers;
        newstatus.msg = msg;
        this.set('status',newstatus);
    },
    disconnect: function(){
        if(this.get('status').status !== 'disconnected'){
            this.connection.destroy();
            this.set_connection_status('disconnected');
        }
    },

    /**
     * Connects to the specified url.
     *
     * @param {string} url
     * @returns {Promise}
     */
    connect: function(url){
        var self = this;
        this.connection = new Session(undefined,url, { use_cors: true});
        this.host = url;
        if (this.pos.config.iface_print_via_proxy) {
            this.connect_to_printer();
        }
        this.set_connection_status('connecting',{});

        return this.message('handshake').then(function(response){
                if(response){
                    self.set_connection_status('connected');
                    localStorage.hw_proxy_url = url;
                    self.keepalive();
                }else{
                    self.set_connection_status('disconnected');
                    console.error('Connection refused by the Proxy');
                }
            },function(){
                self.set_connection_status('disconnected');
                console.error('Could not connect to the Proxy');
            });
    },

    connect_to_printer: function () {
        this.printer = new Printer(this.host, this.pos);
    },

    /**
     * Find a proxy and connects to it.
     *
     * @param {Object} [options]
     * @param {string} [options.force_ip] only try to connect to the specified ip.
     * @param {string} [options.port] @see find_proxy
     * @param {function} [options.progress] @see find_proxy
     * @returns {Promise}
     */
    autoconnect: function (options) {
        var self = this;
        this.set_connection_status('connecting',{});
        if (this.pos.config.iface_print_via_proxy) {
            this.connect_to_printer();
        }
        var found_url = new Promise(function () {});

        if (options.force_ip) {
            // if the ip is forced by server config, bailout on fail
            found_url = this.try_hard_to_connect(options.force_ip, options);
        } else if (localStorage.hw_proxy_url) {
            // try harder when we remember a good proxy url
            found_url = this.try_hard_to_connect(localStorage.hw_proxy_url, options)
                .catch(function () {
                    if (window.location.protocol != 'https:') {
                        return self.find_proxy(options);
                    }
                });
        } else {
            // just find something quick
            if (window.location.protocol != 'https:'){
                found_url = this.find_proxy(options);
            }
        }

        var successProm = found_url.then(function (url) {
            return self.connect(url);
        });

        successProm.catch(function () {
            self.set_connection_status('disconnected');
        });

        return successProm;
    },

    // starts a loop that updates the connection status
    keepalive: function () {
        var self = this;

        function status(){
            var always = function () {
                setTimeout(status, 5000);
            };
            self.connection.rpc('/hw_proxy/status_json',{},{shadow: true, timeout:2500})
                .then(function (driver_status) {
                    self.set_connection_status('connected',driver_status);
                }, function () {
                    if(self.get('status').status !== 'connecting'){
                        self.set_connection_status('disconnected');
                    }
                }).then(always, always);
        }

        if (!this.keptalive) {
            this.keptalive = true;
            status();
        }
    },

    /**
     * @param {string} name
     * @param {Object} [params]
     * @returns {Promise}
     */
    message : function (name, params) {
        var callbacks = this.notifications[name] || [];
        for (var i = 0; i < callbacks.length; i++) {
            callbacks[i](params);
        }
        if (this.get('status').status !== 'disconnected') {
            return this.connection.rpc('/hw_proxy/' + name, params || {}, {shadow: true});
        } else {
            return Promise.reject();
        }
    },

    /**
     * Tries several time to connect to a known proxy url.
     *
     * @param {*} url
     * @param {Object} [options]
     * @param {string} [options.port=8069] what port to listen to
     * @returns {Promise<string|Array>}
     */
    try_hard_to_connect: function (url, options) {
        options   = options || {};
        var protocol = window.location.protocol;
        var port = ( !options.port && protocol == "https:") ? ':443' : ':' + (options.port || '8069');

        this.set_connection_status('connecting');

        if(url.indexOf('//') < 0){
            url = protocol + '//' + url;
        }

        if(url.indexOf(':',5) < 0){
            url = url + port;
        }

        // try real hard to connect to url, with a 1sec timeout and up to 'retries' retries
        function try_real_hard_to_connect(url, retries) {
            return Promise.resolve(
                $.ajax({
                    url: url + '/hw_proxy/hello',
                    method: 'GET',
                    timeout: 1000,
                })
                .then(function () {
                    return Promise.resolve(url);
                }, function (resp) {
                    if (retries > 0) {
                        return try_real_hard_to_connect(url, retries-1);
                    } else {
                        return Promise.reject([resp.statusText, url]);
                    }
                })
            );
        }

        return try_real_hard_to_connect(url, 3);
    },

    /**
     * Returns as a promise a valid host url that can be used as proxy.
     *
     * @param {Object} [options]
     * @param {string} [options.port] what port to listen to (default 8069)
     * @param {function} [options.progress] callback for search progress ( fac in [0,1] )
     * @returns {Promise<string>} will be resolved with the proxy valid url
     */
    find_proxy: function(options){
        options = options || {};
        var self  = this;
        var port  = ':' + (options.port || '8069');
        var urls  = [];
        var found = false;
        var parallel = 8;
        var threads  = [];
        var progress = 0;


        urls.push('http://localhost'+port);
        for(var i = 0; i < 256; i++){
            urls.push('http://192.168.0.'+i+port);
            urls.push('http://192.168.1.'+i+port);
            urls.push('http://10.0.0.'+i+port);
        }

        var prog_inc = 1/urls.length;

        function update_progress(){
            progress = found ? 1 : progress + prog_inc;
            if(options.progress){
                options.progress(progress);
            }
        }

        function thread () {
            var url = urls.shift();

            if (!url || found || !self.searching_for_proxy) {
                return Promise.resolve();
            }

            return Promise.resolve(
                $.ajax({
                    url: url + '/hw_proxy/hello',
                    method: 'GET',
                    timeout: 400,
                }).then(function () {
                    found = true;
                    update_progress();
                    return Promise.resolve(url);
                }, function () {
                    update_progress();
                    return thread();
                })
            );
        }

        this.searching_for_proxy = true;

        var len  = Math.min(parallel, urls.length);
        for(i = 0; i < len; i++){
            threads.push(thread());
        }

        return new Promise(function (resolve, reject) {
            Promise.all(threads).then(function(results){
                var urls = [];
                for(var i = 0; i < results.length; i++){
                    if(results[i]){
                        urls.push(results[i]);
                    }
                }
                resolve(urls[0]);
            });
        });
    },

    stop_searching: function(){
        this.searching_for_proxy = false;
        this.set_connection_status('disconnected');
    },

    // this allows the client to be notified when a proxy call is made. The notification
    // callback will be executed with the same arguments as the proxy call
    add_notification: function(name, callback){
        if(!this.notifications[name]){
            this.notifications[name] = [];
        }
        this.notifications[name].push(callback);
    },

    /**
     * Returns the weight on the scale.
     *
     * @returns {Promise<Object>}
     */
    scale_read: function () {
        var self = this;
        if (self.use_debug_weight) {
            return Promise.resolve({weight:this.debug_weight, unit:'Kg', info:'ok'});
        }
        return new Promise(function (resolve, reject) {
            self.message('scale_read',{})
            .then(function (weight) {
                resolve(weight);
            }, function () { //failed to read weight
                resolve({weight:0.0, unit:'Kg', info:'ok'});
            });
        });
    },

    // sets a custom weight, ignoring the proxy returned value.
    debug_set_weight: function(kg){
        this.use_debug_weight = true;
        this.debug_weight = kg;
    },

    // resets the custom weight and re-enable listening to the proxy for weight values
    debug_reset_weight: function(){
        this.use_debug_weight = false;
        this.debug_weight = 0;
    },

    update_customer_facing_display: function(html) {
        if (this.posbox_supports_display && this.get('status').status == 'connected') {
            return this.message('customer_facing_display',
                { html: html },
                { timeout: 5000 });
        }
    },

    /**
     * @param {string} html
     * @returns {Promise}
     */
    take_ownership_over_client_screen: function(html) {
        return this.message("take_control", { html: html });
    },

    /**
     * @returns {Promise}
     */
    test_ownership_of_client_screen: function() {
        if (this.connection) {
            return this.message("test_ownership", {});
        }
        return Promise.reject({abort: true});
    },

    // asks the proxy to log some information, as with the debug.log you can provide several arguments.
    log: function(){
        return this.message('log',{'arguments': _.toArray(arguments)});
    },

});

return {
    JobQueue: JobQueue,
    ProxyDevice: ProxyDevice,
};

});
