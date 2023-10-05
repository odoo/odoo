/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { initializeDesignTabCss } from "@mass_mailing/js/mass_mailing_design_constants"
import { toInline, getCSSRules } from "@web_editor/js/backend/convert_inline";
import { loadBundle } from "@web/core/assets";
import { renderToElement } from "@web/core/utils/render";
import { useService } from "@web/core/utils/hooks";
import { HtmlField, htmlField } from "@web_editor/js/backend/html_field";
import { MassMailingMobilePreviewDialog } from "./mass_mailing_mobile_preview";
import { getRangePosition } from '@web_editor/js/editor/odoo-editor/src/utils/utils';
import { MassMailingWysiwyg } from '@mass_mailing/js/mass_mailing_wysiwyg';
import { utils as uiUtils } from "@web/core/ui/ui_service";
import { useSubEnv, status } from "@odoo/owl";

export class MassMailingHtmlField extends HtmlField {
    static props = {
        ...standardFieldProps,
        ...HtmlField.props,
        filterTemplates: { type: Boolean, optional: true },
        inlineField: { type: String, optional: true },
        iframeHtmlClass: { type: String, optional: true },
    }
    static components = {
        ...HtmlField.components,
        Wysiwyg: MassMailingWysiwyg,
    }

    setup() {
        super.setup();

        useSubEnv({
            onWysiwygReset: this._resetIframe.bind(this),
        });
        this.action = useService('action');
        this.rpc = useService('rpc');
        this.orm = useService('orm');
        this.dialog = useService('dialog');

        useRecordObserver((record) => {
            if (record.data.mailing_model_id && this.wysiwyg) {
                this._hideIrrelevantTemplates(record);
            }
        });
    }

    get wysiwygOptions() {
        return {
            ...super.wysiwygOptions,
            onIframeUpdated: () => this.onIframeUpdated(),
            snippets: 'mass_mailing.email_designer_snippets',
            resizable: false,
            linkOptions: {
                ...super.wysiwygOptions.linkOptions,
                initialIsNewWindow: true,
            },
            toolbarOptions: {
                ...super.wysiwygOptions.toolbarOptions,
                dropDirection: 'dropup',
            },
            onWysiwygBlur: () => {
                this.commitChanges();
                this.wysiwyg.odooEditor.toolbarHide();
            },
            dropImageAsAttachment: false,
            ...this.props.wysiwygOptions,
        };
    }

    /**
     * @param {HTMLElement} popover
     * @param {Object} position
     * @override
     */
    positionDynamicPlaceholder(popover, position) {
        const editable = this.wysiwyg.$iframe ? this.wysiwyg.$iframe[0] : this.wysiwyg.$editable[0];
        const relativeParentPosition = editable.getBoundingClientRect();

        let topPosition = relativeParentPosition.top;
        let leftPosition = relativeParentPosition.left;

        const rangePosition = getRangePosition(popover, this.wysiwyg.options.document);
        topPosition += rangePosition.top;
        // Offset the popover to ensure the arrow is pointing at
        // the precise range location.
        leftPosition += rangePosition.left - 14;

        // Apply the position back to the element.
        popover.style.top = topPosition + 'px';
        popover.style.left = leftPosition + 'px';
    }

