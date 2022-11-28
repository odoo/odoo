/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { initializeDesignTabCss } from "mass_mailing.design_constants";
import { toInline } from "web_editor.convertInline";
import { loadBundle, loadJS } from "@web/core/assets";
import { qweb } from 'web.core';
import { useService } from "@web/core/utils/hooks";
import { buildQuery } from "web.rpc";
import { HtmlField } from "@web_editor/js/backend/html_field";
import { getWysiwygClass } from 'web_editor.loader';
import { device } from 'web.config';
import { MassMailingMobilePreviewDialog } from "./mass_mailing_mobile_preview";
import { getRangePosition } from '@web_editor/js/editor/odoo-editor/src/utils/utils';

const {
    onWillStart,
    useEffect,
    useSubEnv,
    onWillUpdateProps,
} = owl;

export class MassMailingHtmlField extends HtmlField {
    setup() {
        super.setup();

        useSubEnv({
            onWysiwygReset: this._resetIframe.bind(this),
        });
        this.action = useService('action');
        this.rpc = useService('rpc');
        this.dialog = useService('dialog');

        // Load html2canvas for toInline.
        onWillStart(() => loadJS('/web_editor/static/lib/html2canvas.js'));

        onWillUpdateProps(() => {
            if (this.props.record.data.mailing_model_id && this.wysiwyg) {
                this._hideIrrelevantTemplates();
            }
        });

        useEffect(() => {
            const listener = () => {
                this._lastClickInIframe = false;
            };
            document.addEventListener('mousedown', listener, true);

            return () => document.removeEventListener('mousedown', listener, true);
        }, () => []);
    }

