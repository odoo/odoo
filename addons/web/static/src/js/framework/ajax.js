odoo.define('web.ajax', function (require) {
"use strict";

var core = require('web.core');
var utils = require('web.utils');
var time = require('web.time');

function genericJsonRpc (fct_name, params, fct) {
    var data = {
        jsonrpc: "2.0",
        method: fct_name,
        params: params,
        id: Math.floor(Math.random() * 1000 * 1000 * 1000)
    };
    var xhr = fct(data);
    var result = xhr.pipe(function(result) {
        core.bus.trigger('rpc:result', data, result);
        if (result.error !== undefined) {
            if (result.error.data.arguments[0] !== "bus.Bus not available in test mode") {
                console.error("Server application error", JSON.stringify(result.error));
            }
            return $.Deferred().reject("server", result.error);
        } else {
            return result.result;
        }
    }, function() {
        //console.error("JsonRPC communication error", _.toArray(arguments));
        var def = $.Deferred();
        return def.reject.apply(def, ["communication"].concat(_.toArray(arguments)));
    });
    // FIXME: jsonp?
    result.abort = function () { if (xhr.abort) xhr.abort(); };
    return result;
}

function jsonRpc(url, fct_name, params, settings) {
    return genericJsonRpc(fct_name, params, function(data) {
        return $.ajax(url, _.extend({}, settings, {
            url: url,
            dataType: 'json',
            type: 'POST',
            data: JSON.stringify(data, time.date_to_utc),
            contentType: 'application/json'
        }));
    });
}

function jsonpRpc(url, fct_name, params, settings) {
    settings = settings || {};
    return genericJsonRpc(fct_name, params, function(data) {
        var payload_str = JSON.stringify(data, time.date_to_utc);
        var payload_url = $.param({r:payload_str});
        var force2step = settings.force2step || false;
        delete settings.force2step;
        var session_id = settings.session_id || null;
        delete settings.session_id;
        if (payload_url.length < 2000 && ! force2step) {
            return $.ajax(url, _.extend({}, settings, {
                url: url,
                dataType: 'jsonp',
                jsonp: 'jsonp',
                type: 'GET',
                cache: false,
                data: {r: payload_str, session_id: session_id}
            }));
        } else {
            var args = {session_id: session_id, id: data.id};
            var ifid = _.uniqueId('oe_rpc_iframe');
            var html = "<iframe src='javascript:false;' name='" + ifid + "' id='" + ifid + "' style='display:none'></iframe>";
            var $iframe = $(html);
            var nurl = 'jsonp=1&' + $.param(args);
            nurl = url.indexOf("?") !== -1 ? url + "&" + nurl : url + "?" + nurl;
            var $form = $('<form>')
                        .attr('method', 'POST')
                        .attr('target', ifid)
                        .attr('enctype', "multipart/form-data")
                        .attr('action', nurl)
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
                    $.ajax({
                        url: url,
                        dataType: 'jsonp',
                        jsonp: 'jsonp',
                        type: 'GET',
                        cache: false,
                        data: {session_id: session_id, id: data.id}
                    }).always(function() {
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
            if (settings.timeout) {
                realSetTimeout(function() {
                    deferred.reject({});
                }, settings.timeout);
            }
            return deferred;
        }
    });
}

// helper function to make a rpc with a function name hardcoded to 'call'
function rpc(url, params, settings) {
    return jsonRpc(url, 'call', params, settings);
}

// helper
function realSetTimeout (fct, millis) {
    var finished = new Date().getTime() + millis;
    var wait = function() {
        var current = new Date().getTime();
        if (current < finished) {
            setTimeout(wait, finished - current);
        } else {
            fct();
        }
    };
    setTimeout(wait, millis);
}

function loadCSS(url) {
    if (!$('link[href="' + url + '"]').length) {
        $('head').append($('<link>', {
            'href': url,
            'rel': 'stylesheet',
            'type': 'text/css'
        }));
    }
}

function loadJS(url) {
    var def = $.Deferred();
    if ($('script[src="' + url + '"]').length) {
        def.resolve();
    } else {
        var script = document.createElement('script');
        script.type = 'text/javascript';
        script.src = url;
        script.onload = script.onreadystatechange = function() {
            if ((script.readyState && script.readyState != "loaded" && script.readyState != "complete") || script.onload_done) {
                return;
            }
            script.onload_done = true;
            def.resolve(url);
        };
        script.onerror = function () {
            console.error("Error loading file", script.src);
            def.reject(url);
        };
        var head = document.head || document.getElementsByTagName('head')[0];
        head.appendChild(script);
    }
    return def;
}

/**
 * Cooperative file download implementation, for ajaxy APIs.
 *
 * Requires that the server side implements an httprequest correctly
 * setting the `fileToken` cookie to the value provided as the `token`
 * parameter. The cookie *must* be set on the `/` path and *must not* be
 * `httpOnly`.
 *
 * It would probably also be a good idea for the response to use a
 * `Content-Disposition: attachment` header, especially if the MIME is a
 * "known" type (e.g. text/plain, or for some browsers application/json
 *
 * @param {Object} options
 * @param {String} [options.url] used to dynamically create a form
 * @param {Object} [options.data] data to add to the form submission. If can be used without a form, in which case a form is created from scratch. Otherwise, added to form data
 * @param {HTMLFormElement} [options.form] the form to submit in order to fetch the file
 * @param {Function} [options.success] callback in case of download success
 * @param {Function} [options.error] callback in case of request error, provided with the error body
 * @param {Function} [options.complete] called after both ``success`` and ``error` callbacks have executed
 */
function get_file(options) {
    // need to detect when the file is done downloading (not used
    // yet, but we'll need it to fix the UI e.g. with a throbber
    // while dump is being generated), iframe load event only fires
    // when the iframe content loads, so we need to go smarter:
    // http://geekswithblogs.net/GruffCode/archive/2010/10/28/detecting-the-file-download-dialog-in-the-browser.aspx
    var timer, token = new Date().getTime(),
        cookie_name = 'fileToken', cookie_length = cookie_name.length,
        CHECK_INTERVAL = 1000, id = _.uniqueId('get_file_frame'),
        remove_form = false;


    // iOS devices doesn't allow iframe use the way we do it,
    // opening a new window seems the best way to workaround
    if (navigator.userAgent.match(/(iPod|iPhone|iPad)/)) {
        var params = _.extend({}, options.data || {}, {token: token});
        var url = options.session.url(options.url, params);
        if (options.complete) { options.complete(); }

        return window.open(url);
    }

    var $form, $form_data = $('<div>');

    var complete = function () {
        if (options.complete) { options.complete(); }
        clearTimeout(timer);
        $form_data.remove();
        $target.remove();
        if (remove_form && $form) { $form.remove(); }
    };
    var $target = $('<iframe style="display: none;">')
        .attr({id: id, name: id})
        .appendTo(document.body)
        .load(function () {
            try {
                if (options.error) {
                    var body = this.contentDocument.body;
                    var nodes = body.children.length === 0 ? body.childNodes : body.children;
                    var node = nodes[1] || nodes[0];
                    options.error(JSON.parse(node.textContent));
                }
            } finally {
                complete();
            }
        });

    if (options.form) {
        $form = $(options.form);
    } else {
        remove_form = true;
        $form = $('<form>', {
            action: options.url,
            method: 'POST'
        }).appendTo(document.body);
    }
    if (core.csrf_token) {
        $('<input type="hidden" name="csrf_token">')
                .val(core.csrf_token)
                .appendTo($form_data);
    }

    var hparams = _.extend({}, options.data || {}, {token: token});
    _.each(hparams, function (value, key) {
            var $input = $form.find('[name=' + key +']');
            if (!$input.length) {
                $input = $('<input type="hidden" name="' + key + '">')
                    .appendTo($form_data);
            }
            $input.val(value);
        });

    $form
        .append($form_data)
        .attr('target', id)
        .get(0).submit();

    var waitLoop = function () {
        var cookies = document.cookie.split(';');
        // setup next check
        timer = setTimeout(waitLoop, CHECK_INTERVAL);
        for (var i=0; i<cookies.length; ++i) {
            var cookie = cookies[i].replace(/^\s*/, '');
            if (!cookie.indexOf(cookie_name === 0)) { continue; }
            var cookie_val = cookie.substring(cookie_length + 1);
            if (parseInt(cookie_val, 10) !== token) { continue; }

            // clear cookie
            document.cookie = _.str.sprintf("%s=;expires=%s;path=/",
                cookie_name, new Date().toGMTString());
            if (options.success) { options.success(); }
            complete();
            return;
        }
    };
    timer = setTimeout(waitLoop, CHECK_INTERVAL);
};

function post (controller_url, data) {

    var progressHandler = function (deferred) {
        return function (state) {
            if(state.lengthComputable) {
                deferred.notify({
                    h_loaded: utils.human_size(state.loaded),
                    h_total : utils.human_size(state.total),
                    loaded  : state.loaded,
                    total   : state.total,
                    pcent   : Math.round((state.loaded/state.total)*100)
                });
            }
        };
    };

    var Def = $.Deferred();
    var postData = new FormData();

    $.each(data, function(i,val) {
        postData.append(i, val);
    });
    if (core.csrf_token) {
        postData.append('csrf_token', core.csrf_token);
    }

    var xhr = new XMLHttpRequest();
    if(xhr.upload) xhr.upload.addEventListener('progress', progressHandler(Def), false);

    var ajaxDef = $.ajax(controller_url, {
        xhr: function() {return xhr;},
        data:           postData,
        processData:    false,
        contentType:    false,
        type:           'POST'
    }).then(function (data) {Def.resolve(data);})
    .fail(function (data) {Def.reject(data);});

    return Def;
}

var loadXML = (function () {
    var loading = false;
    var urls = [];
    var qwebs = [];
    var templates_def = $.Deferred();

    var load = function loadXML(url, qweb) {
        if (url) {
            urls.push(url);
            qwebs.push(qweb);
        }

        if (!loading && urls.length) {
            if (templates_def.state() === "resolved") {
                templates_def = $.Deferred();
            }

            loading = true;
            qwebs.shift().add_template(urls.shift(), function () {
                loading = false;
                if (!urls.length) {
                    templates_def.resolve();
                }
                load(null);
            });
        }

        return templates_def;
    };

    return load;
})();

return {
    jsonRpc: jsonRpc,
    jsonpRpc: jsonpRpc,
    rpc: rpc,
    loadCSS: loadCSS,
    loadJS: loadJS,
    loadXML: loadXML,
    get_file: get_file,
    post: post,
};

});
