import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { zip } from "@web/core/utils/arrays";
import { DIMENSIONS } from "../hooks";
import { CellLayout, EmptyCellLayout, TableRowLayout } from "./table_models";
import { Analysis, ElementLayout, EmailNode } from "../core/render_models";
import { withSequence } from "@html_editor/utils/resource";
import { DEFAULT_SPACING_SEQUENCE } from "./spacing_plugin";
import { StyleInfo } from "../core/style_models";
import { Rules } from "../core/rules_models";
import { parseCssValue } from "../css_parsers";
import { isAllowedContent } from "@html_editor/utils/dom_info";

const { DESKTOP, MOBILE } = DIMENSIONS;

// align-items|self -> verticalAlign map
const VERTICAL_ALIGN = {
    start: "top",
    end: "bottom",
    center: "middle",
    "flex-start": "top",
    "flex-end": "bottom",
};

// TODO EGGMAIL: should it be completed?
const ILLEGAL_TABLE_STRATEGY_NODES = new Set(["TABLE", "TBODY", "TR", "THEAD", "TFOOT"]);

export class TableStrategyPlugin extends Plugin {
    static id = "tableStrategy";
    static dependencies = [
        "contextStyle",
        "math",
        "measurementSnapshot",
        "render",
        "responsiveBlock",
        "referenceNode",
        "rules",
        "spacing",
        "style",
    ];
    static shared = [
        "addTableOuterSpacingFacts",
        "applyCellNewWidth",
        "applyDescendantBackground",
        "applyDescendantBorder",
        "attemptCellMerge",
        "buildCell",
        "buildCellWithOffset",
        "buildEmptyCell",
        "buildRow",
        "extractRowsFromBands",
        "fillTableContainer",
        "getCellMarginStyleInfo",
        "getClusterEmailNodes",
        "getVerticalAlign",
    ];
    resources = {
        element_layout_analysis_processors: [
            this.analyzeElementLayout.bind(this),
            this.addBottomUpConstraintsForTables.bind(this),
            this.addAlignSelfConstraint.bind(this),
        ],
        merge_layout_overrides: [this.mergeCellDescendant.bind(this)],
        should_discard_reference_node_predicates: this.isUnsupportedTableElement.bind(this),
        synthetic_email_node_processors: (emailNode) => {
            if (!emailNode.analysis.facts.isTableContainer) {
                return emailNode;
            }
            const rowMeasures = this.extractRowsFromBands(emailNode.lastReferenceNode);
            return this.fillTableContainer(emailNode, rowMeasures);
        },
        refine_layout_processors: [
            withSequence(DEFAULT_SPACING_SEQUENCE - 1, this.applyTableSpacing.bind(this)),
            this.applyDescendantBackground.bind(this),
            this.applyDescendantBorder.bind(this),
            this.forceVerticalAlign.bind(this),
        ],
        accept_table_strategy_report_overrides: this.acceptTableStrategyReport.bind(this),
        merge_fact_overrides: this.mergeTableStrategyReport.bind(this),
    };

    setup() {
        this.builders = {};
        const buildContext = {
            strategy: "useTableStrategy",
            row: { Layout: TableRowLayout },
            cell: { Layout: CellLayout },
            emptyCell: { Layout: EmptyCellLayout },
            builders: this.builders,
        };
        Object.assign(this.builders, {
            row: this.buildRow.bind(this, buildContext),
            cell: this.buildCell.bind(this, buildContext),
            emptyCell: this.buildEmptyCell.bind(this, buildContext),
            cellWithOffset: this.buildCellWithOffset.bind(this, buildContext),
        });
        this.borderStyleRules = new Rules();
        this.backgroundStyleRules = new Rules();
        this.cellMarginStyleRules = new Rules();
        this.provideStyleRules();
    }

    getVerticalAlign(align) {
        return VERTICAL_ALIGN[align];
    }

    mergeTableStrategyReport({ fact, isConstraint }) {
        if (isConstraint) {
            return;
        }
        if (fact === "tableStrategyReport" || fact === "cellMargin") {
            // never overwrite tableStrategyReport or cellMargin unless it is a
            // constraint
            return true;
        }
    }

    isUnsupportedTableElement(referenceNode) {
        if (!referenceNode) {
            return;
        }
        if (referenceNode.nodeName === "COLGROUP") {
            return true;
        }
    }

