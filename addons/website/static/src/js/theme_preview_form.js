odoo.define('website.theme_preview_form', function (require) {
"use strict";

var FormController = require('web.FormController');
var FormView = require('web.FormView');
var viewRegistry = require('web.view_registry');
var core = require('web.core');
var _t = core._t;
var qweb = core.qweb;

var ThemePreviewController = FormController.extend({
    events: Object.assign({}, FormController.prototype.events, {
        'click .o_use_theme': '_onUseThemeClick',
        'click .o_switch_theme': '_onSwitchThemeClick',
        'click .o_switch_mode_button': '_onSwitchButtonClick',
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
    autofocus: function () {
        // force refresh label of button switch
        this.$switchButton = this._renderSwitchButton();
        $('.o_switch_mode_button').replaceWith(this.$switchButton);
        this._super.apply(this, arguments);
    },
     /**
     * @override
     */
    renderButtons: function ($node) {
        var $previewButton = $(qweb.render('website.ThemePreview.Buttons'));
        $node.html($previewButton);
        this.$switchButton = this._renderSwitchButton();
        $node.find('.o_switch_mode_button').replaceWith(this.$switchButton);
    },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------
     /**
     * Return jQuery Element button 'Switch Mode' with correct labelling.
     *
     * @private
     */
    _renderSwitchButton: function () {
        var isMobile = !!this.$('.is_mobile').length;
        return $(qweb.render('website.ThemePreview.SwitchModeButton', {
            'icon': isMobile ? 'fa-desktop' : 'fa-refresh',
            'PreviewType': isMobile ? _t('Desktop') : _t('Mobile'),
        }));
    },
    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------
    /**
     * Handler called when user click on 'Desktop/Mobile preview' button in forw view.
     *
     * @private
     */
    _onSwitchButtonClick: function () {
        this.$('.o_preview_frame').toggleClass('is_mobile');
        const $switchButton = this.$switchButton;
        this.$switchButton = this._renderSwitchButton();
        $switchButton.replaceWith(this.$switchButton);
    },
    /**
     * Handler called when user click on 'Choose another theme' button in forw view.
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
