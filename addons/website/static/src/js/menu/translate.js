odoo.define('website.translateMenu', function (require) {
'use strict';

require('web.dom_ready');
var core = require('web.core');
var weDialog = require('wysiwyg.widgets.Dialog');
var Dialog = require('web.Dialog');
var EditorMenu = require('website.editMenu');
var localStorage = require('web.local_storage');
var websiteNavbarData = require('website.navbar');

const { registry } = require("@web/core/registry");

var _t = core._t;

var localStorageNoDialogKey = 'website_translator_nodialog';

var TranslatorInfoDialog = Dialog.extend({
    template: 'website.TranslatorInfoDialog',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/website/static/src/xml/translator.xml']
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

// TODO: Handle this once images are handled.
var AttributeTranslateDialog = weDialog.extend({
    /**
     * @constructor
     */
    init: function (parent, options, node) {
        this._super(parent, _.extend({
            title: _t("Translate Attribute"),
            buttons: [
                {text: _t("Close"), classes: 'btn-primary', click: this.save}
            ],
        }, options || {}));
        this.wysiwyg = options.wysiwyg;
        this.node = node;
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
                const $originalNode = $node.data('$node');
                const nodeAttribute = $node.data('attribute');
                if (nodeAttribute) {
                    $originalNode.attr(nodeAttribute, value);
                    if (nodeAttribute === 'value') {
                        $originalNode[0].value = value;
                    }
                    $originalNode.trigger('translate');
                } else {
                    $originalNode.val(value).trigger('translate');
                }
                $node.trigger('change');
                $originalNode[0].classList.add('oe_translated');
            });
            $group.append($label).append($input);
        });
        return this._super.apply(this, arguments);
    },
});

