openerp.web.sessionless = function(openerp) {
    var QWeb = new QWeb2.Engine();
    openerp.web.Sessionless = openerp.web.SessionAware.extend({
        rpc: function(url, params, success_callback, error_callback) {
            var self = this;
            // Call using the rpc_mode
            var deferred = $.Deferred();
            this.rpc_ajax(url, {
                jsonrpc: "2.0",
                method: "call",
                params: params,
                id:null
            }).then(function () {deferred.resolve.apply(deferred, arguments);},
            function(error) {deferred.reject(error, $.Event());});
            return deferred.fail(function() {
                deferred.fail(function(error, event) {
                    if (!event.isDefaultPrevented()) {
                        self.on_rpc_error(error, event);
                    }
                });
            }).then(success_callback, error_callback).promise();
        },
        /**
         * Raw JSON-RPC call
         *
         * @returns {jQuery.Deferred} ajax-webd deferred object
         */
        rpc_ajax: function(url, payload) {
            var self = this;
            this.on_rpc_request();
            // url can be an $.ajax option object
            if (_.isString(url)) {
                url = {
                    url: url
                }
            }
            var ajax = _.extend({
                type: "POST",
                url: url,
                dataType: 'json',
                contentType: 'application/json',
                data: JSON.stringify(payload),
                processData: false
            }, url);
            var deferred = $.Deferred();
            $.ajax(ajax).done(function(response, textStatus, jqXHR) {
                self.on_rpc_response();
                if (!response.error) {
                    deferred.resolve(response["result"], textStatus, jqXHR);
                    return;
                }
                if (response.error.data.type !== "session_invalid") {
                    deferred.reject(response.error);
                    return;
                }
                
            }).fail(function(jqXHR, textStatus, errorThrown) {
                self.on_rpc_response();
                var error = {
                    code: -32098,
                    message: "XmlHttpRequestError " + errorThrown,
                    data: {type: "xhr"+textStatus, debug: jqXHR.responseText, objects: [jqXHR, errorThrown] }
                };
                deferred.reject(error);
            });
            return deferred.promise();
        },
        on_rpc_request: function() {
        },
        on_rpc_response: function() {
        },
        on_rpc_error: function(error) {
        },    
    });
}
