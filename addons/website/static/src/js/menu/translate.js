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
                if ($node.data('attribute')) {
                    $node.data('$node').attr($node.data('attribute'), value).trigger('translate');
                } else {
                    $node.data('$node').val(value).trigger('translate');
                }
                $node.trigger('change');
            });
            $group.append($label).append($input);
        });
        return this._super.apply(this, arguments);
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

        this.translator = new EditorMenu(this, {
            wysiwygOptions: params,
            savableSelector: savableSelector,
            editableFromEditorMenu: () => {
                return $(savableSelector)
                    .not('[data-oe-readonly]');
            },
            beforeEditorActive: async () => {
                var attrs = ['placeholder', 'title', 'alt', 'value'];
                const $editable = self._getEditableArea();
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

                    $node.addClass('o_translatable_text').data('translation', translation);
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

                self.translations = [];
                self.$translations = self._getEditableArea().filter('.o_translatable_attribute, .o_translatable_text');
                self.$editables = $('.o_editable_translatable_attribute, .o_editable_translatable_text');

                self.$editables.on('change', function () {
                    self.trigger_up('rte_change', {target: this});
                });

                self._markTranslatableNodes();
                this.$translations.filter('input[type=hidden].o_translatable_input_hidden').prop('type', 'text');
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
        this._getEditableArea().prependEvent('click.translator', function (ev) {
            if (ev.ctrlKey || !$(ev.target).is(':o_editable')) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();
        });

        // attributes

        this.$translations.each(function () {
            var $node = $(this);
            var translation = $node.data('translation');
            _.each(translation, function (node, attr) {
                var trans = self._getTranlationObject(node);
                trans.value = (trans.value ? trans.value : $node.html()).replace(/[ \t\n\r]+/, ' ');
                $node.attr('data-oe-translation-state', (trans.state || 'to_translate'));
            });
        });

        this.$translations.prependEvent('mousedown.translator click.translator mouseup.translator', function (ev) {
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

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onSave: function (ev) {
        ev.stopPropagation();
    },
});

registry.category("website_navbar_widgets").add("TranslatePageMenu", {
    Widget: TranslatePageMenu,
    selector: '.o_menu_systray:has([data-action="translate"])',
});
});