    async commitChanges() {
        if (this.props.readonly || !this.isRendered) {
            return super.commitChanges();
        }
        if (!this._isDirty()) {
            // In case there is still a pending change while committing the
            // changes from the save button, we need to wait for the previous
            // operation to finish, otherwise the "inline field" of the mass
            // mailing might not be saved.
            return this._pendingCommitChanges;
        }

        this._pendingCommitChanges = (async () => {
            const codeViewEl = this._getCodeViewEl();
            if (codeViewEl) {
                this.wysiwyg.setValue(codeViewEl.value);
            }

            if (this.wysiwyg.$iframeBody.find('.o_basic_theme').length) {
                this.wysiwyg.$iframeBody.find('*').css('font-family', '');
            }

            const $editable = this.wysiwyg.getEditable();
            this.wysiwyg.odooEditor.historyPauseSteps();
            await this.wysiwyg.cleanForSave();
            await this.wysiwyg.savePendingImages(this.$content);

            await super.commitChanges();

            const $editorEnable = $editable.closest('.editor_enable');
            $editorEnable.removeClass('editor_enable');
            // Prevent history reverts.
            this.wysiwyg.odooEditor.observerUnactive('toInline');
            const iframe = document.createElement('iframe');
            iframe.style.height = '0px';
            iframe.style.visibility = 'hidden';
            iframe.setAttribute('sandbox', 'allow-same-origin'); // Make sure no scripts get executed.
            const clonedHtmlNode = $editable[0].closest('html').cloneNode(true);
            // Replace the body to only contain the target as we do not care for
            // other elements (e.g. sidebar, toolbar, ...)
            const clonedBody = clonedHtmlNode.querySelector('body');
            const clonedIframeTarget = clonedHtmlNode.querySelector('#iframe_target');
            clonedBody.replaceChildren(clonedIframeTarget);
            clonedBody.querySelector('.iframe-utils-zone').remove();
            clonedHtmlNode.querySelectorAll('script').forEach(script => script.remove()); // Remove scripts.
            iframe.srcdoc = clonedHtmlNode.outerHTML;
            const iframePromise = new Promise((resolve) => {
                iframe.addEventListener("load", resolve);
            });
            document.body.append(iframe);
            // Wait for the css and images to be loaded.
            await iframePromise;
            const editableClone = iframe.contentDocument.querySelector('.note-editable');
            this.cssRules = this.cssRules || getCSSRules($editable[0].ownerDocument);
            await toInline($(editableClone), this.cssRules, $(iframe));
            iframe.remove();
            this.wysiwyg.odooEditor.observerActive('toInline');
            const inlineHtml = editableClone.innerHTML;
            $editorEnable.addClass('editor_enable');
            this.wysiwyg.odooEditor.historyUnpauseSteps();
            this.wysiwyg.odooEditor.historyRevertCurrentStep();

            const fieldName = this.props.inlineField;
            await this.props.record.update({[fieldName]: inlineHtml});
        })();
        return this._pendingCommitChanges;
    }
    async startWysiwyg(...args) {
        await super.startWysiwyg(...args);

        await loadBundle("mass_mailing.assets_wysiwyg");

        if (status(this) === "destroyed") {
            return;
        }

        await this._resetIframe();
    }

    async _resetIframe() {
        if (this._switchingTheme) {
            return;
        }
        this.wysiwyg.$iframeBody.find('.o_mail_theme_selector_new').remove();
        await this._onSnippetsLoaded();

        // Data is removed on save but we need the mailing and its body to be
        // named so they are handled properly by the snippets menu.
        this.wysiwyg.$iframeBody.find('.o_layout').addBack().data('name', 'Mailing');
        // We don't want to drop snippets directly within the wysiwyg.
        this.wysiwyg.$iframeBody.find('.odoo-editor-editable').removeClass('o_editable');

        initializeDesignTabCss(this.wysiwyg.getEditable());
        this.wysiwyg.getEditable().find('img').attr('loading', '');

        this.wysiwyg.odooEditor.observerFlush();
        this.wysiwyg.odooEditor.historyReset();
        this.wysiwyg.$iframeBody.addClass('o_mass_mailing_iframe');

        this.onIframeUpdated();
    }

