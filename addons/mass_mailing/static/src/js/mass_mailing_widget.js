odoo.define('mass_mailing.FieldHtml', function (require) {
'use strict';

var config = require('web.config');
var core = require('web.core');
var FieldHtml = require('web_editor.field.html');
var fieldRegistry = require('web.field_registry');

var QWeb = core.qweb;
var _t = core._t;


var MassMailingFieldHtml = FieldHtml.extend({
    xmlDependencies: (FieldHtml.prototype.xmlDependencies || []).concat(["/mass_mailing/static/src/xml/mass_mailing.xml"]),
    assetLibs: ['web_editor.compiled_assets_wysiwyg'],
    jsLibs: [
        '/mass_mailing/static/src/js/mass_mailing_snippets.js',
        '/mass_mailing/static/src/js/mass_mailing_link_dialog_fix.js'
    ],

    custom_events: _.extend({}, FieldHtml.prototype.custom_events, {
        snippets_loaded: '_onSnippetsLoaded',
    }),

    events: {
        'click .o_we_show_themes_btn': '_onShowThemesClick',
        'click .o_mail_theme_selector a': '_onChangeThemeClick',
        'mouseenter .o_mail_theme_selector a': '_onChangeThemeMouseEnter',
        'mouseleave .o_mail_theme_selector a': '_onChangeThemeMouseLeave',
        'click .o_we_fullscreen_btn': '_onFullScreenClick',
    },

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        if (!this.nodeOptions.snippets) {
            this.nodeOptions.snippets = 'mass_mailing.email_designer_snippets';
        }
        this.enableResizer = false;
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
        await this._super();
        if (this.mode === 'readonly' || !this.wysiwyg) {
            return;
        }

        const isDirty = this._isDirty;
        const changes = {};
        changes[this.nodeOptions['inline-field']] = await this.wysiwyg.getValue('text/mail');

        self.trigger_up('field_changed', {
            dataPointID: self.dataPointID,
            changes: changes,
        });

        if (isDirty && self.mode === 'edit') {
            return self._doAction();
        }
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _renderEdit: function () {
        if (!this.value) {
            this.value = this.recordData[this.nodeOptions['inline-field']];
        }
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    _renderReadonly: function () {
        this.value = this.recordData[this.nodeOptions['inline-field']];
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
    },
    _getContent: async function () {
        return $(this.$('jw-shadow')[0].shadowRoot).find(':not(style,link)');
    },
    /**
     * Reload snippet when choose a template.
     *
     * @override
     */
    _createWysiwygIntance: async function () {
        await this._super();
        const onCommitCheckSnippets = (params) => {
            if (params.commandNames.includes('applyTemplate')) {
                setTimeout(() => {
                    // use setTimeout to reload snippets after the redraw
                    this.wysiwyg.snippetsMenu.trigger('reload_snippet_dropzones');
                });
            }
        };
       this.wysiwyg.editor.dispatcher.registerCommandHook('@commit', onCommitCheckSnippets);
    },
    /**
     * Add templates & themes.
     *
     * @override
     */
    _getWysiwygOptions: async function () {
        this.needShadow = true;
        const options = await this._super();
        const self = this;

        // Get the snippets to have the templates and themes container.
        const $snippets = $(await this._rpc({
            model: 'ir.ui.view',
            method: 'render_public_asset',
            args: [options.snippets, {}],
            kwargs: {
                context: options.recordInfo.context,
            },
        }));

        // Create templates and themes components.
        const themes = [{
            id: 'default',
            label: _t('Default'),
            render(editor) {
                return editor.plugins.get(self.wysiwyg.JWEditorLib.Parser).parse('text/html',
                    '<div class="oe_structure"><t-placeholder/></div>');
            },
        }];
        const components = [];
        const templateConfigurations = {};
        $snippets.find("#email_designer_themes").children().each(function () {
            const $template = $(this);
            const data = $template.data();
            const templateId = 'template-' + data.name;
            const themeId = 'theme-' + data.name;
            const nowrap = !!$template.data('nowrap');
            components.push({
                id: templateId,
                async render(editor) {
                    const valueAndTheme = self._getValueAndTheme($template.html());
                    const html = '<t-theme name="' + themeId + '">' + valueAndTheme.value + '</t-theme>';
                    return editor.plugins.get(self.wysiwyg.JWEditorLib.Parser).parse('text/html', html);
                },
            });
            templateConfigurations[templateId] = {
                componentId: templateId,
                zoneId: 'editable',
                label: data.name,
                thumbnail: data.img + '_large.png',
                thumbnailZoneId: 'container',
            };
            themes.push({
                id: themeId,
                data: data,
                label: data.name,
                render(editor) {
                    const parserPlugin = editor.plugins.get(self.wysiwyg.JWEditorLib.Parser);
                    if (nowrap) {
                        return parserPlugin.parse('text/html',
                        '<div class="o_layout oe_structure" contenteditable="true"><t-placeholder/></div>');
                    } else {
                        // This wrapper structure is the only way to have a responsive
                        // and centered fixed-width content column on all mail clients
                        return parserPlugin.parse('text/html',
                        '<div class="o_layout o_' + data.name + '_theme">' +
                            '<table class="o_mail_wrapper">' +
                                '<tr>' +
                                    '<td class="o_mail_no_resize o_not_editable"></td>' +
                                    '<td class="o_mail_no_options o_mail_wrapper_td oe_structure" contenteditable="true"><t-placeholder/></td>' +
                                    '<td class="o_mail_no_resize o_not_editable"></td>' +
                                '</tr>' +
                            '</table>' +
                        '</div>');
                    }
                },
            });
        });

        // Add the templates and themes as options.
        options.templates = {
            components: components,
            templateConfigurations: templateConfigurations,
        };
        options.themes = themes;

        // Get the current theme.
        const valueAndTheme = this._getValueAndTheme(options.value);
        if (valueAndTheme.themeId) {
            options.value = '<t-theme name="' + valueAndTheme.themeId + '">' + valueAndTheme.value + '</t-theme>';
        } else if (options.value.length) {
            options.value = '<t-theme>' + valueAndTheme.value + '</t-theme>';
        }

        return options;
    },
    /**
     * Returns the selected theme, if any.
     *
     * @private
     * @param {string} value
     * @returns {[string, string]} [value, themeId]
     */
    _getValueAndTheme: function (value) {
        const $value = $(value);
        let $layout = $value.hasClass("o_layout") ? $value : $value.find(".o_layout");
        let themeId;
        if ($layout.length) {
            let $contents = $layout.contents();
            const classNameThemeId = [].find.call($layout[0].classList, className => className.includes('_theme'));
            themeId = classNameThemeId && ('theme-' + classNameThemeId.slice(2, -6));
            const $td = $contents.find('.o_mail_wrapper_td');
            if ($td.length) {
                $contents = $td.contents();
            } else if ($layout.length) {
                $contents = $layout.contents();
            }
            value = $contents.get().map(node => node.outerHTML || node.textContent).join('');
        }
        return {value: value, themeId: themeId};
    },
    /**
     * @private
     */
    _closeThemes: function () {
        this.$el.find('#o_scroll, .o_snippet_search_filter').removeClass('d-none');
        this.$el.find('.o_mail_theme_selector').addClass('d-none');
    },
    /**
     * @private
     */
    _previewUpdateTheme: function (themeId) {
        const theme = this.wysiwyg.options.themes.find(theme => theme.id === themeId);
        const $layout = $(this.el.querySelector('jw-shadow::shadow /deep/ .o_layout'));
        $layout.attr('class', 'o_layout o_' + theme.data.name + '_theme');

        const themeName = theme.data.name;
        const imagesInfo = theme.data.imagesInfo;
        $layout.find('img').each(function () {
            const $img = $(this);
            let src = $img.attr('src');

            const isLogo = src.includes('logo.');
            let moduleName = 'mass_mailing';
            let format = 'jpg';
            if (imagesInfo.logo && imagesInfo.logo.module && isLogo) {
                moduleName = imagesInfo.logo.module;
            } else if (imagesInfo.all && imagesInfo.all.module) {
                moduleName = imagesInfo.all.module;
            }
            if (imagesInfo.logo && imagesInfo.logo.format && isLogo) {
                format = imagesInfo.logo.format;
            } else if (imagesInfo.all && imagesInfo.all.format) {
                format = imagesInfo.all.format;
            }

            src = src.replace(
                /^\/[^\/]+\/(.+)\/theme_[^/]+\/(.*)\.\w+$/,
                '/' + moduleName + '/$1/theme_' + themeName + '/$2.' + format);
            $img.attr('src', src);
        });
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _onSnippetsLoaded: function () {
        this.$el.find("#email_designer_themes").remove();
        this.$el.find('#oe_snippets').append($(QWeb.render('mass_mailing.theme_selector', {themes: this.wysiwyg.options.themes})));
        this.$el.find('#snippets_menu').append($('<button type="button" class="o_we_show_themes_btn"><span>' + _t('Select a theme') + '</span></button>'));
        this.$el.find('#oe_snippets').before($('<button type="button" class="o_we_fullscreen_btn"><span class="fa fa-expand"></span></button>'));
    },
    /**
     * @private
     */
    _onChangeThemeClick: function (ev) {
        ev.preventDefault();
        const themeId = $(ev.target.closest('a')).data('id');
        const theme = this.wysiwyg.options.themes.find(theme => theme.id === themeId);
        const layoutPlugin = this.wysiwyg.editor.plugins.get(this.wysiwyg.JWEditorLib.Layout)
        const domEngine = layoutPlugin.engines.dom;
        const themeNode = domEngine.components.main[0].firstDescendant(node => node.themeName);
        if (themeId !== themeNode.themeName) {
            const changeTheme = () => {
                themeNode.themeName = themeId;

                const themeName = theme.data.name;
                const imagesInfo = theme.data.imagesInfo;
                const imageNodes = themeNode.descendants(this.wysiwyg.JWEditorLib.ImageNode);

                for (const imageNode of imageNodes) {
                    const attributes = imageNode.modifiers.get(this.wysiwyg.JWEditorLib.Attributes);
                    let src = attributes.get('src');

                    const isLogo = src.includes('logo.');
                    let moduleName = 'mass_mailing';
                    let format = 'jpg';
                    if (imagesInfo.logo && imagesInfo.logo.module && isLogo) {
                        moduleName = imagesInfo.logo.module;
                    } else if (imagesInfo.all && imagesInfo.all.module) {
                        moduleName = imagesInfo.all.module;
                    }
                    if (imagesInfo.logo && imagesInfo.logo.format && isLogo) {
                        format = imagesInfo.logo.format;
                    } else if (imagesInfo.all && imagesInfo.all.format) {
                        format = imagesInfo.all.format;
                    }

                    src = src.replace(
                        /^\/[^\/]+\/(.+)\/theme_[^/]+\/(.*)\.\w+$/,
                        '/' + moduleName + '/$1/theme_' + themeName + '/$2.' + format);
                    attributes.set('src', src);
                }
            };
            this.wysiwyg.editor.execCommand(changeTheme);
        }
        this._closeThemes();
    },
    /**
     * @private
     */
    _onChangeThemeMouseEnter: function (ev) {
        const themeId = $(ev.target.closest('a')).data('id');
        this._previewUpdateTheme(themeId);
    },
    /**
     * @private
     */
    _onChangeThemeMouseLeave: function (ev) {
        const layoutPlugin = this.wysiwyg.editor.plugins.get(this.wysiwyg.JWEditorLib.Layout)
        const domEngine = layoutPlugin.engines.dom;
        const themeNode = domEngine.components.main[0].firstDescendant(node => node.themeName);
        this._previewUpdateTheme(themeNode.themeName);
    },
    /**
     * @private
     */
    _onFullScreenClick: function (ev) {
        if (this.el.classList.contains('jw-fullscreen')) {
           document.body.classList.remove('jw-fullscreen');
           this.el.classList.remove('jw-fullscreen');
        } else {
           document.body.classList.add('jw-fullscreen');
           this.el.classList.add('jw-fullscreen');
        }
    },
    /**
     * @private
     */
    _onShowThemesClick: function () {
        const $mailThemeSelector = this.$el.find('.o_mail_theme_selector');
        const $panels = this.$el.find('#o_scroll, .o_snippet_search_filter, .o_we_customize_panel');
        if ($mailThemeSelector.hasClass('d-none')) {
            $mailThemeSelector.removeClass('d-none');
            $panels.addClass('d-none');
        } else {
            $mailThemeSelector.addClass('d-none');
            $panels.removeClass('d-none');
        }
        this.$el.one('click', '.o_we_add_snippet_btn, .o_we_customize_snippet_btn',  () => this._closeThemes());
    },
    /**
     * @override
     * @param {MouseEvent} ev
     */
    _onTranslate: function () {
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
