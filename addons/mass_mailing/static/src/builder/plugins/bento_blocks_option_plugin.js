import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class BentoBlocksOptionPlugin extends Plugin {
    static id = "mass_mailing.BentoBlocks";
    resources = {
        builder_actions: {
            AddBentoCardAction,
        },
    };
}

export class AddBentoCardAction extends BuilderAction {
    static id = "addBentoCard";
    static dependencies = ["clone", "history"];
    async apply({ editingElement }) {
        const cardCols = editingElement.querySelectorAll(
            ".row > div:has(> [data-name='Bento card'])"
        );
        const lastCardCol = cardCols[cardCols.length - 1];
        if (lastCardCol) {
            await this.dependencies.clone.cloneElement(lastCardCol, { scrollToClone: true });
            this.dependencies.history.commit();
        }
    }
}

export class BentoBlocksAddCardOption extends BaseOptionComponent {
    static id = "bento_blocks_add_card_option";
    static template = "mass_mailing.BentoBlocksAddCardOption";
}

registry
    .category("mass_mailing-plugins")
    .add(BentoBlocksOptionPlugin.id, BentoBlocksOptionPlugin);

registry
    .category("mass_mailing-options")
    .add(BentoBlocksAddCardOption.id, BentoBlocksAddCardOption);
