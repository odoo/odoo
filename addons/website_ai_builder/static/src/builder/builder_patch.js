import { Builder } from "@html_builder/builder";
import { patch } from "@web/core/utils/patch";

patch(Builder.prototype, {
    async onAiChatClick() {
        const launcher = this.env.services["aiChatLauncher"];
        if (!launcher) {
            this.notification.add("AI service not available.", { type: "warning" });
            return;
        }

        try {
            // Get the current page HTML for AI context
            const pageHtml = this.editor?.editable?.innerHTML || "";

            await launcher.launchAIChat({
                interfaceKey: "website_builder_ai",
                channelTitle: "AI Website Assistant",
                textOfEditable: pageHtml.slice(0, 50000),
            });
        } catch (e) {
            this.notification.add("Failed to open AI chat.", { type: "danger" });
            console.error(e);
        }
    },
});
