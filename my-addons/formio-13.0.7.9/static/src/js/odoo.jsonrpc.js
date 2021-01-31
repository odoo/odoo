(function($, undefined) {
    $.extend({
        jsonRpc: {
            genericJsonRpc: function(fct_name, params, settings, fct) {
                // Copied from addons/web/static/src/js/core/ajax.js
                // with slightly modifications.
                var data = {
                    jsonrpc: "2.0",
                    method: fct_name,
                    params: params,
                    id: Math.floor(Math.random() * 1000 * 1000 * 1000)
                };
                var xhr = fct(data);
                var result = xhr.pipe(function(result) {
                    if (result.error !== undefined) {
                        console.error(
                            "Server application error\n",
                            "Error code:", result.error.code, "\n",
                            "Error message:", result.error.message, "\n",
                            "Error data message:\n", result.error.data.message, "\n",
                            "Error data debug:\n", result.error.data.debug
                        );
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
                
                var p = result.then(function (result) {
                    return result;
                }, function (type, error, textStatus, errorThrown) {
                    if (type === "server") {
                        return $.Deferred().reject(error, $.Event());
                    } else {
                        var nerror = {
                            code: -32098,
                            message: "XmlHttpRequestError " + errorThrown,
                            data: {
                                type: "xhr"+textStatus,
                                debug: error.responseText,
                                objects: [error, errorThrown]
                            },
                        };
                        return $.Deferred().reject(nerror, $.Event());
                    }
                });
                return p.fail(function () { // Allow deferred user to disable rpc_error call in fail
                    p.fail(function (error, event) {
                        console.log(error);
                    });
                });
            },
            
            request: function(url, fct_name, params, settings) {
                // original function is jsonRpc
                settings = settings || {};
                return this.genericJsonRpc(fct_name, params, settings, function(data) {
                    return $.ajax(url, $.extend({}, settings, {
                        url: url,
                        dataType: 'json',
                        type: 'POST',
                        data: JSON.stringify(data),
                        contentType: 'application/json'
                    }));
                });
            }
        }
    });
})(jQuery);
