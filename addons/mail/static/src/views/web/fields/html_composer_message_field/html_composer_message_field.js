import { DYNAMIC_PLACEHOLDER_PLUGINS } from "@html_editor/plugin_sets";
import { registry } from "@web/core/registry";
import { HtmlMailField, htmlMailField } from "../html_mail_field/html_mail_field";
import { MentionPlugin } from "./mention_plugin";
import { markup } from "@odoo/owl";

export class HtmlComposerMessageField extends HtmlMailField {
    static template = "mail.HtmlComposerMessageField";

    setup() {
        super.setup();
        this.replyState = this.props.record.data.in_reply_mode;
    }

    async onClickView() {
        this.replyState = false;
        const domParser = new DOMParser();
        const parsedBody = domParser.parseFromString(
            this.props.record.data.body || "",
            "text/html"
        );
        for (const block of parsedBody.body.querySelectorAll(".o_mail_reply_hide")) {
            block.classList.remove("o_mail_reply_hide");
        }
        await this.props.record.update({
            body: markup(parsedBody.body.innerHTML),
        });
    }

    getConfig() {
        const config = super.getConfig(...arguments);
        config.Plugins = [...config.Plugins, MentionPlugin];
        if (!this.props.record.data.composition_batch) {
            config.Plugins = config.Plugins.filter(
                (plugin) => !DYNAMIC_PLACEHOLDER_PLUGINS.includes(plugin)
            );
        }
        config.onAttachmentChange = (attachment) => {
            // This only needs to happen for the composer for now
            if (
                !(
                    this.props.record.fieldNames.includes("attachment_ids") &&
                    this.props.record.resModel === "mail.compose.message"
                )
            ) {
                return;
            }
            this.props.record.data.attachment_ids.linkTo(attachment.id, attachment);
        };
        return config;
    }
}

export const htmlComposerMessageField = {
    ...htmlMailField,
    component: HtmlComposerMessageField,
};

registry.category("fields").add("html_composer_message", htmlComposerMessageField);
