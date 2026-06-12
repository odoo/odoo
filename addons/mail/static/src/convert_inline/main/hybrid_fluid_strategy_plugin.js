import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { zip } from "@web/core/utils/arrays";
import { DIMENSIONS } from "../hooks";
import { EmailNode } from "../core/render_models";
import {
    HybridFluidCell,
    HybridFluidEmptyCell,
    HybridFluidRow,
    HybridFluidTableCell,
    HybridFluidTableRow,
} from "./hybrid_fluid_models";
import { parseCssValue } from "../css_parsers";
import { isAllowedContent } from "@html_editor/utils/dom_info";
import { withSequence } from "@html_editor/utils/resource";
import { DEFAULT_SPACING_SEQUENCE } from "./spacing_plugin";
import { StyleInfo } from "../core/style_models";
import { EmptyCellLayout } from "./table_models";

const { DESKTOP, MOBILE } = DIMENSIONS;

// When multiple sized elements are displayed horizontally, the user zoom
// may introduce rounding errors. This correction must be subtracted from
// the width (px) of one element to accommodate for the error.
// Prevent the last inline-block element from wrapping to the next line due
// to window zoom px rounding in some cases.
const ZOOM_WIDTH_CORRECTION = 0.1;

export class HybridFluidStrategyPlugin extends Plugin {
    static id = "hybridFluidStrategy";
    static dependencies = [
        "measurementSnapshot",
        "math",
        "responsiveBlock",
        "rules",
        "referenceNode",
        "spacing",
        "tableStrategy",
    ];
    resources = {
        element_layout_analysis_processors: this.analyzeElementLayout.bind(this),
        synthetic_email_node_processors: this.fillHybridFluidContainer.bind(this),
        refine_layout_processors: withSequence(
            DEFAULT_SPACING_SEQUENCE - 1,
            this.applyTableSpacing.bind(this)
        ),
        accept_table_strategy_report_overrides: this.acceptTableStrategyReport.bind(this),
    };

    setup() {
        this.hybridBuilders = {
            row: this.buildHybridRow.bind(this),
            cell: this.buildHybridCell.bind(this),
            emptyCell: this.buildHybridEmptyCell.bind(this),
            cellWithOffset: this.buildHybridCellWithOffset.bind(this),
        };
        this.tableBuilders = {
            row: this.buildTableRow.bind(this),
            cell: this.buildTableCell.bind(this),
            emptyCell: this.buildTableEmptyCell.bind(this),
            cellWithOffset: this.buildTableCellWithOffset.bind(this),
        };
    }

    applyTableSpacing(layout, { emailNode }) {
        if (!emailNode.analysis.facts.useHybridFluidTableStrategy) {
            return;
        }
        // TODO EGGMAIL NOW: WORKING HERE NOW:
        if (emailNode.analysis.facts.acceptTableOuterSpacing) {
            this.addTableOuterSpacingFacts(layout, { emailNode });
        }
        if (emailNode.analysis.facts.acceptCellMobileMarginBottom) {
            this.applyCellMobileMarginBottom(layout, { emailNode });
        }
        if (emailNode.analysis.facts.acceptCellPaddingRight) {
            this.applyCellPaddingRight(layout, { emailNode });
        }
    }

    addTableOuterSpacingFacts(layout, { emailNode }) {
        // Rely on the spacing_plugin to build a margin wrapper
        // around the table
        // TODO EGGMAIL: replace test value
        emailNode.analysis.facts.desktopMarginStyleInfo = this.getMarginStyleInfo(
            StyleInfo.from({
                margin: "16px",
            }),
            emailNode.layout.ancestorTag
        );
    }

    applyCellMobileMarginBottom(layout, { emailNode }) {
        // TODO EGGMAIL: replace test value
        layout.setAttributes({ classNames: "o-ci-m-margin-bottom-16" });
    }

