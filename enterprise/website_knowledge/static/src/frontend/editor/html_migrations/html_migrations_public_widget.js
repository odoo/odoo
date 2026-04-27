import publicWidget from "@web/legacy/js/public/public_widget";
import { VERSION_SELECTOR } from "@html_editor/html_migrations/html_migrations_utils";
import { HtmlUpgradeManager } from "@html_editor/html_migrations/html_upgrade_manager";

export const HtmlMigrationsPublicWidget = publicWidget.Widget.extend({
    selector: `.o_knowledge_public_view_static .o_readonly:has(${VERSION_SELECTOR}, .o_knowledge_behavior_anchor)`,

    start() {
        if (this.isComplete) {
            // Ensure that an upgrade can only be attempted once, even if
            // widgets are restarted.
            return;
        }
        const children = [...this.el.children];
        for (const child of children) {
            // Don't destroy this widget, because it would prevent
            // the restart trigger after the migration.
            this.trigger_up("widgets_stop_request", {
                $target: $(child),
            });
        }
        const htmlUpgradeManager = new HtmlUpgradeManager();
        const initialValue = this.el.innerHTML;
        const upgradedValue = htmlUpgradeManager.processForUpgrade(initialValue);
        if (initialValue !== upgradedValue) {
            this.el.innerHTML = upgradedValue;
        }
        for (const el of this.el.querySelectorAll(VERSION_SELECTOR)) {
            delete el.dataset.oeVersion;
        }
        this.trigger_up("widgets_start_request", {
            $target: $(this.el),
        });
        this.isComplete = true;
    },
});

publicWidget.registry.HtmlMigrationsPublicWidget = HtmlMigrationsPublicWidget;