    get wysiwygOptions() {
        return {
            ...super.wysiwygOptions,
            onIframeUpdated: () => this.onIframeUpdated(),
            snippets: 'mass_mailing.email_designer_snippets',
            resizable: false,
            defaultDataForLinkTools: { isNewWindow: true },
            toolbarTemplate: 'mass_mailing.web_editor_toolbar',
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

        if (this.wysiwyg.$iframeBody.find('.o_basic_theme').length) {
            this.wysiwyg.$iframeBody.find('*').css('font-family', '');
        }

        const $editable = this.wysiwyg.getEditable();
        const initialHtml = $editable.html();
        await this.wysiwyg.cleanForSave();
        await this.wysiwyg.saveModifiedImages(this.$content);

        await super.commitChanges();

        const $editorEnable = $editable.closest('.editor_enable');
        $editorEnable.removeClass('editor_enable');
        // Prevent history reverts.
        this.wysiwyg.odooEditor.observerUnactive('toInline');
        await toInline($editable, this.cssRules, this.wysiwyg.$iframe);
        this.wysiwyg.odooEditor.observerActive('toInline');
        const inlineHtml = $editable.html();
        $editorEnable.addClass('editor_enable');
        this.wysiwyg.odooEditor.resetContent(initialHtml);

        const fieldName = this.props.inlineField;
        return this.props.record.update({[fieldName]: this._unWrap(inlineHtml)});
    }
    async startWysiwyg(...args) {
        await super.startWysiwyg(...args);

        await loadBundle({
            jsLibs: [
                '/mass_mailing/static/src/js/mass_mailing_link_dialog_fix.js',
                '/mass_mailing/static/src/js/mass_mailing_snippets.js',
                '/mass_mailing/static/src/snippets/s_masonry_block/options.js',
                '/mass_mailing/static/src/snippets/s_media_list/options.js',
                '/mass_mailing/static/src/snippets/s_showcase/options.js',
                '/mass_mailing/static/src/snippets/s_rating/options.js',
            ],
        });

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

        this.wysiwyg.odooEditor.document.addEventListener('mousedown', () => {
            this._lastClickInIframe = true;
        }, true);

        this.onIframeUpdated();
    }

    async _onSnippetsLoaded() {
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

        const rpcQuery = buildQuery({
            model: 'mailing.mailing',
            method: 'action_fetch_favorites',
            args: args,
        })
        // Templates taken from old mailings
        const result = await this.rpc(rpcQuery.route, rpcQuery.params);
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

        if (device.isMobile) {
            $snippetsSideBar.hide();
            this.$content.attr('style', 'padding-left: 0px !important');
        }

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
                title: this.env._t("Mobile Preview"),
                preview: mailingHtml.body.innerHTML,
            }, {
                onClose: () => $previewBtn.prop('disabled', false),
            });
        });

        if (!this._themeParams) {
            // Initialize theme parameters.
            this._themeClassNames = "";
            this._themeParams = _.map($themes, (theme) => {
                const $theme = $(theme);
                const name = $theme.data("name");
                const classname = "o_" + name + "_theme";
                this._themeClassNames += " " + classname;
                const imagesInfo = _.defaults($theme.data("imagesInfo") || {}, {
                    all: {}
                });
                for (const info of Object.values(imagesInfo)) {
                    _.defaults(info, imagesInfo.all, {
                        module: "mass_mailing",
                        format: "jpg"
                    });
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
            $themes.parent().remove();
        }

        if (!this._themeParams.length) {
            return;
        }

        const themesParams = [...this._themeParams];

        // Create theme selection screen and check if it must be forced opened.
        // Reforce it opened if the last snippet is removed.
        const $themeSelectorNew = $(qweb.render("mass_mailing.theme_selector_new", {
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

            this._switchImages(themeParams, $snippets);

            const $editable = this.wysiwyg.$editable.find('.o_editable');
            this.$editorMessageElements = $editable
                .not('[data-editor-message]')
                .attr('data-editor-message', this.env._t('DRAG BUILDING BLOCKS HERE'));
            $editable.filter(':empty').attr('contenteditable', false);

            // Wait the next tick because some mutation have to be processed by
            // the Odoo editor before resetting the history.
            setTimeout(() => {
                this.wysiwyg.historyReset();

                // The selection has been lost when switching theme.
                const document = this.wysiwyg.odooEditor.document;
                const selection = document.getSelection();
                const p = this.wysiwyg.odooEditor.editable.querySelector('p');
                if (p) {
                    const range = document.createRange();
                    range.setStart(p, 0);
                    range.setEnd(p, 0);
                    selection.removeAllRanges();
                    selection.addRange(range);
                }
            }, 0);
        });

        // Remove the mailing from the favorites list
        $themeSelectorNew.on('click', '.o_mail_template_preview i.o_mail_template_remove_favorite', async (ev) => {
            ev.stopPropagation();
            ev.preventDefault();

            const $target = $(ev.currentTarget);
            const mailingId = $target.data('id');

            const rpcQuery = buildQuery({
                model: 'mailing.mailing',
                method: 'action_remove_favorite',
                args: [mailingId],
            })
            const action = await this.rpc(rpcQuery.route, rpcQuery.params);

            this.action.doAction(action);

            $target.parents('.o_mail_template_preview').remove();
        });

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

        this.wysiwyg.$iframeBody.find('.iframe-utils-zone').removeClass('d-none');
        if (this.env.mailingFilterTemplates && this.wysiwyg) {
            this._hideIrrelevantTemplates();
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
    _hideIrrelevantTemplates() {
        const iframeContent = this.wysiwyg.$iframe.contents();

        const mailing_model_id = this.props.record.data.mailing_model_id[0];
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
            iframeContent.find('.o_mailing_template_message span').text(this.props.record.data.mailing_model_id[1]);
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
            _.each(themesParams, function (themeParams) {
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
        this.wysiwyg.trigger('reload_snippet_dropzones');
        this.onIframeUpdated();
        this.wysiwyg.odooEditor.historyStep(true);
        // The value of the field gets updated upon editor blur. If for any
        // reason, the selection was not in the editable before modifying
        // another field, ensure that the value is properly set.
        this._switchingTheme = true;
        await this.commitChanges();
        this._switchingTheme = false;
    }
    async _getWysiwygClass() {
        return getWysiwygClass({moduleName: 'mass_mailing.wysiwyg'});
    }
    _onWysiwygBlur() {
        if (!this._lastClickInIframe) {
            super._onWysiwygBlur();
        }
    }
}

MassMailingHtmlField.props = {
    ...standardFieldProps,
    ...HtmlField.props,
    filterTemplates: { type: Boolean, optional: true },
    inlineField: { type: String, optional: true },
    iframeHtmlClass: { type: String, optional: true },
};

MassMailingHtmlField.displayName = _lt("Email");
MassMailingHtmlField.extractProps = (...args) => {
    const [{ attrs }] = args;
    const htmlProps = HtmlField.extractProps(...args);
    return {
        ...htmlProps,
        filterTemplates: attrs.options.filterTemplates,
        inlineField: attrs.options['inline-field'],
        iframeHtmlClass: attrs['iframeHtmlClass'],
    };
};

registry.category("fields").add("mass_mailing_html", MassMailingHtmlField);
