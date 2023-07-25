odoo.define('web_editor.wysiwyg.multizone.translate', function (require) {
'use strict';

var core = require('web.core');
var webDialog = require('web.Dialog');
var WysiwygMultizone = require('web_editor.wysiwyg.multizone');
var rte = require('web_editor.rte');
var Dialog = require('wysiwyg.widgets.Dialog');
var websiteNavbarData = require('website.navbar');

var _t = core._t;


var RTETranslatorWidget = rte.Class.extend({
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
            });
        }
        return this._super($el, context, withLang === undefined ? true : withLang);
    },
});

var AttributeTranslateDialog = Dialog.extend({
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
        this.translation = $(node).data('translation');
    },
    /**
     * @override
     */
    start: function () {
        var $group = $('<div/>', {class: 'form-group'}).appendTo(this.$el);
        _.each(this.translation, function (node, attr) {
            var $node = $(node);
            var $label = $('<label class="col-form-label"></label>').text(attr);
            var $input = $('<input class="form-control"/>').val($node.html());
            $input.on('change keyup', function () {
                var value = $input.val();
                $node.html(value).trigger('change', node);
                $node.data('$node').attr($node.data('attribute'), value).trigger('translate');
                $node.trigger('change');
            });
            $group.append($label).append($input);
        });
        return this._super.apply(this, arguments);
    }
});

// Used to translate the text of `<select/>` options since it should not be
// possible to interact with the content of `.o_translation_select` elements.
const SelectTranslateDialog = Dialog.extend({
    /**
     * @constructor
     */
    init: function (parent, options) {
        this._super(parent, {
            ...options,
            title: _t("Translate Selection Option"),
            buttons: [
                {text: _t("Close"), click: this.save}
            ],
        });
        this.optionEl = this.options.targetEl;
        this.translationObject = this.optionEl.closest('[data-oe-translation-id]');
    },
    /**
     * @override
     */
    start: function () {
        const inputEl = document.createElement('input');
        inputEl.className = 'form-control my-3';
        inputEl.value = this.optionEl.textContent;
        inputEl.addEventListener('keyup', () => {
            this.optionEl.textContent = inputEl.value;
            const translationUpdated = inputEl.value !== this.optionEl.dataset.initialTranslationValue;
            this.translationObject.classList.toggle('o_dirty', translationUpdated);
            this.optionEl.classList.toggle('oe_translated', translationUpdated);
        });
        this.el.appendChild(inputEl);
        return this._super(...arguments);
    },
});

