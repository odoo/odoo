// Part of web_progress. See LICENSE file for full copyright and licensing details.
odoo.define('web.progress.ajax', function (require) {
"use strict";

/**
 * Add progress code into Ajax RPC and relay events through a bus
 */

var core = require('web.core');
var ajax = require('web.ajax');
var mixins = require('web.mixins');

var ajax_jsonRpc = ajax.jsonRpc;
var ajax_jsonpRpc = ajax.jsonpRpc;
var ajax_rpc = ajax.rpc;
var ajax_get_file = ajax.get_file;
var progress_codes = {};
var rpcIdToProgressCodes = {};

function pseudoUuid(a){
    return a?(a^Math.random()*16>>a/4).toString(16):([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g,pseudoUuid)
}

var RelayRequest = core.Class.extend(mixins.EventDispatcherMixin, {
    init: function (url, fct_name, params, progress_code) {
        const handle = function (rpcId = -1) {
            if (validateCall(url, fct_name, params)) {
                if (rpcId >= 0) {
                    rpcIdToProgressCodes[rpcId] = progress_code;
                }
                core.bus.trigger('rpc_progress_request', progress_code);
            }
            this.destroy();
        }
        mixins.EventDispatcherMixin.init.call(this);
        core.bus.on('rpc_request', this, handle);
        core.bus.on('RPC:REQUEST', this, handle);
    },
});

var RelayResult = core.Class.extend(mixins.EventDispatcherMixin, {
    init: function () {
        var self = this;
        mixins.EventDispatcherMixin.init.call(this);
        core.bus.on('RPC:RESPONSE', this, function (rpcId) {
            if (rpcId in rpcIdToProgressCodes) {
                const progress_code = rpcIdToProgressCodes[rpcId];
                delete rpcIdToProgressCodes[rpcId];
                self.handle(progress_code);
            }
        });
        core.bus.on('rpc:result', this, function (data, result) {
            var progress_code = -1;
            var context = findContext(data.params);
            if (context) {
                progress_code = context.progress_code;
                self.handle(progress_code);
            }
        });
    },
    handle: function (progress_code) {
        if (progress_code in progress_codes) {
            delete progress_codes[progress_code];
            core.bus.trigger('rpc_progress_result', progress_code);
        }
    }
});

var relay_result = new RelayResult();

function validateCall(url, fct_name, params, settings) {
    if (settings && settings.shadow) {
        // do not track shadowed calls
        return false;
    }
    return url.startsWith('/web/') && fct_name === 'call' && params.model !== 'web.progress';
}

function findContext(params) {
    var ret = false;
    if ('context' in params) {
            ret = params.context;
        } else if ('kwargs' in params) {
            if ('context' in params.kwargs) {
                ret = params.kwargs.context;
            }
        } else if ('args' in params && params.args.length > 0) {
            ret = params.args[params.args.length - 1];
        }
    return ret;
}

function genericRelayEvents(url, fct_name, params) {
    if (validateCall(url, fct_name, params)) {
        var progress_code = pseudoUuid();
        var context = findContext(params);
        if (context && !context.progress_code) {
            context['progress_code'] = progress_code;
            progress_codes[progress_code] = new RelayRequest(url, fct_name, params, progress_code);
        }
    }
    return params;
}

function jsonRpc(url, fct_name, params, settings) {
    if (validateCall(url, fct_name, params, settings)) {
        genericRelayEvents(url, fct_name, params);
    }
    return ajax_jsonRpc(url, fct_name, params, settings);
}

function jsonpRpc(url, fct_name, params, settings) {
    if (validateCall(url, fct_name, params, settings)) {
        genericRelayEvents(url, fct_name, params);
    }
    return ajax_jsonpRpc(url, fct_name, params, settings);
}

function rpc(url, params, settings) {
    var fct_name = 'call';
    if (validateCall(url, fct_name, params, settings)) {
        genericRelayEvents(url, fct_name, params);
    }
    return ajax_rpc(url, params, settings);
}

function get_file(options) {
    var complete = options.complete;
    if (options.data && options.data.data) {
        var data = JSON.parse(options.data.data);
        var context = data.context;
        if (!context && Array.isArray(data)) {
            data.push({});
            context = data[data.length - 1];
        }
        if (complete && context) {
            var progress_code = pseudoUuid();
            context['progress_code'] = progress_code;
            options.complete = function () {
                core.bus.trigger('rpc_progress_result', progress_code);
                complete();
            };
            core.bus.trigger('rpc_progress_request', progress_code);
            options.data.data = JSON.stringify(data)
        }
    }
    return ajax_get_file(options);
}

ajax.jsonRpc = jsonRpc;
ajax.jsonpRpc = jsonpRpc;
ajax.rpc = rpc;
ajax.get_file = get_file;

return {
    jsonRpc: jsonRpc,
    jsonpRpc: jsonpRpc,
    rpc: rpc,
    get_file: get_file,
    RelayRequest: RelayRequest,
    RelayResult: RelayResult,
    genericRelayEvents: genericRelayEvents,
    relay_result: relay_result,
    pseudo_uuid: pseudoUuid,
    validateCall: validateCall,
    findContext: findContext,
}
});

