import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { VERSION_SELECTOR } from "@html_editor/html_migrations/html_migrations_utils";
import { HtmlUpgradeManager } from "@html_editor/html_migrations/html_upgrade_manager";

export class HtmlMigrationInteraction extends Interaction {
    static selector = `${VERSION_SELECTOR}, .o_knowledge_behavior_anchor`;
    static upgradeElements = [];

    setup() {
        this.editable = this.el.parentElement;
        if (HtmlMigrationInteraction.upgradeElements.some((el) => el.contains(this.editable))) {
            return;
        }
        HtmlMigrationInteraction.upgradeElements.push(this.editable);
        this.shouldMigrate = true;
    }

    start() {
        if (!this.shouldMigrate) {
            return;
        }
        this.services["public.interactions"].stopInteractions(this.editable);
        const htmlUpgradeManager = new HtmlUpgradeManager();
        const initialValue = this.editable.innerHTML;
        const upgradedValue = htmlUpgradeManager.processForUpgrade(initialValue);
        if (initialValue !== upgradedValue) {
            this.editable.innerHTML = upgradedValue;
            for (const el of this.editable.querySelectorAll(VERSION_SELECTOR)) {
                delete el.dataset.oeVersion;
            }
        }
        this.services["public.interactions"].startInteractions(this.editable);
    }
}

registry
    .category("public.interactions")
    .add("html_editor.html_migration", HtmlMigrationInteraction);
