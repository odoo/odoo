openerp.edi = function(openerp) {
openerp.edi = {}

openerp.edi.EdiView = openerp.web.Widget.extend({
    init: function(parent, db, token) {
        this._super();
        this.db = db;
        this.token = token;
        this.session = openerp.session;
        this.template = "EdiEmpty";
        this.content = "";
        this.sidebar = "";
    },
    start: function() {
        this._super();
        var self = this;
        var param = {"db": self.db, "token": self.token};
        return self.rpc('/edi/get_edi_document', param, this.on_document_loaded, this.on_document_failed);
    },
    on_document_loaded: function(docs){
        this.doc = docs[0];
        var template_content = "Edi." + this.doc.__model + ".content";
        var template_sidebar = "Edi." + this.doc.__model + ".sidebar";
        var param = {"widget":this, "doc":this.doc};
        if (openerp.web.qweb.templates[template_sidebar]) {
            this.sidebar = openerp.web.qweb.render(template_sidebar, param);
        }
        if (openerp.web.qweb.templates[template_content]) {
            this.content = openerp.web.qweb.render(template_content, param);
        }
        this.$element.html(openerp.web.qweb.render("EdiView", param));
        this.$element.find('button.oe_edi_action_print').bind('click', this.do_print);
        this.$element.find('button#oe_edi_import_existing').bind('click', this.do_import_existing);
        this.$element.find('button#oe_edi_import_create').bind('click', this.do_import_create);
        this.$element.find('button#oe_edi_download').bind('click', this.do_download);
        this.$element.find('.oe_edi_import_choice, .oe_edi_import_choice_label').bind('click', this.toggle_choice('import'));
        this.$element.find('.oe_edi_pay_choice, .oe_edi_pay_choice_label').bind('click', this.toggle_choice('pay'));
        this.$element.find('#oe_edi_download_show_code').bind('click', this.show_code);
    },
    on_document_failed: function(response) {
        var self = this;
        var params = {
                error: response,
                //TODO: should this be _t() wrapped?
                message: "Sorry, this document cannot be located. Perhaps the link you are using has expired?"
        }
        $(openerp.web.qweb.render("DialogWarning", params)).dialog({
            title: "Document not found",
            modal: true,
        });
    },
    show_code: function($event) {
        $('#oe_edi_download_code').toggle();
    },
    get_download_url: function() {
        var l = window.location;
        var url_prefix = l.protocol + '//' + l.host;
        return url_prefix +'/edi/download?db=' + this.db + '&token=' + this.token;
    },
    get_paypal_url: function(document_type, ref_field) {
        var comp_name = encodeURIComponent(this.doc.company_id[1]);
        var doc_ref = encodeURIComponent(this.doc[ref_field]);
        var paypal_account = encodeURIComponent(this.doc.company_address.paypal_account);
        var amount = encodeURIComponent(this.doc.amount_total);
        var cur_code = encodeURIComponent(this.doc.currency.code);
        var paypal_url = "https://www.paypal.com/cgi-bin/webscr?cmd=_xclick" +
                     "&business=" + paypal_account +
                     "&item_name=" + document_type + "%20" + comp_name + "%20" + doc_ref +
                     "&invoice=" + doc_ref + 
                     "&amount=" + amount +
                     "&currency_code=" + cur_code +
                     "&button_subtype=services&amp;no_note=1&amp;bn=OpenERP_PayNow_" + cur_code;
        return paypal_url;
    },
    toggle_choice: function(mode) {
        return function($e) {
            $('.oe_edi_nested_block_'+mode).hide();
            $('.'+$e.target.id+'_nested').show();
            return true;
        }
    },
    do_print: function(e){
        var l = window.location;
        window.location = l.protocol + '//' + l.host + "/edi/download_attachment?db=" + this.db + "&token=" + this.token;
    },
    do_import_existing: function(e) {
        var url_download = this.get_download_url();
        var $edi_text_server_input = this.$element.find('#oe_edi_txt_server_url');
        var server_url = $edi_text_server_input.val();
        $edi_text_server_input.removeClass('invalid');
        if (!server_url) {
            $edi_text_server_input.addClass('invalid');
            return false;
        }
        var protocol = "http://";
        if (server_url.toLowerCase().lastIndexOf('http', 0) == 0 ) {
            protocol = '';
        }
        window.location = protocol + server_url + '/edi/import_url?url=' + encodeURIComponent(url_download);
    },
    do_import_create: function(e){
        var url_download = this.get_download_url();
        window.location = "https://cc.my.openerp.com/odms/create_edi?url=" + encodeURIComponent(url_download);
    },
    do_download: function(e){
        window.location = this.get_download_url();
    }
});

openerp.edi.edi_view = function (db, token) {
    openerp.session.session_bind().then(function () {
        new openerp.edi.EdiView(null,db,token).appendTo($("body").addClass('openerp'));
    });
}

openerp.edi.EdiImport = openerp.web.Widget.extend({
    init: function(parent,url) {
        this._super();
        this.url = url;
    },
    start: function() {
        if (!this.session.session_is_valid()) {
            this.show_login();
            this.session.on_session_valid.add({
                callback: this.proxy('show_import'),
                unique: true,
            });
        } else {
            this.show_import();
        }
    },

    show_import: function() {
        this.destroy_content();
        this.do_import();
    },

    show_login: function() {
        this.destroy_content();
        this.login = new openerp.web.Login(this);
        this.login.appendTo(this.$element);
    },

    destroy_content: function() {
        _.each(_.clone(this.getChildren()), function(el) {
            el.destroy();
        });
        this.$element.children().remove();
    },

    do_import: function() {
        this.rpc('/edi/import_edi_url', {url: this.url}, this.on_imported, this.on_imported_error);
    },
    on_imported: function(response) {
        if ('action' in response) {
            this.rpc("/web/session/save_session_action", {the_action: response.action}, function(key) {
                window.location = "/#sa="+encodeURIComponent(key);
            });
        }
        else {
            $('<div>').dialog({
                modal: true,
                title: 'Import Successful!',
                buttons: {
                    Ok: function() {
                        $(this).dialog("close");
                        window.location = "/";
                    }
                }
            }).html('The document has been successfully imported!');
        }
    },
    on_imported_error: function(response){
        var self = this;
        var msg = "Sorry, the document could not be imported.";
        if (response.data.fault_code) {
            msg += "\n Reason:" + response.data.fault_code;
        }
        var params = {error: response, message: msg};
        $(openerp.web.qweb.render("CrashManagerWarning", params)).dialog({
            title: "Document Import Notification",
            modal: true,
            buttons: {
                Ok: function() { $(this).dialog("close"); }
            }
        });
    }
});

openerp.edi.edi_import = function (url) {
    openerp.session.session_bind().then(function () {
        new openerp.edi.EdiImport(null,url).appendTo($("body").addClass('openerp'));
    });
}

};
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
