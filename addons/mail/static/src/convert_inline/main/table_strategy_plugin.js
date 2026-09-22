import { registry } from "@web/core/registry";
import { Plugin } from "@mail/convert_inline/plugin";
import { zip } from "@web/core/utils/arrays";
import {
    CellLayout,
    EmptyCellLayout,
    TableRowLayout,
} from "@mail/convert_inline/main/table_models";
import { Analysis, ElementLayout, EmailNode } from "@mail/convert_inline/core/render_models";
import { withSequence } from "@html_editor/utils/resource";
import { DEFAULT_SPACING_SEQUENCE } from "@mail/convert_inline/main/spacing_plugin";
import { StyleInfo } from "@mail/convert_inline/core/style_models";
import { Rules } from "@mail/convert_inline/core/rules_models";
import { parseCssValue } from "@mail/convert_inline/css_parsers";
import { isAllowedContent } from "@html_editor/utils/dom_info";
import { DIMENSIONS } from "@mail/convert_inline/core/utils";

const { DESKTOP, MOBILE } = DIMENSIONS;

// align-items|self -> verticalAlign map
const VERTICAL_ALIGN = {
    start: "top",
    end: "bottom",
    center: "middle",
    stretch: "top",
    "flex-start": "top",
    "flex-end": "bottom",
    "flow-start": "top",
    "flow-end": "bottom",
};

const ILLEGAL_TABLE_STRATEGY_NODES = new Set(["TABLE", "TBODY", "TR", "THEAD", "TFOOT"]);

export class TableStrategyPlugin extends Plugin {
    static id = "tableStrategy";
    static dependencies = [
        "border",
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
        "attemptCellMerge",
        "buildCell",
        "buildCellWithOffset",
        "buildEmptyCell",
        "buildRow",
        "extractRowsFromBands",
        "fillTableContainer",
        "getCellBackgroundStyleInfo",
        "getCellMarginStyleInfo",
        "getClusterEmailNodes",
        "getVerticalAlign",
    ];
    resources = {
        element_layout_analysis_processors: [
            this.analyzeElementLayout.bind(this),
            this.addBottomUpConstraintsForTables.bind(this),
            this.addAlignSelfConstraint.bind(this),
            this.addCenterHRConstraint.bind(this),
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
            this.forceTextAlign.bind(this),
        ],
        accept_table_strategy_report_overrides: this.acceptTableStrategyReport.bind(this),
        merge_fact_overrides: this.mergeTableStrategyReport.bind(this),
        table_strategy_cell_background_style_rules_processors:
            this.provideCellBackgroundStyleRules.bind(this),
        table_strategy_cell_margin_style_rules_processors:
            this.provideCellMarginStyleRules.bind(this),
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
        this.backgroundStyleRules = this.processRules(
            "table_strategy_cell_background_style_rules_processors",
            new Rules()
        );
        this.cellMarginStyleRules = this.processRules(
            "table_strategy_cell_margin_style_rules_processors",
            new Rules()
        );
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

    provideCellBackgroundStyleRules(rules) {
        rules.allow(/^background.*/);
    }

    provideCellMarginStyleRules(rules) {
        rules.allow(/^margin-(top|bottom)$/);
    }

    getCellBackgroundStyleInfo(styleInfo, referenceNode) {
        if (!styleInfo) {
            return styleInfo;
        }
        return this.filterStyleInfo(styleInfo, referenceNode, this.backgroundStyleRules);
    }

    /**
     * Remove horizontal margin (for the child of a cell), as
     * it won't render properly with box-sizing: content-box (cells have a
     * dimension)
     */
    getCellMarginStyleInfo(styleInfo, referenceNode) {
        if (!styleInfo) {
            return styleInfo;
        }
        return this.filterStyleInfo(styleInfo, referenceNode, this.cellMarginStyleRules);
    }

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
        if (emailNode.analysis.facts.acceptTableOuterSpacing) {
            this.addTableOuterSpacingFacts(layout, { emailNode });
        }
        if (emailNode.analysis.facts.acceptCellNewWidth) {
            this.applyCellNewWidth(layout, { emailNode });
        }
        return layout;
    }

