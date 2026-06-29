import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { zip } from "@web/core/utils/arrays";
import { DIMENSIONS } from "../hooks";
import { CellLayout, EmptyCellLayout, TableRowLayout } from "./table_models";
import { EmailNode } from "../core/render_models";
import { withSequence } from "@html_editor/utils/resource";
import { DEFAULT_SPACING_SEQUENCE } from "./spacing_plugin";
import { StyleInfo } from "../core/style_models";
import { Rules } from "../core/rules_models";
import { parseCssValue } from "../css_parsers";
import { isAllowedContent } from "@html_editor/utils/dom_info";

const { DESKTOP, MOBILE } = DIMENSIONS;

const VERTICAL_ALIGN = {
    start: "top",
    end: "bottom",
    center: "middle",
    "flex-start": "top",
    "flex-end": "bottom",
};

export class TableStrategyPlugin extends Plugin {
    static id = "tableStrategy";
    static dependencies = [
        "math",
        "measurementSnapshot",
        "responsiveBlock",
        "referenceNode",
        "rules",
        "spacing",
    ];
    static shared = [
        "addTableOuterSpacingFacts",
        "applyCellNewWidth",
        "applyDescendantBackground",
        "applyDescendantBorder",
        "extractRowsFromBands",
        "fillTableContainer",
        "getCellMarginStyleInfo",
        "getClusterEmailNodes",
    ];
    resources = {
        element_layout_analysis_processors: [
            this.analyzeElementLayout.bind(this),
            this.addBottomUpConstraintsForTables.bind(this),
        ],
        synthetic_email_node_processors: (emailNode) => {
            if (!emailNode.analysis.facts.isTableContainer) {
                return;
            }
            const rowMeasures = this.extractRowsFromBands(emailNode);
            return this.fillTableContainer(emailNode, rowMeasures);
        },
        refine_layout_processors: [
            withSequence(DEFAULT_SPACING_SEQUENCE - 1, this.applyTableSpacing.bind(this)),
            this.applyDescendantBackground.bind(this),
            this.applyDescendantBorder.bind(this),
        ],
        accept_table_strategy_report_overrides: this.acceptTableStrategyReport.bind(this),
    };

    setup() {
        this.builders = {
            row: this.buildRow.bind(this),
            cell: this.buildCell.bind(this),
            emptyCell: this.buildEmptyCell.bind(this),
            cellWithOffset: this.buildCellWithOffset.bind(this),
        };
        this.borderStyleRules = new Rules();
        this.backgroundStyleRules = new Rules();
        this.cellMarginStyleRules = new Rules();
        this.provideStyleRules();
    }

    provideStyleRules() {
        const borderRules = this.borderStyleRules.forPlugin(TableStrategyPlugin.id);
        const backgroundRules = this.backgroundStyleRules.forPlugin(TableStrategyPlugin.id);
        const cellMarginRules = this.cellMarginStyleRules.forPlugin(TableStrategyPlugin.id);
        borderRules.allow(/^border.*/);
        backgroundRules.allow(/^background.*/);
        cellMarginRules.allow(/^margin-(top|bottom)$/);
    }

    getCellMarginStyleInfo(styleInfo, emailNode) {
        return this.filterStyleInfo(
            styleInfo,
            emailNode.layout.ancestorTag,
            this.cellMarginStyleRules
        );
    }

