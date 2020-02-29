odoo.define('website.snippet.editor', function (require) {
'use strict';

const weSnippetEditor = require('web_editor.snippet.editor');
const wSnippetOptions = require('website.editor.snippets.options');

const FontFamilyPickerUserValueWidget = wSnippetOptions.FontFamilyPickerUserValueWidget;

weSnippetEditor.Class.include({
    events: _.extend({}, weSnippetEditor.Class.prototype.events, {
        'click .o_we_customize_theme_btn': '_onThemeTabClick',
    }),
    tabs: _.extend({}, weSnippetEditor.Class.prototype.tabs, {
        THEME: 'theme',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeSnippetTemplates: function (html) {
        const $html = $(html);
        const fontVariables = _.map($html.find('we-fontfamilypicker[data-variable]'), el => {
            return el.dataset.variable;
        });
        FontFamilyPickerUserValueWidget.prototype.fontVariables = fontVariables;

        return this._super(...arguments);
    },
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
    _onThemeTabClick: async function (ev) {
        if (!this.fakeThemeEl) {
            this.fakeThemeEl = document.createElement('theme');
            this.fakeThemeEl.dataset.name = "";
            this.el.appendChild(this.fakeThemeEl);
        }

        await this._activateSnippet($(this.fakeThemeEl));

        if (!this.themeCustomizationMenuEl) {
            this.themeCustomizationMenuEl = document.createElement('div');
            for (const node of this.customizePanel.childNodes) {
                this.themeCustomizationMenuEl.appendChild(node);
            }
        }

        this._updateLeftPanelContent({
            content: this.themeCustomizationMenuEl,
            tab: this.tabs.THEME,
        });
    },
});
});
