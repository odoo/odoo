odoo.define('web_editor.translate', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var localStorage = require('web.local_storage');
var Widget = require('web.Widget');
var weContext = require('web_editor.context');
var rte = require('web_editor.rte');
var weWidgets = require('web_editor.widget');
var Dialog = require('web.Dialog');

var _t = core._t;

var localStorageNoDialogKey = 'website_translator_nodialog';

var RTETranslatorWidget = rte.Class.extend({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * If the element holds a translation, saves it. Otherwise, fallback to the
     * standard saving but with the lang kept.
     *
     * @override
     */
    _saveElement: function ($el, context, withLang) {
        var self = this;
        if ($el.data('oe-translation-id')) {
            return this._rpc({
                model: 'ir.translation',
                method: 'save_html',
                args: [
                    [+$el.data('oe-translation-id')],
                    this._getEscapedElement($el).html()
                ],
                context: context,
            }).fail(function (error) {
                Dialog.alert(null, error.data.message);
            });
        }
        return this._super($el, context, withLang === undefined ? true : withLang);
    },
});

var AttributeTranslateDialog = weWidgets.Dialog.extend({
    /**
     * @constructor
     */
    init: function (parent, options, node) {
        this._super(parent, _.extend({
            title: _t("Translate Attribute"),
            buttons: [
                {text:  _t("Close"), classes: 'btn-primary', click: this.save}
            ],
        }, options || {}));
        this.$target = $(node);
        this.translation = $(node).data('translation');
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        var $group = $('<div/>', {class: 'form-group'}).appendTo(this.$el);
        _.each(this.translation, function (node, attr) {
            var $node = $(node);
            var $label = $('<label class="col-form-label"></label>').text(attr);
            var $input = $('<input class="form-control"/>').val($node.html());
            $input.on('change keyup', function () {
                var value = $input.val();
                $node.html(value).trigger('change', node);
                $node.data('$node').attr($node.data('attribute'), value).trigger('translate');
                self.trigger_up('rte_change', {target: node});
            });
            $group.append($label).append($input);
        });
        return this._super.apply(this, arguments);
    }
});

var TranslatorInfoDialog = Dialog.extend({
    template: 'web_editor.TranslatorInfoDialog',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/web_editor/static/src/xml/translator.xml']
    ),

    /**
     * @constructor
     */
    init: function (parent, options) {
        this._super(parent, _.extend({
            title: _t("Translation Info"),
            buttons: [
                {text: _t("Ok, never show me this again"), classes: 'btn-primary', close: true, click: this._onStrongOk.bind(this)},
                {text: _t("Ok"), close: true}
            ],
        }, options || {}));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the "strong" ok is clicked -> adapt localstorage to make sure
     * the dialog is never displayed again.
     *
     * @private
     */
    _onStrongOk: function () {
        localStorage.setItem(localStorageNoDialogKey, true);
    },
});

var TranslatorMenuBar = Widget.extend({
    template: 'web_editor.editorbar',
    xmlDependencies: ['/web_editor/static/src/xml/editor.xml'],
    events: {
        'click [data-action="save"]': '_onSaveClick',
        'click [data-action="cancel"]': '_onCancelClick',
    },
    custom_events: {
        'rte_change': '_onRTEChange',
    },

    /**
     * @constructor
     */
    init: function (parent, $target, lang) {
        this._super.apply(this, arguments);

        var $edit = $target.find('[data-oe-translation-id], [data-oe-model][data-oe-id][data-oe-field]');
        $edit.filter(':has([data-oe-translation-id], [data-oe-model][data-oe-id][data-oe-field])').attr('data-oe-readonly', true);
        this.$target = $edit.not('[data-oe-readonly]');
        var attrs = ['placeholder', 'title', 'alt'];
        _.each(attrs, function (attr) {
            $target.find('['+attr+'*="data-oe-translation-id="]').filter(':empty, input, select, textarea, img').each(function () {
                var $node = $(this);
                var translation = $node.data('translation') || {};
                var trans = $node.attr(attr);
                var match = trans.match(/<span [^>]*data-oe-translation-id="([0-9]+)"[^>]*>(.*)<\/span>/);
                var $trans = $(trans).addClass('d-none o_editable o_editable_translatable_attribute').appendTo('body');
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

        this.lang = lang || weContext.get().lang;

        this.rte = new RTETranslatorWidget(this, this._getRTEConfig);
    },
    /**
     * @override
     */
    start: function () {
        this.$('#web_editor-toolbars').remove();

        var flag = false;
        window.onbeforeunload = function (event) {
            if ($('.o_editable.o_dirty').length && !flag) {
                flag = true;
                setTimeout(function () {
                    flag = false;
                }, 0);
                return _t('This document is not saved!');
            }
        };
        this.$target.addClass('o_editable');
        this.rte.start();
        this.translations = [];
        this._markTranslatableNodes();
        this.$el.show(); // TODO seems useless
        this.trigger('edit');

        if (!localStorage.getItem(localStorageNoDialogKey)) {
            new TranslatorInfoDialog(this).open();
        }

        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._cancel();
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Leaves translation mode by hiding the translator bar.
     *
     * @todo should be destroyed?
     * @private
     */
    _cancel: function () {
        var self = this;
        this.rte.cancel();
        this.$target.each(function () {
            $(this).html(self._getTranlationObject(this).value);
        });
        this._unmarkTranslatableNode();
        this.trigger('cancel');
        this.$el.hide();
        window.onbeforeunload = null;
    },
    /**
     * Returns the RTE summernote configuration for translation mode.
     *
     * @private
     * @param {jQuery} $editable
     */
    _getRTEConfig: function ($editable) {
        return {
            airMode : true,
            focus: false,
            airPopover: $editable.data('oe-model') ? [
                ['history', ['undo', 'redo']],
            ] : [
                ['font', ['bold', 'italic', 'underline', 'clear']],
                ['fontsize', ['fontsize']],
                ['color', ['color']],
                ['history', ['undo', 'redo']],
            ],
            styleWithSpan: false,
            inlinemedia : ['p'],
            lang: 'odoo',
            onChange: function (html, $editable) {
                $editable.trigger('content_changed');
            },
        };
    },
    /**
     * @private
     */
    _getTranlationObject: function (node) {
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
    /**
     * @private
     */
    _markTranslatableNodes: function () {
        var self = this;
        this.$target.add(this.$target_attribute).each(function () {
            var $node = $(this);
            var trans = self._getTranlationObject(this);
            trans.value = (trans.value ? trans.value : $node.html() ).replace(/[ \t\n\r]+/, ' ');
        });
        this.$target.parent().prependEvent('click.translator', function (ev) {
            if (ev.ctrlKey || !$(ev.target).is(':o_editable')) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();
        });

        // attributes

        this.$target_attr.each(function () {
            var $node = $(this);
            var translation = $node.data('translation');
            _.each(translation, function (node, attr) {
                var trans = self._getTranlationObject(node);
                trans.value = (trans.value ? trans.value : $node.html() ).replace(/[ \t\n\r]+/, ' ');
                $node.attr('data-oe-translation-state', (trans.state || 'to_translate'));
            });
        });

        this.$target_attr.prependEvent('mousedown.translator click.translator mouseup.translator', function (ev) {
            if (ev.ctrlKey) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();
            if (ev.type !== 'mousedown') {
                return;
            }

            new AttributeTranslateDialog(self, {}, ev.target).open();
        });
    },
    /**
     * Saves the translation and reloads the page to leave edit mode.
     *
     * @private
     * @returns {Deferred} (never resolved as the page is reloading anyway)
     */
    _save: function () {
        return this.rte.save(weContext.get({lang: this.lang})).then(function () {
            window.location.href = window.location.href.replace(/&?edit_translations(=[^&]*)?/g, '');
            return $.Deferred();
        });
    },
    /**
     * @private
     */
    _unmarkTranslatableNode: function () {
        this.$target.removeClass('o_editable').removeAttr('contentEditable');
        this.$target.parent().off('.translator');
        this.$target_attr.off('.translator');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the "cancel" button is clicked -> undo changes and leaves
     * edition.
     *
     * @private
     */
    _onCancelClick: function () {
        this._cancel();
    },
    /**
     * Called when text is edited -> make sure text is not messed up and mark
     * the element as dirty.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onRTEChange: function (ev) {
        var $node = $(ev.data.target);
        $node.find('p,div').each(function () { // remove P,DIV elements which might have been inserted because of copy-paste
            var $p = $(this);
            $p.after($p.html()).remove();
        });
        var trans = this._getTranlationObject($node[0]);
        $node.toggleClass('o_dirty', trans.value !== $node.html().replace(/[ \t\n\r]+/, ' '));
    },
    /**
     * Called when the "save" button is clicked -> saves the translations.
     *
     * @private
     */
    _onSaveClick: function () {
        this._save();
    },
});

return {
    Class: TranslatorMenuBar,
};
});
