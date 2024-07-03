/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { SnippetOption } from "@web_editor/js/editor/snippets.options";
import { registerWebsiteOption } from "@website/js/editor/snippets.registry";
import wUtils from "@website/js/utils";

class Group extends SnippetOption {
    constructor() {
        super(...arguments);
        this.orm = this.env.services.orm;
    }
    /**
     * @override
     */
    async willStart() {
        await super.willStart(...arguments);
        this.renderContext.mailGroups = await this._getMailGroups();
    }
    /**
     * If we have already created groups => select the first one
     * else => modal prompt (create a new group)
     *
     * @override
     */
    onBuilt() {
        if (this.renderContext.mailGroups.length) {
            this.$target[0].dataset.id = this.renderContext.mailGroups[0][0];
        } else {
            this.createGroup();
        }
    }

    cleanUI() {
        // TODO: this should probably be done by the public widget, not the
        // option code, not important enough to try and fix in stable though.
        const emailInput = this.$target.find('.o_mg_subscribe_email');
        emailInput.val('');
        emailInput.removeAttr('readonly');
        this.$target.find('.o_mg_subscribe_btn').text(_t('Subscribe'));
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Creates a new mail.group through a modal prompt.
     *
     * @see this.selectClass for parameters
     */
    async createGroup(previewMode, widgetValue, params) {
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
        this.renderContext.mailGroups = await this._getMailGroups();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @return {Promise}
     */
    _getMailGroups() {
        return this.orm.call("mail.group", "name_search", [""]);
    }
}
registerWebsiteOption("Group", {
    Class: Group,
    template: "website_mail_group.s_group_options",
    selector: ".s_group",
    dropNear: "p, h1, h2, h3, blockquote, .card",
});
