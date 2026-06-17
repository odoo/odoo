import { patch } from "@web/core/utils/patch";
import { htmlField, HtmlField } from "@html_editor/fields/html_field";
import { PING_MENTION_PLUGINS } from "@mail/core/web/avatar_card/ping_mention_plugin_set";

const superExtraProps = htmlField.extractProps;
htmlField.extractProps = (params) => {
    const props = superExtraProps(params);
    const { options } = params;
    props.allowMentions = "allowMentions" in options ? Boolean(options.allowMentions) : false;
    return props;
};

HtmlField.props = {
    ...HtmlField.props,
    allowMentions: { type: Boolean, optional: true },
};

patch(HtmlField.prototype, {
    getConfig() {
        const config = super.getConfig();
        config.Plugins = [
            ...config.Plugins,
            ...(this.props.allowMentions ? PING_MENTION_PLUGINS : []),
        ];
        return config;
    },
});