    provideStyleRules() {
        const borderRules = this.borderStyleRules.forPlugin(TableStrategyPlugin.id);
        const backgroundRules = this.backgroundStyleRules.forPlugin(TableStrategyPlugin.id);
        const cellMarginRules = this.cellMarginStyleRules.forPlugin(TableStrategyPlugin.id);
        borderRules.allow(/^border.*/);
        backgroundRules.allow(/^background.*/);
        cellMarginRules.allow(/^margin-(top|bottom)$/);
    }

    /**
     * Remove horizontal margin (for the child of a cell), as
     * it won't render properly with box-sizing: content-box (cells have a
     * dimension)
     */
    getCellMarginStyleInfo(styleInfo, emailNode) {
        if (!styleInfo) {
            return styleInfo;
        }
        return this.filterStyleInfo(
            styleInfo,
            emailNode.layout.ancestorTag,
            this.cellMarginStyleRules
        );
    }

    /**
     * TODO EGGMAIL:
     * background color for card body should be applied on cell, but the
     * logic does not support it => need custo:
     * secondary report which will fight for priority over the first one
     * -> need to check in which order constraints are packed, and/or
     * use !important, because this use case does not make much sense
     * technically, but functionally it's what we want => need custom main
     * plugin
     */
    applyDescendantBackground(layout, { emailNode }) {
        const facts = emailNode.analysis.facts;
        const { acceptDescendantBackground, tableStrategyReport } = facts;
        const acceptTableStrategyReport = this.delegateTo(
            "accept_table_strategy_report_overrides",
            emailNode
        );
        if (!acceptTableStrategyReport || !acceptDescendantBackground || !tableStrategyReport) {
            return layout;
        }
        const { styleInfo } = facts.tableStrategyReport.descendantBackground;
        layout.setAttributes({ style: styleInfo });
        return layout;
    }

    applyDescendantBorder(layout, { emailNode }) {
        const facts = emailNode.analysis.facts;
        const { acceptDescendantBorder, tableStrategyReport } = facts;
        const acceptTableStrategyReport = this.delegateTo(
            "accept_table_strategy_report_overrides",
            emailNode
        );
        if (!acceptTableStrategyReport || !acceptDescendantBorder || !tableStrategyReport) {
            return layout;
        }
        const { styleInfo } = facts.tableStrategyReport.descendantBorder;
        layout.setAttributes({ style: styleInfo });
        return layout;
    }

    applyTableSpacing(layout, { emailNode }) {
        const { tableStrategyReport } = emailNode.analysis.facts;
        if (!emailNode.analysis.facts.useTableStrategy || !tableStrategyReport) {
            return layout;
        }
        // apply outer spacing
        // - identify that the node is a tableLayout or a hybridTableLayout
        // - define/override the "desktopMarginStyleInfo" as per the spacing_plugin spec
        // DONE
        // TODO EGGMAIL: replace constructor check with a named boolean fact
        // this allows to have some instances that don't have the fact
        if (emailNode.analysis.facts.acceptTableOuterSpacing) {
            this.addTableOuterSpacingFacts(layout, { emailNode });
        }
        // apply horizontal padding between cells
        // - identify that the node is a tableLayout Cell or a hybridTableLayout Cell
        // - splice horizontal padding cells inside the row
        // DONE
        // apply new dimensions in case padding cells had to be inserted
        if (emailNode.analysis.facts.acceptCellNewWidth) {
            this.applyCellNewWidth(layout, { emailNode });
        }
        return layout;
    }

    addTableOuterSpacingFacts(layout, { emailNode }) {
        const nonEmptyCells = emailNode.children.array.filter(
            (child) => !child.analysis.facts.isEmptyCell
        );
        const cellMargins = nonEmptyCells
            .map((cell) => cell.analysis.facts.cellMargin)
            .filter(Boolean);
        if (cellMargins.length !== nonEmptyCells.length) {
            return;
        }
        const rowMargin = cellMargins.reduce((acc, cur) => this.minRect(acc, cur));
        if (rowMargin.top === 0 && rowMargin.bottom === 0) {
            return;
        }
        emailNode.analysis.facts.desktopMarginStyleInfo = this.getMarginStyleInfo(
            StyleInfo.from({
                "margin-top": `${rowMargin.top}px`,
                "margin-bottom": `${rowMargin.bottom}px`,
            }),
            emailNode.layout.ancestorTag
        );
    }