// Used to translate the text of `<select/>` options since it should not be
// possible to interact with the content of `.o_translation_select` elements.
const SelectTranslateDialog = weDialog.extend({
    /**
     * @constructor
     */
    init(parent, options) {
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
    start() {
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

const savableSelector = '[data-oe-translation-id], ' +
    '[data-oe-model][data-oe-id][data-oe-field], ' +
    '[placeholder*="data-oe-translation-id="], ' +
    '[title*="data-oe-translation-id="], ' +
    '[value*="data-oe-translation-id="], ' +
    'textarea:contains(data-oe-translation-id), ' +
    '[alt*="data-oe-translation-id="]';

var TranslatePageMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    assetLibs: ['web_editor.compiled_assets_wysiwyg', 'website.compiled_assets_wysiwyg'],

    actions: _.extend({}, websiteNavbarData.WebsiteNavbar.prototype.actions || {}, {
        edit_master: '_goToMasterPage',
        translate: '_startTranslateMode',
    }),
    custom_events: {
        ready_to_save: '_onSave',
    },

    /**
     * @override
     */
    start: function () {
        var context;
        this.trigger_up('context_get', {
            extra: true,
            callback: function (ctx) {
                context = ctx;
            },
        });
        this._mustEditTranslations = context.edit_translations;
        if (this._mustEditTranslations) {
            var url = new URL(window.location.href);
            url.searchParams.delete('edit_translations');
            window.history.replaceState({}, null, url);

            this._startTranslateMode();
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Redirects the user to the same page but in the original language and in
     * edit mode.
     *
     * @private
     * @returns {Promise}
     */
    _goToMasterPage: function () {
        var current = document.createElement('a');
        current.href = window.location.toString();
        current.search += (current.search ? '&' : '?') + 'enable_editor=1';
        // We are in translate mode, the pathname starts with '/<url_code>'. By
        // adding a trailing slash we can simply search for the first slash
        // after the language code to remove the language part.
        const startPath = (current.pathname + '/').indexOf('/', 1);
        current.pathname = current.pathname.substring(startPath);

        var link = document.createElement('a');
        link.href = '/website/lang/default';
        link.search += (link.search ? '&' : '?') + 'r=' + encodeURIComponent(current.pathname + current.search + current.hash);

        window.location = link.href;
        return new Promise(function () {});
    },
    /**
     * Redirects the user to the same page in translation mode (or start the
     * translator is translation mode is already enabled).
     *
     * @private
     * @returns {Promise}
     */
    _startTranslateMode: async function () {
        const self = this;
        if (!this._mustEditTranslations) {
            window.location.search += '&edit_translations';
            return new Promise(function () {});
        }

        const params = {
            enableTranslation: true,
            devicePreview: false,
        };

        const showNotification = ev => {
            let message = _t('This translation is not editable.');
            if (ev.target.closest('.s_table_of_content_navbar_wrap')) {
                message = _t('Translate header in the text. Menu is generated automatically.');
            }
            this.displayNotification({
                type: 'info',
                message: message,
                sticky: false,
            });
        };
        for (const translationEl of $('.o_not_editable [data-oe-translation-id]').not(':o_editable')) {
            translationEl.addEventListener('click', showNotification);
        }

        this.translator = new EditorMenu(this, {
            wysiwygOptions: params,
            savableSelector: savableSelector,
            editableFromEditorMenu: () => {
                return $(savableSelector)
                    .not('[data-oe-readonly]');
            },
            beforeEditorActive: async () => {
                const $editable = self._getEditableArea();
                // Remove styles from table of content menu entries.
                for (const el of $editable.filter('.s_table_of_content_navbar .table_of_content_link span[data-oe-translation-id]')) {
                    const text = el.textContent; // Get text from el.
                    el.textContent = text; // Replace all of el's content with that text.
                }

                var attrs = ['placeholder', 'title', 'alt', 'value'];
                const translationRegex = /<span [^>]*data-oe-translation-id="([0-9]+)"[^>]*>(.*)<\/span>/;
                let $edited = $();
                _.each(attrs, function (attr) {
                    const attrEdit = $editable.filter('[' + attr + '*="data-oe-translation-id="]').filter(':empty, input, select, textarea, img');
                    attrEdit.each(function () {
                        var $node = $(this);
                        var translation = $node.data('translation') || {};
                        var trans = $node.attr(attr);
                        var match = trans.match(translationRegex);
                        var $trans = $(trans).addClass('d-none o_editable o_editable_translatable_attribute').appendTo('body');
                        $trans.data('$node', $node).data('attribute', attr);

                        translation[attr] = $trans[0];
                        $node.attr(attr, match[2]);
                        // Using jQuery attr() to update the "value" will not change what appears in the
                        // DOM and will not update the value property on inputs. We need to force the
                        // right value instead of the original translation <span/>.
                        if (attr === 'value') {
                            $node[0].value = match[2];
                        }

                        $node.addClass('o_translatable_attribute').data('translation', translation);
                    });
                    $edited = $edited.add(attrEdit);
                });
                const textEdit = $editable.filter('textarea:contains(data-oe-translation-id)');
                textEdit.each(function () {
                    var $node = $(this);
                    var translation = $node.data('translation') || {};
                    var trans = $node.text();
                    var match = trans.match(translationRegex);
                    var $trans = $(trans).addClass('d-none o_editable o_editable_translatable_text').appendTo('body');
                    $trans.data('$node', $node);

                    translation['textContent'] = $trans[0];
                    $node.val(match[2]);
                    // Update the text content of textarea too.
                    $node[0].innerText = match[2];

                    $node.addClass('o_translatable_text').removeClass('o_text_content_invisible')
                        .data('translation', translation);
                });
                $edited = $edited.add(textEdit);

                $edited.each(function () {
                    var $node = $(this);
                    var select2 = $node.data('select2');
                    if (select2) {
                        select2.blur();
                        $node.on('translate', function () {
                            select2.blur();
                        });
                        $node = select2.container.find('input');
                    }
                });

                // Hack: we add a temporary element to handle option's text
                // translations from the linked <select/>. The final values are
                // copied to the original element right before save.
                self.selectTranslationEls = [];
                $editable.filter('[data-oe-translation-id] > select').each((index, select) => {
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
                    self.selectTranslationEls.push(selectTranslationEl);
                });

                self.translations = [];
                self.$translations = self._getEditableArea().filter('.o_translatable_attribute, .o_translatable_text');
                self.$editables = $('.o_editable_translatable_attribute, .o_editable_translatable_text');

                self.$editables.on('change', function () {
                    self.trigger_up('rte_change', {target: this});
                });

                self._markTranslatableNodes();
                this.$translations.filter('input[type=hidden].o_translatable_input_hidden').prop('type', 'text');
            },
            processRecordsCallback(record, el) {
                const tocMainEl = el.closest('.s_table_of_content_main');
                const headerEl = el.closest('h1, h2');
                if (!tocMainEl || !headerEl) {
                    return;
                }
                const headerIndex = [...tocMainEl.querySelectorAll('h1, h2')].indexOf(headerEl);
                const tocMenuEl = tocMainEl.closest('.s_table_of_content').querySelectorAll('.table_of_content_link > span')[headerIndex];
                if (tocMenuEl.textContent !== headerEl.textContent) {
                    tocMenuEl.textContent = headerEl.textContent;
                    tocMenuEl.classList.add('o_dirty');
                }
            },
        });

        // We don't want the BS dropdown to close
        // when clicking in a element to translate
        $('.dropdown-menu').on('click', '.o_editable', function (ev) {
            ev.stopPropagation();
        });

        if (!localStorage.getItem(localStorageNoDialogKey)) {
            new TranslatorInfoDialog(this.translator).open();
        }

        await this.translator.prependTo(document.body);
        // Apply data-oe-readonly on nested data.
        $(savableSelector)
            .filter(':has(' + savableSelector + ')')
            .attr('data-oe-readonly', true);
        await this.translator._startEditMode();
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
        return this.translator.wysiwyg.$editable.find(':o_editable').add(this.$editables);
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
            id = $node.data('oe-model') + ',' + $node.data('oe-id') + ',' + $node.data('oe-field');
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
            trans.value = (trans.value ? trans.value : $node.html()).replace(/[ \t\n\r]+/, ' ');
        });

        // attributes

        this.$translations.each(function () {
            var $node = $(this);
            var translation = $node.data('translation');
            _.each(translation, function (node, attr) {
                var trans = self._getTranlationObject(node);
                trans.value = (trans.value ? trans.value : $node.html()).replace(/[ \t\n\r]+/, ' ');
                trans.state = node.dataset.oeTranslationState;
                // If a node has an already translated attribute, we don't
                // need to update its state, since it can be set again as
                // "to_translate" by other attributes...
                if ($node[0].dataset.oeTranslationState === 'translated') {
                    return;
                }
                $node.attr('data-oe-translation-state', (trans.state || 'to_translate'));
            });
        });

        this.$translations
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
                    new AttributeTranslateDialog(self, {}, ev.target).open();
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
        for (const optionsEl of this.selectTranslationEls) {
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

registry.category("website_navbar_widgets").add("TranslatePageMenu", {
    Widget: TranslatePageMenu,
    selector: '.o_menu_systray:has([data-action="translate"])',
});

return {
    TranslatorInfoDialog: TranslatorInfoDialog,
    AttributeTranslateDialog: AttributeTranslateDialog,
    TranslatePageMenu: TranslatePageMenu,
};

});
