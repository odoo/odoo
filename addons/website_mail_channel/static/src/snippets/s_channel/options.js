odoo.define('website_mail_channel.s_channel_options', function (require) {
'use strict';

var core = require('web.core');
var options = require('web_editor.snippets.options');
var wUtils = require('website.utils');

var _t = core._t;

options.registry.Channel = options.Class.extend({
    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this.publicChannels = await this._getPublicChannels();
    },
    /**
     * @override
     */
    cleanForSave: function () {
        this.$target.addClass('d-none');
    },
    /**
     * If we have already created channels => select the first one
     * else => modal prompt (create a new channel)
     *
     * @override
     */
    onBuilt() {
        if (this.publicChannels.length) {
            this.$target[0].dataset.id = this.publicChannels[0][0];
        } else {
            const widget = this._requestUserValueWidgets('create_mail_channel_opt')[0];
            widget.$el.click();
        }
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Creates a new mail.channel through a modal prompt.
     *
     * @see this.selectClass for parameters
     */
    createChannel: function (previewMode, widgetValue, params) {
        var self = this;
        return wUtils.prompt({
            id: "editor_new_mail_channel_subscribe",
            window_title: _t("New Mail Channel"),
            input: _t("Name"),
        }).then(function (result) {
            var name = result.val;
            if (!name) {
                return;
            }
            return self._rpc({
                model: 'mail.channel',
                method: 'create',
                args: [{
                    name: name,
                    public: 'public',
                }],
            }).then(function (id) {
                self.$target.attr("data-id", id);
                return self._rerenderXML();
            });
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _renderCustomXML(uiFragment) {
        // TODO remove this part in master 
        const createChannelEl = uiFragment.querySelector('we-button[data-create-channel]');
        createChannelEl.dataset.name = 'create_mail_channel_opt';

        return this._getPublicChannels().then(channels => {
            const menuEl = uiFragment.querySelector('.select_discussion_list');
            for (const channel of channels) {
                const el = document.createElement('we-button');
                el.dataset.selectDataAttribute = channel[0];
                el.textContent = channel[1];
                menuEl.appendChild(el);
            }
        });
    },
    /**
     * @private
     * @return {Promise}
     */
    _getPublicChannels() {
        return this._rpc({
            model: 'mail.channel',
            method: 'name_search',
            args: ['', [['public', '=', 'public']]],
        });
    },
});
});
