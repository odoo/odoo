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
        // investigate children of referenceNode per row
        return defaultEmailNodeArguments;
    }
    fillMosaicContainer() {}
}
