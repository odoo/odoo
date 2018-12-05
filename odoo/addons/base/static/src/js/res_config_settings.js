odoo.define('base.settings', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var core = require('web.core');
var config = require('web.config');
var FormView = require('web.FormView');
var FormController = require('web.FormController');
var FormRenderer = require('web.FormRenderer');
var view_registry = require('web.view_registry');

var QWeb = core.qweb;

var BaseSettingRenderer = FormRenderer.extend({
    events: _.extend({}, FormRenderer.prototype.events, {
        'click .tab': '_onSettingTabClick',
        'keyup .searchInput': '_onKeyUpSearch',
    }),

    init: function () {
        this._super.apply(this, arguments);
        this.activeView = false;
        this.activeTab = false;
    },

    start: function () {
        this._super.apply(this, arguments);
        if (config.device.isMobile) {
            core.bus.on("DOM_updated", this, function () {
                this._moveToTab(this.currentIndex || this._currentAppIndex());
            });
        }
    },

    /**
     * @override
     */
    on_attach_callback: function () {
        this._super.apply(this, arguments);
        // set default focus on searchInput
        this.searchInput.focus();
    },

    /**
     * initialize modules list.
     * remove module that restricted in groups
     * data contains
     *  {
     *     key: moduel key
     *     string: moduel string
     *     imgurl: icon url
     *  }
     *
     * @private
     */
    _initModules: function () {
        var self = this;
        this.modules = [];
        _.each(this.$('.app_settings_block'), function (settingView, index) {
            var group = !$(settingView).hasClass('o_invisible_modifier');
            var isNotApp = $(settingView).hasClass('o_not_app');
            if(group && !isNotApp) {
                var data = $(settingView).data();
                data.string = $(settingView).attr('string') || data.string;
                self.modules.push({
                    key: data.key,
                    string: data.string,
                    imgurl: self._getAppIconUrl(data.key),
                });
            } else {
                $(settingView).remove();
            }
        });
    },
    /**
     * initialize searchtext variable
     * initialize jQuery search input element
     *
     * @private
     */
    _initSearch: function () {
        this.searchInput = this.$('.searchInput');
        if (this.searchText) {
            this.searchInput.val(this.searchText);
            this._onKeyUpSearch();
        } else {
            this.searchText = "";
        }
    },
    /**
     * In mobile view behaviour is like swipe content left / right and apps tab will be shown on the top.
     * This method will set the required properties (styling and css).
     *
     * @private
     * @param {int} currentTab
     */
    _activateSettingMobileTab: function (currentTab) {
        var self = this;
        var moveTo = currentTab;
        var next = moveTo + 1;
        var previous = moveTo - 1;

        this.$(".settings .app_settings_block").removeClass("previous next current before after");
        this.$(".settings_tab .tab").removeClass("previous next current before after");
        _.each(this.modules, function (module, index) {
            var tab = self.$(".tab[data-key='" + module.key + "']");
            var view = module.settingView;

            if (index === previous) {
                tab.addClass("previous");
                tab.css("margin-left", "0px");
                view.addClass("previous");
            } else if (index === next) {
                tab.addClass("next");
                tab.css("margin-left", "-" + tab.outerWidth() + "px");
                view.addClass("next");
            } else if (index < moveTo) {
                tab.addClass("before");
                tab.css("margin-left", "-" + tab.outerWidth() + "px");
                view.addClass("before");
            } else if (index === moveTo) {
                var marginLeft = tab.outerWidth() / 2;
                tab.css("margin-left", "-" + marginLeft + "px");
                tab.addClass("current");
                view.addClass("current");
            } else if (index > moveTo) {
                tab.addClass("after");
                tab.css("margin-left", "0");
                view.addClass("after");
            }
        });
    },
    /**
     * find current app index in modules
     *
     */
    _currentAppIndex: function () {
        var self = this;
        var index = _.findIndex(this.modules, function (module) {
            return module.key === self.activeSettingTab;
        });
        return index;
    },
    /**
     * Enables swipe navigation between settings pages
     *
     * @private
     */
    _enableSwipe: function () {
        var self = this;
        this.$('.settings').swipe({
            swipeLeft: function () {
                self._moveToTab(self.currentIndex + 1);
            },
            swipeRight: function () {
                self._moveToTab(self.currentIndex - 1);
            }
        });
    },
    /**
     *
     * @private
     * @param {string} module
     * @returns {string} icon url
     */
    _getAppIconUrl: function (module) {
        return module === "general_settings" ? "/base/static/description/settings.png" : "/"+module+"/static/description/icon.png";
    },
    /**
     *
     * @private
     * @param {string} imgurl
     * @param {string} string(moduel name)
     * @returns {object}
     */
    _getSearchHeader: function (imgurl, string) {
        return $(QWeb.render('BaseSetting.SearchHeader', {
            imgurl: imgurl,
            string: string
        }));
    },
    /**
     * add placeholder attr in input element
     * @override
     * @private
     * @param {jQueryElement} $el
     * @param {Object} node
     */
    _handleAttributes: function ($el, node) {
        this._super.apply(this, arguments);
        if (node.attrs.placeholder) {
            $el.attr('placeholder', node.attrs.placeholder);
        }
    },
    /**
     * move to selected setting
     *
     * @private
     * @param {int} index
     */
    _moveToTab: function (index) {
        this.currentIndex = !index || index === -1 ? 0 : (index === this.modules.length ? index - 1 : index);
        if (this.currentIndex !== -1) {
            if (this.activeView) {
                this.activeView.addClass("o_hidden");
            }
            if (this.activeTab) {
                this.activeTab.removeClass("selected");
            }
            var view = this.modules[this.currentIndex].settingView;
            var tab = this.$(".tab[data-key='" + this.modules[this.currentIndex].key + "']");
            view.removeClass("o_hidden");
            this.activeView = view;
            this.activeTab = tab;

            if (config.device.isMobile) {
                this._activateSettingMobileTab(this.currentIndex);
            } else {
                tab.addClass("selected");
            }
        }
    },

    _onSettingTabClick: function (event) {
        this.searchInput.focus();
        if (this.searchText.length > 0) {
            this.searchInput.val('');
            this.searchText = "";
            this._searchSetting();
        }
        var settingKey = this.$(event.currentTarget).data('key');
        this._moveToTab(_.findIndex(this.modules, function (m) {
            return m.key === settingKey;
        }));
    },

    _onKeyUpSearch: function (event) {
        this.searchText = this.searchInput.val();
        this.activeTab.removeClass('selected');
        if (config.device.isMobile) {
            this.$('.settings_tab').addClass('o_hidden');
            this.$('.settings').addClass('d-block');
        }
        this._searchSetting();
    },
    /**
     * reset setting view
     *
     * @private
     */
    _resetSearch: function () {
        this.searchInput.val("");
        _.each(this.modules, function (module) {
            module.settingView.addClass('o_hidden');
            module.settingView.find('.o_setting_box').removeClass('o_hidden');
            module.settingView.find('h2').removeClass('o_hidden');
            module.settingView.find('.settingSearchHeader').addClass('o_hidden');
            module.settingView.find('.o_settings_container').addClass('mt16');
        });
        this.activeTab.removeClass('o_hidden').addClass('selected');
        this.activeView.removeClass('o_hidden');
        if (config.device.isMobile) {
            this.$('.settings_tab').removeClass('o_hidden');
            this.$('.settings').removeClass('d-block');
        }
    },

    _render: function () {
        var res = this._super.apply(this, arguments);
        this._initModules();
        this._renderLeftPanel();
        this._initSearch();
        if (config.device.isMobile) {
            this._enableSwipe();
        }
        return res;
    },

    _renderLeftPanel: function () {
        var self = this;
        _.each(this.modules, function (module) {
            module.settingView = self.$('.app_settings_block[data-key="' + module.key + '"]');
            module.settingView.addClass("o_hidden");
            module.settingView.prepend(self._getSearchHeader(module.imgurl, module.string));
        });
        this._renderTabs();
        this._moveToTab(this.currentIndex || this._currentAppIndex());
    },

    _renderTabs: function () {
        var tabs = $(QWeb.render('BaseSetting.Tabs', {tabItems : this.modules}));
        tabs.appendTo(this.$(".settings_tab"));
    },
    /**
     * search setting in DOM
     *
     * @private
     */
    _searchSetting: function () {
        var self = this;
        this.count = 0;
        _.each(this.modules, function (module) {
            self.inVisibleCount = 0;
            module.settingView.find('.o_setting_box').addClass('o_hidden');
            module.settingView.find('h2').addClass('o_hidden');
            module.settingView.find('.settingSearchHeader').addClass('o_hidden');
            module.settingView.find('.o_settings_container').removeClass('mt16');
            var resultSetting = module.settingView.find("label:containsTextLike('" + self.searchText + "')");
            if (resultSetting.length > 0) {
                resultSetting.each(function () {
                    var settingBox = $(this).closest('.o_setting_box');
                    if (!settingBox.hasClass('o_invisible_modifier')) {
                        settingBox.removeClass('o_hidden');
                        $(this).html(self._wordHighlighter($(this).html(), self.searchText));
                    } else {
                        self.inVisibleCount++;
                    }
                });
                if (self.inVisibleCount !== resultSetting.length) {
                    module.settingView.find('.settingSearchHeader').removeClass('o_hidden');
                    module.settingView.removeClass('o_hidden');
                }
            } else {
                ++self.count;
            }
        });
        this.count === _.size(this.modules) ? this.$('.notFound').removeClass('o_hidden') : this.$('.notFound').addClass('o_hidden');
        if (this.searchText.length === 0) {
            this._resetSearch();
        }
    },
    /**
     * highlight search word
     *
     * @private
     * @param {string} text
     * @param {string} word
     */
    _wordHighlighter: function (text, word) {
        if (text.indexOf('highlighter') !== -1) {
            text = text.replace('<span class="highlighter">', "");
            text = text.replace("</span>", "");
        }
        var match = text.search(new RegExp(word, "i"));
        word = text.substring(match, match + word.length);
        var hilitedWord = "<span class='highlighter'>" + word + '</span>';
        return text.replace(word, hilitedWord);
    },
});

var BaseSettingController = FormController.extend({
    init: function () {
        this._super.apply(this, arguments);
        this.disableAutofocus = true;
        this.renderer.activeSettingTab = this.initialState.context.module;
    },
    /**
     * Settings view should always be in edit mode, so we have to override
     * default behaviour
     *
     * @override
     */
    willRestore: function () {
        this.mode = 'edit';
    },
});

var BaseSettingsModel = BasicModel.extend({
    /**
     * @override
     */
    save: function (recordID) {
        var self = this;
        return this._super.apply(this, arguments).then(function (result) {
            // we remove here the res_id, because the record should still be
            // considered new.  We want the web client to always perform a
            // default_get to fetch the settings anew.
            delete self.localData[recordID].res_id;
            return result;
        });
    },
});

var BaseSettingView = FormView.extend({
    jsLibs: [],

    config: _.extend({}, FormView.prototype.config, {
        Model: BaseSettingsModel,
        Renderer: BaseSettingRenderer,
        Controller: BaseSettingController,
    }),

    /**
     * Overrides to lazy-load touchSwipe library in mobile.
     *
     * @override
    */
    init: function () {
        if (config.device.isMobile) {
            this.jsLibs.push('/web/static/lib/jquery.touchSwipe/jquery.touchSwipe.js');
        }
        this._super.apply(this, arguments);
    },
});

view_registry.add('base_settings', BaseSettingView);

return {
    Model: BaseSettingsModel,
    Renderer: BaseSettingRenderer,
    Controller: BaseSettingController,
};
});