    async _onSnippetsLoaded() {
        if (status(this) === 'destroyed') return;
        if (this.wysiwyg.snippetsMenu && $(window.top.document).find('.o_mass_mailing_form_full_width')[0]) {
            // In full width form mode, ensure the snippets menu's scrollable is
            // in the form view, not in the iframe.
            this.wysiwyg.snippetsMenu.$scrollable = this.wysiwyg.$el.closestScrollable();
            // Ensure said scrollable keeps its scrollbar at all times to
            // prevent the scrollbar from appearing at awkward moments (ie: when
            // previewing an option)
            this.wysiwyg.snippetsMenu.$scrollable.css('overflow-y', 'scroll');
        }

        // Remove the web editor menu to avoid flicker (we add it back at the
        // end of the method)
        this.wysiwyg.$iframeBody.find('.iframe-utils-zone').addClass('d-none');

        // Filter the fetched templates based on the current model
        const args = this.props.filterTemplates
            ? [[['mailing_model_id', '=', this.props.record.data.mailing_model_id[0]]]]
            : [];

        // Templates taken from old mailings
        const result = await this.orm.call('mailing.mailing', 'action_fetch_favorites', args);
        if (status(this) === 'destroyed') return;
        const templatesParams = result.map(values => {
            return {
                id: values.id,
                modelId: values.mailing_model_id[0],
                modelName: values.mailing_model_id[1],
                name: `template_${values.id}`,
                nowrap: true,
                subject: values.subject,
                template: values.body_arch,
                userId: values.user_id[0],
                userName: values.user_id[1],
            };
        });

        const $snippetsSideBar = this.wysiwyg.snippetsMenu.$el;
        const $themes = $snippetsSideBar.find("#email_designer_themes").children();
        const $snippets = $snippetsSideBar.find(".oe_snippet");
        const selectorToKeep = '.o_we_external_history_buttons, .email_designer_top_actions';
        // Overide `d-flex` class which style is `!important`
        $snippetsSideBar.find(`.o_we_website_top_actions > *:not(${selectorToKeep})`).attr('style', 'display: none!important');

        if (!odoo.debug) {
            $snippetsSideBar.find('.o_codeview_btn').hide();
        }
        const $codeview = this.wysiwyg.$iframe.contents().find('textarea.o_codeview');
        // Unbind first the event handler as this method can be called multiple time during the component life.
        $snippetsSideBar.off('click', '.o_codeview_btn');
        $snippetsSideBar.on('click', '.o_codeview_btn', () => {
            this.wysiwyg.odooEditor.observerUnactive();
            $codeview.toggleClass('d-none');
            this.wysiwyg.getEditable().toggleClass('d-none');
            this.wysiwyg.odooEditor.observerActive();

            if ($codeview.hasClass('d-none')) {
                this.wysiwyg.setValue($codeview.val());
            } else {
                $codeview.val(this.wysiwyg.getValue());
            }
            this.wysiwyg.snippetsMenu.activateSnippet(false);
            this.onIframeUpdated();
        });
        const $previewBtn = $snippetsSideBar.find('.o_mobile_preview_btn');
        $previewBtn.off('click');
        $previewBtn.on('click', () => {
            $previewBtn.prop('disabled', true); // Prevent double execution when double-clicking on the button
            let mailingHtml = new DOMParser().parseFromString(this.wysiwyg.getValue(), 'text/html');
            [...mailingHtml.querySelectorAll('a')].forEach(el => {
                el.style.setProperty('pointer-events', 'none');
            });
            this.mobilePreview = this.dialog.add(MassMailingMobilePreviewDialog, {
                title: _t("Mobile Preview"),
                preview: mailingHtml.body.innerHTML,
            }, {
                onClose: () => $previewBtn.prop('disabled', false),
            });
        });

        if (!this._themeParams) {
            // Initialize theme parameters.
            this._themeClassNames = "";
            const displayableThemes =
                uiUtils.isSmall() ?
                $themes.filter(theme => !$(theme).data("hideFromMobile")) :
                $themes;
            this._themeParams = Array.from(displayableThemes).map((theme) => {
                const $theme = $(theme);
                const name = $theme.data("name");
                const classname = "o_" + name + "_theme";
                this._themeClassNames += " " + classname;
                const imagesInfo = Object.assign({
                    all: {}
                }, $theme.data("imagesInfo") || {});
                for (const [key, info] of Object.entries(imagesInfo)) {
                    imagesInfo[key] = Object.assign({
                        module: "mass_mailing",
                        format: "jpg"
                        },
                        imagesInfo.all,
                        info
                    );
                }
                return {
                    name: name,
                    title: $theme.attr("title") || "",
                    className: classname || "",
                    img: $theme.data("img") || "",
                    template: $theme.html().trim(),
                    nowrap: !!$theme.data('nowrap'),
                    get_image_info: function (filename) {
                        if (imagesInfo[filename]) {
                            return imagesInfo[filename];
                        }
                        return imagesInfo.all;
                    },
                    layoutStyles: $theme.data('layout-styles'),
                };
            });
        }
        $themes.parent().remove();

        if (!this._themeParams.length) {
            return;
        }

        const themesParams = [...this._themeParams];

        // Create theme selection screen and check if it must be forced opened.
        // Reforce it opened if the last snippet is removed.
        const $themeSelectorNew = $(renderToElement("mass_mailing.theme_selector_new", {
            themes: themesParams,
            templates: templatesParams,
            modelName: this.props.record.data.mailing_model_id[1] || '',
        }));

        // Check if editable area is empty.
        const $layout = this.wysiwyg.$iframeBody.find(".o_layout");
        let $mailWrapper = $layout.children(".o_mail_wrapper");
        let $mailWrapperContent = $mailWrapper.find('.o_mail_wrapper_td');
        if (!$mailWrapperContent.length) {
            $mailWrapperContent = $mailWrapper;
        }
        let value;
        if ($mailWrapperContent.length > 0) {
            value = $mailWrapperContent.html();
        } else if ($layout.length) {
            value = $layout.html();
        } else {
            value = this.wysiwyg.getValue();
        }
        let blankEditable = "<p><br></p>";
        const editableAreaIsEmpty = value === "" || value === blankEditable;

        if (editableAreaIsEmpty) {
            // unfold to prevent toolbar from going over the menu
            this.wysiwyg.setSnippetsMenuFolded(false);
            $themeSelectorNew.appendTo(this.wysiwyg.$iframeBody);
        }

        $themeSelectorNew.on('click', '.dropdown-item', async (e) => {
            e.preventDefault();
            e.stopImmediatePropagation();

            const themeName = $(e.currentTarget).attr('id');

            const themeParams = [...themesParams, ...templatesParams].find(theme => theme.name === themeName);

            await this._switchThemes(themeParams);
            this.wysiwyg.$iframeBody.closest('body').removeClass("o_force_mail_theme_choice");

            $themeSelectorNew.remove();

            this.wysiwyg.setSnippetsMenuFolded(uiUtils.isSmall() || themeName === 'basic');

            this._switchImages(themeParams, $snippets);

            const $editable = this.wysiwyg.$editable.find('.o_editable');
            this.$editorMessageElements = $editable
                .not('[data-editor-message]')
                .attr('data-editor-message', _t('DRAG BUILDING BLOCKS HERE'));
            $editable.filter(':empty').attr('contenteditable', false);

            // Wait the next tick because some mutation have to be processed by
            // the Odoo editor before resetting the history.
            setTimeout(() => {
                this.wysiwyg.historyReset();

                // The selection has been lost when switching theme.
                const document = this.wysiwyg.odooEditor.document;
                const selection = document.getSelection();
                const p = this.wysiwyg.odooEditor.editable.querySelector('p');
                if (p && selection) {
                    const range = document.createRange();
                    range.setStart(p, 0);
                    range.setEnd(p, 0);
                    selection.removeAllRanges();
                    selection.addRange(range);
                }
                // mark selection done for tour testing
                $editable.addClass('theme_selection_done');
                this.onIframeUpdated();
            }, 0);
        });

        // Remove the mailing from the favorites list
        $themeSelectorNew.on('click', '.o_mail_template_preview i.o_mail_template_remove_favorite', async (ev) => {
            ev.stopPropagation();
            ev.preventDefault();

            const $target = $(ev.currentTarget);
            const mailingId = $target.data('id');

            const action = await this.orm.call('mailing.mailing', 'action_remove_favorite', [mailingId]);
            this.action.doAction(action);

            $target.parents('.o_mail_template_preview').remove();
        });

        // Clear any previous theme class before adding new one.
        this.wysiwyg.$iframeBody.closest('body').removeClass(this._themeClassNames);
        let selectedTheme = this._getSelectedTheme(themesParams);
        if (selectedTheme) {
            this.wysiwyg.$iframeBody.closest('body').addClass(selectedTheme.className);
            this._switchImages(selectedTheme, $snippets);
        } else if (this.wysiwyg.$iframeBody.find('.o_layout').length) {
            themesParams.push({
                name: 'o_mass_mailing_no_theme',
                className: 'o_mass_mailing_no_theme',
                img: "",
                template: this.wysiwyg.$iframeBody.find('.o_layout').addClass('o_mass_mailing_no_theme').clone().find('oe_structure').empty().end().html().trim(),
                nowrap: true,
                get_image_info: function () {}
            });
            selectedTheme = this._getSelectedTheme(themesParams);
        }

        this.wysiwyg.setSnippetsMenuFolded(uiUtils.isSmall() || (selectedTheme && selectedTheme.name === 'basic'));

        this.wysiwyg.$iframeBody.find('.iframe-utils-zone').removeClass('d-none');
        if (this.env.mailingFilterTemplates && this.wysiwyg) {
            this._hideIrrelevantTemplates(this.props.record);
        }
    }
    _getCodeViewEl() {
        const codeView = this.wysiwyg &&
            this.wysiwyg.$iframe &&
            this.wysiwyg.$iframe.contents().find('textarea.o_codeview')[0];
        return codeView && !codeView.classList.contains('d-none') && codeView;
    }
    /**
     * This method will take the model in argument and will hide all mailing template
     * in the mass mailing widget that do not belong to this model.
     *
     * This will also update the help message in the same widget to include the
     * new model name.
     *
     * @param {Number} modelId
     * @param {String} modelName
     *
     * @private
     */
    _hideIrrelevantTemplates(record) {
        const iframeContent = this.wysiwyg.$iframe.contents();

        const mailing_model_id = record.data.mailing_model_id[0];
        iframeContent
            .find(`.o_mail_template_preview[model-id!="${mailing_model_id}"]`)
            .addClass('d-none')
            .removeClass('d-inline-block');

        const sameModelTemplates = iframeContent
            .find(`.o_mail_template_preview[model-id="${mailing_model_id}"]`);

        sameModelTemplates
            .removeClass('d-none')
            .addClass('d-inline-block');

        // Hide or show the help message and preview wrapper based on whether there are any relevant templates
        if (sameModelTemplates.length) {
            iframeContent.find('.o_mailing_template_message').addClass('d-none');
            iframeContent.find('.o_mailing_template_preview_wrapper').removeClass('d-none');
        } else {
            iframeContent.find('.o_mailing_template_message').removeClass('d-none');
            iframeContent.find('.o_mailing_template_message span').text(record.data.mailing_model_id[1]);
            iframeContent.find('.o_mailing_template_preview_wrapper').addClass('d-none');
        }
    }
    /**
     * Returns the selected theme, if any.
     *
     * @private
     * @param {Object} themesParams
     * @returns {false|Object}
     */
    _getSelectedTheme(themesParams) {
        const $layout = this.wysiwyg.$iframeBody.find(".o_layout");
        let selectedTheme = false;
        if ($layout.length !== 0) {
            themesParams.forEach((themeParams) => {
                if ($layout.hasClass(themeParams.className)) {
                    selectedTheme = themeParams;
                }
            });
        }
        return selectedTheme;
    }
    /**
     * Swap the previous theme's default images with the new ones.
     * (Redefine the `src` attribute of all images in a $container, depending on the theme parameters.)
     *
     * @private
     * @param {Object} themeParams
     * @param {JQuery} $container
     */
    _switchImages(themeParams, $container) {
        if (!themeParams) {
            return;
        }
        for (const img of $container.find("img")) {
            const $img = $(img);
            const src = $img.attr("src");
            $img.removeAttr('loading');

            let m = src.match(/^\/web\/image\/\w+\.s_default_image_(?:theme_[a-z]+_)?(.+)$/);
            if (!m) {
                m = src.match(/^\/\w+\/static\/src\/img\/(?:theme_[a-z]+\/)?s_default_image_(.+)\.[a-z]+$/);
            }
            if (!m) {
                return;
            }

            if (themeParams.get_image_info) {
                const file = m[1];
                const imgInfo = themeParams.get_image_info(file);

                const src = imgInfo.format
                    ? `/${imgInfo.module}/static/src/img/theme_${themeParams.name}/s_default_image_${file}.${imgInfo.format}`
                    : `/web/image/${imgInfo.module}.s_default_image_theme_${themeParams.name}_${file}`;

                $img.attr('src', src);
            }
        }
    }
    /**
     * Switch themes or import first theme.
     *
     * @private
     * @param {Object} themeParams
     */
    async _switchThemes(themeParams) {
        if (!themeParams || this.switchThemeLast === themeParams) {
            return;
        }
        this.switchThemeLast = themeParams;

        this.wysiwyg.$iframeBody.closest('body').removeClass(this._themeClassNames).addClass(themeParams.className);

        const old_layout = this.wysiwyg.$editable.find('.o_layout')[0];

        let $newWrapper;
        let $newWrapperContent;
        if (themeParams.nowrap) {
            $newWrapper = $('<div/>', {
                class: 'oe_structure'
            });
            $newWrapperContent = $newWrapper;
        } else {
            // This wrapper structure is the only way to have a responsive
            // and centered fixed-width content column on all mail clients
            $newWrapper = $('<div/>', {
                class: 'container o_mail_wrapper o_mail_regular oe_unremovable',
            });
            $newWrapperContent = $('<div/>', {
                class: 'col o_mail_no_options o_mail_wrapper_td bg-white oe_structure o_editable'
            });
            $newWrapper.append($('<div class="row"/>').append($newWrapperContent));
        }
        const $newLayout = $('<div/>', {
            class: 'o_layout oe_unremovable oe_unmovable bg-200 ' + themeParams.className,
            style: themeParams.layoutStyles,
            'data-name': 'Mailing',
        }).append($newWrapper);

        const $contents = themeParams.template;
        $newWrapperContent.append($contents);
        this._switchImages(themeParams, $newWrapperContent);
        old_layout && old_layout.remove();
        this.wysiwyg.odooEditor.resetContent($newLayout[0].outerHTML);

        $newWrapperContent.find('*').addBack()
            .contents()
            .filter(function () {
                return this.nodeType === 3 && this.textContent.match(/\S/);
            }).parent().addClass('o_default_snippet_text');

        if (themeParams.name === 'basic') {
            this.wysiwyg.$editable[0].focus();
        }
        initializeDesignTabCss(this.wysiwyg.$editable);
        this.wysiwyg.snippetsMenu.reload_snippet_dropzones();
        this.onIframeUpdated();
        this.wysiwyg.odooEditor.historyStep(true);
        // The value of the field gets updated upon editor blur. If for any
        // reason, the selection was not in the editable before modifying
        // another field, ensure that the value is properly set.
        this._switchingTheme = true;
        await this.commitChanges();
        this._switchingTheme = false;
    }
    /**
     * @override
     */
    async _setupReadonlyIframe() {
        if (!this.props.record.data[this.props.name].length) {
            this.props.record.data[this.props.name] = this.props.record.data.body_html;
        }
        await super._setupReadonlyIframe();
    }
}

export const massMailingHtmlField = {
    ...htmlField,
    component: MassMailingHtmlField,
    displayName: _t("Email"),
    supportedOptions: [...htmlField.supportedOptions, {
        label: _t("Filter templates"),
        name: "filterTemplates",
        type: "boolean"
    }, {
        label: _t("Inline field"),
        name: "inline-field",
        type: "field"
    }],
    extractProps({ attrs, options }) {
        const props = htmlField.extractProps(...arguments);
        props.filterTemplates = options.filterTemplates;
        props.inlineField = options['inline-field'];
        props.iframeHtmlClass = attrs.iframeHtmlClass;
        return props;
    },
    fieldDependencies: [{ name: 'body_html', type: 'html' }],
};

registry.category("fields").add("mass_mailing_html", massMailingHtmlField);
