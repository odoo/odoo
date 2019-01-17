odoo.define('web_editor.wysiwyg.plugin.registry', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var Registry = require('web.Registry');


var WysiwygRegistry = Registry.extend({
    init: function () {
        this._super();
        this._jobs = [];
        this._xmlDependencies = [];
        this._def = $.when();
    },
    start: function (wysiwyg) {
        var defs = [this._def];
        var fn;
        while ((fn = this._jobs.shift())) {
            defs.push(fn(wysiwyg));
        }
        var xmlPath;
        while ((xmlPath = this._xmlDependencies.shift())) {
            defs.push(ajax.loadXML(xmlPath, core.qweb));
        }
        if (defs.length !== 1) {
            this._def = $.when.apply($, defs);
        }
        return this._def.state() === 'resolved' ? $.when() : this._def;
    },
    addJob: function (job) {
        this._jobs.push(job);
    },
    addXmlDependency: function (xmlDependency) {
        this._xmlDependencies.push(xmlDependency);
    },
    plugins: function () {
        return _.clone(this.map);
    },
});

return new WysiwygRegistry();
});
