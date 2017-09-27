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
        this.url = options.url
        console.log ("dddddddddd");
        },

    start: function(){
        this._super.apply(this, arguments);
        var dialog = new Dialog(this, {
            title: _t("Share Document"),
            $content: $(qweb.render('portal.portal_share_document',{
                url: this.url
            })),
            buttons: [{text: _t('Send'), classes: 'btn-primary', close: true, click: function () {
                console.log(this.$('.o_website_email').val());
                // Todo
            }}, {text: _t('Cancel'), close: true}],
        });
        dialog.open();
        this.set_partner_ids(dialog.$content);
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
            formatSelection: function (data) {
                if (data.tag) {
                    data.text = data.tag;
                }
                return data.text;
            },
            createSearchChoice: function (term, data) {
                var added_tags = $(this.opts.element).select2('data');
                if (_.filter(_.union(added_tags, data), function (tag) {
                    return tag.text.toLowerCase().localeCompare(term.toLowerCase()) === 0;
                }).length === 0) {
                    return {
                        id: _.uniqueId('partner_'),
                        create: true,
                        tag: term,
                        text: _.str.sprintf(_t("Create new partner '%s'"), term),
                    };
                }
            },
            fill_data: function (query, data) {
                var that = this,
                    tags = {results: []};
                _.each(data, function (obj) {
                    if (that.matcher(query.term, obj.name)) {
                        console.log(obj);
                        tags.results.push({id: obj.id, text: obj.name });
                    }
                });
                query.callback(tags);
            },
            query: function (query) {
                console.log("data", query)
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
                    fields: ['name'],
                    context: weContext.get()
                }
            });
        }));
    },
    get_partner_ids: function () {
        var res = [];
        _.each($('.partner_ids').select2('data'),
            function (val) {
                if (val.create) {
                    res.push([0, 0, {'name': val.text}]);
                } else {
                    res.push([4, val.id]);
                }
            });
        return res;
    },
    });
return ShareDocument;



});