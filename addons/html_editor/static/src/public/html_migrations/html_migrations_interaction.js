import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { VERSION_SELECTOR } from "@html_editor/html_migrations/html_migrations_utils";
import { HtmlUpgradeManager } from "@html_editor/html_migrations/html_upgrade_manager";
import { markup } from "@odoo/owl";

const upgradeElementToInteractionMap = new Map();

export class HtmlMigrationsInteraction extends Interaction {
    static selector = VERSION_SELECTOR;

    setup() {
        const parentElement = this.el.parentElement;
        if (!parentElement) {
            this.isComplete = true;
            return;
        }
        for (const el of [...upgradeElementToInteractionMap.keys()]) {
            if (el.contains(parentElement)) {
                // Avoid handling an upgrade that is already being handled.
                this.isComplete = true;
                return;
            } else if (parentElement.contains(el)) {
                // Avoid handling a upgrade with a contained scope.
                const interaction = upgradeElementToInteractionMap.get(el);
                interaction.isComplete = true;
                interaction.container = undefined;
                upgradeElementToInteractionMap.delete(el);
            }
        }
        this.container = parentElement;
        upgradeElementToInteractionMap.set(this.container, this);
    }

    start() {
        if (this.isComplete || this.isUpgrading || !this.container.isConnected) {
            // Ensure that an upgrade can only be attempted once, even if
            // interactions are restarted.
            return;
        }
        this.isUpgrading = true;
        this.services["public.interactions"].stopInteractions(this.container);
        const htmlUpgradeManager = new HtmlUpgradeManager();
        const initialValue = markup(this.container.innerHTML);
        const upgradedValue = htmlUpgradeManager.processForUpgrade(initialValue);
        if (initialValue !== upgradedValue) {
            this.container.innerHTML = upgradedValue;
        }
        for (const el of this.container.querySelectorAll(VERSION_SELECTOR)) {
            delete el.dataset.oeVersion;
        }
        this.services["public.interactions"].startInteractions(this.container);
        this.isUpgrading = false;
        this.isComplete = true;
    }

    destroy() {
        if (this.isComplete && this.container) {
            // Ensure that the container reference is kept during the upgrade
            // so that no other upgrade can start in the same Element while this
            // one is still ongoing.
            upgradeElementToInteractionMap.delete(this.container);
        }
    }
}

registry
    .category("public.interactions")
    .add("html_editor.html_migrations", HtmlMigrationsInteraction);
