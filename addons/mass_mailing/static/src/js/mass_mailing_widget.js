odoo.define('mass_mailing.FieldHtml', function (require) {
'use strict';

var config = require('web.config');
var core = require('web.core');
var FieldHtml = require('web_editor.field.html');
var fieldRegistry = require('web.field_registry');
var convertInline = require('web_editor.convertInline');

var _t = core._t;


var MassMailingFieldHtml = FieldHtml.extend({
    xmlDependencies: (FieldHtml.prototype.xmlDependencies || []).concat(["/mass_mailing/static/src/xml/mass_mailing.xml"]),
    jsLibs: [
        '/mass_mailing/static/src/js/mass_mailing_link_dialog_fix.js',
        '/mass_mailing/static/src/js/mass_mailing_snippets.js',
        '/mass_mailing/static/src/snippets/s_blockquote/options.js',
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
            convertInline.toInline($editable, self.cssRules, self.wysiwyg.$iframe);
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
     _createWysiwygIntance: async function () {
        await this._super(...arguments);
        // Data is removed on save but we need the mailing and its body to be
        // named so they are handled properly by the snippets menu.
        this.$content.find('.o_layout').addBack().data('name', 'Mailing');
        // We don't want to drop snippets directly within the wysiwyg.
        this.$content.removeClass('o_editable');
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
                    'class': 'o_field_translate fa fa-globe btn btn-link',
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

            var file = m[1];
            var img_info = themeParams.get_image_info(file);

            if (img_info.format) {
                src = "/" + img_info.module + "/static/src/img/theme_" + themeParams.name + "/s_default_image_" + file + "." + img_info.format;
            } else {
                src = "/web/image/" + img_info.module + ".s_default_image_theme_" + themeParams.name + "_" + file;
            }

            $img.attr("src", src);
        });
        $container.find('.o_mail_block_cover .oe_img_bg').each(function () {
            $(this).css('background-image', `url('/mass_mailing_themes/static/src/img/theme_${themeParams.name}/s_default_image_block_banner.jpg')`);
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
        this.wysiwyg.trigger('reload_snippet_dropzones');
        this.trigger_up('iframe_updated', { $iframe: this.wysiwyg.$iframe });
        this.wysiwyg.odooEditor.historyStep(true);
    },

    /**
     * @private
     * @override
     */
    _toggleCodeView: function ($codeview) {
        this._super(...arguments);
        const isFullWidth = !!$(window.top.document).find('.o_mass_mailing_form_full_width')[0];
        $codeview.css('height', isFullWidth ? $(window).height() : '');
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
        if (this._wysiwygSnippetsActive) {
            options.wysiwygAlias = 'mass_mailing.wysiwyg';
        } else {
            delete options.snippets;
        }
        return options;
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
    _restartWysiwygIntance: async function (activateSnippets = true) {
        this.wysiwyg.destroy();
        this.$el.empty();
        this._wysiwygSnippetsActive = activateSnippets;
        await this._createWysiwygIntance();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetsLoaded: function (ev) {
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
        var $snippetsSideBar = ev.data;
        var $themes = $snippetsSideBar.find("#email_designer_themes").children();
        var $snippets = $snippetsSideBar.find(".oe_snippet");
        var selectorToKeep = '.o_we_external_history_buttons, .email_designer_top_actions';
        // Overide `d-flex` class which style is `!important`
        $snippetsSideBar.find(`.o_we_website_top_actions > *:not(${selectorToKeep})`).attr('style', 'display: none!important');
        var $snippets_menu = $snippetsSideBar.find("#snippets_menu");
        var $selectTemplateBtn = $snippets_menu.find('.o_we_select_template');

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
                className: classname || "",
                img: $theme.data("img") || "",
                template: $theme.html().trim(),
                nowrap: !!$theme.data('nowrap'),
                get_image_info: function (filename) {
                    if (imagesInfo[filename]) {
                        return imagesInfo[filename];
                    }
                    return imagesInfo.all;
                }
            };
        });
        $themes.parent().remove();

        /**
         * Create theme selection screen and check if it must be forced opened.
         * Reforce it opened if the last snippet is removed.
         */
        const $themeSelector = $(core.qweb.render("mass_mailing.theme_selector", {
            themes: themesParams
        }));
        const $themeSelectorNew = $(core.qweb.render("mass_mailing.theme_selector_new", {
            themes: themesParams
        }));


        let firstChoice = this._editableAreaIsEmpty();
        if (firstChoice) {
            $themeSelectorNew.appendTo(this.wysiwyg.$iframeBody);
        }

        /**
         * Add proposition to install enterprise themes if not installed.
         */
        var $mail_themes_upgrade = $themeSelector.find(".o_mass_mailing_themes_upgrade");
        $mail_themes_upgrade.on("click", function (e) {
            e.stopImmediatePropagation();
            e.preventDefault();
            self.do_action("mass_mailing.action_mass_mailing_configuration");
        });

        $selectTemplateBtn.on('click', () => {
            $snippetsSideBar.data('snippetMenu').activateCustomTab($themeSelector);
            /**
             * Ensure the parent of the theme selector is not used as parent for a
             * tooltip as it is overflow auto and would result in the tooltip being
             * hidden by the body of the mail.
             */
            $themeSelector.parent().addClass('o_forbidden_tooltip_parent');
            $selectTemplateBtn.addClass('active');
        });

        /**
         * Switch theme when a theme button is hovered. Confirm change if the theme button
         * is pressed.
         */
        var selectedTheme = false;
        $themeSelector.on("mouseenter", ".dropdown-item", function (e) {
            e.preventDefault();
            var themeParams = themesParams[$(e.currentTarget).index()];
            self.wysiwyg.odooEditor.automaticStepSkipStack();
            self._switchThemes(themeParams);
        });
        $themeSelector.on("mouseleave", ".dropdown-item", function (e) {
            if (self.$lastContent) {
                self._switchThemes(Object.assign({}, selectedTheme, {template: self.$lastContent}));
            } else {
                self._switchThemes(selectedTheme);
            }
        });
        $themeSelector.on("click", '[data-toggle="dropdown"]', function (e) {
            var $menu = $themeSelector.find('.dropdown-menu');
            var isVisible = $menu.hasClass('show');
            if (isVisible) {
                e.preventDefault();
                e.stopImmediatePropagation();
                $menu.removeClass('show');
            }
        });

        const selectTheme = (e) => {
            e.preventDefault();
            e.stopImmediatePropagation();
            const themeParams = themesParams[$(e.currentTarget).index()];
            self._switchImages(themeParams, $snippets);

            selectedTheme = themeParams;

            // Notify form view
            $themeSelector.find('.dropdown-item.selected').removeClass('selected');
            $themeSelector.find('.dropdown-item:eq(' + themesParams.indexOf(selectedTheme) + ')').addClass('selected');

            // Invalidate previous content.
            self.$lastContent = undefined;
        };

        $themeSelector.on("click", ".dropdown-item", selectTheme);
        $themeSelectorNew.on("click", ".dropdown-item", async (e) => {
            e.preventDefault();
            e.stopImmediatePropagation();
            const themeParams = themesParams[$(e.currentTarget).index()];

            if (themeParams.name === "basic") {
                await this._restartWysiwygIntance(false);
            }
            this._switchThemes(themeParams);
            this.$content.closest('body').removeClass("o_force_mail_theme_choice");

            $themeSelectorNew.remove();

            if ($mail_themes_upgrade.length) {
                $snippets_menu.empty();
            }

            selectTheme(e);
            this._addEditorMessages();
            // Wait the next tick because some mutation have to be processed by
            // the Odoo editor before resetting the history.
            setTimeout(() => {
                this.wysiwyg.historyReset();
            }, 0);
        });

        /**
         * On page load, check the selected theme and force switching to it (body needs the
         * theme style for its edition toolbar).
         */
        selectedTheme = this._getSelectedTheme(themesParams);
        if (selectedTheme) {
            this.$content.closest('body').addClass(selectedTheme.className);
            $themeSelector.find('.dropdown-item:eq(' + themesParams.indexOf(selectedTheme) + ')').addClass('selected');
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
