odoo.define('web_editor.wysiwyg.plugins', function (require) {
'use strict';

var AbstractPlugin = require('web_editor.wysiwyg.plugin.abstract');
var registry = require('web_editor.wysiwyg.plugin.registry');
var wysiwygOptions = require('web_editor.wysiwyg.options');


var plugins = _.mapObject(wysiwygOptions.modules, function (Module, pluginName) {
    var prototype = {
        init: function () {
            var self = this;
            this._super.apply(this, arguments);
            var events = _.clone(this.events);
            this.summernote.options.modules[pluginName].apply(this, arguments);
            _.each(events, function (value, key) {
                self.events[key] = value;
            });
        },
    };
    _.each(Module.prototype, function (prop, name) {
        if (typeof prop === 'function') {
            prototype[name] = function () {
                return this.summernote.options.modules[pluginName].prototype[name].apply(this, arguments);
            };
        } else {
            prototype[name] = prop;
        }
    });

    var Plugin = AbstractPlugin.extend(prototype).extend({
        destroy: function () {
            if (this.shouldInitialize()) {
                this._super();
            }
        },
    });

    // override summernote default buttons
    registry.add(pluginName, Plugin);

    return Plugin;
});

// export table plugin to convert it in module (see editor)

var $textarea = $('<textarea>');
$('body').append($textarea);
$textarea.summernote();
var summernote = $textarea.data('summernote');

_.each(['style', 'table', 'typing', 'bullet', 'history'], function (name) {
    var prototype = {};
    for (var k in summernote.modules.editor[name]) {
        prototype[k] = summernote.modules.editor[name][k];
    }
    plugins[name] = AbstractPlugin.extend(prototype);
});

var History = summernote.modules.editor.history.constructor;
plugins.history.include({
    init: function (context) {
        this._super(context);
        History.call(this, this.$editable);
    },
});

try {
    $textarea.summernote('destroy');
} catch (e) {
    summernote.layoutInfo.editor.remove();
}
$textarea.remove();


return plugins;

});
