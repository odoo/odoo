import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { zip } from "@web/core/utils/arrays";
import { DIMENSIONS } from "../hooks";
import { Analysis, EmailNode } from "../core/render_models";
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
        "render",
        "responsiveBlock",
        "rules",
        "referenceNode",
        "spacing",
        "tableStrategy",
    ];
    resources = {
        element_layout_analysis_processors: this.analyzeElementLayout.bind(this),
        cell_ref_name_processors: [this.getCellRefName.bind(this)],
        synthetic_email_node_processors: this.fillHybridFluidContainer.bind(this),
        refine_layout_processors: [
            withSequence(DEFAULT_SPACING_SEQUENCE - 1, this.applyTableSpacing.bind(this)),
            this.applyDescendantBackground.bind(this),
            this.applyDescendantBorder.bind(this),
        ],
        accept_table_strategy_report_overrides: this.acceptTableStrategyReport.bind(this),
    };

    setup() {
        this.hybridBuilders = {};
        const hybridContext = {
            strategy: "useHybridFluidStrategy",
            row: { Layout: HybridFluidRow },
            cell: { Layout: HybridFluidCell },
            emptyCell: { Layout: HybridFluidEmptyCell },
            builders: this.hybridBuilders,
        };
        Object.assign(this.hybridBuilders, {
            row: this.buildHybridRow.bind(this, hybridContext),
            cell: this.buildHybridCell.bind(this, hybridContext),
            emptyCell: this.buildHybridEmptyCell.bind(this, hybridContext),
            cellWithOffset: this.buildHybridCellWithOffset.bind(this, hybridContext),
        });
        this.tableBuilders = {};
        const tableContext = {
            strategy: "useHybridFluidTableStrategy",
            row: { Layout: HybridFluidTableRow },
            cell: { Layout: HybridFluidTableCell },
            emptyCell: { Layout: EmptyCellLayout },
            builders: this.tableBuilders,
        };
        Object.assign(this.tableBuilders, {
            row: this.buildRow.bind(this, tableContext),
            cell: this.buildCell.bind(this, tableContext),
            emptyCell: this.buildEmptyCell.bind(this, tableContext),
            cellWithOffset: this.buildCellWithOffset.bind(this, tableContext),
        });
    }

    applyTableSpacing(layout, { emailNode }) {
        const { tableStrategyReport } = emailNode.analysis.facts;
        if (!emailNode.analysis.facts.useHybridFluidTableStrategy || !tableStrategyReport) {
            return layout;
        }
        // TODO EGGMAIL:
        // issue: currently multiple cells merge into the row and
        // multiple rows merge into the table => need filtering to decide
        // the best spacing strategy
        // need to implement tableStrategyReport data extraction to be able
        // to provide the relevant information to all "apply" function below
        // there is always the issue that the card background color only applies
        // on part of the cell and we may want to apply it on the whole cell,
        // not sure about that part since it is not technically correct, but
        // artistically it matches better what we want to do
        if (emailNode.analysis.facts.acceptTableOuterSpacing) {
            this.addTableOuterSpacingFacts(layout, { emailNode });
        }
        // apply cell margin bottom
        // - identify that the node is a tableLayout cell or a hybridTableLayout cell
        // - add the hardcoded mass_mailing_mail.css class for the closest equivalent margin
        // DONE
        if (emailNode.analysis.facts.acceptCellMobileMarginBottom) {
            this.applyCellMobileMarginBottom(layout, { emailNode });
        }
        if (emailNode.analysis.facts.acceptCellNewWidth) {
            this.applyFluidCellNewWidth(layout, { emailNode });
        }
        return layout;
    }

    applyFluidCellNewWidth(layout, { emailNode }) {
        this.applyCellNewWidth(layout, { emailNode });
        layout.setAttributes({
            classNames: "o-ci-m-horizontal-margin-16",
        });
    }

    applyCellMobileMarginBottom(layout, { emailNode }) {
        // TODO EGGMAIL: can be improved by hardcoding multiple values and
        // defining a heuristic to choose the closest one
        layout.setAttributes({ classNames: "o-ci-m-margin-bottom-16" });
    }

    analyzeElementLayout(defaultEmailNodeArguments, { referenceNode }) {
        const { layout, analysis } = defaultEmailNodeArguments;
        const div = this.config.referenceDocument.createElement("DIV");
        if (analysis.facts.isMainTable || !isAllowedContent(referenceNode, [div])) {
            return defaultEmailNodeArguments;
        }
        const isHybridFluidLayout = this.detectHybridFluidLayout(referenceNode);
        const isResponsiveElement =
            !isHybridFluidLayout && this.detectResponsiveElement(referenceNode);
        if (!isHybridFluidLayout && !isResponsiveElement) {
            return defaultEmailNodeArguments;
        } else if (isResponsiveElement) {
            analysis.facts.isResponsiveElement = true;
        }
        Object.assign(analysis.parsingFacts, {
            canMerge: false,
            needSyntheticEmailNode: true,
        });
        // TODO EGGMAIL: maybe add a generic "isContainer" fact. a "container"
        // should be a flexible node that can become e.g. a table for MSO, and
        // can be merged with its parent if they also are a container and there
        // is no positioning consideration between the 2
        analysis.facts.isHybridFluidContainer = true;
        layout.pluginIds.add(HybridFluidStrategyPlugin.id);
        return defaultEmailNodeArguments;
    }

    acceptTableStrategyReport(emailNode) {
        return emailNode.analysis.facts.useHybridFluidTableStrategy;
    }

    fillHybridFluidContainer(emailNode) {
        if (!emailNode.analysis.facts.isHybridFluidContainer) {
            return emailNode;
        }
        const rowMeasures = this.extractRowsFromBands(emailNode);
        const firstRowMeasure = rowMeasures.at(0);
        let verticalAlign;
        if (firstRowMeasure) {
            verticalAlign = firstRowMeasure.verticalAlign;
        }
        if (!verticalAlign && emailNode.analysis.facts.isResponsiveElement) {
            // force the responsive element to use hybridBuilders (which don't
            // have the tableStrategyReport, as it is not needed)
            verticalAlign = "top";
        }
        return this.fillTableContainer(emailNode, rowMeasures, {
            builders:
                verticalAlign && !emailNode.analysis.facts.isResponsiveElement
                    ? this.hybridBuilders
                    : this.tableBuilders,
        });
    }

    /**
     * TODO EGGMAIL: also consider mobile dimensions?
     */
    detectResponsiveElement(referenceNode) {
        const block = this.getLayoutBlock(referenceNode);
        if (
            !block ||
            block.bands.length !== 1 ||
            block.bands[0].clusters.length !== 1 ||
            !block.bands[0].clusters[0].isBlock
        ) {
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

    buildHybridRow({ row, strategy }) {
        const emailNode = new EmailNode({ layout: new row.Layout() });
        emailNode.analysis.facts[strategy] = true;
        return emailNode;
    }

    buildHybridCell(
        { cell, strategy },
        { needsZoomCorrection, cluster, emailNode, width, verticalAlign }
    ) {
        let clusterEmailNodes = this.getClusterEmailNodes(emailNode, cluster);
        const refs = { root: {} };
        const cellWidth = width - (needsZoomCorrection ? ZOOM_WIDTH_CORRECTION : 0);
        Object.assign(refs.root, {
            style: {
                "vertical-align": verticalAlign,
                "max-width": `${cellWidth}px`,
            },
        });
        const layout = new cell.Layout({ refs });
        const analysis = new Analysis({ parsingFacts: { canMerge: true, attemptCellMerge: true } });
        const cellEmailNode = new EmailNode({ layout, analysis });
        cellEmailNode.analysis.facts[strategy] = true;
        if (
            clusterEmailNodes.length === 1 &&
            this.attemptMerge(cellEmailNode, clusterEmailNodes.at(0))
        ) {
            clusterEmailNodes = clusterEmailNodes.at(0).children;
        }
        for (const child of clusterEmailNodes) {
            child.analysis.facts.desktopMarginStyleInfo = this.getCellMarginStyleInfo(
                child.analysis.facts.desktopMarginStyleInfo,
                child
            );
            cellEmailNode.appendChild(child);
        }
        return cellEmailNode;
    }

    buildHybridEmptyCell({ emptyCell, strategy }, { needsZoomCorrection, width }) {
        const refs = { root: {} };
        const cellWidth = width - (needsZoomCorrection ? ZOOM_WIDTH_CORRECTION : 0);
        Object.assign(refs.root, {
            style: { "max-width": `${cellWidth}px` },
        });
        const layout = new emptyCell.Layout({ refs });
        const emailNode = new EmailNode({ layout });
        emailNode.analysis.facts.isEmptyCell = true;
        emailNode.analysis.facts[strategy] = true;
        return emailNode;
    }

    buildHybridCellWithOffset(context, cellMeasure) {
        const { needsZoomCorrection, width, offsetWidth, offsetWidthRatio } = cellMeasure;
        const refs = { root: {} };
        const cells = [];
        const cellOffsetWidth = offsetWidth - (needsZoomCorrection ? ZOOM_WIDTH_CORRECTION : 0);
        const cellWidth = width + cellOffsetWidth;
        const offsetEmailNode = context.builders["emptyCell"]({
            ...cellMeasure,
            width: cellOffsetWidth,
            widthRatio: offsetWidthRatio,
            isLast: false,
            offsetWidth: undefined,
            offsetWidthRatio: undefined,
        });
        const cellEmailNode = context.builders["cell"]({
            ...cellMeasure,
            needsZoomCorrection: false,
            offsetWidth: undefined,
            offsetWidthRatio: undefined,
        });
        Object.assign(refs.root, { style: { "max-width": `${cellWidth}px` } });
        const cellWithOffsetEmailNode = new EmailNode({
            layout: new context.cell.Layout({ refs }),
        });
        cellWithOffsetEmailNode.appendChild(offsetEmailNode);
        cellWithOffsetEmailNode.appendChild(cellEmailNode);
        cells.push(cellWithOffsetEmailNode);
        return cells;
    }

    getCellRefName(refName, emailNode) {
        if (emailNode.layout instanceof HybridFluidCell) {
            return "styleContext";
        }
        return refName;
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(HybridFluidStrategyPlugin.id, HybridFluidStrategyPlugin);
