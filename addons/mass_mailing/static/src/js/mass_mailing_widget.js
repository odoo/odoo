odoo.define('mass_mailing.FieldHtml', function (require) {
'use strict';

var config = require('web.config');
var core = require('web.core');
var FieldHtml = require('web_editor.field.html');
var fieldRegistry = require('web.field_registry');
var convertInline = require('web_editor.convertInline');
const { initializeDesignTabCss } = require('mass_mailing.design_constants');

var _t = core._t;


var MassMailingFieldHtml = FieldHtml.extend({
    xmlDependencies: (FieldHtml.prototype.xmlDependencies || []).concat(["/mass_mailing/static/src/xml/mass_mailing.xml"]),
    jsLibs: [
        '/mass_mailing/static/src/js/mass_mailing_link_dialog_fix.js',
        '/mass_mailing/static/src/js/mass_mailing_snippets.js',
        '/mass_mailing/static/src/snippets/s_masonry_block/options.js',
        '/mass_mailing/static/src/snippets/s_media_list/options.js',
        '/mass_mailing/static/src/snippets/s_showcase/options.js',
        '/mass_mailing/static/src/snippets/s_rating/options.js',
    ],

    custom_events: _.extend({}, FieldHtml.prototype.custom_events, {
        snippets_loaded: '_onSnippetsLoaded',
    }),
    _wysiwygSnippetsActive: true,

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        if (!this.nodeOptions.snippets) {
            this.nodeOptions.snippets = 'mass_mailing.email_designer_snippets';
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Commit the change in 'style-inline' on an other field nodeOptions:
     *
     * - inline-field: fieldName to save the html value converted into inline code
     *
     * @override
     */
    commitChanges: async function () {
        var self = this;
        if (this.mode === 'readonly' || !this.isRendered) {
            return this._super();
        }
        var fieldName = this.nodeOptions['inline-field'];

        if (this.$content.find('.o_basic_theme').length) {
            this.$content.find('*').css('font-family', '');
        }

        var $editable = this.wysiwyg.getEditable();
        await this.wysiwyg.cleanForSave();
        return this.wysiwyg.saveModifiedImages(this.$content).then(async function () {
            self._isDirty = self.wysiwyg.isDirty();
            await self._doAction();

            const $editorEnable = $editable.closest('.editor_enable');
            $editorEnable.removeClass('editor_enable');
            await convertInline.toInline($editable, self.cssRules, self.wysiwyg.$iframe);
            $editorEnable.addClass('editor_enable');

            self.trigger_up('field_changed', {
                dataPointID: self.dataPointID,
                changes: _.object([fieldName], [self._unWrap($editable.html())])
            });

            $editable.html(self.value);
            if (self._isDirty && self.mode === 'edit') {
                return self._doAction();
            }
        });
    },
    /**
     * The html_frame widget is opened in an iFrame that has its URL encoded
     * with all the key/values returned by this method.
     *
     * Some fields can get very long values and we want to omit them for the URL building.
     *
     * @override
     */
    getDatarecord: function () {
        return _.omit(this._super(), [
            'mailing_domain',
            'contact_list_ids',
            'body_html',
            'attachment_ids'
        ]);
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds automatic editor messages on drag&drop zone elements.
     *
     * @private
     */
     _addEditorMessages: function () {
        const $editable = this.wysiwyg.getEditable().find('.o_editable');
        this.$editorMessageElements = $editable
            .not('[data-editor-message]')
            .attr('data-editor-message', _t('DRAG BUILDING BLOCKS HERE'));
        $editable.filter(':empty').attr('contenteditable', false);
    },
    /**
     * @override
     */
     _createWysiwygInstance: async function () {
        await this._super(...arguments);
        // Data is removed on save but we need the mailing and its body to be
        // named so they are handled properly by the snippets menu.
        this.$content.find('.o_layout').addBack().data('name', 'Mailing');
        // We don't want to drop snippets directly within the wysiwyg.
        this.$content.removeClass('o_editable');
        initializeDesignTabCss(this.wysiwyg.getEditable());
        this.wysiwyg.getEditable().find('img').attr('loading', '');
    },
    /**
     * Returns true if the editable area is empty.
     *
     * @private
     * @param {JQuery} [$layout]
     * @returns {Boolean}
     */
    _editableAreaIsEmpty: function ($layout) {
        $layout = $layout || this.$content.find(".o_layout");
        var $mailWrapper = $layout.children(".o_mail_wrapper");
        var $mailWrapperContent = $mailWrapper.find('.o_mail_wrapper_td');
        if (!$mailWrapperContent.length) { // compatibility
            $mailWrapperContent = $mailWrapper;
        }
        var value;
        if ($mailWrapperContent.length > 0) {
            value = $mailWrapperContent.html();
        } else if ($layout.length) {
            value = $layout.html();
        } else {
            value = this.wysiwyg.getValue();
        }
        var blankEditable = "<p><br></p>";
        return value === "" || value === blankEditable;
    },
    /**
     * @override
     */
    _renderEdit: function () {
        this._wysiwygSnippetsActive = !$(this.value).is('.o_layout.o_basic_theme');
        if (!this.value) {
            this.value = this.recordData[this.nodeOptions['inline-field']];
        }
        return this._super.apply(this, arguments);
    },

    /**
     * @override
     * @returns {JQuery}
     */
    _renderTranslateButton: function () {
        var fieldName = this.nodeOptions['inline-field'];
        if (_t.database.multi_lang && this.record.fields[fieldName].translate && this.res_id) {
            return $('<button>', {
                    type: 'button',
                    'class': 'o_field_translate fa fa-globe btn btn-primary',
                })
                .on('click', this._onTranslate.bind(this));
        }
        return $();
    },
    /**
     * Returns the selected theme, if any.
     *
     * @private
     * @param {Object} themesParams
     * @returns {false|Object}
     */
    _getSelectedTheme: function (themesParams) {
        var $layout = this.$content.find(".o_layout");
        var selectedTheme = false;
        if ($layout.length !== 0) {
            _.each(themesParams, function (themeParams) {
                if ($layout.hasClass(themeParams.className)) {
                    selectedTheme = themeParams;
                }
            });
        }
        return selectedTheme;
    },
    /**
     * Swap the previous theme's default images with the new ones.
     * (Redefine the `src` attribute of all images in a $container, depending on the theme parameters.)
     *
     * @private
     * @param {Object} themeParams
     * @param {JQuery} $container
     */
    _switchImages: function (themeParams, $container) {
        if (!themeParams) {
            return;
        }
        $container.find("img").each(function () {
            var $img = $(this);
            var src = $img.attr("src");

            var m = src.match(/^\/web\/image\/\w+\.s_default_image_(?:theme_[a-z]+_)?(.+)$/);
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
        });
    },
    /**
     * Switch themes or import first theme.
     *
     * @private
     * @param {Object} themeParams
     */
    _switchThemes: function (themeParams) {
        if (!themeParams || this.switchThemeLast === themeParams) {
            return;
        }
        this.switchThemeLast = themeParams;

        this.$lastContent = this.$content.find('.o_mail_wrapper_td').contents();

        this.$content.closest('body').removeClass(this._allClasses).addClass(themeParams.className);

        const old_layout = this.$content.find('.o_layout')[0];

        var $new_wrapper;
        var $newWrapperContent;
        if (themeParams.nowrap) {
            $new_wrapper = $('<div/>', {
                class: 'oe_structure'
            });
            $newWrapperContent = $new_wrapper;
        } else {
            // This wrapper structure is the only way to have a responsive
            // and centered fixed-width content column on all mail clients
            $new_wrapper = $('<div/>', {
                class: 'container o_mail_wrapper o_mail_regular oe_unremovable',
            });
            $newWrapperContent = $('<div/>', {
                class: 'col o_mail_no_options o_mail_wrapper_td bg-white oe_structure o_editable'
            });
            $new_wrapper.append($('<div class="row"/>').append($newWrapperContent));
        }
        var $newLayout = $('<div/>', {
            class: 'o_layout oe_unremovable oe_unmovable bg-200 ' + themeParams.className,
            style: themeParams.layoutStyles,
            'data-name': 'Mailing',
        }).append($new_wrapper);

        const $contents = themeParams.template;
        $newWrapperContent.append($contents);
        this._switchImages(themeParams, $newWrapperContent);
        old_layout && old_layout.remove();
        this.$content.empty().append($newLayout);

        $newWrapperContent.find('*').addBack()
            .contents()
            .filter(function () {
                return this.nodeType === 3 && this.textContent.match(/\S/);
            }).parent().addClass('o_default_snippet_text');

        if (themeParams.name === 'basic') {
            this.$content[0].focus();
        }
        initializeDesignTabCss(this.wysiwyg.getEditable());
        this.wysiwyg.trigger('reload_snippet_dropzones');
        this.trigger_up('iframe_updated', { $iframe: this.wysiwyg.$iframe });
        this.wysiwyg.odooEditor.historyStep(true);
        this._setValue(this._getValue());
    },

    /**
     * @private
     * @override
     */
    _toggleCodeView: function ($codeview) {
        this._super(...arguments);
        if ($codeview.hasClass('d-none')) {
            this.trigger_up('iframe_updated', { $iframe: this.wysiwyg.$iframe });
        }
    },

    /**
     * @override
     */
    _getWysiwygOptions: function () {
        const options = this._super.apply(this, arguments);
        options.resizable = false;
        options.defaultDataForLinkTools = { isNewWindow: true };
        options.wysiwygAlias = 'mass_mailing.wysiwyg';
        if (!this._wysiwygSnippetsActive) {
            delete options.snippets;
        }
        // Add the commandBar (powerbox) option to open the Dynamic Placeholder
        // generator.
        options.powerboxCommands = [
            {
                category: _t('Marketing Tools'),
                name: _t('Dynamic Placeholder'),
                priority: 10,
                description: _t('Insert personalized content'),
                fontawesome: 'fa-magic',
                callback: () => {
                    const baseModel =
                        this.recordData && this.recordData.mailing_model_real
                            ? this.recordData.mailing_model_real
                            : undefined;
                    if (baseModel) {
                        // The method openDynamicPlaceholder need to be triggered
                        // after the focus from powerBox prevalidate.
                        setTimeout(() => {
                            this.openDynamicPlaceholder(baseModel);
                        });
                    }
                },
            }];

        options.powerboxFilters = [this._filterPowerBoxCommands.bind(this)];

        return options;
    },
    /**
     * Prevent usage of the dynamic placeholder command inside widgets
     * containing background images ( cover & masonry ).
     *
     * We cannot use dynamic placeholder in block containing background images
     * because the email processing will flatten the text into the background
     * image and this case the dynamic placeholder cannot be dynamic anymore.
     *
     * @param {Array} commands commands available in this wysiwyg
     * @returns {Array} commands which can be used after the filter was applied
     */
    _filterPowerBoxCommands: function (commands) {
        let selectionIsInForbidenSnippet = false;
        if (this.wysiwyg && this.wysiwyg.odooEditor) {
            const selection = this.wysiwyg.odooEditor.document.getSelection();
            selectionIsInForbidenSnippet = this.wysiwyg.closestElement(
                selection.anchorNode,
                'div[data-snippet="s_cover"], div[data-snippet="s_masonry_block"]'
            );
        }
        return selectionIsInForbidenSnippet ? commands.filter((o) => o.title !== "Dynamic Placeholder") : commands;
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onLoadWysiwyg: function () {
        // Let the global hotkey manager know about our iframe.
        this.call('hotkey', 'registerIframe', this.wysiwyg.$iframe[0]);

        if (this.snippetsLoaded) {
            this._onSnippetsLoaded(this.snippetsLoaded);
        }
        this._super();
        this.wysiwyg.odooEditor.observerFlush();
        this.wysiwyg.odooEditor.historyReset();
        this.wysiwyg.$iframeBody.addClass('o_mass_mailing_iframe');
        this.trigger_up('iframe_updated', { $iframe: this.wysiwyg.$iframe });
    },
    /**
     * @private
     * @param {boolean} activateSnippets
     */
    _restartWysiwygInstance: async function (activateSnippets = true) {
        this.wysiwyg.destroy();
        this.$el.empty();
        this._wysiwygSnippetsActive = activateSnippets;
        await this._createWysiwygInstance();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetsLoaded: async function (ev) {
        var self = this;
        if (this.wysiwyg.snippetsMenu && $(window.top.document).find('.o_mass_mailing_form_full_width')[0]) {
            // In full width form mode, ensure the snippets menu's scrollable is
            // in the form view, not in the iframe.
            this.wysiwyg.snippetsMenu.$scrollable = this.$el.closestScrollable();
            // Ensure said scrollable keeps its scrollbar at all times to
            // prevent the scrollbar from appearing at awkward moments (ie: when
            // previewing an option)
            this.wysiwyg.snippetsMenu.$scrollable.css('overflow-y', 'scroll');
        }
        if (!this.$content) {
            this.snippetsLoaded = ev;
            return;
        }

        this.wysiwyg.$iframeBody.find('.iframe-utils-zone').addClass('d-none');

        // Filter the fetched templates based on the current model
        const args = this.nodeOptions.filterTemplates
            ? [[['mailing_model_id', '=', this.recordData.mailing_model_id.res_id]]]
            : [];

        // Templates taken from old mailings
        const result = await this._rpc({
            model: 'mailing.mailing',
            method: 'action_fetch_favorites',
            args: args,
        });
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

        var $snippetsSideBar = ev.data;
        var $themes = $snippetsSideBar.find("#email_designer_themes").children();
        var $snippets = $snippetsSideBar.find(".oe_snippet");
        var selectorToKeep = '.o_we_external_history_buttons, .email_designer_top_actions';
        // Overide `d-flex` class which style is `!important`
        $snippetsSideBar.find(`.o_we_website_top_actions > *:not(${selectorToKeep})`).attr('style', 'display: none!important');

        if (config.device.isMobile) {
            $snippetsSideBar.hide();
            this.$content.attr('style', 'padding-left: 0px !important');
        }

        if (!odoo.debug) {
            $snippetsSideBar.find('.o_codeview_btn').hide();
        }
        this._$codeview = this.wysiwyg.$iframe.contents().find('textarea.o_codeview');
        $snippetsSideBar.on('click', '.o_codeview_btn', () => this._toggleCodeView(this._$codeview));

        if ($themes.length === 0) {
            return;
        }

        /**
         * Initialize theme parameters.
         */
        this._allClasses = "";
        var themesParams = _.map($themes, function (theme) {
            var $theme = $(theme);
            var name = $theme.data("name");
            var classname = "o_" + name + "_theme";
            self._allClasses += " " + classname;
            var imagesInfo = _.defaults($theme.data("imagesInfo") || {}, {
                all: {}
            });
            _.each(imagesInfo, function (info) {
                info = _.defaults(info, imagesInfo.all, {
                    module: "mass_mailing",
                    format: "jpg"
                });
            });
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

        /**
         * Create theme selection screen and check if it must be forced opened.
         * Reforce it opened if the last snippet is removed.
         */
        const $themeSelectorNew = $(core.qweb.render("mass_mailing.theme_selector_new", {
            themes: themesParams,
            templates: templatesParams,
            modelName: this.recordData.mailing_model_id.data.display_name || '',
        }));


        let firstChoice = this._editableAreaIsEmpty();
        if (firstChoice) {
            $themeSelectorNew.appendTo(this.wysiwyg.$iframeBody);
        }

        let selectedTheme = false;
        const selectTheme = themeParams => {
            self._switchImages(themeParams, $snippets);
            selectedTheme = themeParams;

            // Invalidate previous content.
            self.$lastContent = undefined;
        };

        $themeSelectorNew.on('click', '.dropdown-item', async (e) => {
            e.preventDefault();
            e.stopImmediatePropagation();

            const themeName = $(e.currentTarget).attr('id');

            const themeParams = [...themesParams, ...templatesParams].find(theme => theme.name === themeName);

            if (themeParams.name === "basic") {
                await this._restartWysiwygInstance(false);
            }
            this._switchThemes(themeParams);
            this.$content.closest('body').removeClass("o_force_mail_theme_choice");

            $themeSelectorNew.remove();

            selectTheme(themeParams);
            this._addEditorMessages();
            // Wait the next tick because some mutation have to be processed by
            // the Odoo editor before resetting the history.
            setTimeout(() => {
                this.wysiwyg.historyReset();
            }, 0);
        });

        // Remove the mailing from the favorites list
        $themeSelectorNew.on('click', '.o_mail_template_preview i.o_mail_template_remove_favorite', async (ev) => {
            ev.stopPropagation();
            ev.preventDefault();

            const $target = $(ev.currentTarget);
            const mailingId = $target.data('id');

            const action = await this._rpc({
                model: 'mailing.mailing',
                method: 'action_remove_favorite',
                args: [mailingId],
            });

            this.do_action(action);

            $target.parents('.o_mail_template_preview').remove();
        });

        /**
         * On page load, check the selected theme and force switching to it (body needs the
         * theme style for its edition toolbar).
         */
        selectedTheme = this._getSelectedTheme(themesParams);
        if (selectedTheme) {
            this.$content.closest('body').addClass(selectedTheme.className);
            this._switchImages(selectedTheme, $snippets);
        } else if (this.$content.find('.o_layout').length) {
            themesParams.push({
                name: 'o_mass_mailing_no_theme',
                className: 'o_mass_mailing_no_theme',
                img: "",
                template: this.$content.find('.o_layout').addClass('o_mass_mailing_no_theme').clone().find('oe_structure').empty().end().html().trim(),
                nowrap: true,
                get_image_info: function () {}
            });
            selectedTheme = this._getSelectedTheme(themesParams);
        }

        this.wysiwyg.$iframeBody.find('.iframe-utils-zone').removeClass('d-none');

        this.trigger_up('themes_loaded');
    },
    /**
     * @override
     * @param {MouseEvent} ev
     */
    _onTranslate: function (ev) {
        this.trigger_up('translate', {
            fieldName: this.nodeOptions['inline-field'],
            id: this.dataPointID,
            isComingFromTranslationAlert: false,
        });
    },
});

fieldRegistry.add('mass_mailing_html', MassMailingFieldHtml);

return MassMailingFieldHtml;

});
