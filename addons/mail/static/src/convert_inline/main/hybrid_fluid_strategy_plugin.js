import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { zip } from "@web/core/utils/arrays";
import { DIMENSIONS } from "../hooks";
import { Analysis, EmailNode } from "../core/render_models";
import {
    HybridFluidCell,
    HybridFluidEmptyCell,
    HybridFluidEmptyTableCell,
    HybridFluidRow,
    HybridFluidTableCell,
    HybridFluidTableRow,
} from "./hybrid_fluid_models";
import { parseCssValue } from "../css_parsers";
import { isAllowedContent } from "@html_editor/utils/dom_info";

const { DESKTOP, MOBILE, ZOOM_WIDTH_CORRECTION } = DIMENSIONS;

/**
 * TODO EGGMAIL NOW:
 * WORKING HERE:
 * check out getContextStyleInfo for the "table" case to revert table styling
 * currently a table inside the td will not take the full height of the td
 * current solution does not support well padding + border inside padding
 * real solution implies converting the padding to filler cells and move the
 * border on the stretched TD
 */
export class HybridFluidStrategyPlugin extends Plugin {
    static id = "hybridFluidStrategy";
    static dependencies = [
        "measurementSnapshot",
        "math",
        "responsiveBlock",
        "rules",
        "referenceNode",
        "tableStrategy",
    ];
    resources = {
        element_layout_analysis_processors: this.analyzeElementLayout.bind(this),
        synthetic_email_node_processors: (emailNode) => {
            if (!emailNode.analysis.facts.isHybridFluidContainer) {
                return;
            }
            return this.fillTableContainer(emailNode, {
                withTable: false,
                builders: this.builders,
            });
        },
    };

    setup() {
        this.builders = {
            row: this.buildRow.bind(this),
            cell: this.buildCell.bind(this),
            emptyCell: this.buildEmptyCell.bind(this),
            cellWithOffset: this.buildCellWithOffset.bind(this),
        };
    }

    analyzeElementLayout({ layout, analysis }, { referenceNode }) {
        const div = this.config.referenceDocument.createElement("DIV");
        if (
            analysis.facts.isMainTable ||
            !isAllowedContent(referenceNode, [div]) ||
            (!this.detectHybridFluidLayout(referenceNode) &&
                !this.detectResponsiveElement(referenceNode))
        ) {
            return;
        }
        Object.assign(analysis.parsingFacts, {
            canMerge: false,
            needSyntheticEmailNode: true,
        });
        // TODO EGGMAIL: add a generic "isContainer" fact. a "container" should
        // be a flexible node that can become e.g. a table for MSO, and can
        // be merged with its parent if they also are a container and there
        // is no positioning consideration between the 2
        analysis.facts.isHybridFluidContainer = true;
        layout.pluginIds.add(HybridFluidStrategyPlugin.id);
    }

    /**
     * TODO EGGMAIL: also consider mobile dimensions?
     */
    detectResponsiveElement(referenceNode) {
        const block = this.getLayoutBlock(referenceNode);
        if (!block || block.bands.length !== 1 || block.bands[0].clusters.length !== 1) {
            return;
        }
        const cluster = block.bands[0].clusters[0];
        // check if margin of child + padding of parent ~= block spacing to the left and to the right
        const { number: paddingLeft } = parseCssValue(
            this.getStylePropertyValue(referenceNode, "padding-left")
        );
        const { number: paddingRight } = parseCssValue(
            this.getStylePropertyValue(referenceNode, "padding-right")
        );
        const spacing = this.containerPadding(block.rect, cluster.rect);
        const deltaLeft = spacing.left - (paddingLeft ?? 0);
        const deltaRight = spacing.right - (paddingRight ?? 0);
        return (
            (!this.isZero(deltaLeft) && deltaLeft > 0) ||
            (!this.isZero(deltaRight) && deltaRight > 0)
        );
    }

    /**
     * TODO EGGMAIL: can I get an hybrid fluid row with only inline children? to investigate
     */
    detectHybridFluidLayout(referenceNode) {
        // detect hybrid fluid "rows"
        // -> detect a band with multiple clusters inside a block
        // -> look in mobile mode, the amount of bands should be different
        // -> should not be captured by table, since the table strictly verifies
        // that the amount of bands is the same
        let isHybridFluidCandidate;
        const mobileBlock = this.getLayoutBlock(referenceNode, MOBILE);
        const desktopBlock = this.getLayoutBlock(referenceNode, DESKTOP);
        if (!desktopBlock || !mobileBlock) {
            return;
        }
        if (desktopBlock.bands.length !== mobileBlock.bands.length) {
            isHybridFluidCandidate = true;
        } else {
            for (const [dBand, mBand] of zip(desktopBlock.bands, mobileBlock.bands)) {
                if (dBand.clusters.length !== mBand.clusters.length) {
                    isHybridFluidCandidate = true;
                    break;
                }
            }
        }
        return isHybridFluidCandidate;
    }

