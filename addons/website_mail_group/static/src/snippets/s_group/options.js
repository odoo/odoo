odoo.define('website_mail_group.s_group_options', function (require) {
'use strict';

const core = require('web.core');
const options = require('web_editor.snippets.options');
const wUtils = require('website.utils');
const _t = core._t;

options.registry.Group = options.Class.extend({
    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this.mailGroups = await this._getMailGroups();
    },
    /**
     * If we have already created groups => select the first one
     * else => modal prompt (create a new group)
     *
     * @override
     */
    onBuilt() {
        if (this.mailGroups.length) {
            this.$target[0].dataset.id = this.mailGroups[0][0];
        } else {
            const widget = this._requestUserValueWidgets('create_mail_group_opt')[0];
            widget.$el.click();
        }
    },

    cleanForSave: function () {
        // Hide the element by default, this class will be removed
        // if the current user has access to the group
        this.$target.addClass('d-none');

        const emailInput = this.$target.find('.o_mg_subscribe_email');
        emailInput.val('');
        emailInput.removeAttr('readonly');
        this.$target.find('.o_mg_subscribe_btn').text(_t('Subscribe'));
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Creates a new mail.group through a modal prompt.
     *
     * @see this.selectClass for parameters
     */
    createGroup: async function (previewMode, widgetValue, params) {
        const result = await wUtils.prompt({
            id: "editor_new_mail_group_subscribe",
            window_title: _t("New Mail Group"),
            input: _t("Name"),
        });

        const name = result.val;
        if (!name) {
            return;
        }

        const groupId = await this._rpc({
            model: 'mail.group',
            method: 'create',
            args: [{
                name: name,
            }],
        });

        this.$target.attr("data-id", groupId);
        return this._rerenderXML();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _renderCustomXML(uiFragment) {
        const groups = await this._getMailGroups();
        const menuEl = uiFragment.querySelector('.select_discussion_list');
        for (const group of groups) {
            const el = document.createElement('we-button');
            el.dataset.selectDataAttribute = group[0];
            el.textContent = group[1];
            menuEl.appendChild(el);
        }
    },
    /**
     * @private
     * @return {Promise}
     */
    _getMailGroups() {
        return this._rpc({
            model: 'mail.group',
            method: 'name_search',
            args: [''],
        });
    },
});
});
