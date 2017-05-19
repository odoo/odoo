
odoo.define('web.translation', function (require) {
"use strict";

var Class = require('web.Class');

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
            this.parameters.grouping = JSON.parse(this.parameters.grouping);
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
/**
 * Lazy translation function, only performs the translation when actually
 * printed (e.g. inserted into a template)
 *
 * Useful when defining translatable strings in code evaluated before the
 * translation database is loaded, as class attributes or at the top-level of
 * an OpenERP Web module
 *
 * @param {String} s string to translate
 * @returns {Object} lazy translation object
 */
var _lt = function (s) {
    return {toString: function () { return _t(s); }};
};

/** Setup jQuery timeago */
/*
 * Strings in timeago are "composed" with prefixes, words and suffixes. This
 * makes their detection by our translating system impossible. Use all literal
 * strings we're using with a translation mark here so the extractor can do its
 * job.
 */
{
    _t('less than a minute ago');
    _t('about a minute ago');
    _t('%d minutes ago');
    _t('about an hour ago');
    _t('%d hours ago');
    _t('a day ago');
    _t('%d days ago');
    _t('about a month ago');
    _t('%d months ago');
    _t('about a year ago');
    _t('%d years ago');
}


return {
    _t: _t,
    _lt: _lt,
    TranslationDataBase: TranslationDataBase,
};

});
