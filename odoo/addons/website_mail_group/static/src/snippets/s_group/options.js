/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import options from "@web_editor/js/editor/snippets.options";
import wUtils from "@website/js/utils";

options.registry.Group = options.Class.extend({
    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },

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
        // TODO: this should probably be done by the public widget, not the
        // option code, not important enough to try and fix in stable though.
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

        const groupId = await this.orm.create("mail.group", [{ name: name }]);

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
        return this.orm.call("mail.group", "name_search", [""]);
    },
});
