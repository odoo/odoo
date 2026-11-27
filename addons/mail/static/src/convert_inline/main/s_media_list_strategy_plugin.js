import { registry } from "@web/core/registry";
import { Plugin } from "@mail/convert_inline/plugin";

const BODY_SELECTOR = ".s_media_list_body";

export class MediaListStrategyPlugin extends Plugin {
    static id = "mediaListStrategy";
    resources = {
        reference_node_facts_processors: this.addMobileSpacingFacts.bind(this),
    };

    /**
     * Neutralize the padding of the media list body in mobile
     * TODO EGGMAIL: this could be generalized without identifying this
     * element in particular => make use of callWithDimensions, evaluate
     * that the padding does not exist in mobile mode and add the fact. But
     * that generalization should be optimized to not be too costly
     * (callWithDimensions requires 2 layout refreshes) => make use
     * of the mobile analyze phase (dimension_plugin) for that optimization.
     */
    addMobileSpacingFacts(facts, { referenceNode }) {
        if (!referenceNode.matches?.(BODY_SELECTOR)) {
            return facts;
        }
        facts.mobileZeroPaddingSides = new Set(facts.mobileZeroPaddingSides).add("left");
        return facts;
    }
}

registry
    .category("mail-html-conversion-core-plugins")
    .add(MediaListStrategyPlugin.id, MediaListStrategyPlugin);
