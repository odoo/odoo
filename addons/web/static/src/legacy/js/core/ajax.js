/** @odoo-module **/

import core from "@web/legacy/js/services/core";
import time from "@web/legacy/js/core/time";
import { session } from "@web/session";

import { markup } from "@odoo/owl";

// Create the final object containing all the functions first to allow monkey
// patching them correctly if ever needed.
var ajax = {};

function _genericJsonRpc (fct_name, params, settings, fct) {
    var shadow = settings.shadow || false;
    delete settings.shadow;
    var data = {
        jsonrpc: "2.0",
        method: fct_name,
        params: params,
        id: Math.floor(Math.random() * 1000 * 1000 * 1000)
    };

    if (!shadow) {
        core.bus.trigger('rpc_request', data.id);
    }

    var xhr = fct(data);
    var result = xhr.then(function(result) {
        core.bus.trigger('rpc:result', data, result);
        if (result.error !== undefined) {
            console.debug(
                "Server application error\n",
                "Error code:", result.error.code, "\n",
                "Error message:", result.error.message, "\n",
                "Error data message:\n", result.error.data.message, "\n",
                "Error data debug:\n", result.error.data.debug
            );
            return Promise.reject({type: "server", error: result.error});
        } else {
            return result.result;
        }
    }, function() {
        //console.error("JsonRPC communication error", [...arguments]);
        var reason = {
            type: 'communication',
            error: arguments[0],
            textStatus: arguments[1],
            errorThrown: arguments[2],
        };
        return Promise.reject(reason);
    });

    var rejection;
    var promise = new Promise(function (resolve, reject) {
        rejection = reject;

        result.then(function (result) {
            if (!shadow) {
                core.bus.trigger('rpc_response', data.id);
            }
            resolve(result);
        }, function (reason) {
            var type = reason.type;
            var error = reason.error;
            var textStatus = reason.textStatus;
            var errorThrown = reason.errorThrown;
            if (type === "server") {
                if (!shadow) {
                    core.bus.trigger('rpc_response', data.id);
                }
                reject({message: error, event: $.Event()});
            } else {
                if (!shadow) {
                    core.bus.trigger('rpc_response_failed', data.id);
                }
                var nerror = {
                    code: -32098,
                    message: "XmlHttpRequestError " + errorThrown,
                    data: {
                        type: "xhr"+textStatus,
                        debug: error.responseText,
                        objects: [error, errorThrown],
                        arguments: [reason || textStatus]
                    },
                };
                reject({message: nerror, event: $.Event()});
            }
        });
    });

    // FIXME: jsonp?
    promise.abort = function () {
        rejection({
            message: "XmlHttpRequestError abort",
            event: $.Event('abort')
        });

        if (!shadow) {
            core.bus.trigger('rpc_response');
        }

        if (xhr.abort) {
            xhr.abort();
        }
    };
    promise.guardedCatch(function (reason) { // Allow promise user to disable rpc_error call in case of failure
        setTimeout(function () {
            // we want to execute this handler after all others (hence
            // setTimeout) to let the other handlers prevent the event
            if (!reason.event.isDefaultPrevented()) {
                core.bus.trigger('rpc_error', reason.message, reason.event);
            }
        }, 0);
    });
    return promise;
};

export function jsonRpc(url, fct_name, params, settings) {
    settings = settings || {};
    return _genericJsonRpc(fct_name, params, settings, function(data) {
        return $.ajax(url, Object.assign({}, settings, {
            url: url,
            dataType: 'json',
            type: 'POST',
            data: JSON.stringify(data, time.date_to_utc),
            contentType: 'application/json'
        }));
    });
}

// helper function to make a rpc with a function name hardcoded to 'call'
function rpc(url, params, settings) {
    return jsonRpc(url, 'call', params, settings);
}

function post (controller_url, data) {
    var postData = new FormData();

    $.each(data, function(i,val) {
        postData.append(i, val);
    });
    if (odoo.csrf_token) {
        postData.append('csrf_token', odoo.csrf_token);
    }

    return new Promise(function (resolve, reject) {
        $.ajax(controller_url, {
            data: postData,
            processData: false,
            contentType: false,
            type: 'POST'
        }).then(resolve).fail(reject);
    });
}


/**
 * Loads a template file according to the given xmlId.
 *
 * @param {string} [xmlId] - the template xmlId
 * @param {Object} [context]
 *        additionnal rpc context to be merged with the default one
 * @param {string} [tplRoute='/web/dataset/call_kw/']
 * @returns {Deferred} resolved with an object
 *          cssLibs: list of css files
 *          cssContents: list of style tag contents
 *          jsLibs: list of JS files
 *          jsContents: list of script tag contents
 */
var loadAsset = (function () {
    var cache = {};

    var load = function loadAsset(xmlId, context, tplRoute = '/web/dataset/call_kw/') {
        if (cache[xmlId]) {
            return cache[xmlId];
        }
        context = Object.assign({}, session.user_context, context);
        const params = {
            args: [xmlId, {
                debug: !!odoo.debug
            }],
            kwargs: {
                context: context,
            },
        };
        if (tplRoute === '/web/dataset/call_kw/') {
            Object.assign(params, {
                model: 'ir.ui.view',
                method: 'render_public_asset',
            });
        }
        cache[xmlId] = rpc(tplRoute, params).then(function (xml) {
            var $xml = $(xml);
            return {
                cssLibs: $xml.filter('link[href]:not([type="image/x-icon"])').map(function () {
                    return $(this).attr('href');
                }).get(),
                cssContents: $xml.filter('style').map(function () {
                    return markup($(this).html());
                }).get(),
                jsLibs: $xml.filter('script[src]').map(function () {
                    return $(this).attr('src');
                }).get(),
                jsContents: $xml.filter('script:not([src])').map(function () {
                    return markup($(this).html());
                }).get(),
            };
        }).guardedCatch(reason => {
            reason.event.preventDefault();
            throw `Unable to render the required templates for the assets to load: ${reason.message.message}`;
        });
        return cache[xmlId];
    };

    return load;
})();

Object.assign(ajax, {
    jsonRpc: jsonRpc,
    rpc: rpc,
    loadAsset: loadAsset,
    post: post,
});

export default ajax;