    /**
     * TODO EGGMAIL NOW: WORKING HERE NOW:
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
            return;
        }
        const { styleInfo } = facts.tableStrategyReport.descendantBackground;
        layout.setAttributes({ style: styleInfo });
    }

    applyDescendantBorder(layout, { emailNode }) {
        const facts = emailNode.analysis.facts;
        const { acceptDescendantBorder, tableStrategyReport } = facts;
        const acceptTableStrategyReport = this.delegateTo(
            "accept_table_strategy_report_overrides",
            emailNode
        );
        if (!acceptTableStrategyReport || !acceptDescendantBorder || !tableStrategyReport) {
            return;
        }
        const { styleInfo } = facts.tableStrategyReport.descendantBorder;
        layout.setAttributes({ style: styleInfo });
    }

    applyTableSpacing(layout, { emailNode }) {
        if (!emailNode.analysis.facts.useTableStrategy) {
            return;
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
    }

    addTableOuterSpacingFacts(layout, { emailNode }) {
        // rely on the spacing_plugin to apply a margin node
        // TODO EGGMAIL: propagate dimensions from descendant to get a margin
        // closer to what is expected instead of a single hardcoded value
        emailNode.analysis.facts.desktopMarginStyleInfo = this.getMarginStyleInfo(
            StyleInfo.from({
                "margin-top": "16px",
                "margin-bottom": "16px",
            }),
            emailNode.layout.ancestorTag
        );
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
        const rightRatio = this.ratioPercentage(paddingRect.right, {
            inputUnit: rowWidth,
        });
        const leftRatio = this.ratioPercentage(paddingRect.left, {
            inputUnit: rowWidth,
        });
        // Padding cells
        const index = parent.children.indexOf(emailNode);
        parent.spliceChildren(
            index + 1,
            0,
            new EmailNode({
                layout: new EmptyCellLayout({
                    style: { width: `${rightRatio}%` },
                    attributes: { width: `${rightRatio}%` },
                }),
            })
        );
        parent.spliceChildren(
            index,
            0,
            new EmailNode({
                layout: new EmptyCellLayout({
                    style: { width: `${leftRatio}%` },
                    attributes: { width: `${leftRatio}%` },
                }),
            })
        );
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
     *   ancestors as a constraintsForAncestors
     *   this report should include cleanup functions that will be called when
     *   the report is accepted AND is stopped from propagating
     * - stop propagation if
     *   - the ancestor has its own tableStrategyReport
     *   - the ancestor returns true to accept_table_strategy_report_overrides
     *     and manually stops propagating the tableStrategyReport
     */
    addBottomUpConstraintsForTables({ layout, analysis }, { referenceNode, parentEmailNode }) {
        if (referenceNode.nodeType !== Node.ELEMENT_NODE) {
            return;
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
        if (borderStyleInfo.size === 0 && backgroundStyleInfo.size === 0) {
            return;
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
        analysis.constraintsForAncestors.push((emailNode) => {
            const analysis = emailNode.analysis;
            const referenceNode = emailNode.lastReferenceNode;
            const acceptTableStrategyReport = this.delegateTo(
                "accept_table_strategy_report_overrides",
                emailNode
            );
            if (acceptTableStrategyReport) {
                const report = { ...tableStrategyReport };
                const facts = { tableStrategyReport: report };
                report.spacing = { ...report.spacing, marginRect };
                const constraintsForDescendants = [];
                let shouldPropagate = true;
                if (analysis.facts.acceptTableOuterSpacing) {
                    shouldPropagate = false;
                    constraintsForDescendants.push(...tableStrategyReport.spacing.cleanup);
                }
                if (analysis.facts.acceptDescendantBorder) {
                    constraintsForDescendants.push(...tableStrategyReport.descendantBorder.cleanup);
                }
                if (analysis.facts.acceptDescendantBackground) {
                    constraintsForDescendants.push(
                        ...tableStrategyReport.descendantBackground.cleanup
                    );
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
                    constraintsForDescendants,
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
            tableStrategyReport.spacing.cleanup.push(cleanupSpacing.bind(undefined, referenceNode));
            const marginStyleInfo = analysis.facts.desktopMarginStyleInfo;
            if (marginStyleInfo.size > 0) {
                const computedStyle = this.getComputedStyle(referenceNode);
                const top = parseCssValue(computedStyle.getPropertyValue("margin-top"));
                let right;
                const bottom = parseCssValue(computedStyle.getPropertyValue("margin-bottom"));
                let left;
                if (emailNode.parent && !emailNode.parent.analysis.facts.acceptCellNewWidth) {
                    // Only consider horizontal margin if the parent is not the cell node,
                    // as margin in that case would already have been handled
                    right = parseCssValue(computedStyle.getPropertyValue("margin-right"));
                    left = parseCssValue(computedStyle.getPropertyValue("margin-left"));
                }
                marginRect = this.computeRect(referenceRect, {
                    top: -top.number,
                    right: right?.number ?? 0,
                    bottom: bottom.number,
                    left: -(left?.number ?? 0),
                });
            }
            return { shouldPropagate: true };
        });

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
    analyzeElementLayout({ layout, analysis }, { referenceNode, parentEmailNode }) {
        const div = this.config.referenceDocument.createElement("DIV");
        if (
            referenceNode.nodeName === "TR" ||
            analysis.facts.isMainTable ||
            !isAllowedContent(referenceNode, [div]) ||
            !this.detectTableLayout(referenceNode)
        ) {
            return;
        }
        Object.assign(analysis.parsingFacts, {
            canMerge: false,
            needSyntheticEmailNode: true,
        });
        analysis.facts.isTableContainer = true;
        layout.pluginIds.add(TableStrategyPlugin.id);
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

    // TODO EGGMAIL NOW (remark from hybrid_fluid_strategy_plugin)
    // MAYBE OBSOLETE COMMENT:
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
    fillTableContainer(emailNode, rowMeasures, { builders = this.builders } = {}) {
        const rows = [];
        for (const rowMeasure of rowMeasures) {
            const width = rowMeasure.width;
            const assignRowInfo = (emailNode) => {
                Object.assign(emailNode.analysis.facts, {
                    rowWidth: width,
                });
            };
            let ratio = 100;
            const rowEmailNode = builders["row"](rowMeasure);
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
                    for (const cell of builders["cellWithOffset"](cellMeasure)) {
                        assignRowInfo(cell);
                        rowEmailNode.appendChild(cell);
                    }
                } else if (cellMeasure.type === "emptyCell") {
                    const cell = builders["emptyCell"](cellMeasure);
                    assignRowInfo(cell);
                    rowEmailNode.appendChild(cell);
                } else if (cellMeasure.type === "cell") {
                    const cell = builders["cell"](cellMeasure);
                    assignRowInfo(cell);
                    rowEmailNode.appendChild(cell);
                }
            }
        }
        emailNode.spliceChildren(0, emailNode.children.length, ...rows);
    }

    extractRowsFromBands(emailNode) {
        const referenceNode = emailNode.lastReferenceNode;
        const desktopBlock = this.getLayoutBlock(referenceNode, DESKTOP);
        // TODO EGGMAIL WORKING HERE: the block width does not take into
        // account the real padding of the block, and the block padding
        // combines all centering strategies. To get the correct ratio,
        // we need to subtract the real padding of the block element here.
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
                const measures = {
                    styleContext,
                    isLast: !hasLastOffset && band.clusters.length === 1,
                    cluster: prevCluster,
                    emailNode,
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
                const measures = {
                    styleContext,
                    isLast: !hasLastOffset && i === band.clusters.length - 1,
                    cluster,
                    emailNode,
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
                    isLast: true,
                    verticalAlign,
                });
            }
            // TODO EGGMAIL: REMOVE;
            // row.cellsWidth = width;
        }
        const lastRowMeasure = rowMeasures.at(-1);
        if (lastRowMeasure) {
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

    buildRow({ isLast }) {
        const layout = new TableRowLayout();
        const emailNode = new EmailNode({ layout });
        emailNode.analysis.facts.acceptTableOuterSpacing = true;
        emailNode.analysis.facts.useTableStrategy = true;
        return emailNode;
    }

    buildCell({ styleContext, cluster, emailNode, widthRatio, verticalAlign, isLast }) {
        const clusterEmailNodes = this.getClusterEmailNodes(emailNode, cluster);
        const refs = {
            root: {},
            styleContext,
        };
        const style = { width: `${widthRatio}%` };
        if (verticalAlign) {
            style["vertical-align"] = verticalAlign;
        }
        Object.assign(refs.root, {
            style: { width: `${widthRatio}%` },
            attributes: { width: `${widthRatio}%` },
        });
        const layout = new CellLayout(refs.root);
        const cellEmailNode = new EmailNode({ layout });
        for (const child of clusterEmailNodes) {
            child.analysis.facts.desktopMarginStyleInfo = this.getCellMarginStyleInfo(
                child.analysis.facts.desktopMarginStyleInfo,
                child
            );
            cellEmailNode.appendChild(child);
        }
        if (!isLast) {
            cellEmailNode.analysis.facts.acceptCellMobileMarginBottom = true;
        }
        cellEmailNode.analysis.facts.useTableStrategy = true;
        cellEmailNode.analysis.facts.acceptCellNewWidth = true;
        cellEmailNode.analysis.facts.acceptDescendantBackground = true;
        cellEmailNode.analysis.facts.acceptDescendantBorder = true;
        return cellEmailNode;
    }

    buildEmptyCell({ widthRatio }) {
        const layout = new EmptyCellLayout({
            style: { width: `${widthRatio}%` },
            attributes: { width: `${widthRatio}%` },
        });
        const emailNode = new EmailNode({ layout });
        emailNode.analysis.facts.useTableStrategy = true;
        return emailNode;
    }

    buildCellWithOffset({
        styleContext,
        cluster,
        emailNode,
        widthRatio,
        verticalAlign,
        offsetWidthRatio,
        isLast,
    }) {
        const cells = [];
        const offsetEmailNode = this.buildEmptyCell({ widthRatio: offsetWidthRatio });
        const cellEmailNode = this.buildCell({
            styleContext,
            widthRatio,
            emailNode,
            cluster,
            verticalAlign,
            isLast,
        });
        cells.push(offsetEmailNode, cellEmailNode);
        return cells;
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(TableStrategyPlugin.id, TableStrategyPlugin);
