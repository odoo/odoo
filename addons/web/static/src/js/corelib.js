/*
 * Copyright (c) 2012, OpenERP S.A.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions and the following disclaimer in the documentation
 *    and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
 * ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

openerp.web.corelib = function(instance) {

var ControllerMixin = {
    /**
     * Informs the action manager to do an action. This supposes that
     * the action manager can be found amongst the ancestors of the current widget.
     * If that's not the case this method will simply return `false`.
     */
    do_action: function() {
        var parent = this.getParent();
        if (parent) {
            return parent.do_action.apply(parent, arguments);
        }
        return false;
    },
    do_notify: function() {
        if (this.getParent()) {
            return this.getParent().do_notify.apply(this,arguments);
        }
        return false;
    },
    do_warn: function() {
        if (this.getParent()) {
            return this.getParent().do_warn.apply(this,arguments);
        }
        return false;
    },
    rpc: function(url, data, options) {
        return this.alive(openerp.session.rpc(url, data, options));
    }
};

/**
    A class containing common utility methods useful when working with OpenERP as well as the PropertiesMixin.
*/
openerp.web.Controller = openerp.web.Class.extend(openerp.web.PropertiesMixin, ControllerMixin, {
    /**
     * Constructs the object and sets its parent if a parent is given.
     *
     * @param {openerp.web.Controller} parent Binds the current instance to the given Controller instance.
     * When that controller is destroyed by calling destroy(), the current instance will be
     * destroyed too. Can be null.
     */
    init: function(parent) {
        openerp.web.PropertiesMixin.init.call(this);
        this.setParent(parent);
        this.session = openerp.session;
    },
});

openerp.web.Widget.include(_.extend({}, ControllerMixin, {
    init: function() {
        this._super.apply(this, arguments);
        this.session = openerp.session;
    },
}));

instance.web.Registry = instance.web.Class.extend({
    /**
     * Stores a mapping of arbitrary key (strings) to object paths (as strings
     * as well).
     *
     * Resolves those paths at query time in order to always fetch the correct
     * object, even if those objects have been overloaded/replaced after the
     * registry was created.
     *
     * An object path is simply a dotted name from the instance root to the
     * object pointed to (e.g. ``"instance.web.Session"`` for an OpenERP
     * session object).
     *
     * @constructs instance.web.Registry
     * @param {Object} mapping a mapping of keys to object-paths
     */
    init: function (mapping) {
        this.parent = null;
        this.map = mapping || {};
    },
    /**
     * Retrieves the object matching the provided key string.
     *
     * @param {String} key the key to fetch the object for
     * @param {Boolean} [silent_error=false] returns undefined if the key or object is not found, rather than throwing an exception
     * @returns {Class} the stored class, to initialize or null if not found
     */
    get_object: function (key, silent_error) {
        var path_string = this.map[key];
        if (path_string === undefined) {
            if (this.parent) {
                return this.parent.get_object(key, silent_error);
            }
            if (silent_error) { return void 'nooo'; }
            return null;
        }

        var object_match = instance;
        var path = path_string.split('.');
        // ignore first section
        for(var i=1; i<path.length; ++i) {
            object_match = object_match[path[i]];

            if (object_match === undefined) {
                if (silent_error) { return void 'noooooo'; }
                return null;
            }
        }
        return object_match;
    },
    /**
     * Checks if the registry contains an object mapping for this key.
     *
     * @param {String} key key to look for
     */
    contains: function (key) {
        if (key === undefined) { return false; }
        if (key in this.map) {
            return true;
        }
        if (this.parent) {
            return this.parent.contains(key);
        }
        return false;
    },
    /**
     * Tries a number of keys, and returns the first object matching one of
     * the keys.
     *
     * @param {Array} keys a sequence of keys to fetch the object for
     * @returns {Class} the first class found matching an object
     */
    get_any: function (keys) {
        for (var i=0; i<keys.length; ++i) {
            var key = keys[i];
            if (!this.contains(key)) {
                continue;
            }

            return this.get_object(key);
        }
        return null;
    },
    /**
     * Adds a new key and value to the registry.
     *
     * This method can be chained.
     *
     * @param {String} key
     * @param {String} object_path fully qualified dotted object path
     * @returns {instance.web.Registry} itself
     */
    add: function (key, object_path) {
        this.map[key] = object_path;
        return this;
    },
    /**
     * Creates and returns a copy of the current mapping, with the provided
     * mapping argument added in (replacing existing keys if needed)
     *
     * Parent and child remain linked, a new key in the parent (which is not
     * overwritten by the child) will appear in the child.
     *
     * @param {Object} [mapping={}] a mapping of keys to object-paths
     */
    extend: function (mapping) {
        var child = new instance.web.Registry(mapping);
        child.parent = this;
        return child;
    },
    /**
     * @deprecated use Registry#extend
     */
    clone: function (mapping) {
        console.warn('Registry#clone is deprecated, use Registry#extend');
        return this.extend(mapping);
    }
});

