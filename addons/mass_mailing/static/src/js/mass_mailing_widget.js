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
    ],

    custom_events: _.extend({}, FieldHtml.prototype.custom_events, {
        snippets_loaded: '_onSnippetsLoaded',
    }),

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        if (!this.nodeOptions.snippets) {
            this.nodeOptions.snippets = 'mass_mailing.email_designer_snippets';
        }

        // All the code related to this __extraAssetsForIframe variable is an
        // ugly hack to restore mass mailing options in stable versions. The
        // whole logic has to be refactored as soon as possible...
        this.__extraAssetsForIframe = [{
            jsLibs: ['/mass_mailing/static/src/js/mass_mailing_snippets.js'],
        }];
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
    commitChanges: function () {
        var self = this;
        if (config.isDebug() && this.mode === 'edit') {
            var layoutInfo = $.summernote.core.dom.makeLayoutInfo(this.wysiwyg.$editor);
            $.summernote.pluginEvents.codeview(undefined, undefined, layoutInfo, false);
        }
        if (this.mode === 'readonly' || !this.isRendered) {
            return this._super();
        }
        var fieldName = this.nodeOptions['inline-field'];

        if (this.$content.find('.o_basic_theme').length) {
            this.$content.find('*').css('font-family', '');
        }

        var $editable = this.wysiwyg.getEditable();

        return this.wysiwyg.saveModifiedImages(this.$content).then(function () {
            return self.wysiwyg.save().then(function (result) {
                self._isDirty = result.isDirty;

                convertInline.attachmentThumbnailToLinkImg($editable);
                convertInline.fontToImg($editable);
                convertInline.classToStyle($editable);

                // fix outlook image rendering bug
                _.each(['width', 'height'], function(attribute) {
                    $editable.find('img[style*="width"], img[style*="height"]').attr(attribute, function(){
                        return $(this)[attribute]();
                    }).css(attribute, function(){
                        return $(this).get(0).style[attribute] || 'auto';
                    });
                });

                self.trigger_up('field_changed', {
                    dataPointID: self.dataPointID,
                    changes: _.object([fieldName], [self._unWrap($editable.html())])
                });
                self.wysiwyg.setValue(result.html);

                if (self._isDirty && self.mode === 'edit') {
                    return self._doAction();
                }
            });
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
     * Returns true if must force the user to choose a theme.
     *
     * @private
     * @returns {Boolean}
     */
    _checkIfMustForceThemeChoice: function () {
        var firstChoice = this._editableAreaIsEmpty();
        this.$content.closest('body').toggleClass("o_force_mail_theme_choice", firstChoice);
        return firstChoice;
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
        this._isFromInline = !!this.value;
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
    },
    /**
     * Switch themes or import first theme.
     *
     * @private
     * @param {Boolean} firstChoice true if this is the first chosen theme (going from no theme to a theme)
     * @param {Object} themeParams
     */
    _switchThemes: function (firstChoice, themeParams) {
        if (!themeParams || this.switchThemeLast === themeParams) {
            return;
        }
        this.switchThemeLast = themeParams;

        this.$content.closest('body').removeClass(this._allClasses).addClass(themeParams.className);

        var $old_layout = this.$content.find('.o_layout');

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
            $new_wrapper = $('<table/>', {
                class: 'o_mail_wrapper'
            });
            $newWrapperContent = $('<td/>', {
                class: 'o_mail_no_options o_mail_wrapper_td oe_structure'
            });
            $new_wrapper.append($('<tr/>').append(
                $('<td/>', {
                    class: 'o_mail_no_resize o_not_editable',
                    contenteditable: 'false'
                }),
                $newWrapperContent,
                $('<td/>', {
                    class: 'o_mail_no_resize o_not_editable',
                    contenteditable: 'false'
                })
            ));
        }
        var $newLayout = $('<div/>', {
            class: 'o_layout ' + themeParams.className
        }).append($new_wrapper);

        var $contents;
        if (firstChoice) {
            $contents = themeParams.template;
        } else if ($old_layout.length) {
            $contents = ($old_layout.hasClass('oe_structure') ? $old_layout : $old_layout.find('.oe_structure').first()).contents();
        } else {
            $contents = this.$content.find('.o_editable').contents();
        }

        $newWrapperContent.append($contents);
        this._switchImages(themeParams, $newWrapperContent);
        this.$content.find('.o_editable').empty().append($newLayout);
        $old_layout.remove();

        if (firstChoice) {
            $newWrapperContent.find('*').addBack()
                .contents()
                .filter(function () {
                    return this.nodeType === 3 && this.textContent.match(/\S/);
                }).parent().addClass('o_default_snippet_text');

            if (themeParams.name == 'basic') {
                this.$content.focusIn();
            }
        }
        this.wysiwyg.trigger('reload_snippet_dropzones');
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onLoadWysiwyg: function () {
        if (this._isFromInline) {
            this._fromInline();
        }
        if (this.snippetsLoaded) {
            this._onSnippetsLoaded(this.snippetsLoaded);
        }
        this._super();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetsLoaded: function (ev) {
        var self = this;
        if (!this.$content) {
            this.snippetsLoaded = ev;
            return;
        }
        var $snippetsSideBar = ev.data;
        var $themes = $snippetsSideBar.find("#email_designer_themes").children();
        var $snippets = $snippetsSideBar.find(".oe_snippet");
        var $snippets_menu = $snippetsSideBar.find("#snippets_menu");

        for (const button of $snippets_menu.get(0).children) {
            if (!button.hasAttribute('tabindex') && !button.hasAttribute('accesskey')) {
                button.style.display = 'none';
            }
        }

        if (config.device.isMobile) {
            $snippetsSideBar.hide();
            this.$content.attr('style', 'padding-left: 0px !important');
        }

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
        var $dropdown = $(core.qweb.render("mass_mailing.theme_selector", {
            themes: themesParams
        })).dropdown();

        var firstChoice = this._checkIfMustForceThemeChoice();

        /**
         * Add proposition to install enterprise themes if not installed.
         */
        var $mail_themes_upgrade = $dropdown.find(".o_mass_mailing_themes_upgrade");
        $mail_themes_upgrade.on("click", function (e) {
            e.stopImmediatePropagation();
            e.preventDefault();
            self.do_action("mass_mailing.action_mass_mailing_configuration");
        });

        /**
         * Switch theme when a theme button is hovered. Confirm change if the theme button
         * is pressed.
         */
        var selectedTheme = false;
        $dropdown.on("mouseenter", ".dropdown-item", function (e) {
            if (firstChoice) {
                return;
            }
            e.preventDefault();
            var themeParams = themesParams[$(e.currentTarget).index()];
            self._switchThemes(firstChoice, themeParams);
        });
        $dropdown.on("mouseleave", ".dropdown-item", function (e) {
            self._switchThemes(false, selectedTheme);
        });
        $dropdown.on("click", '[data-toggle="dropdown"]', function (e) {
            var $menu = $dropdown.find('.dropdown-menu');
            var isVisible = $menu.hasClass('show');
            if (isVisible) {
                e.preventDefault();
                e.stopImmediatePropagation();
                $menu.removeClass('show');
            }
        });

        $dropdown.on("click", ".dropdown-item", function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var themeParams = themesParams[$(e.currentTarget).index()];
            if (firstChoice) {
                self._switchThemes(firstChoice, themeParams);
                self.$content.closest('body').removeClass("o_force_mail_theme_choice");
                firstChoice = false;

                if ($mail_themes_upgrade.length) {
                    $dropdown.remove();
                    $snippets_menu.empty();
                }
            }

            self._switchImages(themeParams, $snippets);

            selectedTheme = themeParams;

            // Notify form view
            self.wysiwyg.getEditable().trigger('change');
            $dropdown.find('.dropdown-menu').removeClass('show');
            $dropdown.find('.dropdown-item.selected').removeClass('selected');
            $dropdown.find('.dropdown-item:eq(' + themesParams.indexOf(selectedTheme) + ')').addClass('selected');
        });

        // Prevent expansion of drop-down while clicking on empty area during theme selection
        $dropdown.on("click", ".dropdown-menu", function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
        });

        /**
         * If the user opens the theme selection screen, indicates which one is active and
         * saves the information...
         * ... then when the user closes check if the user confirmed its choice and restore
         * previous state if this is not the case.
         */
        $dropdown.on("shown.bs.dropdown", function () {
            selectedTheme = self._getSelectedTheme(themesParams);
            $dropdown.find(".dropdown-item").removeClass("selected").filter(function () {
                return ($(this).has(".o_thumb[style=\"" + "background-image: url(" + (selectedTheme && selectedTheme.img) + "_small.png)" + "\"]").length > 0);
            }).addClass("selected");
        });
        $dropdown.on("hidden.bs.dropdown", function () {
            self._switchThemes(firstChoice, selectedTheme);
        });

        /**
         * On page load, check the selected theme and force switching to it (body needs the
         * theme style for its edition toolbar).
         */
        selectedTheme = this._getSelectedTheme(themesParams);
        if (selectedTheme) {
            this.$content.closest('body').addClass(selectedTheme.className);
            $dropdown.find('.dropdown-item:eq(' + themesParams.indexOf(selectedTheme) + ')').addClass('selected');
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

        $dropdown.insertAfter($snippets_menu);
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
