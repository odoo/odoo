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

const { DESKTOP, MOBILE } = DIMENSIONS;
// Prevent the last inline-block element from wrapping to the next line due
// to window zoom px rounding in some cases.
const ZOOM_WIDTH_CORRECTION = 0.1;

const VERTICAL_ALIGN = {
    start: "top",
    end: "bottom",
    center: "middle",
    "flex-start": "top",
    "flex-end": "bottom",
};

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
    ];
    resources = {
        element_layout_analysis_processors: this.analyzeElementLayout.bind(this),
        synthetic_email_node_processors: this.fillHybridFluidContainer.bind(this),
    };

    extractHybridFluidInfo(emailNode) {
        const referenceNode = emailNode.lastReferenceNode;
        const desktopBlock = this.getLayoutBlock(referenceNode, DESKTOP);
        // TODO EGGMAIL: some values for text-align are not supported
        // getStylePropertyValue should probably filter values and only
        // return what is allowed
        // TODO EGGMAIL: style should probably be refined in this fragment
        const styleContext = {
            style: {
                "text-align": this.getStylePropertyValue(referenceNode, "text-align"),
                "font-size": this.getStylePropertyValue(referenceNode, "font-size"),
            },
        };
        // TODO EGGMAIL: approximate vertical alignment support:
        // start/center/end/stretch -> default stretch
        const verticalAlign =
            VERTICAL_ALIGN[this.getStylePropertyValue(referenceNode, "align-items")];
        // STEP 1: construct measure bundles
        const rowMeasures = [];
        for (const band of desktopBlock.bands) {
            const row = { verticalAlign, children: [] };
            rowMeasures.push(row);
            let width = 0;
            let prevCluster;
            const hasLastOffset = !this.isZero(desktopBlock.padding.right);
            if (band.clusters.length > 0) {
                prevCluster = band.clusters[0];
                const measures = {
                    styleContext,
                    isLast: !hasLastOffset && band.clusters.length === 1,
                    cluster: prevCluster,
                    emailNode,
                    width: prevCluster.rect.width,
                    verticalAlign,
                };
                width += measures.width;
                if (!this.isZero(desktopBlock.padding.left)) {
                    const offsetWidth = desktopBlock.padding.left;
                    width += offsetWidth;
                    row.children.push(
                        Object.assign({ type: "cellWithOffset", offsetWidth }, measures)
                    );
                } else {
                    row.children.push(Object.assign({ type: "cell" }, measures));
                }
            }
            for (let i = 1; i < band.clusters.length; i++) {
                const cluster = band.clusters[i];
                const gap = this.gapX(prevCluster.rect, cluster.rect);
                const measures = {
                    styleContext,
                    isLast: !hasLastOffset && i === band.clusters.length - 1,
                    cluster,
                    emailNode,
                    width: cluster.rect.width,
                    verticalAlign,
                };
                width += measures.width;
                if (gap > 0) {
                    width += gap;
                    row.children.push(
                        Object.assign({ type: "cellWithOffset", offsetWidth: gap }, measures)
                    );
                } else {
                    row.children.push(Object.assign({ type: "cell" }, measures));
                }
                prevCluster = cluster;
            }
            if (hasLastOffset) {
                width += desktopBlock.padding.right;
                row.children.push({
                    type: "emptyCell",
                    width: desktopBlock.padding.right,
                    isLast: true,
                    verticalAlign,
                });
            }
            row.width = width;
        }
        return rowMeasures;
    }

    // TODO EGGMAIL NOW:
    // we have a container which is supposed to be a hybrid fluid table
    // with potentially multiple rows, each with potentially multiple
    // cells.
    // however right now, we only have one container and its children
    // we have to create a EmailNode for each row, and a EmailNode
    // for each cell.
    // some of the existing children can be used as is as a cell
    // the current emailNode should be replaced with the list of rows
    // need feature to insert multiple nodes as children of another
    // emailNode
    // features needed here:
    // - replace an item in emailNode.children
    // // currently setParent appends -> this is not enough
    // // -> honestly, need to replace the set by a special set+list structure
    // // done
    // Logic:
    // exact copy paste of buildFragment logic except we create a datastructure of
    // template arguments instead of the templates directly?
    // Real idea here is that I should create a synthetic emailNode
    // I already have my basic emailNode from the first pass which identifies the row
    // and potentially some other emailNode as children of that row that may have any purpose.
    // Objective here is to make sure that every child of the row is classified as a CELL,
    // be it a child itself becomes a CELL, or 1+ children are wrapped in a CELL
    // BTW the row node itself can become multiple row in some circumstances
    fillHybridFluidContainer(emailNode) {
        if (!emailNode.analysis.facts.isHybridFluidContainer) {
            return;
        }
        const rowMeasures = this.extractHybridFluidInfo(emailNode);
        const rows = [];
        for (const rowMeasure of rowMeasures) {
            const width = rowMeasure.width;
            let ratio = 100;
            const rowEmailNode = this.buildRow(rowMeasure);
            rows.push(rowEmailNode);
            for (const cellMeasure of rowMeasure.children) {
                const widthRatio = this.ratioPercentage(cellMeasure.width, width, ratio);
                cellMeasure.widthRatio = widthRatio;
                ratio -= widthRatio;
                if (cellMeasure.type === "cellWithOffset") {
                    cellMeasure.offsetWidthRatio = this.ratioPercentage(
                        cellMeasure.offsetWidth,
                        width,
                        ratio
                    );
                    ratio -= cellMeasure.offsetWidthRatio;
                    for (const cell of this.buildCellWithOffset(cellMeasure)) {
                        rowEmailNode.appendChild(cell);
                    }
                } else if (cellMeasure.type === "emptyCell") {
                    rowEmailNode.appendChild(this.buildEmptyCell(cellMeasure));
                } else {
                    rowEmailNode.appendChild(this.buildCell(cellMeasure));
                }
            }
        }
        emailNode.spliceChildren(0, emailNode.children.length, ...rows);
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
            analysis: new Analysis({
                facts: { isHybridFluidRow: true },
            }),
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
            analysis: new Analysis({
                facts: {
                    isHybridFluidCell: true,
                    // TODO EGGMAIL: evaluate what positioning facts should be shared
                    // and how
                },
            }),
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
            analysis: new Analysis({
                facts: {
                    isHybridFluidCell: true,
                    // TODO EGGMAIL: evaluate what positioning facts should be shared
                    // and how
                },
            }),
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
                analysis: new Analysis({
                    facts: {
                        isHybridFluidCell: true,
                        // TODO EGGMAIL: evaluate what positioning facts should be shared
                        // and how
                    },
                }),
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
