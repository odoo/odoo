import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";

export class MosaicStrategyPlugin extends Plugin {
    static id = "mosaicStrategy";
    static dependencies = ["tableStrategy", "hybridFluidStrategy"];
    resources = {
        element_layout_analysis_processors: this.analyzeElementLayout.bind(this),
        synthetic_email_node_processors: this.fillMosaicContainer.bind(this),
    };

    analyzeElementLayout(defaultEmailNodeArguments, { referenceNode, parentEmailNode }) {
        const { layout, analysis } = defaultEmailNodeArguments;
        if (
            !analysis.facts.isTableContainer &&
            (!analysis.facts.isHybridFluidContainer || analysis.facts.isResponsiveElement)
        ) {
            return defaultEmailNodeArguments;
        }
        const cellsProviders = this.processThrough(
            "mosaic_cells_providers_processors",
            [],
            defaultEmailNodeArguments,
            { referenceNode, parentEmailNode }
        );
        if (cellsProviders.length === 0) {
            return defaultEmailNodeArguments;
        }
        delete analysis.facts.isHybridFluidContainer;
        delete analysis.facts.isTableContainer;
        Object.assign(analysis.parsingFacts, {
            canMerge: false,
            needSyntheticEmailNode: true,
            isSkippingContainer: true,
            skippingContainerDescendantProviders: cellsProviders,
        });
        analysis.facts.isMosaicContainer;
        analysis.facts.cellsProviders = cellsProviders;
        layout.pluginIds.add(MosaicStrategyPlugin.id);
        return defaultEmailNodeArguments;


        // request for mosaic cells providers => check ancestor snippet class
        // s_comparisons -> card (columns) -> card-body | card-footer = cells
        // approximation: align card-bodies and card-footers in a table of 2 rows
        // that is a better approximation than a table of 2 columns 1 row.
        //
        // s_masonry_block -> data-name="Block" (cells) => position each block
        // using the boundingclientrect
        //
        // neutralize isTableContainer and isHybridFluidContainer if a provider
        // exists. Compute final table dimensions using desktop geometry
        // compute final mobile dimensions using mobile geometry?
    }
    fillMosaicContainer() {}
}

registry
    .category("mail-html-conversion-core-plugins")
    .add(MosaicStrategyPlugin.id, MosaicStrategyPlugin);
