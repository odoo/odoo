odoo.define('website.theme', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var session = require('web.session');
var Dialog = require('web.Dialog');
var weContext = require('web_editor.context');
var websiteNavbarData = require('website.navbar');

var QWeb = core.qweb;
var _t = core._t;

var templateDef = null;

var ThemeCustomizeDialog = Dialog.extend({
    template: 'website.theme_customize',
    events: {
        'change input[data-xmlid],input[data-enable],input[data-disable]': 'change_selection',
        'mousedown label:has(input[data-xmlid],input[data-enable],input[data-disable])': function (event) {
            var self = this;
            this.time_select = _.defer(function () {
                var input = $(event.target).find('input').length ? $(event.target).find('input') : $(event.target).parent().find('input');
                self.on_select(input, event);
            });
        },
        'click .close': 'close',
        'click': 'click',
    },
    init: function (parent, options) {
        this._super(parent, _.extend({
            title: _t("Customize this theme"),
        }, options || {}));
    },
    willStart: function () {
        if (templateDef === null) {
            templateDef = this._rpc({
                model: 'ir.ui.view',
                method: 'read_template',
                args: ['website.theme_customize', weContext.get()],
            }).then(function (data) {
                return QWeb.add_template(data);
            });
        }
        return $.when(this._super.apply(this, arguments), templateDef);
    },
    start: function () {
        var self = this;

        // Theme modal
        var $contents = this.$el.children('content');

        $contents.remove();
        this.$el.append(QWeb.render('website.modal_custom_theme'));
        var $navContents = this.$('.o_container_right');
        var $navLink = this.$(".o_el_nav_modal");

        // The big loop, to interpret xml
        _.each($contents, function (content) {
            var $content = $(content);

            // Build the nav of the panel (nav_modal)
            $navLink.append($('<li/>', {
                class: 'mb4 nav-item col-12',
            })
            .append($('<a/>', {
                text: $content.data('string'),
                href: '#' + $content.data('id'),
                'data-toggle': 'tab',
                class: 'd-block nav-link',
            })))

            // Build the main of the panel
            var $navContent = $(QWeb.render('website.multi_choice', {
                title: $content.data('title'),
                id: $content.data('id'),
                class: $content.data('class') + ' ' + 'tab-pane',
            }))
            $navContents.append($navContent);

            var $initialList = $navContent.find('.o_initial_list');
            var $options = $content.children('opt');

            var $items = $content.children();

            _.each($items, function (item) {
                var $item = $(item);

                if ($item.is('opt, font')) {
                    // Build the options template
                    var $multiChoiceLabel = $(QWeb.render('website.multi_choice_content', {
                        string: $item.data('string'),
                        xmlid: $item.data('xmlid'),
                        class: $item.data('class') + ' ' + 'text-center',
                        liclass: $item.data('liclass') + ' ' + 'mb8',
                        name: $item.data('name'),
                    }));
                    $initialList.append($multiChoiceLabel);
                    if ($item.is('opt')) {
                        $multiChoiceLabel.find('.o_multi_choice_label').prepend($('<div/>', {
                            class: $item.data('class') + ' ' + 'text-center pt8 pb4',
                            text: $item.data('string'),
                        }))
                    } else if ($item.is('font')) {
                        // Build the example font list
                        $multiChoiceLabel.find('.o_multi_choice_label').prepend($('<div/>', {
                            class: 'text-center',
                        })
                        .append($('<p/>', {
                            class: 'o_title mb8 mt16',
                            text: 'Title',
                            style: 'font-family:' + $item.data('style'),
                        }))
                        .append($('<p/>', {
                            class: 'o_body_font mb2',
                            text: 'Lorem ipsum dolor sit amet, consectetur.',
                            style: 'font-family:' + $item.data('style'),
                        })))
                    }

                } else if ($item.is('themecolor')) {
                    var $themeChildren = $item.children();
                    // Build the theme list
                    var $ColorPicker = $(QWeb.render('website.theme_color_picker', {
                        xmlid: $item.data('xmlid'),
                        name: $item.data('name'),
                    }));
                    $initialList.append($ColorPicker);

                    var $colorThemeContainer = $ColorPicker.find('.o_color_theme_list');
                    _.each($themeChildren, function(themeChild) {
                        var $themeChild = $(themeChild);

                        if($themeChild.is('color')) {
                            // var $colorThemeContainer = $initialList.find('.o_color_theme_list');
                            var $appendColorContainer = $($('<span/>',{
                                style: 'background-color: #' + $themeChild.data('color') + ';',
                                class: 'd-block',
                            }));
                            $colorThemeContainer.append($appendColorContainer);
                        }
                    });
                } else if ($item.is('more')) {
                    // add a button more and the content it will display
                    var $itemsChildren = $item.children();
                    var $more = $content.children('more');

                    $navContent.append($('<button/>', {
                        class: 'o_more_font o_more_btn mx-auto d-block mb16 mt32',
                        'data-toggle': 'collapse',
                        'data-target': "#" + $item.data('id'),
                        text: $item.data('btnstring'),
                        'type': 'button',
                    }))
                    $navContent.append($('<div/>',{
                        id: $item.data('id'),
                        class: 'collapse',
                    }))

                    if ($itemsChildren.is('colorchoice')) {
                        var $moreCustomChoice = $more.children('colorchoice');
                        var $customChoiceContainer = $navContent.find('#o_create_theme');
                        // Build the custom theme section
                        $customChoiceContainer.append(QWeb.render('website.create_theme'));
                    }
                        var name = 0;
                    _.each($itemsChildren, function(itemChild){
                        var $itemChild = $(itemChild);

                        if ($itemChild.is('listchoice')) {
                            var $moreList = $navContent.find('.collapse');
                            // Build the select to choose the fonts (in the more section)
                            var $moreUnderList = $(QWeb.render('website.more_list', {
                                id: $itemChild.data('id'),
                                selecttitle: $itemChild.data('choice'),
                                title: $itemChild.data('title'),
                                name: $itemChild.data('inputname'),
                            }));
                            $moreList.append($moreUnderList);
                            var $font = $content.find('font');

                            var $selectMore = $moreUnderList.find('.o_more_font_list');
                            // Put the options on the select list
                            _.each($font, function(fontList) {
                                var $fontList = $(fontList);

                                $selectMore.append(QWeb.render('website.list_fonts', {
                                    fontname: $fontList.data('fontname'),
                                    fontstyle: 'font-family:' + $fontList.data('fontname') + ";",
                                    name: 'listfont-' + name,
                                    xmlid: $fontList.data('xmlid' + name),
                                }));
                            });
                            name ++;
                        } else if ($itemChild.is('colorchoice')) {
                            
                            var $customChoice = $customChoiceContainer.find('.o_nav_theme');
                            var $CustomColorContent = $customChoiceContainer.find('.o_element_color');
                            // Create the navigation and the section to recive colors palets
                            $customChoice.append($('<li/>',{
                                class: $itemChild.data('liclass') + ' ' + 'text-center',
                            })
                            .append($('<a/>',{
                                'data-toggle': 'tab',
                                text: $itemChild.data('name'),
                                class: 'd-block',
                                href: '#' + $itemChild.data('link'),
                            })))

                            $CustomColorContent.append($('<div/>',{
                                id: $itemChild.data('link'),
                                class: 'o_content_palet tab-pane in',
                            }))

                            var $paletCustomTheme = $customChoiceContainer.find('.o_content_palet');
                            $paletCustomTheme.first().addClass('active');
                        }
                    });
                }
            }); 
        });

        this.timer = null;
        this.reload = false;
        this.flag = false;
        this.$inputs = this.$('input[data-xmlid],input[data-enable],input[data-disable]');
        setTimeout(function () {self.$el.addClass('in');}, 0);
        this.keydown_escape = function (event) {
            if (event.keyCode === 27) {
                self.close();
            }
        };
        // click remove the checked and data of brother if more button
        var $inputContainer = this.$('.o_more_btn').parents('.tab-pane').find('.o_initial_list');
        var $moreSelectInput = this.$('.o_more_btn').parents('.tab-pane').find('#o_more_font');
        var $collapseDiv = this.$('.o_more_btn').parents('.tab-pane').find('.collapse');

        $inputContainer.find('input').click(function() {
            $moreSelectInput.find('label').removeClass('active');
            $moreSelectInput.find('input').prop('checked', false).change();
            $collapseDiv.removeClass('show');
        });
        $moreSelectInput.find('input').click(function() {
            $inputContainer.find('label').removeClass('active');
            $inputContainer.find('input').prop('checked', false).change();
        });

        // put the first element of content and nav visible (active)
        var $navFirstChild = this.$('.o_el_nav_modal').children('li').first().find('a');
        var $containerFirstChild = this.$('.o_container_right').children('div').first();
        $navFirstChild.addClass('active');
        $containerFirstChild.addClass('active');

        var $containerInput = this.$('#colors').find('.o_initial_list');
        var $containerInputContent = $containerInput.find('input');

        if($containerInputContent.length == 0) {
            $containerInputContent.prop('checked', true).change();
        }

        var $listMore = this.$('.o_more_font_list');

        $listMore.click(function(){
            var $brotherListMore = self.$el.find('.o_container_select').find('ul');
            if($(this).hasClass('o_hover_select')){
                $brotherListMore.removeClass('o_hover_select');
            } else {
                $brotherListMore.removeClass('o_hover_select');
                $(this).addClass('o_hover_select');
            }
        });
        var $moreBtn = this.$('.o_more_btn');

        $moreBtn.click(function() {
            $(this).parents('.tab-pane').find('.o_more_font_list').removeClass('o_hover_select');
        });

        $(document).on('keydown', this.keydown_escape);
        return this.load_xml_data().then(function () {
            self.flag = true;
        });
    },
    load_xml_data: function () {
        var self = this;
        $('#theme_error').remove();
        return this._rpc({
            route: '/website/theme_customize_get',
            params: {
                xml_ids: this.get_xml_ids(this.$inputs),
            },
        }).done(function (data) {            
            self.$inputs.filter('[data-xmlid]:not([data-xmlid=""])').each(function () {
                if (!_.difference(self.get_xml_ids($(this)), data[1]).length) {
                    $(this).prop('checked', false).trigger('change', true);
                }
                if (!_.difference(self.get_xml_ids($(this)), data[0]).length) {
                    $(this).prop('checked', true).trigger('change', true);
                }
            });
            // // Display the color background choice of boxed choice
            var $addColorClick = self.$el.find('.o_add_color_choice');
            var $labelColorClick = $addColorClick.find('label');
            var $checkedColorClick = $addColorClick.find('.checked');

            if(self.$el.find('.o_add_color_choice label').hasClass('checked')){
                $checkedColorClick.parent('.o_add_color_choice').addClass('active');
            }
        }).fail(function (d, error) {
            $('body').prepend($('<div id="theme_error"/>').text(error.data.message));
        });
    },
    get_inputs: function (string) {
        return this.$inputs.filter('#'+string.split(/\s*,\s*/).join(', #'));
    },
    get_xml_ids: function ($inputs) {
        var xml_ids = [];
        $inputs.each(function () {
            if ($(this).data('xmlid') && $(this).data('xmlid').length) {
                xml_ids = xml_ids.concat($(this).data('xmlid').split(/\s*,\s*/));
            }
        });

        var $moreFontsSelect = this.$('.o_container_select').find('input').filter(':checked');

        if($moreFontsSelect.length >= 1){
            var $moreFonts = this.$('#o_more_font');
            $moreFonts.addClass('show');
        }
        return xml_ids;
    },
    update_style: function (enable, disable, reload) {
        if (this.$el.hasClass('loading')) {
            return;
        }
        this.$el.addClass('loading');

        if (!reload && session.debug !== 'assets') {
            var self = this;
            return this._rpc({
                route: '/website/theme_customize',
                params: {
                    enable: enable,
                    disable: disable,
                    get_bundle: true,
                },
            }).then(function (bundleHTML) {
                var $links = $('link[href*=".assets_frontend"]');
                var $newLinks = $(bundleHTML).filter('link');

                var linksLoaded = $.Deferred();
                var nbLoaded = 0;
                $newLinks.on('load', function (e) {
                    if (++nbLoaded >= $newLinks.length) {
                        linksLoaded.resolve();
                    }
                });
                $newLinks.on('error', function (e) {
                    linksLoaded.reject();
                    window.location.hash = 'theme=true';
                    window.location.reload();
                });

                $links.last().after($newLinks);
                return linksLoaded.then(function () {
                    $links.remove();
                    self.$el.removeClass('loading');
                });
            });
        } else {
            var href = '/website/theme_customize_reload'+
                '?href='+encodeURIComponent(window.location.href)+
                '&enable='+encodeURIComponent(enable.join(','))+
                '&disable='+encodeURIComponent(disable.join(','));
            window.location.href = href;
            return $.Deferred();
        }

    },
    enable_disable: function ($inputs, enable) {
        $inputs.each(function () {
            var check = $(this).prop('checked');
            var $label = $(this).closest('label');
            $(this).prop('checked', enable);
            if (enable) $label.addClass('checked');
            else $label.removeClass('checked');
            if (check !== enable) {
                $(this).change();
            }
        });
    },
    change_selection: function (event, init_mode) {
        var self = this;
        clearTimeout(this.time_select);

        if (this.$el.hasClass('loading')) return; // prevent to change selection when css is loading

        var $option = $(event.target).is('input') ? $(event.target) : $('input', event.target),
            $options = $option,
            checkeds = $option.prop('checked'),
            checked = $option.filter(':checked');  

        this.$('label').removeClass('checked');
        if (checked) {
            var $inputs;
            if ($option.data('enable')) {
                $inputs = this.get_inputs($option.data('enable'));
                $options = $options.add($inputs.filter(':not(:checked)'));
                this.enable_disable($inputs, true);
            }
            if ($option.data('disable')) {
                $inputs = this.get_inputs($option.data('disable'));
                $options = $options.add($inputs.filter(':checked'));
                this.enable_disable($inputs, false);
            }
            $options.filter(':checked').closest('Slabel').addClass('checked');
        }
        
        var $enable = this.$inputs.filter('[data-xmlid]:checked');
        $enable.closest('label').addClass('checked');
        var $disable = this.$inputs.filter('[data-xmlid]:not(:checked)');
        $disable.closest('label').removeClass('checked');

        var $sets = this.$inputs.filter('input[data-enable]:not([data-xmlid]), input[data-disable]:not([data-xmlid])');
        $sets.each(function () {
            var $set = $(this);
            var checked = true;
            if ($set.data('enable')) {
                self.get_inputs($(this).data('enable')).each(function () {
                    if (!$(this).prop('checked')) checked = false;
                });
            }
            if ($set.data('disable')) {
                self.get_inputs($(this).data('disable')).each(function () {
                    if ($(this).prop('checked')) checked = false;
                });
            }
            if (checked) {
                $set.prop('checked', true).closest('label').addClass('checked');
            } else {
                $set.prop('checked', false).closest('label').removeClass('checked');
            }
            $set.trigger('update');
        });

        // // Display the color background choice of boxed choice
        var $addColorClick = $('.o_add_color_choice');
        var $labelColorClick = $addColorClick.find('label');
        var $checkedColorClick = $addColorClick.find('.checked');

        this.$('.o_add_color_choice').removeClass('active');

        if($('.o_add_color_choice label').hasClass('checked')){
            $checkedColorClick.parent('.o_add_color_choice').addClass('active');
        }

        if (this.flag && $option.data('reload') && document.location.href.match(new RegExp( $option.data('reload') ))) {
            this.reload = true;
        }
        //Reload the page  with a click to apply scss
        clearTimeout(this.timer);
        if (this.flag) {
            this.timer = _.defer(function () {
                if (!init_mode) self.on_select($options, event);
                self.update_style(self.get_xml_ids($enable), self.get_xml_ids($disable), self.reload);
                self.reload = false;
            });
        } else {
            this.timer = _.defer(function () {
                if (!init_mode) self.on_select($options, event);
                self.reload = false;
            });
        }
    },
    /* Method call when the user change the selection or click on an input
     * @values: all changed inputs
     */
    on_select: function ($inputs, event) {
        clearTimeout(this.time_select);
    },
    click: function (event) {
        if (!$(event.target).closest('#theme_customize_modal > *').length) {
            this.close();
        }
    },
    close: function () {
        var self = this;
        $(document).off('keydown', this.keydown_escape);
        $('#theme_error').remove();
        $('link[href*=".assets_"]').removeAttr('data-loading');
        this.$el.removeClass('in');
        this.$el.addClass('out');
        setTimeout(function () {self.destroy();}, 500);
    }
});

var ThemeCustomizeMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    actions: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.actions || {}, {
        customize_theme: '_openThemeCustomizeDialog',
    }),

    /**
     * Automatically opens the theme customization dialog if the corresponding
     * hash is in the page URL.
     *
     * @override
     */
    start: function () {
        var def;
        if ((window.location.hash || '').indexOf('theme=true') > 0) {
            def = this._openThemeCustomizeDialog();
            window.location.hash = '';
        }
        return $.when(this._super.apply(this, arguments), def);
    },

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Instantiates and opens the theme customization dialog.
     *
     * @private
     * @returns {Deferred}
     */
    _openThemeCustomizeDialog: function () {
        return new ThemeCustomizeDialog(this).open();
    },
});

websiteNavbarData.websiteNavbarRegistry.add(ThemeCustomizeMenu, '#theme_customize');

return ThemeCustomizeDialog;

});