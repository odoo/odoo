odoo.define('website.editor', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');
var base = require('web_editor.base');
var editor = require('web_editor.editor');
var widget = require('web_editor.widget');
var website = require('website.website');

var qweb = core.qweb;
var _t = core._t;

ajax.loadXML('/website/static/src/xml/website.editor.xml', qweb);

/**
 * Object who contains all method and bind for the top bar, the template is create server side.
 */
website.TopBar.include({
    events: {
        'click [data-action="edit"]': 'edit',
    },
    start: function () {
        var self = this;
        $("#wrapwrap").on('click', '.o_editable, [data-oe-model]', function (event) {
            var $this = $(event.srcElement);
            var tag = $this[0] && $this[0].tagName.toLowerCase();
            if (!(tag === 'a' || tag === "button") && !$this.parents("a, button").length) {
                self.$('[data-action="edit"]').parent().effect('bounce', {distance: 18, times: 5}, 250);
            }
        });

        $("#wrapwrap").find("[data-oe-model] .oe_structure.oe_empty, [data-oe-model].oe_structure.oe_empty, [data-oe-type=html]:empty")
            .filter(".oe_not_editable")
            .filter(".oe_no_empty")
            .addClass("oe_empty")
            .attr("data-oe-placeholder", _t("Press The Top-Left Edit Button"));

        if (location.search.indexOf("enable_editor") >= 0 && $('html').attr('lang') === "en_US") {
            this.$el.hide();
        }

        return this._super();
    },
    edit: function () {
        this.$('button[data-action=edit]').prop('disabled', true);
        this.$el.hide();
        editor.editor_bar = new editor.Class(this);
        editor.editor_bar.prependTo(document.body);
    }
});

/* ----- Customize Template ---- */

website.TopBarCustomize = Widget.extend({
    events: {
        'mousedown a.dropdown-toggle': 'load_menu',
        'click ul a[data-view-id]': 'do_customize',
    },
    start: function() {
        var self = this;
        this.$menu = self.$el.find('ul');
        this.view_name = $(document.documentElement).data('view-xmlid');
        if (!this.view_name) {
            this.$el.hide();
        }
        this.loaded = false;
    },
    load_menu: function () {
        var self = this;
        if(this.loaded) {
            return;
        }
        ajax.jsonRpc('/website/customize_template_get', 'call', { 'key': this.view_name }).then(
            function(result) {
                _.each(result, function (item) {
                    if (item.key === "website.debugger" && !window.location.search.match(/[&?]debug(&|$)/)) return;
                    if (item.header) {
                        self.$menu.append('<li class="dropdown-header">' + item.name + '</li>');
                    } else {
                        self.$menu.append(_.str.sprintf('<li role="presentation"><a href="#" data-view-id="%s" role="menuitem"><strong class="fa fa%s-square-o"></strong> %s</a></li>',
                            item.id, item.active ? '-check' : '', item.name));
                    }
                });
                self.loaded = true;
            }
        );
    },
    do_customize: function (event) {
        var view_id = $(event.currentTarget).data('view-id');
        return ajax.jsonRpc('/web/dataset/call_kw', 'call', {
            model: 'ir.ui.view',
            method: 'toggle',
            args: [],
            kwargs: {
                ids: [parseInt(view_id, 10)],
                context: base.get_context()
            }
        }).then( function() {
            window.location.reload();
        });
    },
});
website.TopBar.include({
    start: function () {
        this.customize_menu = new website.TopBarCustomize();
        var def = this.customize_menu.attachTo($('#customize-menu'));
        return $.when(this._super(), def);
    }
});

/* ----- EDITOR: LINK & MEDIA ---- */

widget.LinkDialog.include({
    bind_data: function () {
        var self = this;
        var href = this.data.url;
        var last;
        
        this.$('#link-page').select2({
            minimumInputLength: 1,
            placeholder: _t("New or existing page"),
            query: function (q) {
                if (q.term == last) return;
                last = q.term;
                $.when(
                    self.page_exists(q.term),
                    self.fetch_pages(q.term)
                ).then(function (exists, results) {
                    var rs = _.map(results, function (r) {
                        return { id: r.loc, text: r.loc, };
                    });
                    if (!exists) {
                        rs.push({
                            create: true,
                            id: q.term,
                            text: _.str.sprintf(_t("Create page '%s'"), q.term),
                        });
                    }
                    q.callback({
                        more: false,
                        results: rs
                    });
                }, function () {
                    q.callback({more: false, results: []});
                });
            },
        });

        if (href) {
            this.page_exists(href).then(function (exist) {
                if (exist) {
                    self.$('#link-page').select2('data', {'id': href, 'text': href}).change();
                } else {
                    self.$('input.url').val(href).change();
                    self.$('input.window-new').closest("div").show();
                }
            });
        }
        return this._super();
    },
    get_data_buy_url: function (def, $e, isNewWindow, label, classes, test) {
        var val = $e.val();
        if (val && val.length && $e.hasClass('page')) {
            var data = $e.select2('data');
            if (!data.create || test) {
                def.resolve(data.id, isNewWindow, label || data.text, classes);
            } else {
                // Create the page, get the URL back
                $.get(_.str.sprintf(
                        '/website/add/%s?noredirect=1', encodeURI(data.id)))
                    .then(function (response) {
                        def.resolve(response, isNewWindow, label, classes);
                    });
            }
        } else {
            return this._super.apply(this, arguments);
        }
    },
    changed: function (e) {
        this.$('.url-source').filter(':input').not($(e.target)).val('')
                .filter(function () { return !!$(this).data('select2'); })
                .select2('data', null);
        this._super(e);
    },
    call: function (method, args, kwargs) {
        var self = this;
        var req = method + '_req';
        if (this[req]) { this[req].abort(); }
        return this[req] = ajax.jsonRpc('/web/dataset/call_kw', 'call', {
            model: 'website',
            method: method,
            args: args,
            kwargs: kwargs,
        }).always(function () {
            self[req] = null;
        });
    },
    page_exists: function (term) {
        return this.call('page_exists', [null, term], {
            context: base.get_context(),
        });
    },
    fetch_pages: function (term) {
        return this.call('search_pages', [null, term], {
            limit: 9,
            context: base.get_context(),
        });
    },
});

});
