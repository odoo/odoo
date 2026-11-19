import { Chatter } from "@mail/chatter/web_portal_project/chatter";
import { Message } from "@mail/core/common/message";

import { Component, onWillStart, useProps, xml } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";

/**
 * Loads the editor before rendering the composer, so that visitors who don't
 * write don't download it. The composer and the modules depending on it are in
 * the chatter bundle but only start once the editor is loaded.
 */
export class LazyComposer extends Component {
    static template = xml`<t t-component="this.Composer" t-props="this.props"/>`;
    props = useProps();

    setup() {
        onWillStart(async () => {
            await loadBundle("html_editor.assets_editor_frontend");
            this.Composer = registry.category("lazy_components").get("mail.Composer");
        });
    }
}

// Replaced by the composer itself once the editor is loaded.
Object.assign(Chatter.components, { Composer: LazyComposer });
Object.assign(Message.components, { Composer: LazyComposer });