    addTableOuterSpacingFacts(layout, { emailNode }) {
        const nonEmptyCells = emailNode.children.filter(
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

    addCenterHRConstraint(defaultEmailNodeArguments, { referenceNode }) {
        if (!referenceNode.matches?.(":scope:has(> .s_hr:only-child)")) {
            return defaultEmailNodeArguments;
        }
        const { analysis } = defaultEmailNodeArguments;
        analysis.bottomUpConstraints.push((emailNode) => {
            if (!emailNode.analysis.facts.isCell || emailNode.children.length !== 1) {
                return;
            }
            return {
                facts: { forceTextAlign: "center" },
                topDownConstraints: [
                    () => ({
                        shouldPropagate: true,
                        facts: {
                            spacingContextStyleInfo: StyleInfo.from({ "text-align": "center" }),
                        },
                    }),
                ],
            };
        });
        return defaultEmailNodeArguments;
    }

    addAlignSelfConstraint(defaultEmailNodeArguments, { referenceNode }) {
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

    forceTextAlign(layout, { emailNode }) {
        const textAlign = emailNode.analysis.facts.forceTextAlign;
        if (!textAlign || !emailNode.analysis.facts.isCell) {
            return layout;
        }
        const ref = layout.getRef();
        ref.styleInfo.setProperty("text-align", textAlign);
        if (ref.attributes.align) {
            ref.attributes.align = textAlign;
        }
        return layout;
    }

    forceVerticalAlign(layout, { emailNode }) {
        const verticalAlign = emailNode.analysis.facts.forceVerticalAlign;
        if (!verticalAlign || !emailNode.analysis.facts.isCell) {
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
     * Summary of the algorithm:
     * - element_layout_analysis_processors | addBottomUpConstraintsForTables
     *   for every reference element, during the first render tree phase,
     *   identify if there is a border/background on every element.
     * - if there is, create a tableStrategyReport that is propagated towards
     *   ancestors as a bottomUpConstraints
     *   this report includes cleanup functions that will be called when
     *   the report is accepted AND is stopped from propagating
     */
    addBottomUpConstraintsForTables(defaultEmailNodeArguments, { referenceNode }) {
        const { layout, analysis } = defaultEmailNodeArguments;
        if (referenceNode.nodeType !== Node.ELEMENT_NODE) {
            return defaultEmailNodeArguments;
        }
        const styleInfo = layout.getRef().styleInfo;
        const borderStyleInfo = this.getBorderStyleInfo(styleInfo, referenceNode);
        if (borderStyleInfo.getPropertyValue("border-radius")) {
            // borderStyleInfo will be applied on an ancestor, and the
            // descendant should be hidden below to appear to have the
            // radius.
            borderStyleInfo.setProperty("overflow", "hidden", "important");
        }
        const backgroundStyleInfo = this.getCellBackgroundStyleInfo(styleInfo, referenceNode);
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
            // TODO EGGMAIL: it is technically possible that the element style
            // was applied on a ref different than "root", in that case the
            // following code is incorrect, to fix when issues arise.
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
        // remove all that is necessary.
        const referenceRect = this.getBoundingClientRect(referenceNode);
        const spacingCleanup = [];
        let marginRect = { ...referenceRect };
        // The marginRect used in the tableReport should always be the second to last
        // marginRect, as the one just below the row element is already taken into
        // account by the table computation.
        let storedMarginRect = { ...marginRect };
        if (this.hasMarginSpacing(analysis)) {
            // TODO EGGMAIL: cleanup this code, eg it probably needs to check
            // that the margin is really in px in the style.
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
            const referenceRect = this.getBoundingClientRect(referenceNode);
            if (this.hasPaddingSpacing(analysis)) {
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
            if (this.hasMarginSpacing(analysis)) {
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
            }
            return { shouldPropagate: true };
        });
        return defaultEmailNodeArguments;
    }

    acceptTableStrategyReport(emailNode) {
        return emailNode.analysis.facts.useTableStrategy;
    }

    analyzeElementLayout(defaultEmailNodeArguments, { referenceNode }) {
        const { analysis } = defaultEmailNodeArguments;
        const div = this.config.referenceDocument.createElement("DIV");
        if (
            ILLEGAL_TABLE_STRATEGY_NODES.has(referenceNode.nodeName) ||
            analysis.facts.isMainTable ||
            !isAllowedContent(referenceNode, [div]) ||
            !this.detectTableLayout(referenceNode)
        ) {
            return defaultEmailNodeArguments;
        }
        Object.assign(analysis.buildDirectives, {
            canMerge: false,
            needSyntheticEmailNode: true,
        });
        analysis.facts.isTableContainer = true;
        return defaultEmailNodeArguments;
    }

    mergeCellDescendant(parentEmailNode, { layout, analysis }) {
        if (!parentEmailNode.analysis.facts.attemptCellMerge) {
            return;
        }
        if (
            layout instanceof ElementLayout &&
            layout.tag === "DIV" &&
            !this.hasMarginSpacing(analysis) &&
            !this.hasPaddingSpacing(analysis)
        ) {
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
        const contextStyleInfo = this.getTableContextStyleInfo(referenceNode);
        // TODO EGGMAIL: some values for text-align are not supported
        // getStylePropertyValue should probably filter values and only
        // return what is allowed
        const verticalAlign = this.getVerticalAlign(
            this.getStylePropertyValue(referenceNode, "align-items")
        );
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
                    isFirst: true,
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
            const queue = [childEmailNode];
            for (let i = 0; i < queue.length; i++) {
                const candidate = queue[i];
                if (candidate.firstReferenceNode) {
                    // Simplification, to invalidate against real cases if need be:
                    // only consider the firstReferenceNode for cluster attribution
                    if (range.comparePoint(candidate.firstReferenceNode, 0) === 0) {
                        clusterEmailNodes.push(childEmailNode);
                    }
                    // Simplification, to invalidate against real cases if need be:
                    // assume that if a firstReferenceNode was not part of the
                    // cluster, no firstReferenceNode from other EmailNode will
                    break;
                }
                // For synthetic EmailNode without referenceNodes, consider their
                // descendants for cluster attribution.
                queue.push(...candidate.children);
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
        { contextStyleInfo, cluster, widthRatio, verticalAlign, isLast, isFirst },
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
        const analysis = new Analysis({
            facts: { attemptCellMerge: true },
            buildDirectives: { canMerge: true },
        });
        analysis.facts.isCell = true;
        const cellEmailNode = new EmailNode({ layout, analysis });
        if (!verticalAlign) {
            Object.assign(cellEmailNode.analysis.facts, {
                acceptCellMobileMargin: {
                    top: !isFirst,
                    right: true,
                    bottom: !isLast,
                    left: true,
                },
                acceptCellNewWidth: true,
                acceptDescendantBackground: true,
                acceptDescendantBorder: true,
            });
        }
        cellEmailNode.analysis.facts[strategy] = true;
        cellEmailNode.analysis.facts.cluster = cluster;
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

    attemptCellMerge(cellEmailNode, emailNode) {
        if (this.attemptMerge(cellEmailNode, emailNode)) {
            for (const child of cellEmailNode.children) {
                child.analysis.facts.desktopMarginStyleInfo = this.getCellMarginStyleInfo(
                    child.analysis.facts.desktopMarginStyleInfo,
                    child.layout.ancestorTag
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
