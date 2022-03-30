odoo.define('base.settings', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var core = require('web.core');
var FormView = require('web.FormView');
var FormController = require('web.FormController');
var FormRenderer = require('web.FormRenderer');
var view_registry = require('web.view_registry');
const Dialog = require('web.Dialog');

var QWeb = core.qweb;
var _t = core._t;

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

    /**
     * @override
     * overridden to show a message, informing user that there are changes
     */
    confirmChange: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            if (!self.$(".o_dirty_warning").length) {
                self.$('.o_statusbar_buttons')
                    .append($('<span/>', {text: _t("Unsaved changes"), class: 'text-muted ml-2 o_dirty_warning'}))
            }
        });
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
     * @override
     */
    displayTranslationAlert: function () {
        // Translation alerts are disabled for res.config.settings:
        // those are designed to warn user to translate field he just changed, but
        // * in res.config.settings almost all fields marked as changed (because
        //   it's not a usual record and all values are set via default_get)
        // * page is reloaded after saving, so those alerts would be visible
        //   only for short time after clicking Save
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
            tab.addClass("selected");
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
            module.settingView.find('.o_settings_container').addClass('mt16').removeClass('mb-0');
        });
        this.activeTab.removeClass('o_hidden').addClass('selected');
        this.activeView.removeClass('o_hidden');
    },

    _render: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function() {
            self._initModules();
            self._renderLeftPanel();
            self._initSearch();
        });
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
            module.settingView.find('.o_settings_container').removeClass('mt16').addClass('mb-0');

            const upperCasedSearchText = self.searchText.toUpperCase();
            const [matches, others] = _.partition(module.settingView.find(".o_form_label"),
                (e) => e.textContent.toUpperCase().includes(upperCasedSearchText));
            if (matches.length) {
                for (let result of matches) {
                    const settingBox = $(result).closest('.o_setting_box');
                    if (!settingBox.hasClass('o_invisible_modifier')) {
                        settingBox.removeClass('o_hidden');
                        self._wordHighlighter(result, upperCasedSearchText);
                    } else {
                        self.inVisibleCount++;
                    }
                }
                if (self.inVisibleCount !== matches.length) {
                    module.settingView.find('.settingSearchHeader').removeClass('o_hidden');
                    module.settingView.removeClass('o_hidden');
                }
            } else {
                ++self.count;
            }
            others.filter(e => e.firstElementChild).forEach(e => self._removeHighlight(e));
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
     * @param {HTMLElement} node
     * @param {string} upperCasedSearchText
     */
    _wordHighlighter: function (node, upperCasedSearchText) {
        const text = node.textContent;
        const startIndex = text.toUpperCase().indexOf(upperCasedSearchText);
        const endIndex = startIndex + upperCasedSearchText.length;
        $(node).empty().append(
            document.createTextNode(text.substring(0, startIndex)),
            $('<span class="highlighter">').text(text.substring(startIndex, endIndex)),
            document.createTextNode(text.substring(endIndex))
        );
    },

    /**
     * @param {HTMLElement} node
     * @private
     */
    _removeHighlight: function(node) {
        node.textContent = node.textContent;
    },
});

var BaseSettingController = FormController.extend({
    custom_events: _.extend({}, FormController.prototype.custom_events, {
        button_clicked: '_onButtonClicked',
    }),
    init: function () {
        this._super.apply(this, arguments);
        this.disableAutofocus = true;
        this.renderer.activeSettingTab = this.initialState.context.module;
        // discardingDef is used to ensure that we don't ask twice the user if
        // he wants to discard changes, when 'canBeDiscarded' is called several
        // times "in parallel"
        this.discardingDef = null;
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
    /**
     * @override
     * @returns {Promise}
     */
    canBeRemoved: function () {
        return this.discardChanges(undefined, {
            noAbandon: true,
            readonlyIfRealDiscard: true,
        });
    },
    /**
     * @override
     * @param {string} recordId
     * @returns {Promise}
     */
    canBeDiscarded: function (recordId) {
        if (this.discardingDef) {
            return this.discardingDef;
        }
        if (!this.isDirty(recordId)) {
            return Promise.resolve(false);
        }
        const message = _t('Would you like to save your changes?');
        this.discardingDef = new Promise((resolve, reject) => {
            const reset = () => {
                // enable buttons if user first save which fails because of required field missed
                // and then cancel confirmation dialog
                this._enableButtons();
                this.discardingDef = null;
            };
            const cancel = () => {
                reject();
                reset();
            };
            const dialog = Dialog.confirm(this, message, {
                title: _t('Unsaved changes'),
                buttons: [{
                    text: _t('Save'),
                    classes: 'btn-primary',
                    click: async () => {
                        this._disableButtons();
                        try {
                            // _onButtonClicked always saves the record even if
                            // it's discarded. Here we need to save before
                            // triggering the changes on the server.
                            await this.saveRecord(recordId, {
                                stayInEdit: true,
                            });
                            const record = this.model.get(recordId);
                            this.trigger_up('execute_action', {
                                action_data: {
                                    context: record.getContext({
                                        additionalContext: {},
                                    }),
                                    name: "execute",
                                    type: "object",
                                },
                                env: {
                                    context: record.getContext(),
                                    currentID: record.data.id,
                                    model: record.model,
                                    resIDs: record.res_ids,
                                },
                                on_success() {
                                    resolve(false);
                                    dialog.close();
                                },
                                on_fail() {
                                    cancel();
                                    dialog.close();
                                },
                            });
                        } catch (e) {
                            cancel();
                            dialog.close();
                        }
                    },
                }, {
                    text: _t('Discard'),
                    close: true,
                    click: () => {
                        resolve(true);
                        reset();
                    },
                }, {
                    text: _t('Stay Here'),
                    close: true,
                    click: cancel,
                }],
            });
            dialog.on('closed', this.discardingDef, cancel);
        });
        return this.discardingDef;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onButtonClicked: function (ev) {
        var self = this;
        if (ev.data.attrs.name !== 'execute' && ev.data.attrs.name !== 'cancel') {
            var recordID = ev.data.recordID;
            var _super = this._super;
            var args = arguments;
            this._discardChanges(recordID, { noAbandon: true }).then(function () {
                _super.apply(self, args);
            });
        } else {
            this._super.apply(this, arguments);
        }
    },
    /**
     * @override
     * @private
     */
    _onBeforeUnload: function () {
        // We should not save when leaving Odoo in the settings
    },

});

const BaseSettingsModel = BasicModel.extend({
    save(recordID, options) {
        const savePoint = options && options.savePoint;
        return this._super.apply(this, arguments).then(result => {
            if (!savePoint && this.localData[recordID].model === 'res.config.settings') {
                // we remove here the res_id, because the record should still be
                // considered new.  We want the web client to always perform a
                // onchange to fetch the settings anew.
                delete this.localData[recordID].res_id;
            }
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
});

view_registry.add('base_settings', BaseSettingView);

return {
    Model: BaseSettingsModel,
    Renderer: BaseSettingRenderer,
    Controller: BaseSettingController,
};
});
