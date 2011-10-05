
openerp.web.edi_view = function(openerp) {
    openerp.web.edi_views = new openerp.web.Registry();
    var QWeb = new QWeb2.Engine();
    // EDI View Engine
    openerp.web.EdiView = openerp.web.Sessionless.extend({
        init: function(element_id){
            var self = this;
            this.template = "EdiView";
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
            this.rpc('/web/get_edi/get_edi_document', params, this.on_response);
        },
        
        on_response: function(value){
            var self = this;
            this.template = "EdiView";
            this.element_id = "oe";
            self.$element = $('#' + this.element_id);
            self.$element.html(QWeb.render(self.template, this));
            
            var edi_document = value.document;

            var render = function(key, element_id, response){
                var registry = openerp.web.edi_views;
                model = response.model
                // get namespace of view of particular model from registry
                try {
                    edi_view = registry.get_object(key + '_' + model);
                }catch (e) {
                    edi_view = undefined;
                }
                // if not found, take default namespace of view
                if (edi_view == undefined){
                    edi_view = registry.get_object(key)   
                }
                $edi_frame = self.$element.find(element_id);

                // create instance of QWeb of view namespace
                edi_qweb = new (edi_view)($edi_frame, response)
                edi_qweb.render();
            };
    
            // EDI Center Frame
            render('view_center', 'div.oe_edi_center', value)
    
            // EDI Right TOP Frame
            render('view_right_top', 'div.oe_edi_right_top', value)
            
            //EDI Right Bottom Frame
            render('view_right_bottom', 'div.oe_edi_right_bottom', value)
            
        },
    
    });

openerp.web.edi_views.add('view_center' , 'openerp.web.EdiViewCenter');
openerp.web.EdiViewCenter = openerp.web.Class.extend({
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

openerp.web.edi_views.add('view_right_top' , 'openerp.web.EdiViewRightTop');
openerp.web.EdiViewRightTop = openerp.web.Class.extend({
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

        if ($element.find('#oe_edi_rd_import_openerp').attr('checked') == 'checked')
        {
            // import EDI
            server_url = $element.find('#oe_edi_txt_server_url').val()
            edi_url = pathName + 'get_edi?db=' + db + '&token=' + token
            edi_url = encodeURIComponent(edi_url)
            window.location = 'http://' + server_url + '/web/import_edi?edi_url=' + edi_url
        }
        if ($element.find('#oe_edi_rd_import_saas_account').attr('checked') == 'checked')
        {
            // create SAAS Account
        }
        if ($element.find('#oe_edi_rd_import_other').attr('checked') == 'checked')
        {
            // GET EDI document
            edi_url = pathName + 'get_edi?db=' + db + '&token=' + token
            window.location = edi_url
        }
    }
});

openerp.web.edi_views.add('view_right_bottom' , 'openerp.web.EdiViewRightBottom');
openerp.web.EdiViewRightBottom = openerp.web.Class.extend({
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
}
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
