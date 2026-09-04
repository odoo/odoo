import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { zip } from "@web/core/utils/arrays";
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
import { ALLOWED_MOBILE_MARGINS_SIZES, DIMENSIONS, DIRECTION_VARIANTS } from "../core/utils";

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
        "responsive",
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
            this.forcePercentWidth.bind(this),
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
        if (emailNode.analysis.facts.acceptCellNewWidth) {
            this.applyFluidCellNewWidth(layout, { emailNode });
        }
        return layout;
    }

    applyFluidCellNewWidth(layout, { emailNode }) {
        this.applyCellNewWidth(layout, { emailNode });

        // mobile margin handling
        const clusterChildren = emailNode.parent?.children.filter(
            (child) => child.analysis.facts.cluster
        );
        let bottomGap = 0;
        const index = clusterChildren?.indexOf(emailNode);
        if (
            emailNode.analysis.facts.acceptCellMobileMargin?.["bottom"] &&
            clusterChildren?.length > 0 &&
            index >= 0 &&
            index < clusterChildren.length - 1
        ) {
            const sibling = clusterChildren.at(index + 1);
            const currentRange = this.getNodeClusterRange(
                emailNode.analysis.facts.cluster.nodes.at(0),
                emailNode.analysis.facts.cluster.nodes.at(-1)
            );
            const siblingRange = this.getNodeClusterRange(
                sibling.analysis.facts.cluster.nodes.at(0),
                sibling.analysis.facts.cluster.nodes.at(-1)
            );
            let mobileRect, siblingRect;
            // TODO EGGMAIL: try to optimize this expensive computation:
            // optimization ideas: pre-compute the mobile boundingClient
            // rect for all cluster cells => cache all cells when they
            // are identified, and introduce a phase to compute this value
            // for all cells at once, once they are all identified.
            // Such phase should probably be after addSyntheticEmailNodes
            this.callWithDimensions(() => {
                mobileRect = this.getBoundingClientRect(currentRange);
                siblingRect = this.getBoundingClientRect(siblingRange);
            }, MOBILE);
            bottomGap = this.gapY(mobileRect, siblingRect);
        }
        const { referenceRect, marginRect } = emailNode.analysis.facts.tableStrategyReport.spacing;
        const paddingRect = this.containerPadding(marginRect, referenceRect);
        for (const side of DIRECTION_VARIANTS) {
            let spacing = paddingRect[side];
            if (side === "bottom" && bottomGap) {
                spacing = Math.max(spacing, bottomGap);
            }
            if (emailNode.analysis.facts.acceptCellMobileMargin?.[side] && !this.isZero(spacing)) {
                layout.setAttributes({
                    classNames: `o-ci-m-margin-${side}-${this.closestValue(
                        spacing,
                        ALLOWED_MOBILE_MARGINS_SIZES
                    )}`,
                });
            }
        }
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
            // add constraint to propagate from the responsive element (cell)
            // if the element inside the cell has a %width, it should be
            // elevated to 100%, because spacing will have been handled
            // around the responsive element
            const percentWidthConstraint = (emailNode) => {
                if (emailNode.analysis.facts["useHybridFluidTableStrategy"]) {
                    return { shouldPropagate: true };
                } else {
                    return { facts: { forcePercentWidth: 100 } };
                }
            };
            analysis.topDownConstraints.push(percentWidthConstraint);
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

    forcePercentWidth(layout, { emailNode }) {
        // TODO EGGMAIL: move this function in another plugin?
        const forcedPercentWidth = emailNode.analysis.facts.forcePercentWidth;
        if (forcedPercentWidth !== undefined) {
            const styleInfo = layout.getRef().styleInfo;
            const widthInfo = styleInfo.get("width");
            if (!widthInfo) {
                return layout;
            }
            const { value } = widthInfo;
            const parsed = parseCssValue(value);
            if (parsed.unit === "%" && parsed.number !== forcedPercentWidth) {
                widthInfo.value = `${forcedPercentWidth}%`;
            }
        }
        return layout;
    }

    acceptTableStrategyReport(emailNode) {
        return emailNode.analysis.facts.useHybridFluidTableStrategy;
    }

    fillHybridFluidContainer(emailNode) {
        if (!emailNode.analysis.facts.isHybridFluidContainer) {
            return emailNode;
        }
        const rowMeasures = this.extractRowsFromBands(emailNode.lastReferenceNode);
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
            builders: this.tableBuilders,
            // TODO EGGMAIL: remove hybridFluidStrategy completely? -> removes a lot of code and does not need custom MSO implementation
            // verticalAlign && !emailNode.analysis.facts.isResponsiveElement
            //     ? this.hybridBuilders
            // : this.tableBuilders,
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
        let isResponsiveElementCandidate;
        this.computeWithEpsilon(() => {
            // Ignore would be responsiveElements if delta is less than 3
            // pixels, as some elements inside table cells were already
            // identified to have a width difference up to 2 pixels with
            // the cell, without any css instruction to justify it.
            isResponsiveElementCandidate =
                (!this.isZero(deltaLeft) && deltaLeft > 0) ||
                (!this.isZero(deltaRight) && deltaRight > 0);
        }, 3);
        if (isResponsiveElementCandidate) {
            return (
                this.checkPredicates("is_responsive_element_predicates", {
                    container: referenceNode,
                    responsiveElement: block.bands[0].clusters[0].nodes[0],
                }) ?? true
            );
        }
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
        { needsZoomCorrection, cluster, width, verticalAlign },
        containerEmailNode
    ) {
        const clusterEmailNodes = this.getClusterEmailNodes(containerEmailNode, cluster);
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
        analysis.facts.isCell = true;
        const cellEmailNode = new EmailNode({ layout, analysis });
        cellEmailNode.analysis.facts[strategy] = true;
        for (const child of clusterEmailNodes) {
            child.analysis.facts.desktopMarginStyleInfo = this.getCellMarginStyleInfo(
                child.analysis.facts.desktopMarginStyleInfo,
                child.layout.ancestorTag
            );
            cellEmailNode.appendChild(child);
        }
        if (clusterEmailNodes.length === 1) {
            this.attemptCellMerge(cellEmailNode, clusterEmailNodes.at(0));
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

    buildHybridCellWithOffset(context, cellMeasure, containerEmailNode) {
        const { needsZoomCorrection, width, offsetWidth, offsetWidthRatio } = cellMeasure;
        const refs = { root: {} };
        const cells = [];
        const cellOffsetWidth = offsetWidth - (needsZoomCorrection ? ZOOM_WIDTH_CORRECTION : 0);
        const cellWidth = width + cellOffsetWidth;
        const offsetEmailNode = context.builders["emptyCell"](
            {
                ...cellMeasure,
                width: cellOffsetWidth,
                widthRatio: offsetWidthRatio,
                isLast: false,
                offsetWidth: undefined,
                offsetWidthRatio: undefined,
            },
            containerEmailNode
        );
        const cellEmailNode = context.builders["cell"](
            {
                ...cellMeasure,
                needsZoomCorrection: false,
                offsetWidth: undefined,
                offsetWidthRatio: undefined,
            },
            containerEmailNode
        );
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
