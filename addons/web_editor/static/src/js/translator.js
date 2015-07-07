odoo.define('web_editor.translate', function (require) {
'use strict';

var core = require('web.core');
var Model = require('web.Model');
var ajax = require('web.ajax');
var Class = require('web.Class');
var Widget = require('web.Widget');
var base = require('web_editor.base');
var rte = require('web_editor.rte');

var qweb = core.qweb;

ajax.loadXML('/web_editor/static/src/xml/translator.xml', qweb);


var translatable = !!$('html').data('translatable');
var edit_translations = !!$('html').data('edit_translations');

function unbind_click(event) {
    if (event.ctrlKey || !$(event.target).is(':o_editable')) {
        return;
    }
    event.preventDefault();
    event.stopPropagation();
}


var RTE_Translate = rte.Class.extend({
    saveElement: function ($el, context) {
        // remove multi edition
        if ($el.data('oe-translation-id')) {
            var key =  'translation:'+$el.data('oe-translation-id');
            if (this.__saved[key]) return true;
            this.__saved[key] = true;

            return ajax.jsonRpc('/web/dataset/call', 'call', {
                model: 'ir.translation',
                method: 'write',
                args: [
                    [+$el.data('oe-translation-id')],
                    {value: $el.html(), state: 'translated'},
                    context || base.get_context()
                ],
            });
        }

        return this._super.apply(this, arguments);
    },
});

var Translate = Widget.extend({
    events: {
        'click [data-action="save"]': 'save_and_reload',
        'click [data-action="cancel"]': 'cancel',
    },
    template: 'web_editor.translator',
    init: function (parent, $target, lang) {
        this.parent = parent;
        this.ir_translation = new Model('ir.translation');
        this.lang = lang || base.get_context().lang;
        this.setTarget($target);
        this._super();

        this.rte = new RTE_Translate(this, this.config);
        this.rte.on('change', this, this.onChange);
    },
    start: function () {
        this._super();
        return this.edit();
    },
    setTarget: function ($target) {
        this.$target = $target.find('[data-oe-translation-id], [data-oe-model][data-oe-id][data-oe-field]');
    },
    find: function (selector) {
        return selector ? this.$target.find(selector).addBack().filter(selector) : this.$target;
    },
    edit: function () {
        var flag = false;
        window.onbeforeunload = function(event) {
            if ($('.o_editable.o_dirty').length && !flag) {
                flag = true;
                setTimeout(function () {flag=false;},0);
                return _t('This document is not saved!');
            }
        };
        this.$target.addClass("o_editable");
        this.rte.start();
        this.translations = [];
        this.markTranslatableNodes();
        this.onTranslateReady();
    },
    onTranslateReady: function () {
        this.$el.show();
        this.trigger("edit");
    },
    onChange: function (node) {
        var $node = $(node);
        var trans = this.getTranlationObject($node[0]);
        $node.toggleClass('o_dirty', trans.value !== $node.html().replace(/[ \t\n\r]+/, ' '));
    },
    getTranlationObject: function (node) {
        var $node = $(node);
        var id = +$node.data('oe-translation-id');
        if (!id) {
            id = $node.data('oe-model')+','+$node.data('oe-id')+','+$node.data('oe-field');
        }
        var trans = _.find(this.translations, function (trans) {
            return trans.id === id;
        });
        if (!trans) {
            this.translations.push(trans = {'id': id});
        }
        return trans;
    },
    markTranslatableNodes: function (node) {
        var self = this;
        this.$target.each(function () {
            var $node = $(this);
            var trans = self.getTranlationObject(this);
            trans.value = (trans.value ? trans.value : $node.html() ).replace(/[ \t\n\r]+/, ' ');
        });
        this.$target.parent().on('click', unbind_click);
        console.info('Click on CTRL when you click in an translatable area to have the default behavior');
    },
    unarkTranslatableNode: function () {
        this.$target.removeClass('o_editable').removeAttr('contentEditable');
        this.$target.parent().off('click', this.__unbind_click);
        this.$target_attr.off('mousedown click mouseup', this.__translate_attribute);
    },
    save_and_reload: function () {
        return this.save().then(function () {
            window.location.href = window.location.href.replace(/&?edit_translations(=[^&]*)?/g, '');
        });
    },
    save: function () {
        var context = base.get_context();
        context.lang = this.lang;
        return this.rte.save(context);
    },
    cancel: function () {
        var self = this;
        this.rte.cancel();
        this.$target.each(function () {
            $(this).html(self.getTranlationObject(this).value);
        });
        this.unarkTranslatableNode();
        this.trigger("cancel");
        this.$el.hide();
    },
    destroy: function () {
        this.cancel();
        this.$el.remove();
        this._super();
    },

    config: function ($editable) {
        if ($editable.data('oe-model')) {
            return {
                'airMode' : true,
                'focus': false,
                'airPopover': [
                    ['history', ['undo', 'redo']],
                ],
                'styleWithSpan': false,
                'inlinemedia' : ['p'],
                'lang': "odoo",
                'onChange': function (html, $editable) {
                    $editable.trigger("content_changed");
                }
            };
        }
        return {
            'airMode' : true,
            'focus': false,
            'airPopover': [
                ['font', ['bold', 'italic', 'underline', 'clear']],
                ['fontsize', ['fontsize']],
                ['color', ['color']],
                ['history', ['undo', 'redo']],
            ],
            'styleWithSpan': false,
            'inlinemedia' : ['p'],
            'lang': "odoo",
            'onChange': function (html, $editable) {
                $editable.trigger("content_changed");
            }
        };
    }
});


if (edit_translations) {
    base.ready().then(function () {
        data.instance = new Translate(this, $('#wrapwrap'));
        data.instance.prependTo(document.body);

        $('a[href*=edit_translations]').each(function () {
            this.href = this.href.replace(/[$?]edit_translations[^&?]+/, '');
        });
        $('form[action*=edit_translations]').each(function () {
            this.action = this.action.replace(/[$?]edit_translations[^&?]+/, '');
        });
    });
}

var data = {
    'translatable': translatable,
    'edit_translations': edit_translations,
    'Class': Translate,
};
return data;

});
