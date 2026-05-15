import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { zip } from "@web/core/utils/arrays";
import { DIMENSIONS } from "../hooks";

const { DESKTOP, MOBILE } = DIMENSIONS;

export class TableStrategyPlugin extends Plugin {
    static id = "tableStrategy";
    static dependencies = ["responsiveBlock", "referenceNode"];
    resources = {
        apply_layout_strategy_overrides: this.applyLayoutStrategy.bind(this),
        element_layout_analysis_processors: this.analyzeElementLayout.bind(this),
    };

    analyzeElementLayout({ layout, analysis }, { referenceNode, parentEmailNode }) {
        if (analysis.facts.isMainTable || !this.detectTableLayout(referenceNode)) {
            // See MainTableStrategyPlugin (more specific representation of a table)
            return;
        }
        if (parentEmailNode.layout.descendantTag === "TABLE") {
            analysis.parsingFacts.canParentMerge = true;
        }
        analysis.parsingFacts.canMerge = false;
        analysis.facts.isTable = true;
        layout.pluginIds.add(TableStrategyPlugin.id);
    }

    // TODO EGGMAIL NOW: special case for the first element inside the reference:
    // - basic editor case (investigate)
    // - builder case (convert to mega wrapper table + background color -> smaller table (mail_wrapper) with margin)
    // - unknown case (add mega wrapper table -> can use "reference" element for this, if mega table strategy was not applied
    // below)
    applyLayoutStrategy(referenceNode) {
        // TODO EGGMAIL NOW: check that `hasTableLayout` can capture a table
        // if so, maybe we shouldn't hardcode "table" here, because we want to
        // allow a table to be an "hybrid" and match other strategies.
        if (!this.detectTableLayout(referenceNode)) {
            // look at element tag, if it's a table.
            // look in // at desktopBlocks and mobileBlocks, they should have:
            // - always the same amount of bands, and the same amount of clusters per band?
            // parent should only have bands with 1 block cluster
            // block cluster should have only 1 band, and at least 1 block cluster band should have 2 clusters
            // look for a block with multiple bands, every band has 1 cluster
            return;
        }
        this.buildFragment(referenceNode);
        referenceNode.defineLayoutStrategy({ pluginId: TableStrategyPlugin.id });
        return true;
    }

    // TODO EGGMAIL: evaluate how float: left/right behave, will it match
    // this table detection algo or does it need a custom one?
    // -> can support it with a specific table layout
    // -> not critical, as we don't use it currently, but would be great for
    // design flexibility
    // TODO EGGMAIL: currently a table with 2 rows of 1 column won't be
    // considered a "table"
    // should we look for "invalid" nodes such as tbody? Or make a whitelist of
    // tagNames and convert unknown tag names to div or span?
    // ideally email strategies should render nodes that can be in any block
    // and few exceptions (table) should verify that they don't have a table
    // as their direct ancestor
    detectTableLayout(referenceNode) {
        let isTableCandidate;
        const mobileBlock = this.getLayoutBlock(referenceNode, MOBILE);
        const desktopBlock = this.getLayoutBlock(referenceNode, DESKTOP);
        if (
            !desktopBlock ||
            !mobileBlock ||
            desktopBlock.bands.length !== mobileBlock.bands.length ||
            desktopBlock.bands.length === 0
        ) {
            return;
        }
        for (const [dBand, mBand] of zip(desktopBlock.bands, mobileBlock.bands)) {
            if (
                dBand.clusters.length !== mBand.clusters.length ||
                dBand.clusters.length !== 1 ||
                !dBand.clusters[0].isBlock ||
                !mBand.clusters[0].isBlock
            ) {
                return;
            }
            const dRowEl = dBand.clusters[0].nodes[0];
            const mRowEl = mBand.clusters[0].nodes[0];
            const dRowBlock = this.getLayoutBlock(dRowEl, MOBILE);
            const mRowBlock = this.getLayoutBlock(mRowEl, DESKTOP);
            if (
                !dRowBlock ||
                !mRowBlock ||
                dRowBlock.bands.length !== mRowBlock.bands.length ||
                dRowBlock.bands.length !== 1 ||
                dRowBlock.bands[0].clusters.length !== dRowBlock.bands[0].clusters.length
            ) {
                return;
            }
            if (dRowBlock.bands[0].clusters.length > 1) {
                isTableCandidate = true;
            }
        }
        return isTableCandidate;
    }

    buildFragment(referenceNode) {
        // => about tables
        // normally, a table will ask that its direct container is not a table nor a row nor a tbody => if it is, we create a row + td to wrap
        // it => becomes legal again
        // -> how to handle it => actual constraint should come from the parent (table) if the child is also a table => it should be
        // wrapped in a tr + td?

        // TODO EGGMAIL NOW: render fragment
        // The above heuristic will match a `tbody` and transform it into a
        // table
        // => avoid putting a table inside another table
        // => re-evaluate strategy of parent in such a case
        // => match a table tagName directly and handle it from that node,
        // aggregate unsupported sub-parts
        referenceNode.fragment;
    }
}

// TODO EGGMAIL: enable plugin
// registry
//     .category("mail-html-conversion-main-plugins")
//     .add(TableStrategyPlugin.id, TableStrategyPlugin);
