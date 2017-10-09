odoo.define('portal.share_document', function (require){
    "use strict";

var ajax = require('web.ajax');
var Widget = require("web.Widget");
var core = require('web.core');
var Dialog = require('web.Dialog');
var weContext = require("web_editor.context");
var qweb = core.qweb;
var _t = core._t;


var ShareDocument = Widget.extend({
    xmlDependencies: ['/portal/static/src/xml/portal_share_document.xml'],

    init: function(options) {
        this._super.apply(this, arguments);
        this.url = options.url;
        this.model = options.res_model;
        this.res_id = options.res_id;
        },

    start: function(){
        this._super.apply(this, arguments);
        var self = this;
        var dialog = new Dialog(this, {
            title: _t("Share Document"),
            $content: $(qweb.render('portal.portal_share_document',{
                url: this.url,
            })),
            buttons: [{text: _t('Send'), classes: 'btn-primary', close: true, click: function () {
                var data = this.$el.find('.partner_ids').select2('data')
                var partner_list = []
                _.each(data, function(obj){
                    partner_list.push(obj.id)
                });
                ajax.jsonRpc('/portal/send_share_email', 'call', {
                    partner_ids: partner_list ,
                    model: self.model,
                    res_id: self.res_id,
                }).then(function () {
                    this.$el.html($('<div class="alert alert-info" role="alert"><strong>Thank you!</strong> Mail has been sent.</div>'));
                });
            }}, {text: _t('Cancel'), close: true}],
        });
        dialog.open();
        this.set_partner_ids(dialog.$content);

        dialog.$content.find('textarea').summernote({
            height: 150
        });
    },

    select2_wrapper: function (tag, multi, fetch_fnc) {
        return {
            width: '100%',
            placeholder: tag,
            allowClear: true,
            formatNoMatches: false,
            multiple: multi,
            selection_data: false,
            fetch_rpc_fnc : fetch_fnc,
            formatResult: function (term) {
                if (term.text) {
                    return term.name + " "+"(" + term.text + ")";
                }
            },
            fill_data: function (query, data) {
                var that = this,
                    tags = {results: []};
                _.each(data, function (obj) {
                    if (that.matcher(query.term, obj.email)) {
                        tags.results.push({id: obj.id, text: obj.email, name: obj.name});
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
            return ajax.jsonRpc("/web/dataset/call_kw", 'call', {
                model: 'res.partner',
                method: 'search_read',
                args: [],
                kwargs: {
                    fields: ['id','name','email'],
                    context: weContext.get()
                }
            });
        }));
    },
    });
return ShareDocument;



});