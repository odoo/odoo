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

        // Need all of this in that order so that:
        // - the element is visible and can be enabled and the onFocus method is
        //   called each time.
        // - the element is hidden afterwards so it does not take space in the
        //   DOM, same as the overlay which may make a scrollbar appear.
        this.fakeThemeEl.classList.remove('d-none');
        const editor = await this._activateSnippet($(this.fakeThemeEl));
        this.fakeThemeEl.classList.add('d-none');
        editor.toggleOverlay(false);

        this._updateLeftPanelContent({
            tab: this.tabs.THEME,
        });
    },
});
});