instance.web.JsonRPC = instance.web.Class.extend(instance.web.PropertiesMixin, {
    triggers: {
        'request': 'Request sent',
        'response': 'Response received',
        'response_failed': 'HTTP Error response or timeout received',
        'error': 'The received response is an JSON-RPC error',
    },
    /**
     * @constructs instance.web.JsonRPC
     *
     * @param {String} [server] JSON-RPC endpoint hostname
     * @param {String} [port] JSON-RPC endpoint port
     */
    init: function() {
        instance.web.PropertiesMixin.init.call(this);
        this.server = null;
        this.debug = ($.deparam($.param.querystring()).debug !== undefined);
        this.override_session = false;
        this.session_id = undefined;
    },
    setup: function(origin) {
        var window_origin = location.protocol+"//"+location.host, self=this;
        this.origin = origin ? _.str.rtrim(origin,'/') : window_origin;
        this.prefix = this.origin;
        this.server = this.origin; // keep chs happy
        this.rpc_function = (this.origin == window_origin) ? this.rpc_json : this.rpc_jsonp;
    },
    /**
     * Executes an RPC call, registering the provided callbacks.
     *
     * Registers a default error callback if none is provided, and handles
     * setting the correct session id and session context in the parameter
     * objects
     *
     * @param {String} url RPC endpoint
     * @param {Object} params call parameters
     * @param {Object} options additional options for rpc call
     * @param {Function} success_callback function to execute on RPC call success
     * @param {Function} error_callback function to execute on RPC call failure
     * @returns {jQuery.Deferred} jquery-provided ajax deferred
     */
    rpc: function(url, params, options) {
        var self = this;
        options = options || {};
        // url can be an $.ajax option object
        if (_.isString(url)) {
            url = { url: url };
        }
        _.defaults(params, {
            context: this.user_context || {}
        });
        // Construct a JSON-RPC2 request, method is currently unused
        var payload = {
            jsonrpc: '2.0',
            method: 'call',
            params: params,
            id: _.uniqueId('r')
        };
        var deferred = $.Deferred();
        if (! options.shadow)
            this.trigger('request', url, payload);
        
        if (options.timeout)
            url.timeout = options.timeout;

        this.rpc_function(url, payload).then(
            function (response, textStatus, jqXHR) {
                if (! options.shadow)
                    self.trigger('response', response);
                if (!response.error) {
                    deferred.resolve(response["result"], textStatus, jqXHR);
                } else if (response.error.code === 100) {
                    self.uid = false;
                } else {
                    deferred.reject(response.error, $.Event());
                }
            },
            function(jqXHR, textStatus, errorThrown) {
                if (! options.shadow)
                    self.trigger('response_failed', jqXHR);
                var error = {
                    code: -32098,
                    message: "XmlHttpRequestError " + errorThrown,
                    data: {type: "xhr"+textStatus, debug: jqXHR.responseText, objects: [jqXHR, errorThrown] }
                };
                deferred.reject(error, $.Event());
            });
        // Allow deferred user to disable rpc_error call in fail
        deferred.fail(function() {
            deferred.fail(function(error, event) {
                if (!event.isDefaultPrevented()) {
                    self.trigger('error', error, event);
                }
            });
        });
        return deferred;
    },
    /**
     * Raw JSON-RPC call
     *
     * @returns {jQuery.Deferred} ajax-webd deferred object
     */
    rpc_json: function(url, payload) {
        var self = this;
        var ajax = _.extend({
            type: "POST",
            dataType: 'json',
            contentType: 'application/json',
            data: JSON.stringify(payload),
            processData: false,
            headers: {
                "X-Openerp-Session-Id": this.override_session ? this.session_id : undefined,
            },
        }, url);
        if (this.synch)
            ajax.async = false;
        return $.ajax(ajax);
    },
    rpc_jsonp: function(url, payload) {
        var self = this;
        // extracted from payload to set on the url
        var data = {
            session_id: this.session_id,
            id: payload.id,
        };

        var set_sid = function (response, textStatus, jqXHR) {
            // If response give us the http session id, we store it for next requests...
            if (response.session_id) {
                self.session_id = response.session_id;
            }
        };

        url.url = this.url(url.url, null);
        var ajax = _.extend({
            type: "GET",
            dataType: 'jsonp',
            jsonp: 'jsonp',
            cache: false,
            data: data
        }, url);
        if (this.synch)
            ajax.async = false;
        var payload_str = JSON.stringify(payload);
        var payload_url = $.param({r:payload_str});
        if (payload_url.length < 2000) {
            // Direct jsonp request
            ajax.data.r = payload_str;
            return $.ajax(ajax).done(set_sid);
        } else {
            // Indirect jsonp request
            var ifid = _.uniqueId('oe_rpc_iframe');
            var display = self.debug ? 'block' : 'none';
            var $iframe = $(_.str.sprintf("<iframe src='javascript:false;' name='%s' id='%s' style='display:%s'></iframe>", ifid, ifid, display));
            var $form = $('<form>')
                        .attr('method', 'POST')
                        .attr('target', ifid)
                        .attr('enctype', "multipart/form-data")
                        .attr('action', ajax.url + '?jsonp=1&' + $.param(data))
                        .append($('<input type="hidden" name="r" />').attr('value', payload_str))
                        .hide()
                        .appendTo($('body'));
            var cleanUp = function() {
                if ($iframe) {
                    $iframe.unbind("load").remove();
                }
                $form.remove();
            };
            var deferred = $.Deferred();
            // the first bind is fired up when the iframe is added to the DOM
            $iframe.bind('load', function() {
                // the second bind is fired up when the result of the form submission is received
                $iframe.unbind('load').bind('load', function() {
                    $.ajax(ajax).always(function() {
                        cleanUp();
                    }).done(function() {
                        deferred.resolve.apply(deferred, arguments);
                    }).fail(function() {
                        deferred.reject.apply(deferred, arguments);
                    });
                });
                // now that the iframe can receive data, we fill and submit the form
                $form.submit();
            });
            // append the iframe to the DOM (will trigger the first load)
            $form.after($iframe);
            return deferred.done(set_sid);
        }
    },

    url: function(path, params) {
        params = _.extend(params || {});
        if (this.override_session)
            params.session_id = this.session_id;
        var qs = '?' + $.param(params);
        var prefix = _.any(['http://', 'https://', '//'], _.bind(_.str.startsWith, null, path)) ? '' : this.prefix; 
        return prefix + path + qs;
    },
});

instance.web.py_eval = function(expr, context) {
    return py.eval(expr, _.extend({}, context || {}, {"true": true, "false": false, "null": null}));
};

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
