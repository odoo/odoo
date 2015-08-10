
odoo.define('web.translation', function (require) {
"use strict";

var Class = require('web.Class');
var qweb = require('qweb');


var TranslationDataBase = Class.extend(/** @lends instance.TranslationDataBase# */{
    init: function() {
        this.db = {};
        this.multi_lang = false
        this.parameters = {"direction": 'ltr',
                        "date_format": '%m/%d/%Y',
                        "time_format": '%H:%M:%S',
                        "grouping": [],
                        "decimal_point": ".",
                        "thousands_sep": ","};
    },
    set_bundle: function(translation_bundle) {
        var self = this;
        this.db = {};
        this.multi_lang = translation_bundle.multi_lang
        var modules = _.keys(translation_bundle.modules);
        modules.sort();
        if (_.include(modules, "web")) {
            modules = ["web"].concat(_.without(modules, "web"));
        }
        _.each(modules, function(name) {
            self.add_module_translation(translation_bundle.modules[name]);
        });
        if (translation_bundle.lang_parameters) {
            this.parameters = translation_bundle.lang_parameters;
            if (typeof(py) !== "undefined") {
                this.parameters.grouping = py.eval(this.parameters.grouping);
            }
        }
    },
    add_module_translation: function(mod) {
        var self = this;
        _.each(mod.messages, function(message) {
            self.db[message.id] = message.string;
        });
    },
    build_translation_function: function() {
        var self = this;
        var fcnt = function(str) {
            var tmp = self.get(str);
            return tmp === undefined ? str : tmp;
        };
        fcnt.database = this;
        return fcnt;
    },
    get: function(key) {
        return this.db[key];
    },
    /**
        Loads the translations from an OpenERP server.

        @param {openerp.Session} session The session object to contact the server.
        @param {Array} [modules] The list of modules to load the translation. If not specified,
        it will default to all the modules installed in the current database.
        @param {Object} [lang] lang The language. If not specified it will default to the language
        of the current user.
        @returns {jQuery.Deferred}
    */
    load_translations: function(session, modules, lang) {
        var self = this;
        return session.rpc('/web/webclient/translations', {
            "mods": modules || null,
            "lang": lang || null
        }).done(function(trans) {
            self.set_bundle(trans);
        });
    }
});

var _t = new TranslationDataBase().build_translation_function();
var _lt = function (s) {
    return {toString: function () { return _t(s); }};
};

// provide timeago.js with our own translator method
if($.timeago){ // make timeago an optional dependency of translation
    $.timeago.settings.translator = _t;
}

qweb.default_dict = {
    '_' : _,
    'JSON': JSON,
    '_t' : _t,
};

return {
    _t: _t,
    _lt: _lt,
    TranslationDataBase: TranslationDataBase,
};

});

