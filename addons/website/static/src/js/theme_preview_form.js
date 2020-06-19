odoo.define('website.theme_preview_form', function (require) {
"use strict";

var FormController = require('web.FormController');
var FormView = require('web.FormView');
var viewRegistry = require('web.view_registry');
var core = require('web.core');
var qweb = core.qweb;

var ThemePreviewController = FormController.extend({
    events: Object.assign({}, FormController.prototype.events, {
        'click .o_use_theme': '_onUseThemeClick',
        'click .o_switch_theme': '_onSwitchThemeClick',
        'change input[name="viewer"]': '_onSwitchButtonChange',
    }),
    /**
     * @override
     */
    start: function () {
        this.$el.addClass('o_view_form_theme_preview_controller');
        return this._super.apply(this, arguments);
    },

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * @override
     */
    renderButtons: function ($node) {
        this.$buttons = $(qweb.render('website.ThemePreview.Buttons'));
        if ($node) {
            $node.html(this.$buttons);
        }
    },
    /**
     * Overriden to prevent the controller from hiding the buttons
     * @see FormController
     *
     * @override
     */
    updateButtons: function () { },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------
    /**
     * Add Switcher View Mobile / Desktop near pager
     *
     * @private
     */
    _updateControlPanelProps: async function () {
        const props = this._super(...arguments);
        const $switchModeButton = $(qweb.render('website.ThemePreview.SwitchModeButton'));
        this.controlPanelProps.cp_content.$pager = $switchModeButton;
        return props;
    },

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------
    /**
     * Handler called when user click on 'Desktop/Mobile' switcher button.
     *
     * @private
     */
    _onSwitchButtonChange: function () {
        this.$('.o_preview_frame').toggleClass('is_mobile');
    },
    /**
     * Handler called when user click on 'Choose another theme' button.
     *
     * @private
     */
    _onSwitchThemeClick: function () {
        this.trigger_up('history_back');
    },
    /**
     * Handler called when user click on 'Use this theme' button in forw view.
     *
     * @private
     */
    _onUseThemeClick: function () {
        const $loader = $(qweb.render('website.ThemePreview.Loader'));
        $('body').append($loader);
        return this._rpc({
            model: 'ir.module.module',
            method: 'button_choose_theme',
            args: [this.getSelectedIds()[0]],
            context: this.initialState.context,
        }, {shadow: true})
            .then(result => this.do_action(result))
            .guardedCatch(() => $loader.remove());
    },
});

var ThemePreviewFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: ThemePreviewController
    }),
});

viewRegistry.add('theme_preview_form', ThemePreviewFormView);

});