var WysiwygTranslate = WysiwygMultizone.extend({
    custom_events: _.extend({}, WysiwygMultizone.prototype.custom_events || {}, {
        ready_to_save: '_onSave',
        rte_change: '_onChange',
    }),

    /**
     * @override
     * @param {string} options.lang
     */
    init: function (parent, options) {
        this.lang = options.lang;
        options.recordInfo = _.defaults({
                context: {lang: this.lang}
            }, options.recordInfo, options);
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        // Hacky way to keep the top editor toolbar in translate mode for now
        this.$webEditorTopEdit = $('<div id="web_editor-top-edit"></div>').prependTo(document.body);
        this.options.toolbarHandler = this.$webEditorTopEdit;
        this.editor = new (this.Editor)(this, Object.assign({Editor: RTETranslatorWidget}, this.options));
        this.$editor = this.editor.rte.editable();
        var promise = this.editor.prependTo(this.$editor[0].ownerDocument.body);

        return promise.then(function () {
            self._relocateEditorBar();
            var attrs = ['placeholder', 'title', 'alt'];
            const $editable = self._getEditableArea();
            _.each(attrs, function (attr) {
                $editable.filter('[' + attr + '*="data-oe-translation-id="]').filter(':empty, input, select, textarea, img').each(function () {
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

            // Hack: we add a temporary element to handle option's text
            // translations from the linked <select/>. The final values are
            // copied to the original element right before save.
            $editable.filter('[data-oe-translation-id] > select').each((index, select) => {
                // Keep the default width of the translation `<span/>`.
                select.parentElement.classList.remove('o_is_inline_editable');
                const selectTranslationEl = document.createElement('div');
                selectTranslationEl.className = 'o_translation_select';
                const optionNames = [...select.options].map(option => option.text);
                optionNames.forEach(option => {
                    const optionEl = document.createElement('div');
                    optionEl.textContent = option;
                    optionEl.dataset.initialTranslationValue = option;
                    optionEl.className = 'o_translation_select_option';
                    selectTranslationEl.appendChild(optionEl);
                });
                select.before(selectTranslationEl);
            });

            self.translations = [];
            self.$editables_attr = self._getEditableArea().filter('.o_translatable_attribute');
            self.$editables_attribute = $('.o_editable_translatable_attribute');

            self.$editables_attribute.on('change', function () {
                self.trigger_up('rte_change', {target: this});
            });

            self._markTranslatableNodes();
        });
    },
    /**
     * @override
     */
    destroy: function () {
        this._super(...arguments);
        this.$webEditorTopEdit.remove();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {Boolean}
     */
    isDirty: function () {
        return this._super() || this.$editables_attribute.hasClass('o_dirty');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Return the editable area.
     *
     * @override
     * @returns {JQuery}
     */
    _getEditableArea: function () {
        var $editables = this._super();
        return $editables.add(this.$editables_attribute);
    },
    /**
     * Return an object describing the linked record.
     *
     * @override
     * @param {Object} options
     * @returns {Object} {res_id, res_model, xpath}
     */
    _getRecordInfo: function (options) {
        options = options || {};
        var recordInfo = this._super(options);
        var $editable = $(options.target).closest(this._getEditableArea());
        if (!$editable.length) {
            $editable = $(this._getFocusedEditable());
        }
        recordInfo.context.lang = this.lang;
        recordInfo.translation_id = $editable.data('oe-translation-id')|0;
        return recordInfo;
    },
    /**
     * @override
     * @returns {Object} the summernote configuration
     */
    _editorOptions: function () {
        var options = this._super();
        options.toolbar = [
            // todo: hide this feature for field (data-oe-model)
            ['font', ['bold', 'italic', 'underline', 'clear']],
            ['fontsize', ['fontsize']],
            ['color', ['color']],
            // keep every time
            ['history', ['undo', 'redo']],
        ];
        return options;
    },
    /**
     * Called when text is edited -> make sure text is not messed up and mark
     * the element as dirty.
     *
     * @override
     * @param {Jquery Event} [ev]
     */
    _onChange: function (ev) {
        var $node = $(ev.data.target);
        if (!$node.length) {
            return;
        }
        $node.find('div,p').each(function () { // remove P,DIV elements which might have been inserted because of copy-paste
            var $p = $(this);
            $p.after($p.html()).remove();
        });
        var trans = this._getTranlationObject($node[0]);
        const updated = trans.value !== $node.html().replace(/[ \t\n\r]+/, ' ');
        $node.toggleClass('o_dirty', updated);
        const $target = $node.data('$node');
        if ($target) {
            $target.toggleClass('oe_translated', updated);
        }
    },
    /**
     * Returns a translation object.
     *
     * @private
     * @param {Node} node
     * @returns {Object}
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
        this._getEditableArea().each(function () {
            var $node = $(this);
            var trans = self._getTranlationObject(this);
            trans.value = (trans.value ? trans.value : $node.html() ).replace(/[ \t\n\r]+/, ' ');
        });
        this._getEditableArea().prependEvent('click.translator', function (ev) {
            if (ev.ctrlKey || !$(ev.target).is(':o_editable')) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();
        });

        // attributes

        this.$editables_attr.each(function () {
            var $node = $(this);
            var translation = $node.data('translation');
            _.each(translation, function (node, attr) {
                var trans = self._getTranlationObject(node);
                trans.value = (trans.value ? trans.value : $node.html() ).replace(/[ \t\n\r]+/, ' ');
                trans.state = node.dataset.oeTranslationState;
                $node.attr('data-oe-translation-state', (trans.state || 'to_translate'));
            });
        });

        this.$editables_attr
            .add(this._getEditableArea().filter('.o_translation_select_option'))
            .prependEvent('mousedown.translator click.translator mouseup.translator', function (ev) {
                if (ev.ctrlKey) {
                    return;
                }
                ev.preventDefault();
                ev.stopPropagation();
                if (ev.type !== 'mousedown') {
                    return;
                }

                const targetEl = ev.target;
                if (targetEl.closest('.o_translation_select')) {
                    new SelectTranslateDialog(self, {size: 'medium', targetEl}).open();
                } else {
                    new AttributeTranslateDialog(self, {}, targetEl).open();
                }
            });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onSave: function (ev) {
        ev.stopPropagation();
        // Adapt translation values for `select` > `options`s and remove all
        // temporary `.o_translation_select` elements.
        for (const optionsEl of this.el.querySelectorAll('.o_translation_select')) {
            const selectEl = optionsEl.nextElementSibling;
            const translatedOptions = optionsEl.children;
            const selectOptions = selectEl.tagName === 'SELECT' ? [...selectEl.options] : [];
            if (selectOptions.length === translatedOptions.length) {
                selectOptions.map((option, i) => {
                    option.text = translatedOptions[i].textContent;
                });
            }
            optionsEl.remove();
        }
    },
});

return WysiwygTranslate;
});