    applyCellPaddingRight(layout, { emailNode }) {
        const parent = emailNode.parent;
        if (!parent) {
            return;
        }
        // TODO EGGMAIL: replace test value
        parent.spliceChildren(
            parent.children.indexOf(emailNode) + 1,
            0,
            new EmailNode({
                layout: new EmptyCellLayout({
                    style: { width: `3%` },
                    attributes: { width: `3%` },
                }),
            })
        );
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

    acceptTableStrategyReport(emailNode) {
        return emailNode.analysis.facts.useHybridFluidTableStrategy;
    }

    fillHybridFluidContainer(emailNode) {
        if (!emailNode.analysis.facts.isHybridFluidContainer) {
            return;
        }
        const rowMeasures = this.extractRowsFromBands(emailNode);
        const firstRowMeasure = rowMeasures.at(0);
        let verticalAlign;
        if (firstRowMeasure) {
            verticalAlign = firstRowMeasure.verticalAlign;
        }
        return this.fillTableContainer(emailNode, rowMeasures, {
            withTable: false,
            builders: verticalAlign ? this.hybridBuilders : this.tableBuilders,
        });
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

    buildHybridRow() {
        return new EmailNode({ layout: new HybridFluidRow() });
    }

    buildTableRow() {
        const emailNode = new EmailNode({ layout: new HybridFluidTableRow() });
        emailNode.analysis.facts.useHybridFluidTableStrategy = true;
        emailNode.analysis.facts.acceptTableOuterSpacing = true;
        return emailNode;
    }

    buildHybridCell({ styleContext, isLast, cluster, emailNode, width, verticalAlign }) {
        const clusterEmailNodes = this.getClusterEmailNodes(emailNode, cluster);
        const refs = {
            root: {},
            styleContext,
        };
        const cellWidth = width - (isLast ? ZOOM_WIDTH_CORRECTION : 0);
        Object.assign(refs.root, {
            style: {
                "vertical-align": verticalAlign,
                "max-width": `${cellWidth}px`,
            },
        });
        const layout = new HybridFluidCell({ refs });
        const cellEmailNode = new EmailNode({
            layout,
            // TODO EGGMAIL: evaluate what positioning facts should be shared
            // and how
        });
        for (const child of clusterEmailNodes) {
            cellEmailNode.appendChild(child);
        }
        return cellEmailNode;
    }

    buildTableCell({ styleContext, isLast, cluster, emailNode, widthRatio }) {
        const clusterEmailNodes = this.getClusterEmailNodes(emailNode, cluster);
        const refs = {
            root: {},
            styleContext,
        };
        Object.assign(refs.root, {
            style: { width: `${widthRatio}%` },
            attributes: { width: `${widthRatio}%` },
        });
        const layout = new HybridFluidTableCell(refs.root);
        const cellEmailNode = new EmailNode({
            layout,
            // TODO EGGMAIL: evaluate what positioning facts should be shared
            // and how
        });
        for (const child of clusterEmailNodes) {
            cellEmailNode.appendChild(child);
        }
        if (!isLast) {
            cellEmailNode.analysis.facts.acceptCellMobileMarginBottom = true;
            cellEmailNode.analysis.facts.acceptCellPaddingRight = true;
        }
        cellEmailNode.analysis.facts.useHybridFluidTableStrategy = true;
        cellEmailNode.analysis.facts.acceptDescendantBackground = true;
        cellEmailNode.analysis.facts.acceptDescendantBorder = true;
        return cellEmailNode;
    }

    buildHybridEmptyCell({ isLast, width }) {
        const refs = { root: {} };
        const cellWidth = width - (isLast ? ZOOM_WIDTH_CORRECTION : 0);
        Object.assign(refs.root, {
            style: { "max-width": `${cellWidth}px` },
        });
        const layout = new HybridFluidEmptyCell({ refs });
        return new EmailNode({ layout });
    }

    buildTableEmptyCell({ widthRatio }) {
        const refs = { root: {} };
        Object.assign(refs.root, {
            style: { width: `${widthRatio}%` },
            attributes: { width: `${widthRatio}%` },
        });
        const layout = new EmptyCellLayout(refs.root);
        const emailNode = new EmailNode({ layout });
        emailNode.analysis.facts.useHybridFluidTableStrategy = true;
        return emailNode;
    }

    buildHybridCellWithOffset({
        styleContext,
        isLast,
        cluster,
        emailNode,
        width,
        verticalAlign,
        offsetWidth,
    }) {
        const refs = { root: {} };
        const cells = [];
        const cellOffsetWidth = offsetWidth - (isLast ? ZOOM_WIDTH_CORRECTION : 0);
        const cellWidth = width + cellOffsetWidth;
        const offsetEmailNode = this.buildHybridEmptyCell({
            verticalAlign,
            width: cellOffsetWidth,
            isLast,
        });
        const cellEmailNode = this.buildHybridCell({
            styleContext,
            cluster,
            emailNode,
            width,
            verticalAlign,
        });
        Object.assign(refs.root, { style: { "max-width": `${cellWidth}px` } });
        const cellWithOffsetEmailNode = new EmailNode({
            layout: new HybridFluidCell({ refs }),
        });
        cellWithOffsetEmailNode.appendChild(offsetEmailNode);
        cellWithOffsetEmailNode.appendChild(cellEmailNode);
        cells.push(cellWithOffsetEmailNode);
        return cells;
    }

    buildTableCellWithOffset({
        styleContext,
        isLast,
        cluster,
        emailNode,
        widthRatio,
        offsetWidthRatio,
    }) {
        const cells = [];
        const offsetEmailNode = this.buildTableEmptyCell({ widthRatio: offsetWidthRatio });
        const cellEmailNode = this.buildTableCell({
            styleContext,
            widthRatio,
            emailNode,
            cluster,
            isLast,
        });
        cells.push(offsetEmailNode, cellEmailNode);
        return cells;
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(HybridFluidStrategyPlugin.id, HybridFluidStrategyPlugin);
