openerp.edi = function(openerp) {
openerp.web.qweb.add_template("/edi/static/src/xml/edi.xml");
openerp.web.qweb.add_template("/edi/static/src/xml/edi_account.xml");
openerp.web.qweb.add_template("/edi/static/src/xml/edi_sale_purchase.xml");
openerp.edi = {}

openerp.edi.EdiView = openerp.web.Widget.extend({
    init: function(parent, db, token) {
        this._super();
        this.db = db;
        this.token = token;
        this.session = new openerp.web.Session();
        this.template = "EdiEmpty";
    },
    start: function() {
        this._super();
        var param = {"db": this.db, "token": this.token};
        console.log("load",param);
        this.rpc('/edi/get_edi_document', param, this.on_document_loaded);
    },
    on_document_loaded: function(docs){
        this.doc = docs[0];
        //console.log("docs",this.doc);
        var template = "Edi." + this.doc.__model;
        var param = {"widget":this, "doc":this.doc};
        this.center = openerp.web.qweb.render(template, param);
        //console.log(this.center);
        this.right = "";
        this.$element.html(openerp.web.qweb.render("EdiView", param));
        this.$element.find('button.oe_edi_action_print').bind('click', this.do_print);
        this.$element.find('button.oe_edi_import_button').bind('click', this.do_import);
    },
    do_print: function(e){
        var l = window.location;
        window.location = l.protocol + '//' + l.host + "/edi/download_attachment?db=" + this.db + "&token=" + this.token;
    },
    do_import: function(e){
        var l = window.location;
        var url_prefix = l.protocol + '//' + l.host;
        var url_download = url_prefix +'/edi/download?db=' + this.db + '&token=' + this.token;

        if (this.$element.find('#oe_edi_import_openerp').attr('checked') == 'checked') {
            var server_url = this.$element.find('#oe_edi_txt_server_url').val()
            window.location = 'http://' + server_url + '/web/import_url?url=' + encodeURIComponent(url_download);
        } else if (this.$element.find('#oe_edi_import_saas').attr('checked') == 'checked') {
            window.location = "https://cc.my.openerp.com/odms/create_edi?url=" + encodeURIComponent(url_download);
        } else if (this.$element.find('#oe_edi_import_download').attr('checked') == 'checked') {
            window.location = url_download
        }
    }
});

openerp.edi.EdiImport = openerp.web.Widget.extend({
    init: function(parent,url) {
        this._super();
        this.url = url;
        this.session = new openerp.web.Session();
        this.template = "EdiEmpty";
    },
    start: function() {
    },
    import_edi: function(edi_url) {
        var self = this;
        this.params = {};
        if(edi_url)
            this.params['edi_url'] = decodeURIComponent(edi_url);
        if (!this.session.db){
            this.start();
            this.session.on_session_valid.add_last(self.do_import);
        } else{
            self.do_import();
        }
    },
    do_import: function() {
        this.rpc('/edi/import_edi_url', this.params, this.on_imported);
    },
    on_imported: function(response){
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
                    var action_manager = new openerp.web.ActionManager(self);
                    action_manager.appendTo($("#oe_app"));
                    action_manager.start();
                    action_manager.do_action(action);
                   }
                }
            });
        } else {
            $(QWeb.render("DialogWarning", "Sorry, Import is not successful.")).dialog({
                modal: true,
                buttons: {
                    Ok: function() {
                        $(this).dialog("close");
                    }
                }
            });
        }
    },
});

openerp.edi.EdiViewCenterInvoice = openerp.web.Class.extend({
    init: function(element, edi){
        this.$_element = $('<div>')
            .appendTo(document.body)
            .delegate('#oe_edi_invoice_button_pay', 'click', {'edi': edi} , this.do_pay)
    },
    do_pay: function(e){
        if ($element.find('#oe_edi_invoice_rd_pay_paypal').attr('checked') == 'checked') {
            alert('Pay Invoice using Paypal service');
        }
        if ($element.find('#oe_edi_invoice_rd_pay_google_checkout').attr('checked') == 'checked') {
            alert('Pay Invoice using Google Checkout');
        }
        if ($element.find('#oe_edi_invoice_rd_pay_bank').attr('checked') == 'checked') {
            alert('Pay Invoice using Bankwire Trasnfer')
        }
    }
});

}
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
