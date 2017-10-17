odoo.define('portal.share_document', function (require){
    "use strict";

var Widget = require("web.Widget");
var core = require('web.core');
var Dialog = require('web.Dialog');
var rpc =  require('web.rpc');
var qweb = core.qweb;
var _t = core._t;


var ShareDocument = Widget.extend({
    xmlDependencies: ['/portal/static/src/xml/portal_share_document.xml'],

    init: function(options) {
        this._super.apply(this, arguments);
        this.url = options.url;
        this.model = options.res_model;
        this.res_id = options.res_id;
        this.name = options.name;
        },

    start: function(){
        this._super.apply(this, arguments);
        var self = this;
        var dialog = new Dialog(this, {
            title: _t("Share Document"),
            $content: $(qweb.render('portal.portal_share_document',{
                url: this.url,
            })),
            buttons: [{text: _t('Send'), classes: 'btn-primary', close: false, click: function () {
                var data = this.$el.find('.partner_ids').select2('data')
                if (data.length) {
                    var partner_list = []
                    _.each(data, function(obj) {
                        partner_list.push(obj.id)
                    });
                    var that = this;
                    rpc.query({
                        route: '/portal/send_share_email',
                        params: {
                            partner_ids: partner_list ,
                            model: self.model,
                            res_id: self.res_id,
                            body: that.$el.find('textarea').val()
                        }
                    }).then(function (result) {
                        var ack = result ? '<div class="alert alert-success">Done!!!</div>' : '<div class="alert alert-danger">Fail!!!</div>';
                        var ack_message = new Dialog(self, {
                            title: _t("Message sent"),
                            $content: '<div>' + ack + '</div>'
                        });
                        dialog.close();
                        ack_message.open();
                    });
                } else {
                    if (!(this.$el.find('.alert-info').length)){
                        this.$el.prepend($('<div class="alert alert-info" role="alert"><strong> Please select the Recipients.</strong></div>'));
                    }
                }
            }}, {text: _t('Cancel'), close: true}],
        });
        dialog.open();
        this.set_partner_ids(dialog.$content);
        dialog.$content.find('textarea').val('<p> Dear, </p><p> A document '+ this.name +' has been shared with you </p><p><a href="'+this.url+'">'+ this.url+'</a><p> Thank you,</p>')
    },

    select2_wrapper: function (tag, multi, fetch_fnc) {
        return {
            width: '100%',
            allowClear: true,
            multiple: multi,
            selection_data: false,
            fetch_rpc_fnc : fetch_fnc,
            formatResult: function (term) {
                if (term.email) {
                    return term.text + " "+"(" + term.email + ")";
                }
            },
            fill_data: function (query, data) {
                var that = this,
                    tags = {results: []};
                _.each(data, function (obj) {
                    if (that.matcher(query.term, obj.email)) {
                        tags.results.push({id: obj.id, text: obj.name, email: obj.email});
                    }
                });
                query.callback(tags);
            },
            query: function (query) {
                var that = this;
                // fetch data only once and store it
                if (!this.selection_data) {
                    this.fetch_rpc_fnc().then(function (data) {
                        that.fill_data(query, data);
                        that.selection_data = data;
                    });
                } else {
                    this.fill_data(query, this.selection_data);
                }
            }
        };
    },
    set_partner_ids: function ($el) {
        $el.find('.partner_ids').select2(this.select2_wrapper(_t('partners'), true, function () {
            return rpc.query({
                model: 'res.partner',
                method: 'search_read',
                fields: ['id','name','email'],
            });
        }));
    },
    });
return ShareDocument;



});