    addAlignSelfConstraint(defaultEmailNodeArguments, { referenceNode, parentEmailNode }) {
        if (referenceNode.nodeType !== Node.ELEMENT_NODE) {
            return defaultEmailNodeArguments;
        }
        const rawStyle = this.getRawStyleInfo(referenceNode);
        const alignSelf = rawStyle.getPropertyValue("align-self");
        if (!(alignSelf in VERTICAL_ALIGN)) {
            return defaultEmailNodeArguments;
        }
        const verticalAlign = this.getVerticalAlign(alignSelf);
        const { analysis } = defaultEmailNodeArguments;
        analysis.bottomUpConstraints.push((emailNode) => {
            if (!emailNode.analysis.facts.isCell || emailNode.children.length !== 1) {
                return;
            }
            return { facts: { forceVerticalAlign: verticalAlign } };
        });
        return defaultEmailNodeArguments;
    }

    forceVerticalAlign(layout, { emailNode }) {
        const verticalAlign = emailNode.analysis.facts.forceVerticalAlign;
        if (!verticalAlign) {
            return layout;
        }
        const rootRef = layout.getRef();
        rootRef.styleInfo.setProperty("vertical-align", verticalAlign);
        if (rootRef.attributes.valign) {
            rootRef.attributes.valign = verticalAlign;
        }
        return layout;
    }

    applyCellNewWidth(layout, { emailNode }) {
        const parent = emailNode.parent;
        if (!parent) {
            return;
        }
        const rowWidth = emailNode.analysis.facts.rowWidth;
        const { referenceRect, marginRect } = emailNode.analysis.facts.tableStrategyReport.spacing;
        const paddingRect = this.containerPadding(marginRect, referenceRect);
        // this is correct
        const widthRatio = this.ratioPercentage(referenceRect.width, {
            inputUnit: rowWidth,
        });
        const rightRatio = this.isZero(paddingRect.right)
            ? 0
            : this.ratioPercentage(paddingRect.right, { inputUnit: rowWidth });
        const leftRatio = this.isZero(paddingRect.left)
            ? 0
            : this.ratioPercentage(paddingRect.left, { inputUnit: rowWidth });
        // Padding cells
        const index = parent.children.indexOf(emailNode);
        // TODO EGGMAIL: RTL consideration
        if (rightRatio) {
            const spacingLayout = new EmptyCellLayout({
                refs: {
                    root: {
                        style: { width: `${rightRatio}%` },
                        attributes: { width: `${rightRatio}%` },
                    },
                },
            });
            parent.spliceChildren(index + 1, 0, new EmailNode({ layout: spacingLayout }));
        }
        if (leftRatio) {
            const spacingLayout = new EmptyCellLayout({
                refs: {
                    root: {
                        style: { width: `${leftRatio}%` },
                        attributes: { width: `${leftRatio}%` },
                    },
                },
            });
            parent.spliceChildren(index, 0, new EmailNode({ layout: spacingLayout }));
        }
        // New width
        layout.setAttributes({
            style: { width: `${widthRatio}%` },
            attributes: { width: `${widthRatio}%` },
        });
    }

