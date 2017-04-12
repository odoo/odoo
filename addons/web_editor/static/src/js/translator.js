odoo.define('web_editor.translate', function (require) {
'use strict';

var core = require('web.core');
var ajax = require('web.ajax');
var Widget = require('web.Widget');
var base = require('web_editor.base');
var rte = require('web_editor.rte');
var editor_widget = require('web_editor.widget');

var _t = core._t;

var translatable = !!$('html').data('translatable');
var edit_translations = !!$('html').data('edit_translations');

$.fn.extend({
  prependEvent: function (events, selector, data, handler) {
    this.on(events, selector, data, handler);
    events = events.split(' ');
    this.each(function () {
        var el = this;
        _.each(events, function (event) {
            var handler = $._data(el, 'events')[event].pop();
            $._data(el, 'events')[event].unshift(handler);
        });
    });
    return this;
  }
});

var RTE_Translate = rte.Class.extend({
    saveElement: function ($el, context) {
        // remove multi edition
        var key = $el.data('oe-translation-id') ? 'translation:'+$el.data('oe-translation-id') :
                ($el.data('oe-model') ? $el.data('oe-model')+":"+$el.data('oe-id')+":"+$el.data('oe-field')+":"+$el.data('oe-type')+":"+$el.data('oe-expression') : false);
        if (!key || this.__saved[key]) return true;
        this.__saved[key] = true;

        if ($el.data('oe-translation-id')) {
            var translation_content = this.getEscapedElement($el).html();

            return ajax.jsonRpc('/web/dataset/call', 'call', {
                model: 'ir.translation',
                method: 'save_html',
                args: [
                    [+$el.data('oe-translation-id')],
                    translation_content,
                    context || base.get_context()
                ],
            });
        } else {
            var markup = this.getEscapedElement($el).prop('outerHTML');

            return ajax.jsonRpc('/web/dataset/call', 'call', {
                model: 'ir.ui.view',
                method: 'save',
                args: [
                    $el.data('oe-id'),
                    markup,
                    $el.data('oe-xpath') || null,
                    context || base.get_context()
                ],
            });
        }
    },
});

var Translate_Modal = editor_widget.Dialog.extend({
    init: function (p, options, parent, node) {
        this._super(p, _.extend({}, {
            title: _t("Translate Attribute"),
            buttons: [
                {text:  _t("Close"), classes: "btn-primary o_save_button", close: true, click: this.save}
            ]
        }, options || {}));
        this.parent = parent;
        this.$target = $(node);
        this.translation = $(node).data('translation');
    },
    start: function () {
        var self = this;
        var def = this._super.apply(this, arguments);
        var $group = $("<div/>", {"class": "form-group"}).appendTo(this.$el);
        _.each(this.translation, function (node, attr) {
            var $node = $(node);
            var $label = $('<label class="control-label"></label>').text(attr);
            var $input = $('<input class="form-control"/>').val($node.html());
            $input.on('change keyup', function () {
                var value = $input.val();
                $node.html(value).trigger('change', node);
                $node.data('$node').attr($node.data('attribute'), value).trigger('translate');
                self.parent.rte_changed(node);
            });
            $group.append($label).append($input);
        });
        return def;
    }
});

var Translate = Widget.extend({
    events: {
        'click [data-action="save"]': 'save_and_reload',
        'click [data-action="cancel"]': 'cancel',
    },
    template: 'web_editor.editorbar',
    init: function (parent, $target, lang) {
        this.parent = parent;
        this.lang = lang || base.get_context().lang;
        this.setTarget($target);
        this._super.apply(this, arguments);

        this.rte = new RTE_Translate(this, this.config);
        this.rte.on('change', this, this.rte_changed);
    },
    start: function () {
        this._super.apply(this, arguments);
        this.$('#web_editor-toolbars').remove();
        return this.edit();
    },
    setTarget: function ($target) {
        var $edit = $target.find('[data-oe-translation-id], [data-oe-model][data-oe-id][data-oe-field]');
        $edit.filter(':has([data-oe-translation-id], [data-oe-model][data-oe-id][data-oe-field])').attr('data-oe-readonly', true);

        this.$target = $edit.not('[data-oe-readonly]');

        // attributes

        var attrs = ['placeholder', 'title', 'alt'];
        _.each(attrs, function (attr) {
            $target.find('['+attr+'*="data-oe-translation-id="]').filter(':empty, input, select, textarea, img').each(function () {
                var $node = $(this);
                var translation = $node.data('translation') || {};
                var trans = $node.attr(attr);
                var match = trans.match(/<span [^>]*data-oe-translation-id="([0-9]+)"[^>]*>(.*)<\/span>/);
                var $trans = $(trans).addClass('hidden o_editable o_editable_translatable_attribute').appendTo('body');
                $trans.data('$node', $node).data('attribute', attr);
                translation[attr] = $trans[0];
                $node.attr(attr, match[2]);

                var select2 = $node.data('select2');
                if (select2) {
                    select2.blur();
                    $node.on('translate', function () {
                        select2.blur();
                    });
                    $node = select2.container.find('input');
                }
                $node.addClass('o_translatable_attribute').data('translation', translation);
            });
        });
        this.$target_attr = $target.find('.o_translatable_attribute');
        this.$target_attribute = $('.o_editable_translatable_attribute');
    },
    find: function (selector) {
        return selector ? this.$target.find(selector).addBack().filter(selector) : this.$target;
    },
    edit: function () {
        var flag = false;
        window.onbeforeunload = function (event) {
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
    rte_changed: function (node) {
        var $node = $(node);
        $node.find("p").each(function () { // remove <p/> element which might have been inserted because of copy-paste
            var $p = $(this);
            $p.after($p.html()).remove();
        });
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
    __unbind_click: function (event) {
        if (event.ctrlKey || !$(event.target).is(':o_editable')) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
    },
    __translate_attribute: function (event) {
        if (event.ctrlKey) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        if (event.type !== 'mousedown') {
            return;
        }

        new Translate_Modal(null, {}, event.data, event.target).open();
    },
    markTranslatableNodes: function (node) {
        var self = this;
        this.$target.add(this.$target_attribute).each(function () {
            var $node = $(this);
            var trans = self.getTranlationObject(this);
            trans.value = (trans.value ? trans.value : $node.html() ).replace(/[ \t\n\r]+/, ' ');
        });
        this.$target.parent().prependEvent('click', this, this.__unbind_click);

        // attributes

        this.$target_attr.each(function () {
            var $node = $(this);
            var translation = $node.data('translation');
            _.each(translation, function (node, attr) {
                var trans = self.getTranlationObject(node);
                trans.value = (trans.value ? trans.value : $node.html() ).replace(/[ \t\n\r]+/, ' ');
                $node.attr('data-oe-translation-state', (trans.state || 'to_translate'));
            });
        });

        this.$target_attr.prependEvent('mousedown click mouseup', this, this.__translate_attribute);

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
        window.onbeforeunload = null;
    },
    destroy: function () {
        this.cancel();
        this.$el.remove();
        this._super.apply(this, arguments);
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

        $('title').html($('title').html().replace(/&lt;span data-oe-model.+?&gt;(.+?)&lt;\/span&gt;/, '\$1'));
    });
}

var data = {
    'translatable': translatable,
    'edit_translations': edit_translations,
    'Class': Translate,
};
return data;

});
