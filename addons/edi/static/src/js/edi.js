/*---------------------------------------------------------
 * OpenERP Web_edi
 *---------------------------------------------------------*/
//
openerp.edi = {}

openerp.edi.EdiView = Class.extend({
    element_id: "oe",
    template: "EdiView",
    init: function(element_id){
        var self = this;
        this.element_id = element_id;
        this.$element = $('#' + element_id);
        QWeb.add_template("/web_edi/static/src/xml/edi.xml");
        
    },
    start: function() {
	},
    view_edi: function(token, db) {
        var params = {};
        if(token) params['token'] = token;
        if(db) params['db'] = db;
        this.rpc('/edi/get_edi/get_edi_document', params, this.on_response);
    },
    on_response: function(value){
        this.element_id = "oe";
        this.template = "EdiView";
        this.$element = $('#' + this.element_id);
        this.$element.html(QWeb.render(this.template, this));
        this.registry = openerp.edi.forms;
        var model = value.model
        var edi_document = value.document

        // EDI Center Frame
        key_edi_center = 'edi_center'
        edi_center = this.registry.get_object(key_edi_center + '_' + model)
        if (edi_center == undefined){
            edi_center = this.registry.get_object(key_edi_center)   
        }
        $edi_center_frame = this.$element.find('div.oe_edi_center');
        var center_frame = new (edi_center)($edi_center_frame, value);
        center_frame.render();

        // EDI Right TOP Frame
        key_edi_right_top = 'edi_right_top'
        edi_right_top = this.registry.get_object(key_edi_right_top + '_' + model)
        if (edi_right_top == undefined){
            edi_right_top = this.registry.get_object(key_edi_right_top)   
        }
        $edi_right_top_frame = this.$element.find('div.oe_edi_right_top');
        var right_top_frame = new (edi_right_top)($edi_right_top_frame, value);
        right_top_frame.render();
        
        //EDI Right Bottom Frame
        key_edi_right_bottom = 'edi_right_bottom'
        edi_right_bottom = this.registry.get_object(key_edi_right_bottom + '_' + model)
        if (edi_right_bottom == undefined){
            edi_right_bottom = this.registry.get_object(key_edi_right_bottom)   
        }
        $edi_right_bottom_frame = this.$element.find('div.oe_edi_right_bottom');
        var right_bottom_frame = new (edi_right_bottom)($edi_right_bottom_frame, value);
        right_bottom_frame.render();
    },
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
     * @returns {jQuery.Deferred} ajax-based deferred object
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
                if (response.error) {
                    if (response.error.data.type == "session_invalid") {
                        self.uid = false;
                        self.on_session_invalid(function() {
                            self.rpc(url, payload.params,
                                function() {deferred.resolve.apply(deferred, arguments);},
                                function(error, event) {event.preventDefault();
                                    deferred.reject.apply(deferred, arguments);});
                        });
                    } else {
                        deferred.reject(response.error);
                    }
                } else {
                    deferred.resolve(response["result"], textStatus, jqXHR);
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



openerp.edi.EdiViewCenter = Class.extend({
    init: function(element, edi){
        var self = this;
        this.edi_document = edi.document;
        this.$element = element;
        QWeb.add_template("/web_edi/static/src/xml/edi.xml");
    },
    start: function() {
	},
    render: function(){
        template = "EdiViewCenter";
        this.$element.append($(QWeb.render(template, {'view': this})))
    }
});

openerp.edi.EdiViewRightTop = Class.extend({
    init: function(element, edi){
        var self = this;
        this.edi_document = edi.document;
        this.$element = element;
        QWeb.add_template("/web_edi/static/src/xml/edi.xml");
        this.$_element = $('<div>')
            .appendTo(document.body)
            .delegate('button.oe_edi_button_import', 'click', {'edi': edi} , this.do_import)
    },
    start: function() {
	},
    render: function(){
        template = "EdiViewRightTop";
        if (this.$current) {
            this.$current.remove();
        }
        this.$current = this.$_element.clone(true);
        this.$current.empty().append(QWeb.render(template, this));
        this.$element.append(this.$current);
        
    },
    do_import: function(e){
        $element = $(e.view.document.body)
        token = e.data.edi.token
        db = e.data.edi.db
        var current_url = $(location).attr('href')
        var pathName = current_url.substring(0, current_url.lastIndexOf('/') +1);

        if ($element.find('#oe_edi_rd_import_openerp').attr('checked') == true)
        {
            // import EDI
            server_url = $element.find('#oe_edi_txt_server_url').val()
            edi_url = pathName + 'get_edi?db=' + db + '&token=' + token
            edi_url = encodeURIComponent(edi_url)
            window.location = 'http://' + server_url + '/base/static/src/base.html?import_edi&edi_url=' + edi_url
        }
        if ($element.find('#oe_edi_rd_import_saas_account').attr('checked') == true)
        {
            // create SAAS Account
        }
        if ($element.find('#oe_edi_rd_import_other').attr('checked') == true)
        {
            // GET EDI document
            edi_url = pathName + 'get_edi?db=' + db + '&token=' + token
            window.location = edi_url
        }
    }
});

openerp.edi.EdiViewRightBottom = Class.extend({
    init: function(element, edi){
        var self = this;
        this.edi_document = edi.document;
        this.$element = element;
        QWeb.add_template("/web_edi/static/src/xml/edi.xml");
    },
    start: function() {
	},
    render: function(){
        template = "EdiViewRightBottom";
        this.$element.append($(QWeb.render(template, this)))
    }
});

openerp.edi.Registry = Class.extend({
    init: function (mapping) {
        this.map = mapping || {};
    },
    
    get_object: function (key) {
        var path_string = this.map[key];
        if (path_string === undefined) {
            // key is not Found
            return undefined;
        }

        var object_match = openerp;
        var path = path_string.split('.');
        // ignore first section
        for(var i=1; i<path.length; ++i) {
            object_match = object_match[path[i]];

            if (object_match === undefined) {
                // Object is not found
                return undefined;
            }
        }
        return object_match;
    },
    
    add: function (key, object_path) {
        this.map[key] = object_path;
        return this;
    },
    
    clone: function (mapping) {
        return new openerp.edi.Registry(
            _.extend({}, this.map, mapping || {}));
    }
});


openerp.edi.forms = new openerp.edi.Registry({
    'edi_center' : 'openerp.edi.EdiViewCenter',
    'edi_right_top' : 'openerp.edi.EdiViewRightTop',
    'edi_right_bottom' : 'openerp.edi.EdiViewRightBottom',
});

openerp.web_edi = function(openerp) {
openerp.web_edi.EdiImport = openerp.base.Controller.extend({
	init: function() {
		var self = this;
	    this._super(null);
	},
	
	start: function() {
	},
	
	
	import_edi: function(edi_url) {
		var self = this;
		var params = {};
        
		if(edi_url) params['edi_url'] = decodeURIComponent(edi_url);
		
		if(!this.session) {
	    	this.session = new openerp.base.Session("oe_errors");
	    	this.session.start();
	    	this.session.session_restore();
	    }
		
		this.rpc('/edi/import_edi', params, function(response){
            if (response.length) {
                $('<div>Import successful, click Ok to see the new document</div>').dialog({
                    modal: true,
                    title: 'Successful',
                    buttons: {
                        Ok: function() {
                            $(this).dialog("close");
                            var action = {
		                		"res_model": response[0][0],
		                		"res_id": parseInt(response[0][1], 10),
		                        "views":[[false,"form"]],
		                        "type":"ir.actions.act_window",
		                        "view_type":"form",
		                        "view_mode":"form"
		                    }
				            action.flags = {
		                		search_view: false,
		                        sidebar : false,
		                        views_switcher : false,
		                        action_buttons : false,
		                        pager: false
	                        }
				            var action_manager = new openerp.base.ActionManager(self.session, 'oe_app');
				
				            action_manager.start();
				            action_manager.do_action(action);
                           }
                     }
                    
                });
            }
            else{
                $(QWeb.render("DialogWarning", "Sorry, Import is not successful.")).dialog({
                    modal: true,
                    buttons: {
                        Ok: function() {
                            $(this).dialog("close");
                        }
                    }
                });
            }
			
		});
	}
});
var parameters = jQuery.deparam(jQuery.param.querystring());


if('import_edi' in parameters) {
	var import_edi = new openerp.web_edi.EdiImport();
	import_edi.import_edi(parameters.edi_url);
}
}
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