    /**
     * TODO EGGMAIL: move explanation to where it fits best:
     * Summary of the algorithm:
     * - element_layout_analysis_processors | addBottomUpConstraintsForTables
     *   for every reference element, during the first render tree phase,
     *   identify if there is a border/background on every element.
     * - if there is, create a tableStrategyReport that is propagated towards
     *   ancestors as a bottomUpConstraints
     *   this report should include cleanup functions that will be called when
     *   the report is accepted AND is stopped from propagating
     * - stop propagation if
     *   - the ancestor has its own tableStrategyReport
     *   - the ancestor returns true to accept_table_strategy_report_overrides
     *     and manually stops propagating the tableStrategyReport
     */
    addBottomUpConstraintsForTables(defaultEmailNodeArguments, { referenceNode, parentEmailNode }) {
        const { layout, analysis } = defaultEmailNodeArguments;
        if (referenceNode.nodeType !== Node.ELEMENT_NODE) {
            return defaultEmailNodeArguments;
        }
        const styleInfo = layout.getRef().styleInfo;
        const borderStyleInfo = this.filterStyleInfo(
            styleInfo,
            referenceNode,
            this.borderStyleRules
        );
        const backgroundStyleInfo = this.filterStyleInfo(
            styleInfo,
            referenceNode,
            this.backgroundStyleRules
        );
        if (
            (borderStyleInfo.size === 0 && backgroundStyleInfo.size === 0) ||
            // HR should not generate a table strategy report (they should keep their border)
            referenceNode.nodeName === "HR"
        ) {
            return defaultEmailNodeArguments;
        }
        const cleanupStyleInfo = (sourceStyleInfo, referenceNode, emailNode) => {
            if (!emailNode.referenceNodes.has(referenceNode)) {
                return { shouldPropagate: true };
            }
            // TODO EGGMAIL: it is possible that the element style was applied
            // on a ref different than "root", in that case the following code
            // is incorrect, to investigate.
            const styleInfo = emailNode.layout.getRef().styleInfo;
            for (const propertyName of sourceStyleInfo.keys()) {
                styleInfo.removeProperty(propertyName);
            }
        };
        const cleanupSpacing = (referenceNode, emailNode) => {
            if (!emailNode.referenceNodes.has(referenceNode)) {
                return { shouldPropagate: true };
            }
            emailNode.analysis.facts.desktopPaddingStyleInfo = undefined;
            emailNode.analysis.facts.desktopMarginStyleInfo = undefined;
        };
        const cleanupBorder = cleanupStyleInfo.bind(undefined, borderStyleInfo, referenceNode);
        const cleanupBackground = cleanupStyleInfo.bind(
            undefined,
            backgroundStyleInfo,
            referenceNode
        );
        // In a topdown traversal (existing only if the propagationReport was accepted)
        // we can search for all owners (keys) and remove their ownership by key:
        // i.e. we find the emailNode which has referenceNode in its referenceNodes,
        // then we remove all propertyInfo by key /!\ in case of merge, we may not
        // remove all that is necessary but oh well for now.
        const marginStyleInfo = analysis.facts.desktopMarginStyleInfo;
        const referenceRect = this.getBoundingClientRect(referenceNode);
        const spacingCleanup = [];
        let marginRect = { ...referenceRect };
        // The marginRect used in the tableReport should always be the second to last
        // marginRect, as the one just below the row element is already taken into
        // account by the table computation
        let storedMarginRect = { ...marginRect };
        if (marginStyleInfo.size > 0) {
            // TODO EGGMAIL: cleanup this code, as it will probably be reused
            // we probably need to check that the margin is really in px in
            // the style
            const computedStyle = this.getComputedStyle(referenceNode);
            const top = parseCssValue(computedStyle.getPropertyValue("margin-top"));
            const right = parseCssValue(computedStyle.getPropertyValue("margin-right"));
            const bottom = parseCssValue(computedStyle.getPropertyValue("margin-bottom"));
            const left = parseCssValue(computedStyle.getPropertyValue("margin-left"));
            marginRect = this.computeRect(referenceRect, {
                top: -top.number,
                right: right.number,
                bottom: bottom.number,
                left: -left.number,
            });
            spacingCleanup.push((emailNode) => {
                if (!emailNode.referenceNodes.has(referenceNode)) {
                    return { shouldPropagate: true };
                }
                emailNode.analysis.facts.desktopMarginStyleInfo = undefined;
            });
        }
        const tableStrategyReport = {
            originNode: referenceNode,
            descendantBackground: {
                styleInfo: backgroundStyleInfo,
                cleanup: [cleanupBackground],
            },
            descendantBorder: {
                styleInfo: borderStyleInfo,
                cleanup: [cleanupBorder],
            },
            spacing: {
                referenceRect,
                cleanup: spacingCleanup,
            },
        };
        analysis.facts.tableStrategyReport = tableStrategyReport;
        /**
         * algo:
         * if Node has a border and/or a background, create a "report" for nodes above
         *   (containing also margin dimensions),and reset any received "report" from descendants
         * if Node receive a "report" from a descendant, but does not have the same internal
         *   dimensions (subtracting the current padding if any) as the report dimensions
         *   (adding the report "margin" section if any), stop the report
         * if Node has a padding and/or a margin, and received a "report" from a direct descendant,
         *   and has the same internal dimensions (subtracting the padding if any) as the descendant
         *   add the margin and/or padding to the report "margin section"
         * if Node is a "stretched table cell" and receives a report compatible with its dimensions,
         *   stop the report propagation, agglomerate the report values on the related "stretched table"
         *   using the "margin section dimensions" as a "padding cells", and propagate the instruction to
         *   nullify all sources (border, bacgkround, margin, padding) of the report (towards descendants)
         *
         */
        analysis.bottomUpConstraints.push((emailNode) => {
            const analysis = emailNode.analysis;
            const referenceNode = emailNode.lastReferenceNode;
            const acceptTableStrategyReport = this.delegateTo(
                "accept_table_strategy_report_overrides",
                emailNode
            );
            if (acceptTableStrategyReport) {
                const report = { ...tableStrategyReport };
                const facts = { tableStrategyReport: report };
                report.spacing = { ...report.spacing, marginRect: storedMarginRect };
                const topDownConstraints = [];
                let shouldPropagate = true;
                if (analysis.facts.stopTableStrategyReportPropagation) {
                    shouldPropagate = false;
                }
                if (analysis.facts.acceptTableOuterSpacing) {
                    shouldPropagate = false;
                    topDownConstraints.push(...tableStrategyReport.spacing.cleanup);
                }
                if (analysis.facts.acceptDescendantBorder) {
                    topDownConstraints.push(...tableStrategyReport.descendantBorder.cleanup);
                }
                if (analysis.facts.acceptDescendantBackground) {
                    topDownConstraints.push(...tableStrategyReport.descendantBackground.cleanup);
                }
                if (analysis.facts.acceptCellNewWidth) {
                    facts.cellMargin = this.containerPadding(
                        marginRect,
                        report.spacing.referenceRect
                    );
                }
                return {
                    facts,
                    shouldPropagate,
                    topDownConstraints,
                };
            } else if (!referenceNode || analysis.facts.tableStrategyReport) {
                return { shouldPropagate: false };
            }
            const paddingStyleInfo = analysis.facts.desktopPaddingStyleInfo;
            const referenceRect = this.getBoundingClientRect(referenceNode);
            if (paddingStyleInfo.size > 0) {
                const computedStyle = this.getComputedStyle(referenceNode);
                const top = parseCssValue(computedStyle.getPropertyValue("padding-top"));
                const right = parseCssValue(computedStyle.getPropertyValue("padding-right"));
                const bottom = parseCssValue(computedStyle.getPropertyValue("padding-bottom"));
                const left = parseCssValue(computedStyle.getPropertyValue("padding-left"));
                const subPaddingRect = this.computeRect(referenceRect, {
                    top: top.number,
                    right: -right.number,
                    bottom: -bottom.number,
                    left: left.number,
                });
                if (!this.areRectEqual(subPaddingRect, marginRect)) {
                    return { shouldPropagate: false };
                }
            } else if (!this.areRectEqual(referenceRect, marginRect)) {
                return { shouldPropagate: false };
            }
            marginRect = referenceRect;
            storedMarginRect = { ...marginRect };
            tableStrategyReport.spacing.cleanup.push(cleanupSpacing.bind(undefined, referenceNode));
            const marginStyleInfo = analysis.facts.desktopMarginStyleInfo;
            if (marginStyleInfo.size > 0) {
                const computedStyle = this.getComputedStyle(referenceNode);
                const top = parseCssValue(computedStyle.getPropertyValue("margin-top"));
                const right = parseCssValue(computedStyle.getPropertyValue("margin-right"));
                const bottom = parseCssValue(computedStyle.getPropertyValue("margin-bottom"));
                const left = parseCssValue(computedStyle.getPropertyValue("margin-left"));
                marginRect = this.computeRect(referenceRect, {
                    top: -top.number,
                    right: right.number,
                    bottom: bottom.number,
                    left: -left.number,
                });
                // const computedStyle = this.getComputedStyle(referenceNode);
                // const top = parseCssValue(computedStyle.getPropertyValue("margin-top"));
                // let right;
                // const bottom = parseCssValue(computedStyle.getPropertyValue("margin-bottom"));
                // let left;
                // if (emailNode.parent && !emailNode.parent.analysis.facts.acceptCellNewWidth) {
                //     // Only consider horizontal margin if the parent is not the cell node,
                //     // as margin in that case would already have been handled
                //     right = parseCssValue(computedStyle.getPropertyValue("margin-right"));
                //     left = parseCssValue(computedStyle.getPropertyValue("margin-left"));
                // }
                // marginRect = this.computeRect(referenceRect, {
                //     top: -top.number,
                //     right: right?.number ?? 0,
                //     bottom: bottom.number,
                //     left: -(left?.number ?? 0),
                // });
            }
            return { shouldPropagate: true };
        });
        return defaultEmailNodeArguments;

        // get margin info as ownership, and computed style to get the
        // final margin rectangle.
        // for comparison, ancestors rect - padding should match the marginRect
        // if true, add padding and margin of the ancestor to the marginrect
        // if false, end the report propagation
        // if an ancestor element also has a report, end the report propagation
        // if an ancestor match the dimensions, and also has the relevant acceptance
        // fact, => take the info and continue propagating the rest up to the table.
        // acceptTableOuterSpacing always terminates the propagation

        // check margin:
        // can check desktopMarginStyleInfo and desktopPaddingStyleInfo, were
        // added during addSpacingFacts
        // check border:
        // use a rule to extract the border style info from the layout styleinfo
        // if not empty => match
        // check background:
        // use a rule to extract the background style info from the layout styleinfo
        // if not empty => match
        // need internal dimensions to compare to ancestors and potentially stop the propagation
    }

