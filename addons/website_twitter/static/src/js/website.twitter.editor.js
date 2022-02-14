odoo.define('website_twitter.editor', function (require) {
'use strict';

var core = require('web.core');
var dom = require('web.dom');
var sOptions = require('web_editor.snippets.options');

var _t = core._t;

sOptions.registry.twitter = sOptions.Class.extend({
    /**
     * @override
     */
    start: function () {
        const $configuration = dom.renderButton({
            attrs: {
                class: 'btn-primary d-none s_twitter_reload_btn',
                contenteditable: 'false',
            },
            text: _t("Reload"),
        }).appendTo(this.$target).on('click', (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            this._rpc({route: '/website_twitter/reload'});
        });
        this.$target.on('mouseover.website_twitter', (ev) => {
            $configuration.removeClass('d-none');
        }).on('mouseout.website_twitter', (ev) => {
            $configuration.addClass('d-none');
        });
        this.$target.on('click.website_twitter', '.lnk_configure', (ev) => {
            window.location = ev.currentTarget.href;
        });
        this.trigger_up('widgets_stop_request', {
            $target: this.$target,
        });
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    cleanForSave: function () {
        this.$target.find('.twitter_timeline').empty();
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        this.$target.off('.website_twitter');
        this.$target[0].querySelector('.s_twitter_reload_btn').remove();
    },
});
});
