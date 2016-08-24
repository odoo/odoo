// ------------------------------------------------------------------------------
// Compatibility with Odoo v8.  
// 
// With the new module system, no global variable can (and should) be accessed
// in openerp.  This file exports everything, to mimic the previous global 
// namespace structure.  This is only supposed to be used by 3rd parties to 
// facilitate migration.  Odoo addons should not use the 'openerp' variable at 
// all.
// ------------------------------------------------------------------------------
odoo.define('web.compatibility', function (require) {
"use strict";

var ActionManager = require('web.ActionManager');
var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var FavoriteMenu = require('web.FavoriteMenu');
var form_common = require('web.form_common');
var formats = require('web.formats');
var FormView = require('web.FormView');
var form_relational = require('web.form_relational'); // necessary
var form_widgets = require('web.form_widgets'); // necessary
var framework = require('web.framework');
var ListView = require('web.ListView');
var Menu = require('web.Menu');
var Model = require('web.DataModel');
var pyeval = require('web.pyeval');
var Registry = require('web.Registry');
var SearchView = require('web.SearchView');
var session = require('web.session');
var Sidebar = require('web.Sidebar');
var SystrayMenu = require('web.SystrayMenu');
var time = require('web.time');
var UserMenu = require('web.UserMenu');
var utils = require('web.utils');
var View = require('web.View');
var ViewManager = require('web.ViewManager');
var WebClient = require('web.WebClient');
var Widget = require('web.Widget');

var client_started = $.Deferred();

var OldRegistry = Registry.extend({
    add: function (key, path) {
    },
    get_object: function (key) {
        return get_object(this.map[key]);
    },
});

window.openerp = window.openerp || {};

$.Mutex = utils.Mutex;
openerp._session_id = "instance0";
openerp._t = core._t;
openerp.get_cookie = utils.get_cookie;

openerp.qweb = core.qweb;
openerp.session = session;

openerp.web = openerp.web || {};
openerp.web._t = core._t;
openerp.web._lt = core._lt;

openerp.web.ActionManager = ActionManager;
openerp.web.auto_str_to_date = time.auto_str_to_date;
openerp.web.blockUI = framework.blockUI;
openerp.web.BufferedDataSet = data.BufferedDataSet;
openerp.web.bus = core.bus;
openerp.web.Class = core.Class;
openerp.web.client_actions = make_old_registry(core.action_registry);
openerp.web.CompoundContext = data.CompoundContext;
openerp.web.CompoundDomain = data.CompoundDomain;
openerp.web.DataSetSearch = data.DataSetSearch;
openerp.web.DataSet = data.DataSet;
openerp.web.date_to_str = time.date_to_str;
openerp.web.Dialog = Dialog;
openerp.web.DropMisordered = utils.DropMisordered;

openerp.web.form = openerp.web.form || {};
openerp.web.form.AbstractField = form_common.AbstractField;
openerp.web.form.compute_domain = data.compute_domain;
openerp.web.form.DefaultFieldManager = form_common.DefaultFieldManager;
openerp.web.form.FieldChar = core.form_widget_registry.get('char');
openerp.web.form.FieldFloat = core.form_widget_registry.get('float');
openerp.web.form.FieldStatus = core.form_widget_registry.get('statusbar');
openerp.web.form.FieldMany2ManyTags = core.form_widget_registry.get('many2many_tags');
openerp.web.form.FieldMany2One = core.form_widget_registry.get('many2one');
openerp.web.form.FormWidget = form_common.FormWidget;
openerp.web.form.tags = make_old_registry(core.form_tag_registry);
openerp.web.form.widgets = make_old_registry(core.form_widget_registry);
openerp.web.form.custom_widgets = make_old_registry(core.form_custom_registry);

openerp.web.format_value = formats.format_value;
openerp.web.FormView = FormView;

openerp.web.json_node_to_xml = utils.json_node_to_xml;

openerp.web.ListView = ListView;
openerp.web.Menu = Menu;
openerp.web.Model = Model;
openerp.web.normalize_format = time.strftime_to_moment_format;
openerp.web.py_eval = pyeval.py_eval;
openerp.web.pyeval = pyeval;
openerp.web.qweb = core.qweb;

openerp.web.Registry = OldRegistry;

openerp.web.search = {};
openerp.web.search.FavoriteMenu = FavoriteMenu;
openerp.web.SearchView = SearchView;
openerp.web.Sidebar = Sidebar;
openerp.web.str_to_date = time.str_to_date;
openerp.web.str_to_datetime = time.str_to_datetime;
openerp.web.SystrayItems = SystrayMenu.Items;
openerp.web.unblockUI = framework.unblockUI;
openerp.web.UserMenu = UserMenu;
openerp.web.View = View;
openerp.web.ViewManager = ViewManager;
openerp.web.views = make_old_registry(core.view_registry);
openerp.web.WebClient = WebClient;
openerp.web.Widget = Widget;

openerp.Widget = openerp.web.Widget;
openerp.Widget.prototype.session = session;


WebClient.include({
    init: function () {
        openerp.client = this;
        openerp.webclient = this;
        start_modules();
        client_started.resolve();
        this._super.apply(this, arguments);
    },
});


function make_old_registry(registry) {
    return {
        add: function (key, path) {
            client_started.done(function () {
                registry.add(key, get_object(path));
            });
        },
    };
}
function get_object(path) {
    var object_match = openerp;
    path = path.split('.');
    // ignore first section
    for(var i=1; i<path.length; ++i) {
        object_match = object_match[path[i]];
    }
    return object_match;
}

/**
 * OpenERP instance constructor
 *
 * @param {Array|String} modules list of modules to initialize
 */
var inited = false;
function start_modules (modules) {
    if (modules === undefined) {
        modules = odoo._modules;
    }
    modules = _.without(modules, "web");
    if (inited) {
        throw new Error("OpenERP was already inited");
    }
    inited = true;
    for(var i=0; i < modules.length; i++) {
        var fct = openerp[modules[i]];
        if (typeof(fct) === "function") {
            openerp[modules[i]] = {};
            for (var k in fct) {
                openerp[modules[i]][k] = fct[k];
            }
            fct(openerp, openerp[modules[i]]);
        }
    }
    openerp._modules = ['web'].concat(modules);
    return openerp;
};

// Monkey-patching of the ListView for backward compatibiliy of the colors and
// fonts row's attributes, as they are deprecated in 9.0.
ListView.include({
    load_list: function(data) {
        this._super(data);
        if (this.fields_view.arch.attrs.colors) {
            this.colors = _(this.fields_view.arch.attrs.colors.split(';')).chain()
                .compact()
                .map(function(color_pair) {
                    var pair = color_pair.split(':'),
                        color = pair[0],
                        expr = pair[1];
                    return [color, py.parse(py.tokenize(expr)), expr];
                }).value();
        }

        if (this.fields_view.arch.attrs.fonts) {
            this.fonts = _(this.fields_view.arch.attrs.fonts.split(';')).chain().compact()
                .map(function(font_pair) {
                    var pair = font_pair.split(':'),
                        font = pair[0],
                        expr = pair[1];
                    return [font, py.parse(py.tokenize(expr)), expr];
                }).value();
        }
    },
    /**
     * Returns the style for the provided record in the current view (from the
     * ``@colors`` and ``@fonts`` attributes)
     *
     * @param {Record} record record for the current row
     * @returns {String} CSS style declaration
     */
    style_for: function (record) {
        var len, style= '';

        var context = _.extend({}, record.attributes, {
            uid: session.uid,
            current_date: moment().format('YYYY-MM-DD')
            // TODO: time, datetime, relativedelta
        });
        var i;
        var pair;
        var expression;
        if (this.fonts) {
            for(i=0, len=this.fonts.length; i<len; ++i) {
                pair = this.fonts[i];
                var font = pair[0];
                expression = pair[1];
                if (py.PY_isTrue(py.evaluate(expression, context))) {
                    switch(font) {
                    case 'bold':
                        style += 'font-weight: bold;';
                        break;
                    case 'italic':
                        style += 'font-style: italic;';
                        break;
                    case 'underline':
                        style += 'text-decoration: underline;';
                        break;
                    }
                }
            }
        }
 
        if (!this.colors) { return style; }
        for(i=0, len=this.colors.length; i<len; ++i) {
            pair = this.colors[i];
            var color = pair[0];
            expression = pair[1];
            if (py.PY_isTrue(py.evaluate(expression, context))) {
                return style += 'color: ' + color + ';';
            }
        }
        return style;
     },
});


});