    acceptTableStrategyReport(emailNode) {
        return emailNode.analysis.facts.useTableStrategy;
    }

    // TODO EGGMAIL NOW: special case for the first element inside the reference:
    // - basic editor case (investigate)
    // - builder case (convert to mega wrapper table + background color -> smaller table (mail_wrapper) with margin)
    // - unknown case (add mega wrapper table -> can use "reference" element for this, if mega table strategy was not applied
    // below)
    analyzeElementLayout(defaultEmailNodeArguments, { referenceNode, parentEmailNode }) {
        const { layout, analysis } = defaultEmailNodeArguments;
        const div = this.config.referenceDocument.createElement("DIV");
        if (
            ILLEGAL_TABLE_STRATEGY_NODES.has(referenceNode.nodeName) ||
            analysis.facts.isMainTable ||
            !isAllowedContent(referenceNode, [div]) ||
            !this.detectTableLayout(referenceNode)
        ) {
            return defaultEmailNodeArguments;
        }
        Object.assign(analysis.parsingFacts, {
            canMerge: false,
            needSyntheticEmailNode: true,
        });
        analysis.facts.isTableContainer = true;
        layout.pluginIds.add(TableStrategyPlugin.id);
        return defaultEmailNodeArguments;
    }

    mergeCellDescendant(parentEmailNode, { layout, analysis }) {
        if (!parentEmailNode.analysis.parsingFacts.attemptCellMerge) {
            return;
        }
        if (
            layout instanceof ElementLayout &&
            layout.tag === "DIV" &&
            !this.hasMarginSpacing(analysis) &&
            !this.hasPaddingSpacing(analysis)
        ) {
            // need to know which ref has to receive the "DIV" info
            const refName = this.processThrough(
                "cell_ref_name_processors",
                "root",
                parentEmailNode
            );
            const ref = layout.getRef();
            const styleInfo = ref.style;
            // TODO EGGMAIL: handle the following properly with rules, evaluate
            // what other properties should be removed
            // Only the resulting layout (from parentEmailNode) can determine
            // the display mode.
            styleInfo.removeProperty("display");
            parentEmailNode.layout.setAttributes(ref, refName);
            return true;
        }
    }

