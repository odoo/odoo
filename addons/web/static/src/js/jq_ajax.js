
        $.ajaxSetup({
            converters: {
                "json oe-jsonp": true,
                "json oe-json": true,
            }
        });


        // common preconditions checks
        $.ajaxPrefilter("oe-json oe-jsonp", function(options, originalOptions, jqXHR) {
            console.log('use', options.dataType);
            if (!$.isPlainObject(options.openerp)) {
                console.error(options.openerp);
                $.error('"openerp" option is required.');
            }
            
            if (_(options.openerp.server).endsWith('/')) {
                options.openerp.server = options.openerp.server.substr(0, options.openerp.server.length-1);
            }

            if (!$.isPlainObject(options.data)) {
                $.error('data must not be serialized');
            }
            options.processData = false;
        });


            
        $.ajaxPrefilter("oe-json", function(options, originalOptions, jqXHR) {
            options.data = JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: options.data,
                id: _.uniqueId('browser-client-')
            });

            return 'json';
        });


        $.ajaxPrefilter("oe-jsonp", function(options, originalOptions, jqXHR) {
            
            var data = null;
            if (options.data) {
                data = $.param({r:JSON.stringify(options.data)});
            }


                var max_url_length = options.max_url_length || 1000,
                    absolute_url, full_url;
                 
                var r_has_protocol = /^https?:\/\//,
                    r_absolute_internal = /^\/[^\/]/;   // starts with / (but not //)

                
                if (r_has_protocol.test(options.url)) {
                    if (!_(options.url).startsWith(options.openerp.server + '/')) {
                        $.error('can only contact openerp.server');
                    }
                    absolute_url = options.url;
                } else if (r_absolute_internal.test(options.url)) {
                    absolute_url = options.openerp.server + options.url;
                } else {    // relative url
                    var parts = document.location.pathname.split('/');
                    parts.pop();
                    parts.push(options.url);
                    absolute_url = options.openerp.server + parts.join('/');
                }
                

                /// now, made the same url changes that jQuery will do...
	            var rquery = /\?/,
	                rts = /([?&])_=[^&]*/;

                full_url = absolute_url;
                if (data) {
                    full_url += (rquery.test(full_url) ? "&" : "?") + data;
                }

                // Add anti-cache in url if needed
                if (!options.cache) {
                    var ts = $.now(),
                        // try replacing _= if it is there
                        ret = full_url.replace(rts, "$1_=" + ts);

                    // if nothing was replaced, add timestamp to the end
                    full_url = ret + ((ret === full_url) ? (rquery.test(full_url) ? "&" : "?") + "_=" + ts : "");
                }

                console.log('absolute_url', absolute_url);
                console.log('full_url', full_url);
                
                options.url = absolute_url;

                if (full_url.length < max_url_length) {
                    options.type = "GET";
                    options.data = data;
                    return "jsonp";  // classic jsonp query...
                }
        });


        $.ajaxTransport("oe-jsonp", function(options, originalOptions, jqXHR) {

            console.log('real oe-jsonp', options);
                var $iframe = null;
                var $form = $('<form>')
                                .attr('method', 'POST')
                                .attr('enctype', "multipart/form-data")
                                .attr('action', options.openerp.server + "/web/jsonp/post")
                                .hide()
                                .appendTo($('body'))
                                ;

                console.log($form);
                
                function cleanUp() {
                    if ($iframe) {
                        $iframe.unbind("load").attr("src", "javascript:false;").remove();
                    }
                    $form.remove();
                }
                
                return {
                    
                    send: function(headers, completeCallback) {
                
                        var ifid = _.uniqueId('oe_jsonp_iframe_');
                        var request_id = _.uniqueId('browser-client-');
                        var oe_callback = _.uniqueId('oe_callback_');

                        window[oe_callback] = function(result) {
                            completeCallback(200, 'success', {json: result});
                        };


                        $iframe = $(_("<iframe src='javascript:false;' name='%s' id='%s' style='display:block'></iframe>").sprintf(ifid, ifid));


                        // the first bind is fired up when the iframe is added to the DOM
                        $iframe.bind('load', function() {
                            //console.log('bind1', this);
                            // the second bind is fired up when the result of the form submission is received
                            $iframe.unbind('load').bind('load', function() {
                                //console.log('bind2', this);
                                
                                // we cannot access the content of remote iframe.
                                // but we don't care, we try to get the result in any cases

                                $.ajax({
                                    type: "GET",
                                    url: options.url,
                                    dataType: 'jsonp', 
                                    jsonp: false,   // do not append callback=? argument on query string
                                    jsonpCallback: oe_callback,
                                    data: {
                                        sid: options.openerp.session_id,
                                        rid: request_id,
                                    },
                                }).always(function() {
                                    cleanUp();
                                });

                            });


                            // now that the iframe can receive data, we fill and submit the form
                            var params = JSON.stringify(options.data);

                            $form
                                .append($('<input type="hidden" name="session_id" />').attr('value', options.openerp.session_id))
                                .append($('<input type="hidden" name="request_id" />').attr('value', request_id))
                                .append($('<input type="hidden" name="params" />').attr('value', params))
                                .append($('<input type="hidden" name="callback" />').attr('value', oe_callback))
                                .submit()
                                ;

                        });
                        
                        $form.attr('target', ifid)  // set the iframe as target of the form
                             .after($iframe);       // append the iframe to the DOM (will trigger the first load)
                             
                    },
                    abort: function() {
                        cleanUp();
                    },
                };
        
        });
        

