import { Plugin } from "../plugin";

export class MosaicStrategyPlugin extends Plugin {
    static id = "mosaicStrategy";
    static dependencies = ["tableStrategy", "hybridFluidStrategy"];
    resources = {
        element_layout_analysis_processors: this.analyzeElementLayout.bind(this),
        synthetic_email_node_processors: this.fillMosaicContainer.bind(this),
    };

    analyzeElementLayout(defaultEmailNodeArguments, { referenceNode }) {
        const { layout, analysis } = defaultEmailNodeArguments;
        if (
            !analysis.facts.isTableContainer &&
            (!analysis.facts.isHybridFluidContainer || analysis.facts.isResponsiveElement)
        ) {
            return defaultEmailNodeArguments;
        }
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

        return defaultEmailNodeArguments;
    }
    fillMosaicContainer() {}
}
