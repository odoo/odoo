/** @odoo-module */
import { useService } from '@web/core/utils/hooks';
import { WebsiteEditorComponent } from '../editor/editor';
import { WebsiteDialog } from '../dialog/dialog';
import localStorage from 'web.local_storage';

const { useEffect, useRef, Component, xml } = owl;

const localStorageNoDialogKey = 'website_translator_nodialog';

export class AttributeTranslateDialog extends Component {
    setup() {
        this.title = this.env._t("Translate Attribute");

        this.formEl = useRef('form-container');

        useEffect(() => {
            this.translation = $(this.props.node).data('translation');
            const $group = $('<div/>', {class: 'mb-3'}).appendTo(this.formEl.el);
            _.each(this.translation, function (node, attr) {
                const $node = $(node);
                const $label = $('<label class="col-form-label"></label>').text(attr);
                const $input = $('<input class="form-control"/>').val($node.html());
                $input.on('change keyup', function () {
                    const value = $input.val();
                    $node.text(value).trigger('change', node);
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
        }, () => [this.props.node]);
    }
}
AttributeTranslateDialog.components = { WebsiteDialog };
AttributeTranslateDialog.template = 'website.AttributeTranslateDialog';

// Used to translate the text of `<select/>` options since it should not be
// possible to interact with the content of `.o_translation_select` elements.
export class SelectTranslateDialog extends Component {
    setup() {
        this.title = this.env._t("Translate Selection Option");
        this.inputEl = useRef('input');
        this.optionEl = this.props.node;
    }

    onInputKeyup() {
        const value = this.inputEl.el.value;
        this.optionEl.textContent = value;
        this.optionEl.classList.toggle(
            'oe_translated',
            value !== this.optionEl.dataset.initialTranslationValue
        );
    }
}
SelectTranslateDialog.components = {WebsiteDialog};
SelectTranslateDialog.template = xml`
<WebsiteDialog close="props.close"
    title="title"
    showSecondaryButton="false">
    <input
        t-ref="input"
        type="text" class="form-control my-3"
        t-att-value="optionEl.textContent or ''"
        t-on-keyup="onInputKeyup"/>
</WebsiteDialog>
`;

export class TranslatorInfoDialog extends Component {
    setup() {
        this.strongOkButton = this.env._t("Ok, never show me this again");
        this.okButton = this.env._t("Ok");
    }

    onStrongOkClick() {
        localStorage.setItem(localStorageNoDialogKey, true);
    }
}
TranslatorInfoDialog.components = { WebsiteDialog };
TranslatorInfoDialog.template = 'website.TranslatorInfoDialog';

const savableSelector = '[data-oe-translation-initial-sha], ' +
    '[data-oe-model][data-oe-id][data-oe-field], ' +
    '[placeholder*="data-oe-translation-initial-sha="], ' +
    '[title*="data-oe-translation-initial-sha="], ' +
    '[value*="data-oe-translation-initial-sha="], ' +
    'textarea:contains(data-oe-translation-initial-sha), ' +
    '[alt*="data-oe-translation-initial-sha="]';

export class WebsiteTranslator extends WebsiteEditorComponent {
    setup() {
        super.setup();

        this.dialogService = useService('dialog');

        this.wysiwygOptions.enableTranslation = true;
        this.wysiwygOptions.devicePreview = false;

        this.editableElements = (...args) => this._editableElements(...args);
        this.beforeEditorActive = (...args) => this._beforeEditorActive(...args);
    }

    /**
     * @override
     */
    publicRootReady() {
        if (!this.websiteService.currentWebsite.metadata.translatable) {
            this.websiteContext.translation = false;
        } else {
            this.state.showWysiwyg = true;
            const url = new URL(this.websiteService.contentWindow.location.href);
            url.searchParams.delete('edit_translations');
            this.websiteService.contentWindow.history.replaceState(this.websiteService.contentWindow.history.state, null, url);
        }
    }

    /**
     * @override
     */
    destroyAfterTransition() {
        this.state.showWysiwyg = false;
        this.websiteContext.translation = false;
    }

    get savableSelector() {
        return savableSelector;
    }

    getEditableArea() {
        return this.$wysiwygEditable.find(':o_editable').add(this.$editables);
    }

    _editableElements() {
        return $(this.websiteService.pageDocument).find(savableSelector)
            .not('[data-oe-readonly]');
    }

    getTranslationObject(nodeEl) {
        const { oeModel, oeId, oeField, oeTranslationInitialMd5 } = nodeEl.dataset;
        const id = [oeModel, oeId, oeField, oeTranslationInitialMd5].join(',');
        let translation = this.translations.filter(t => t.id === id)[0];
        if (!translation) {
            translation = { id };
            this.translations.push(translation);
        }
        return translation;
    }

    async _beforeEditorActive($wysiwygEditable) {
        this.$wysiwygEditable = $wysiwygEditable;
        const self = this;
        var attrs = ['placeholder', 'title', 'alt', 'value'];
        const $editable = this.getEditableArea();
        const translationRegex = /<span [^>]*data-oe-translation-initial-sha="([^"]+)"[^>]*>(.*)<\/span>/;
        let $edited = $();
        _.each(attrs, function (attr) {
            const attrEdit = $editable.filter('[' + attr + '*="data-oe-translation-initial-sha="]').filter(':empty, input, select, textarea, img');
            attrEdit.each(function () {
                var $node = $(this);
                var translation = $node.data('translation') || {};
                var trans = $node.attr(attr);
                var match = trans.match(translationRegex);
                var $trans = $(trans).addClass('d-none o_editable o_editable_translatable_attribute').appendTo(self.websiteService.pageDocument.body);
                $trans.data('$node', $node).data('attribute', attr);

                translation[attr] = $trans[0];
                $node.attr(attr, match[2]);
                // Using jQuery attr() to update the "value" will not change
                // what appears in the DOM and will not update the value
                // property on inputs. We need to force the right value instead
                // of the original translation <span/>.
                if (attr === 'value') {
                    $node[0].value = match[2];
                }

                $node.addClass('o_translatable_attribute').data('translation', translation);
            });
            $edited = $edited.add(attrEdit);
        });
        const textEdit = $editable.filter('textarea:contains(data-oe-translation-initial-sha)');
        textEdit.each(function () {
            var $node = $(this);
            var translation = $node.data('translation') || {};
            var trans = $node.text();
            var match = trans.match(translationRegex);
            var $trans = $(trans).addClass('d-none o_editable o_editable_translatable_text').appendTo(self.websiteService.pageDocument.body);
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
        $editable.filter('[data-oe-translation-initial-sha] > select').each((index, select) => {
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

        this.translations = [];
        this.$translations = this.getEditableArea().filter('.o_translatable_attribute, .o_translatable_text');
        this.$editables = $(this.websiteService.pageDocument).find('.o_editable_translatable_attribute, .o_editable_translatable_text');

        this.markTranslatableNodes();
        this.$translations.filter('input[type=hidden].o_translatable_input_hidden').prop('type', 'text');

        // We don't want the BS dropdown to close
        // when clicking in a element to translate
        $(this.websiteService.pageDocument).find('.dropdown-menu').on('click', '.o_editable', function (ev) {
            ev.stopPropagation();
            ev.preventDefault();
        });

        if (!localStorage.getItem(localStorageNoDialogKey)) {
            this.dialogService.add(TranslatorInfoDialog);
        }

        // Apply data-oe-readonly on nested data.
        $(this.websiteService.pageDocument).find(savableSelector)
            .filter(':has(' + savableSelector + ')')
            .attr('data-oe-readonly', true);

        const styleEl = document.createElement('style');
        styleEl.id = "translate-stylesheet";
        this.websiteService.pageDocument.head.appendChild(styleEl);

        const toTranslateColor = window.getComputedStyle(document.documentElement).getPropertyValue('--o-we-content-to-translate-color');
        const translatedColor = window.getComputedStyle(document.documentElement).getPropertyValue('--o-we-translated-content-color');

        styleEl.sheet.insertRule(`[data-oe-translation-state].o_dirty {background: ${translatedColor} !important;}`);
        styleEl.sheet.insertRule(`[data-oe-translation-state="translated"] {background: ${translatedColor} !important;}`);
        styleEl.sheet.insertRule(`[data-oe-translation-state] {background: ${toTranslateColor} !important;}`);

        const showNotification = ev => {
            let message = this.env._t('This translation is not editable.');
            if (ev.target.closest('.s_table_of_content_navbar_wrap')) {
                message = this.env._t('Translate header in the text. Menu is generated automatically.');
            }
            this.env.services.notification.add(message, {
                type: 'info',
                sticky: false,
            });
        };
        for (const translationEl of $editable) {
            if (translationEl.closest('.o_not_editable')) {
                translationEl.addEventListener('click', showNotification);
            }
            if (translationEl.closest('.s_table_of_content_navbar_wrap')) {
                // Make sure the same translation ids are used.
                const href = translationEl.closest('a').getAttribute('href');
                const headerEl = translationEl.closest('.s_table_of_content').querySelector(`${href} [data-oe-translation-initial-sha]`);
                if (headerEl) {
                    if (translationEl.dataset.oeTranslationInitialSha !== headerEl.dataset.oeTranslationInitialSha) {
                        // Use the same identifier for the generated navigation
                        // label and its associated header so that the general
                        // synchronization mechanism kicks in.
                        // The initial value is kept to be restored before save
                        // in order to keep the translation of the unstyled
                        // label distinct from the one of the header.
                        translationEl.dataset.oeTranslationSaveSha = translationEl.dataset.oeTranslationInitialSha;
                        translationEl.dataset.oeTranslationInitialSha = headerEl.dataset.oeTranslationInitialSha;
                    }
                    translationEl.classList.add('o_translation_without_style');
                }
            }
        }
    }

    markTranslatableNodes() {
        const self = this;
        this.getEditableArea().each(function () {
            var $node = $(this);
            const translation = self.getTranslationObject(this);
            translation.value = (translation.value ? translation.value : $node.html()).replace(/[ \t\n\r]+/, ' ');
        });

        // attributes

        this.$translations.each(function () {
            var $node = $(this);
            var translation = $node.data('translation');
            _.each(translation, function (node, attr) {
                var trans = self.getTranslationObject(node);
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
            .add(this.getEditableArea().filter('.o_translation_select_option'))
            .prependEvent('click.translator', (ev) => {
                const node = ev.target;
                const isSelectTranslation = !!node.closest('.o_translation_select');
                this.dialogService.add(isSelectTranslation ?
                    SelectTranslateDialog : AttributeTranslateDialog, {node});
            });
    }

    _onSave(ev) {
        ev.stopPropagation();
    }
}
