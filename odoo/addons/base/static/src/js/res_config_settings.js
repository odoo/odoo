odoo.define('base.settings', function (require) {
"use strict";

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

    init: function() {
        this.activeView = false;
        this.activeTab = false;
        this._super.apply(this, arguments);
    },

    start: function() {
        this._super.apply(this, arguments);

        var self = this;
        this.modules = [];

        _.each(this.$('.app_settings_block'),function(settingView, index) {
            var group = !$(settingView).hasClass('o_invisible_modifier');
            if(group) {
                var string = $(settingView).attr('data-string');
                var key = $(settingView).attr('data-key');
                var imgurl = self._getAppIconUrl(key);
                var view = $(settingView);
                self.modules.push({
                    key: key,
                    string: string,
                    settingView: view,
                    imgurl: imgurl,
                    order: key=== self.activeSettingTab ? 0 : index+1
                });
                view.addClass("o_hidden");
                view.prepend($("<div>").html('<img class="icon" src="'+imgurl+'"><span class="appName">'+string+'</span>').addClass('settingSearchHeader o_hidden'));
            } else {
                $(settingView).remove();
            }
        });

        this.modules = _.sortBy(this.modules,function(m){return m.order});
        var tabs = $(QWeb.render('BaseSetting.Tabs',{tabItems : this.modules}));
        tabs.appendTo(this.$(".settings_tab"));

        $.expr[':'].contains = function(a, i, m) {
            return jQuery(a).text().toUpperCase()
                .indexOf(m[3].toUpperCase()) >= 0;
        };

        this.searchText = "";
        this.searchInput = this.$('.searchInput');
        core.bus.on("DOM_updated", this, function() {
            if (!this.activeTab)
                this._moveToTab(_.findIndex(this.modules,function(m){
                    return m.key === self.activeSettingTab
                }));
        });
    },

    _getAppIconUrl: function(module) {
        return module === "general_settings" ? "/base/static/description/settings.png" : "/"+module+"/static/description/icon.png";
    },

    _moveToTab: function (index) {
        this.currentIndex = index === -1 ? 0 : (index === this.modules.length ? index-1 : index);
        if (this.currentIndex != -1) {
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

            if (config.isMobile) {
                this._activateSettingMobileTab(this.currentIndex);
            } else {
                tab.addClass("selected");
            }
        }
    },
    _activateSettingMobileTab: function (currentTab) {
        var self = this;
        var moveTo = currentTab;
        var next = moveTo + 1;
        var previous = moveTo - 1;

        this.$(".settings .app_settings_block").removeClass("previous next current before after");
        this.$(".settings_tab .tab").removeClass("previous next current before after");
        _.each(this.modules, function(module, index) {
            var tab = self.$(".tab[data-key='" + module.key + "']");
            var view = module.settingView;

            if (index == previous) {
                tab.addClass("previous");
                tab.css("margin-left", "0px");
                view.addClass("previous");
            } else if (index == next) {
                tab.addClass("next");
                tab.css("margin-left", "-" + tab.outerWidth() + "px");
                view.addClass("next");
            } else if (index < moveTo) {
                tab.addClass("before");
                tab.css("margin-left", "-" + tab.outerWidth() + "px");
                view.addClass("before");
            } else if (index == moveTo) {
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

    _onSettingTabClick: function(event) {
        if(this.searchText.length > 0) {
            this.searchInput.val('');
            this.searchText = "";
            this._searchSetting();
        }
        var settingKey = this.$(event.currentTarget).data('key');
        this._moveToTab(_.findIndex(this.modules, function(m){ return m.key === settingKey}))
    },

    _onKeyUpSearch: function(event) {
        this.searchText = this.searchInput.val();
        this.activeTab.removeClass('selected');
        if(config.isMobile) {
            this.$('.settings_tab').addClass('o_hidden');
            this.$('.settings').addClass('d-block');
        }
        this._searchSetting();
    },

    _searchSetting: function() {
        var self = this;
        this.count = 0;
        _.each(this.modules,function(module) {
            module.settingView.find('.o_setting_box').addClass('o_hidden');
            module.settingView.find('h2').addClass('o_hidden');
            module.settingView.find('.settingSearchHeader').addClass('o_hidden');
            module.settingView.find('.o_settings_container').removeClass('mt16');
            var resultSetting = module.settingView.find("label:contains('" + self.searchText + "')");
            if (resultSetting.length > 0) {
                resultSetting.each(function() {
                    $(this).closest('.o_setting_box').removeClass('o_hidden');
                    $(this).html(self._wordHighlighter($(this).html(),self.searchText));
                });
                module.settingView.find('.settingSearchHeader').removeClass('o_hidden');
                module.settingView.removeClass('o_hidden');
            } else {
                ++self.count;
            }
        });
        this.count === _.size(this.modules) ? this.$('.notFound').removeClass('o_hidden') : this.$('.notFound').addClass('o_hidden');
        if(this.searchText.length == 0) {
            this._resetSearch();
        }
    },

    _wordHighlighter: function(text,word) {
        if (text.indexOf('highlighter') !== -1) {
            text = text.replace('<span class="highlighter">', "");
            text = text.replace("</span>", "");
        }
        var match = text.search(new RegExp(word, "i"));
        word = text.substring(match, match + word.length);
        var hilitedWord = "<span class='highlighter'>" + word + '</span>';
        return text.replace(word,hilitedWord);
    },

    _resetSearch: function() {
        this.searchInput.val("");
        _.each(this.modules,function(module) {
            module.settingView.addClass('o_hidden');
            module.settingView.find('.o_setting_box').removeClass('o_hidden');
            module.settingView.find('h2').removeClass('o_hidden');
            module.settingView.find('.settingSearchHeader').addClass('o_hidden');
            module.settingView.find('.o_settings_container').addClass('mt16');
        });
        this.activeTab.removeClass('o_hidden').addClass('selected');
        this.activeView.removeClass('o_hidden');
        if(config.isMobile) {
            this.$('.settings_tab').removeClass('o_hidden');
            this.$('.settings').removeClass('d-block');
        }
    },

    _handleAttributes: function ($el, node) {
        this._super.apply(this, arguments);
        if (node.attrs.placeholder) {
            $el.attr('placeholder', node.attrs.placeholder);
        }
    },
});

var BaseSettingController = FormController.extend({
    custom_events: _.extend({}, FormController.prototype.custom_events, {}),

    init: function () {
        this._super.apply(this, arguments);
        this.renderer.activeSettingTab = this.initialState.context.module;
    },
});

var BaseSettingView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Renderer: BaseSettingRenderer,
        Controller: BaseSettingController,
    }),

    getRenderer: function (parent, state) {
        return new BaseSettingRenderer(parent, state, this.rendererParams);
    }
});

view_registry.add('base_settings', BaseSettingView);

return {
    Renderer: BaseSettingRenderer,
    Controller: BaseSettingController,
};
});
