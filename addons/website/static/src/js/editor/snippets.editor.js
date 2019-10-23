odoo.define('website.snippet.editor', function (require) {
'use strict';

const weSnippetEditor = require('web_editor.snippet.editor');
const ThemeCustomizationMenu = require('website.theme');

weSnippetEditor.Class.include({
    events: _.extend({}, weSnippetEditor.Class.prototype.events, {
        'click .o_we_customize_theme_btn': '_onThemeTabClick',
    }),
    tabs: _.extend({}, weSnippetEditor.Class.prototype.tabs, {
        THEME: 'theme',
    }),

    /**
     * @override
     */
    start: function () {
        const prom1 = this._super(...arguments);
        this.themeCustomizationMenu = new ThemeCustomizationMenu(this);
        const prom2 = this.themeCustomizationMenu.appendTo(document.createDocumentFragment());
        return Promise.all([prom1, prom2]);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _updateLeftPanelContent: function ({content, tab}) {
        this._super(...arguments);
        this.$('.o_we_customize_theme_btn').toggleClass('active', tab === this.tabs.THEME);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onThemeTabClick: function (ev) {
        this._activateSnippet(false);
        this._updateLeftPanelContent({
            content: this.themeCustomizationMenu.el,
            tab: this.tabs.THEME,
        });
    },
});
});
