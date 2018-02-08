odoo.define('web_editor.iframe', function (require) {
'use strict';

var core = require('web.core');
var editor = require('web_editor.editor');
var translator = require('web_editor.translate');
var rte = require('web_editor.rte');

var callback = window ? window['callback'] : undefined;
window.top.odoo[callback + '_updown'] = function (value, fields_values, field_name) {
    var $editable = $('#editable_area');
    if (value === $editable.prop('innerHTML')) {
        return;
    }

    if ($('body').hasClass('editor_enable')) {
        if (value !== fields_values[field_name]) {
            rte.history.recordUndo($editable);
        }
        core.bus.trigger('deactivate_snippet');
    }

    $editable.html(value);

    if ($('body').hasClass('editor_enable') && value !== fields_values[field_name]) {
        $editable.trigger('content_changed');
    }
};

editor.Class.include({
    start: function () {
        this.on('rte:start', this, function () {
            this.$('form').hide();

            if (window.top.odoo[callback + '_editor']) {
                window.top.odoo[callback + '_editor'](this);
            }

            var $editable = $('#editable_area');
            setTimeout(function () {
                $($editable.find('*').filter(function () {return !this.children.length;}).first()[0] || $editable)
                    .focusIn().trigger('mousedown').trigger('keyup');
            },0);

            $editable.on('content_changed', this, function () {
                if (window.top.odoo[callback + '_downup']) {
                    window.top.odoo[callback + '_downup']($editable.prop('innerHTML'));
                }
            });
        });

        return this._super.apply(this, arguments).then(function () {
            $(window.top).trigger('resize'); // TODO check, probably useless
        });
    }
});

rte.Class.include({
    /**
     * @override
     */
    _getDefaultConfig: function ($editable) {
        var config = this._super.apply(this, arguments);
        if ($.deparam($.param.querystring()).debug !== undefined) {
            config.airPopover.splice(7, 0, ['view', ['codeview']]);
        }
        return config;
    },
});

translator.Class.include({
    start: function () {
        var res = this._super.apply(this, arguments);
        $('button[data-action=save]').hide();
        if (window.top.odoo[callback + '_editor']) {
            window.top.odoo[callback + '_editor'](this);
        }
        return res;
    },
});
});

//==============================================================================

odoo.define('web_editor.IframeRoot.instance', function (require) {
'use strict';

require('web.dom_ready');
var iframeRootData = require('web_editor.IframeRoot');

var iframeRoot = new iframeRootData.IframeRoot(null);
return iframeRoot.attachTo(document.body).then(function () {
    return iframeRoot;
});
});

//==============================================================================

odoo.define('web_editor.IframeRoot', function (require) {
'use strict';

var BodyManager = require('web_editor.BodyManager');
var weContext = require('web_editor.context');
var editor = require('web_editor.editor');
var rootWidget = require('web_editor.root_widget');
var translate = require('web_editor.translate');

var iframeRootRegistry = new rootWidget.RootWidgetRegistry();

var IframeRoot = BodyManager.extend({
    /**
     * @override
     * @todo this is somehow a duplicate of website features
     */
    start: function () {
        var defs = [this._super.apply(this, arguments)];

        var ctx = weContext.getExtra();

        if (ctx.editable && window.location.search.indexOf('enable_editor') >= 0) {
            var editorInstance = new (editor.Class)(this);
            defs.push(editorInstance.prependTo(this.$el));
        }

        if (ctx.edit_translations) {
            var translator = new (translate.Class)(this, this.$('#wrapwrap'));
            defs.push(translator.prependTo(this.$el));
        }

        return $.when.apply($, defs);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * As the IframeRoot instance is designed to be unique, the associated
     * registry has been instantiated outside of the class and is simply
     * returned here.
     *
     * @override
     */
    _getRegistry: function () {
        return iframeRootRegistry;
    },
});

return {
    IframeRoot: IframeRoot,
    iframeRootRegistry: iframeRootRegistry,
};
});
