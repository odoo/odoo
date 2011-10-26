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
        this.content = "";
        this.sidebar = "";
    },
    start: function() {
        this._super();
        var param = {"db": this.db, "token": this.token};
        console.log("load",param);
        this.rpc('/edi/get_edi_document', param, this.on_document_loaded);
    },
    on_document_loaded: function(docs){
        this.doc = docs[0];
        console.log("docs",this.doc);
        var template_content = "Edi." + this.doc.__model + ".content";
        var template_sidebar = "Edi." + this.doc.__model + ".sidebar";
        var param = {"widget":this, "doc":this.doc};
        if (openerp.web.qweb.templates[template_sidebar]) {
            this.sidebar = openerp.web.qweb.render(template_sidebar, param);
        }
        console.log("sidebar",this.sidebar);
        if (openerp.web.qweb.templates[template_content]) {
            this.content = openerp.web.qweb.render(template_content, param);
        }
        console.log("sidebar",this.sidebar);
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
            window.location = 'http://' + server_url + '/edi/import_url?url=' + encodeURIComponent(url_download);
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
        this.session.on_session_valid.add_last(this.do_import);
        // TODO if session invalid ask for login
        this.session.start();
    },
    do_import: function() {
        this.rpc('/edi/import_edi_url', {"url": this.url}, this.on_imported, this.on_imported_error);
    },
    on_imported: function(response) {
        console.log("responde from import",response);
        // response is null when exception
        // model: response[0][0],
        // id: parseInt(response[0][1], 10),
        window.location = "/web/webclient/home?debug=1#model=MODEL&id=ID";
    },
    on_imported_error: function(response){
        var self = this;
        $(openerp.web.qweb.render("DialogWarning", "Sorry, Import is not successful.")).dialog({
            modal: true,
            buttons: {
                Ok: function() { $(this).dialog("close"); }
            }
        });
    }
});

}
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