    /**
     * TODO EGGMAIL: test how this works/find a more optimized solution?
     * Evaluate which children in emailNode are related to a given cluster
     * of nodes
     */
    getClusterEmailNodes(emailNode, cluster) {
        const range = this.getNodeClusterRange(cluster.nodes.at(0), cluster.nodes.at(-1));
        const clusterEmailNodes = [];
        for (const childEmailNode of emailNode.children) {
            if (
                childEmailNode.referenceNodes.length &&
                range.comparePoint(childEmailNode.firstReferenceNode, 0) === 0
            ) {
                clusterEmailNodes.push(childEmailNode);
            }
        }
        return clusterEmailNodes;
    }

    buildRow(rowMeasure) {
        const layout = rowMeasure.verticalAlign ? new HybridFluidRow() : new HybridFluidTableRow();
        return new EmailNode({
            layout,
            analysis: new Analysis(),
        });
    }

    buildCell({ styleContext, isLast, cluster, emailNode, width, widthRatio, verticalAlign }) {
        const clusterEmailNodes = this.getClusterEmailNodes(emailNode, cluster);
        const refs = {
            root: {},
            styleContext,
        };
        let layout;
        if (verticalAlign) {
            const cellWidth = width - (isLast ? ZOOM_WIDTH_CORRECTION : 0);
            Object.assign(refs.root, {
                style: {
                    "vertical-align": verticalAlign,
                    "max-width": `${cellWidth}px`,
                },
            });
            layout = new HybridFluidCell({ refs });
        } else {
            Object.assign(refs.root, {
                style: { width: `${widthRatio}%` },
                attributes: { width: `${widthRatio}%` },
            });
            layout = new HybridFluidTableCell(refs.root);
        }
        const cellEmailNode = new EmailNode({
            layout,
            // TODO EGGMAIL: evaluate what positioning facts should be shared
            // and how
            analysis: new Analysis(),
        });
        for (const child of clusterEmailNodes) {
            cellEmailNode.appendChild(child);
        }
        return cellEmailNode;
    }

    buildEmptyCell({ isLast, width, widthRatio, verticalAlign }) {
        const refs = { root: {} };
        let layout;
        if (verticalAlign) {
            const cellWidth = width - (isLast ? ZOOM_WIDTH_CORRECTION : 0);
            Object.assign(refs.root, {
                style: { "max-width": `${cellWidth}px` },
            });
            layout = new HybridFluidEmptyCell({ refs });
        } else {
            Object.assign(refs.root, {
                style: { width: `${widthRatio}%` },
                attributes: { width: `${widthRatio}%` },
            });
            layout = new HybridFluidEmptyTableCell(refs.root);
        }
        return new EmailNode({
            layout,
            analysis: new Analysis(),
        });
    }

    buildCellWithOffset({
        styleContext,
        isLast,
        cluster,
        emailNode,
        width,
        widthRatio,
        verticalAlign,
        offsetWidth,
        offsetWidthRatio,
    }) {
        const refs = { root: {} };
        const cells = [];
        if (verticalAlign) {
            const cellOffsetWidth = offsetWidth - (isLast ? ZOOM_WIDTH_CORRECTION : 0);
            const cellWidth = width + cellOffsetWidth;
            const offsetEmailNode = this.buildEmptyCell({
                verticalAlign,
                width: cellOffsetWidth,
                isLast,
            });
            const cellEmailNode = this.buildCell({
                styleContext,
                cluster,
                emailNode,
                width,
                verticalAlign,
            });
            Object.assign(refs.root, { style: { "max-width": `${cellWidth}px` } });
            const cellWithOffsetEmailNode = new EmailNode({
                layout: new HybridFluidCell({ refs }),
                analysis: new Analysis(),
            });
            cellWithOffsetEmailNode.appendChild(offsetEmailNode);
            cellWithOffsetEmailNode.appendChild(cellEmailNode);
            cells.push(cellWithOffsetEmailNode);
        } else {
            const offsetEmailNode = this.buildEmptyCell({ widthRatio: offsetWidthRatio });
            const cellEmailNode = this.buildCell({
                styleContext,
                widthRatio,
                emailNode,
                cluster,
            });
            cells.push(offsetEmailNode, cellEmailNode);
        }
        return cells;
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(HybridFluidStrategyPlugin.id, HybridFluidStrategyPlugin);