    // TODO EGGMAIL: evaluate how float: left/right behave, will it match
    // this table detection algo or does it need a custom one?
    // -> can support it with a specific table layout
    // -> not critical, as we don't use it currently, but would be great for
    // design flexibility
    // TODO EGGMAIL: currently a table is not well represented in the final
    // email (some style is lost and the table is not "stretched" horizontally)
    // TODO EGGMAIL: currently a table with 2 rows of 1 column won't be
    // considered a "table"
    // should we look for "invalid" nodes such as tbody? Or make a whitelist of
    // tagNames and convert unknown tag names to div or span?
    // ideally email strategies should render nodes that can be in any block
    // and few exceptions (table) should verify that they don't have a table
    // as their direct ancestor
    detectTableLayout(referenceNode) {
        let isTableCandidate = false;
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
            if (dBand.clusters.length !== mBand.clusters.length) {
                return;
            }
            if (dBand.clusters.length > 1) {
                isTableCandidate = true;
            }
        }
        return isTableCandidate;
    }

    fillTableContainer(containerEmailNode, rowMeasures, { builders = this.builders } = {}) {
        const rows = [];
        for (const rowMeasure of rowMeasures) {
            const width = rowMeasure.width;
            const assignRowInfo = (emailNode) => {
                Object.assign(emailNode.analysis.facts, {
                    rowWidth: width,
                });
            };
            let ratio = 100;
            const rowEmailNode = builders["row"](rowMeasure, containerEmailNode);
            rows.push(rowEmailNode);
            for (const cellMeasure of rowMeasure.children) {
                const widthRatio = this.ratioPercentage(cellMeasure.width, {
                    inputUnit: width,
                    percentageLeft: ratio,
                });
                cellMeasure.widthRatio = widthRatio;
                ratio -= widthRatio;
                if (cellMeasure.type === "cellWithOffset") {
                    cellMeasure.offsetWidthRatio = this.ratioPercentage(cellMeasure.offsetWidth, {
                        inputUnit: width,
                        percentageLeft: ratio,
                    });
                    ratio -= cellMeasure.offsetWidthRatio;
                    for (const cell of builders["cellWithOffset"](
                        cellMeasure,
                        containerEmailNode
                    )) {
                        assignRowInfo(cell);
                        rowEmailNode.appendChild(cell);
                    }
                } else if (cellMeasure.type === "emptyCell") {
                    const cell = builders["emptyCell"](cellMeasure, containerEmailNode);
                    assignRowInfo(cell);
                    rowEmailNode.appendChild(cell);
                } else if (cellMeasure.type === "cell") {
                    const cell = builders["cell"](cellMeasure, containerEmailNode);
                    assignRowInfo(cell);
                    rowEmailNode.appendChild(cell);
                }
            }
        }
        // TODO EGGMAIL: do we need to keep the emailNode if it's a div?
        // At least when it is neutral and has no margin/padding we could
        // replace it by the rows directly
        containerEmailNode.spliceChildren(0, containerEmailNode.children.length, ...rows);
        return containerEmailNode;
    }

    extractRowsFromBands(referenceNode) {
        const desktopBlock = this.getLayoutBlock(referenceNode, DESKTOP);
        // TODO EGGMAIL: export this computation somewhere, it is used multiple times
        const computedStyle = this.getComputedStyle(desktopBlock.element);
        const top = parseCssValue(computedStyle.getPropertyValue("padding-top"));
        const right = parseCssValue(computedStyle.getPropertyValue("padding-right"));
        const bottom = parseCssValue(computedStyle.getPropertyValue("padding-bottom"));
        const left = parseCssValue(computedStyle.getPropertyValue("padding-left"));
        const subPaddingRect = this.computeRect(desktopBlock.rect, {
            top: top.number,
            right: -right.number,
            bottom: -bottom.number,
            left: left.number,
        });
        // TODO EGGMAIL: some values for text-align are not supported
        // getStylePropertyValue should probably filter values and only
        // return what is allowed
        // TODO EGGMAIL: style should probably be refined in this fragment
        const contextStyleInfo = this.getTableContextStyleInfo(referenceNode);
        // TODO EGGMAIL: approximate vertical alignment support:
        // start/center/end/stretch -> default stretch
        const verticalAlign = this.getVerticalAlign(
            this.getStylePropertyValue(referenceNode, "align-items")
        );
        // STEP 1: construct measure bundles
        const rowMeasures = [];
        for (const band of desktopBlock.bands) {
            const row = { verticalAlign, children: [], width: subPaddingRect.width };
            rowMeasures.push(row);
            let prevCluster;
            // TODO EGGMAIL RTL
            let rightOffset = 0;
            let leftOffset = 0;
            const lastCluster = band.clusters.at(-1);
            const firstCluster = band.clusters.at(0);
            if (lastCluster) {
                ({ right: rightOffset } = this.containerPadding(subPaddingRect, lastCluster.rect));
                ({ left: leftOffset } = this.containerPadding(subPaddingRect, firstCluster.rect));
            }
            const hasLastOffset = !this.isZero(rightOffset);
            if (band.clusters.length > 0) {
                prevCluster = band.clusters[0];
                const isLast = band.clusters.length === 1;
                const needsZoomCorrection = !hasLastOffset && isLast;
                const measures = {
                    contextStyleInfo,
                    needsZoomCorrection,
                    isLast,
                    cluster: prevCluster,
                    width: prevCluster.rect.width,
                    verticalAlign,
                };
                if (!this.isZero(leftOffset)) {
                    const offsetWidth = leftOffset;
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
                const isLast = i === band.clusters.length - 1;
                const needsZoomCorrection = !hasLastOffset && isLast;
                const measures = {
                    contextStyleInfo,
                    needsZoomCorrection,
                    isLast,
                    cluster,
                    width: cluster.rect.width,
                    verticalAlign,
                };
                if (gap > 0) {
                    row.children.push(
                        Object.assign({ type: "cellWithOffset", offsetWidth: gap }, measures)
                    );
                } else {
                    row.children.push(Object.assign({ type: "cell" }, measures));
                }
                prevCluster = cluster;
            }
            if (hasLastOffset) {
                row.children.push({
                    type: "emptyCell",
                    width: rightOffset,
                    needsZoomCorrection: true,
                    verticalAlign,
                });
            }
        }
        const firstRowMeasure = rowMeasures.at(0);
        const lastRowMeasure = rowMeasures.at(-1);
        if (firstRowMeasure) {
            firstRowMeasure.isFirst = true;
            lastRowMeasure.isLast = true;
        }
        return rowMeasures;
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

    buildRow({ row, strategy }, { verticalAlign }) {
        const layout = new row.Layout();
        const emailNode = new EmailNode({ layout });
        if (!verticalAlign) {
            emailNode.analysis.facts.acceptTableOuterSpacing = true;
        }
        emailNode.analysis.facts[strategy] = true;
        return emailNode;
    }

    buildCell(
        { cell, strategy },
        { contextStyleInfo, cluster, widthRatio, verticalAlign, isLast },
        containerEmailNode
    ) {
        const clusterEmailNodes = this.getClusterEmailNodes(containerEmailNode, cluster);
        const refs = { root: {} };
        const style = { width: `${widthRatio}%` };
        const attributes = { width: `${widthRatio}%` };
        if (verticalAlign) {
            style["vertical-align"] = verticalAlign;
            attributes.valign = verticalAlign;
        }
        Object.assign(refs.root, {
            style: StyleInfo.from(style).merge(contextStyleInfo),
            attributes,
        });
        const layout = new cell.Layout({ refs });
        const analysis = new Analysis({ parsingFacts: { canMerge: true, attemptCellMerge: true } });
        analysis.facts.isCell = true;
        const cellEmailNode = new EmailNode({ layout, analysis });
        if (!verticalAlign) {
            if (!isLast) {
                cellEmailNode.analysis.facts.acceptCellMobileMarginBottom = true;
            }
            cellEmailNode.analysis.facts.acceptCellNewWidth = true;
            cellEmailNode.analysis.facts.acceptDescendantBackground = true;
            cellEmailNode.analysis.facts.acceptDescendantBorder = true;
        }
        cellEmailNode.analysis.facts[strategy] = true;
        for (const child of clusterEmailNodes) {
            child.analysis.facts.desktopMarginStyleInfo = this.getCellMarginStyleInfo(
                child.analysis.facts.desktopMarginStyleInfo,
                child
            );
            cellEmailNode.appendChild(child);
        }
        if (clusterEmailNodes.length === 1) {
            this.attemptCellMerge(cellEmailNode, clusterEmailNodes.at(0));
        }
        return cellEmailNode;
    }

    attemptCellMerge(cellEmailNode, emailNode) {
        if (this.attemptMerge(cellEmailNode, emailNode)) {
            for (const child of cellEmailNode.children) {
                child.analysis.facts.desktopMarginStyleInfo = this.getCellMarginStyleInfo(
                    child.analysis.facts.desktopMarginStyleInfo,
                    child
                );
            }
        }
    }

    buildEmptyCell({ emptyCell, strategy }, { widthRatio }) {
        const layout = new emptyCell.Layout({
            refs: {
                root: {
                    style: { width: `${widthRatio}%` },
                    attributes: { width: `${widthRatio}%` },
                },
            },
        });
        const emailNode = new EmailNode({ layout });
        emailNode.analysis.facts.isEmptyCell = true;
        emailNode.analysis.facts[strategy] = true;
        return emailNode;
    }

    buildCellWithOffset(context, cellMeasure, containerEmailNode) {
        const cells = [];
        const offsetEmailNode = context.builders["emptyCell"](
            {
                ...cellMeasure,
                width: cellMeasure.offsetWidth,
                widthRatio: cellMeasure.offsetWidthRatio,
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
        cells.push(offsetEmailNode, cellEmailNode);
        return cells;
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(TableStrategyPlugin.id, TableStrategyPlugin);
