import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { zip } from "@web/core/utils/arrays";
import { DIMENSIONS } from "../hooks";
import { Analysis, EmailNode } from "../core/render_models";
import { HybridFluidCell, HybridFluidEmptyCell, HybridFluidRow } from "./hybrid_fluid_models";
import { parseCssValue } from "../css_parsers";
import { isAllowedContent } from "@html_editor/utils/dom_info";

const { DESKTOP, MOBILE } = DIMENSIONS;
// Prevent the last inline-block element from wrapping to the next line due
// to window zoom px rounding in some cases.
const ZOOM_WIDTH_CORRECTION = 0.1;

export class HybridFluidStrategyPlugin extends Plugin {
    static id = "hybridFluidStrategy";
    static dependencies = [
        "dynamicStyleSheet",
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

    setup() {
        this.addToStyleSheet(
            ".o-ci-hybrid-fluid-cell, .o-ci-hybrid-fluid-cell-with-offset",
            { "max-width": { value: "100%", priority: "important" } },
            768
        );
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
        const referenceNode = emailNode.lastReferenceNode;
        const desktopBlock = this.getLayoutBlock(referenceNode, DESKTOP);
        const rows = [];
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
        for (const band of desktopBlock.bands) {
            const rowEmailNode = new EmailNode({
                layout: new HybridFluidRow(),
                analysis: new Analysis({
                    facts: { isHybridFluidRow: true },
                }),
            });
            rows.push(rowEmailNode);
            let prevCluster;
            if (band.clusters.length > 0) {
                prevCluster = band.clusters[0];
                const isLast = band.clusters.length === 1;
                if (!this.isZero(desktopBlock.padding.left)) {
                    const offsetWidth = desktopBlock.padding.left;
                    rowEmailNode.appendChild(
                        this.buildCellWithOffset(
                            emailNode,
                            offsetWidth,
                            prevCluster,
                            styleContext,
                            isLast
                        )
                    );
                } else {
                    rowEmailNode.appendChild(
                        this.buildCell(emailNode, prevCluster, styleContext, isLast)
                    );
                }
            }
            for (let i = 1; i < band.clusters.length; i++) {
                const cluster = band.clusters[i];
                const gap = this.gapX(prevCluster.rect, cluster.rect);
                const isLast = i === band.clusters.length - 1;
                if (gap > 0) {
                    rowEmailNode.appendChild(
                        this.buildCellWithOffset(emailNode, gap, cluster, styleContext, isLast)
                    );
                } else {
                    rowEmailNode.appendChild(
                        this.buildCell(emailNode, cluster, styleContext, isLast)
                    );
                }
                prevCluster = cluster;
            }
            if (!this.isZero(desktopBlock.padding.right)) {
                rowEmailNode.appendChild(this.buildEmptyCell(desktopBlock.padding.right));
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

    buildCell(emailNode, cluster, styleContext, isLast = false) {
        const clusterEmailNodes = this.getClusterEmailNodes(emailNode, cluster);
        const clusterWidth = cluster.rect.width - (isLast ? ZOOM_WIDTH_CORRECTION : 0);
        const refs = {
            root: { style: { "max-width": `${clusterWidth}px` } },
            styleContext,
        };
        const cellEmailNode = new EmailNode({
            layout: new HybridFluidCell({ refs }),
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

    buildEmptyCell(width) {
        const refs = {
            root: { style: { "max-width": `${width}px` } },
        };
        return new EmailNode({
            layout: new HybridFluidEmptyCell({ refs }),
            analysis: new Analysis({
                facts: {
                    isHybridFluidCell: true,
                    // TODO EGGMAIL: evaluate what positioning facts should be shared
                    // and how
                },
            }),
        });
    }

    buildCellWithOffset(emailNode, offsetWidth, cluster, styleContext, isLast = false) {
        const clusterWidth = cluster.rect.width - (isLast ? ZOOM_WIDTH_CORRECTION / 2 : 0);
        const offsetEmailNode = this.buildEmptyCell(offsetWidth);
        const cellEmailNode = this.buildCell(emailNode, cluster, styleContext, isLast);
        const refs = {
            root: { style: { "max-width": `${offsetWidth + clusterWidth}px` } },
        };
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
        return cellWithOffsetEmailNode;
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(HybridFluidStrategyPlugin.id, HybridFluidStrategyPlugin);
