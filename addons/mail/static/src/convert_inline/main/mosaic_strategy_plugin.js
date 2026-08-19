import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { CellLayout, EmptyCellLayout, RowLayout, TableLayout } from "./table_models";
import { Analysis, assignDefaultElementOptions, EmailNode } from "../core/render_models";
import { StyleInfo } from "../core/style_models";
import { CONTOUR_VARIANTS, DIRECTION_VARIANTS, OPPOSITE_DIRECTION } from "../core/utils";
import { parseCssValue } from "../css_parsers";

export class MosaicStrategyPlugin extends Plugin {
    static id = "mosaicStrategy";
    static dependencies = [
        "border",
        "contextStyle",
        "math",
        "measurementSnapshot",
        "hybridFluidStrategy",
        "tableStrategy",
    ];
    resources = {
        accept_table_strategy_report_overrides: this.acceptTableStrategyReport.bind(this),
        element_layout_analysis_processors: this.analyzeElementLayout.bind(this),
        synthetic_email_node_processors: this.processSyntheticEmailNodes.bind(this),
        on_measure_ancestor_handlers: [
            this.handleOverlappingBorders.bind(this),
            this.handleOverlappingBackgroundColors.bind(this),
        ],
    };

    acceptTableStrategyReport(emailNode) {
        return emailNode.analysis.facts.useMosaicStrategy;
    }

    analyzeElementLayout(defaultEmailNodeArguments, { referenceNode, parentEmailNode }) {
        const { layout, analysis } = defaultEmailNodeArguments;
        if (
            !analysis.facts.isTableContainer &&
            (!analysis.facts.isHybridFluidContainer || analysis.facts.isResponsiveElement)
        ) {
            return defaultEmailNodeArguments;
        }
        const cellsProviders = this.processThrough(
            "mosaic_cells_providers_processors",
            [],
            defaultEmailNodeArguments,
            { referenceNode, parentEmailNode }
        );
        if (cellsProviders.length === 0) {
            return defaultEmailNodeArguments;
        }
        delete analysis.facts.isHybridFluidContainer;
        delete analysis.facts.isTableContainer;
        Object.assign(analysis.parsingFacts, {
            canMerge: false,
            needSyntheticEmailNode: true,
            isSkippingContainer: true,
            skippingContainerDescendantProviders: cellsProviders,
        });
        analysis.facts.isMosaicContainer = true;
        analysis.facts.cellsProviders = cellsProviders;
        layout.pluginIds.add(MosaicStrategyPlugin.id);
        return defaultEmailNodeArguments;
    }
    // TODO EGGMAIL: cleanup comment/docstring
    // request for mosaic cells providers => check ancestor snippet class
    // s_comparisons -> card (columns) -> card-body | card-footer = cells
    // approximation: align card-bodies and card-footers in a table of 2 rows
    // that is a better approximation than a table of 2 columns 1 row.
    //
    // s_masonry_block -> data-name="Block" (cells) => position each block
    // using the boundingclientrect
    //
    // neutralize isTableContainer and isHybridFluidContainer if a provider
    // exists. Compute final table dimensions using desktop geometry
    // compute final mobile dimensions using mobile geometry?
    // TODO EGGMAIL: while skipping nodes, we may loose background color
    // or border info or outside-paddings think of a way to recover them
    extractTableInfo(emailNode) {
        // 1) Determine the table matrix in which children (cells) fit (mosaic)
        const rectToEmailNode = new Map();
        for (const childEmailNode of emailNode.children) {
            const node = childEmailNode.firstReferenceNode;
            const rect = this.getBoundingClientRect(node);
            rectToEmailNode.set(rect, childEmailNode);
        }
        const rects = [...rectToEmailNode.keys()];
        const filterSimilarValues = (values) =>
            values
                .reduce(
                    (accumulator, v) => {
                        const aggregate = accumulator.at(-1);
                        if (aggregate.length === 0 || this.isZero(aggregate.at(-1) - v)) {
                            aggregate.push(v);
                        } else {
                            accumulator.push([v]);
                        }
                        return accumulator;
                    },
                    [[]]
                )
                .map(
                    (aggregate) =>
                        aggregate.reduce((total, v) => total + v, 0) / (aggregate.length || 1)
                );
        const containerRect = this.getBoundingClientRect(emailNode.lastReferenceNode);
        const xs = filterSimilarValues(
            rects
                .flatMap((r) => [r.left, r.right])
                .concat([containerRect.left, containerRect.right])
                .sort((a, b) => a - b)
        );
        const ys = filterSimilarValues(
            rects
                .flatMap((r) => [r.top, r.bottom])
                .concat([containerRect.top, containerRect.bottom])
                .sort((a, b) => a - b)
        );
        // 2) Compute metrics useful to build the html table
        let ratio = 100;
        const heights = ys.reduce((heights, y, i) => {
            if (i === 0) {
                return heights;
            }
            const height = y - ys[i - 1];
            heights.push({ height });
            return heights;
        }, []);
        const tableWidth = containerRect.width;
        const widths = xs.reduce((widths, x, i) => {
            if (i === 0) {
                return widths;
            }
            const width = x - xs[i - 1];
            const widthRatio = this.ratioPercentage(width, {
                inputUnit: tableWidth,
                percentageLeft: ratio,
            });
            ratio -= widthRatio;
            widths.push({
                width,
                widthRatio,
            });
            return widths;
        }, []);
        const getWidth = (col, colspan) => {
            const result = { width: 0, widthRatio: 0 };
            for (let i = col; i < col + colspan; i++) {
                result.width += widths[i].width;
                result.widthRatio += widths[i].widthRatio;
            }
            return result;
        };
        // 3) Define cells characteristics for the html table
        const columnCount = xs.length - 1;
        const rowCount = ys.length - 1;
        const computeCellInfo = (rect) => {
            const col = xs.findIndex((x) => this.isZero(rect.left - x));
            const row = ys.findIndex((y) => this.isZero(rect.top - y));
            const nextCol = xs.findIndex((x) => this.isZero(rect.right - x));
            const nextRow = ys.findIndex((y) => this.isZero(rect.bottom - y));
            const colspan = nextCol - col;
            const rowspan = nextRow - row;
            return { col, row, colspan, rowspan };
        };
        const cells = rects.map((rect) => {
            const { col, row, colspan, rowspan } = computeCellInfo(rect);
            const cellEmailNode = rectToEmailNode.get(rect);
            return {
                col,
                row,
                colspan,
                rowspan,
                emailNode: cellEmailNode,
                referenceNode: cellEmailNode.firstReferenceNode,
                ...getWidth(col, colspan),
                styleInfo: new StyleInfo(),
            };
        });
        // 4) Build the occupancy matrix, and compute spacer cells that will
        //   fill up the table. Aggregate spacers cells vertically whenever
        //   possible.
        const rows = new Set(Array.from({ length: rowCount }, (_, i) => i));
        const rowsWithHeight = new Map();
        const occupied = Array.from({ length: rowCount }, () => Array(columnCount).fill(null));
        for (const cell of cells) {
            for (let row = cell.row; row < cell.row + cell.rowspan; row++) {
                for (let col = cell.col; col < cell.col + cell.colspan; col++) {
                    occupied[row][col] = cell;
                    if (!rowsWithHeight.has(row) && cell.rowspan === 1) {
                        rowsWithHeight.set(row, cell);
                    }
                }
            }
        }
        const spacerCells = new Set();
        for (let col = 0; col < columnCount; col++) {
            let cell;
            for (let row = 0; row < rowCount; row++) {
                if (occupied[row][col] === null) {
                    if (cell && cell.row + cell.rowspan === row) {
                        cell.rowspan++;
                        occupied[row][col] = cell;
                        cell.height += heights[row].height;
                    } else {
                        cell = {
                            col,
                            row,
                            colspan: 1,
                            rowspan: 1,
                            ...getWidth(col, 1),
                            styleInfo: new StyleInfo(),
                        };
                        cell.height = heights[row].height;
                        occupied[row][col] = cell;
                        spacerCells.add(cell);
                    }
                } else {
                    cell = undefined;
                }
            }
        }
        // 5) Determine which spacers are necessary and sufficient to define
        //   the height of unspecified rows. Some rowspan may still have an
        //   unspecified height after this. TODO EGGMAIL: un-aggregate some
        //   spacers to define a spacer with specific height for problematic
        //   rowspan if the current implementation fails in some relevant cases.
        const canDefineRow = (cell, row) => {
            for (let r = cell.row; r < cell.row + cell.rowspan; r++) {
                if (r !== row && !rowsWithHeight.has(r)) {
                    return false;
                }
            }
            return true;
        };
        const rowsWithoutHeight = rows.difference(new Set(Object.keys(rowsWithHeight).map(Number)));
        let rowspan = 1;
        let lastSize;
        do {
            if (rowsWithoutHeight.size === lastSize) {
                rowspan++;
            }
            lastSize = rowsWithoutHeight.size;
            for (const row of [...rowsWithoutHeight]) {
                for (let col = 0; col < columnCount; col++) {
                    const cell = occupied[row][col];
                    if (!cell.emailNode && cell.rowspan === rowspan && canDefineRow(cell, row)) {
                        rowsWithHeight.set(row, cell);
                        spacerCells.delete(cell);
                        rowsWithoutHeight.delete(row);
                        break;
                    }
                }
            }
        } while (
            rowsWithoutHeight.size > 0 &&
            (rowsWithoutHeight.size !== lastSize || rowspan < rowCount)
        );
        // Remove all unnecessary heights on spacers (a spacer that does not
        // define the height of a rowspan should not have a set height)
        for (const cell of spacerCells) {
            cell.hasImplicitHeight = true;
        }
        return this.processCellAncestors({
            xs,
            ys,
            cells: new Set(cells), // cells with actual content (not spacers)
            columnCount,
            emailNode,
            rowCount,
            matrix: occupied,
        });
    }

    assignBorderStyleInfo({ cell, borderStyleInfo, boundingClientRect, tableMeasures }) {
        const { matrix, xs, ys } = tableMeasures;
        const findInterval = (values, coordinate, isStart) => {
            let upper = 0;
            while (upper < values.length && values[upper] < coordinate) {
                upper++;
            }
            const lower = upper - 1;
            const lowerDiff = lower >= 0 ? coordinate - values[lower] : Infinity;
            const upperDiff = upper < values.length ? values[upper] - coordinate : Infinity;
            const lowerMatches = lower >= 0 && this.isZero(lowerDiff);
            const upperMatches = upper < values.length && this.isZero(upperDiff);

            let boundary;
            if (lowerMatches || upperMatches) {
                boundary = lowerDiff <= upperDiff ? lower : upper;
            }
            if (boundary !== undefined) {
                return isStart ? Math.min(boundary, values.length - 2) : Math.max(0, boundary - 1);
            }
            return Math.max(0, Math.min(lower, values.length - 2));
        };
        const sets = { top: new Set(), right: new Set(), bottom: new Set(), left: new Set() };
        const firstCol = findInterval(xs, boundingClientRect.left, true);
        const lastCol = findInterval(xs, boundingClientRect.right);
        const firstRow = findInterval(ys, boundingClientRect.top, true);
        const lastRow = findInterval(ys, boundingClientRect.bottom);
        for (let col = firstCol; col <= lastCol; col++) {
            sets.top.add(matrix[firstRow][col]);
            sets.bottom.add(matrix[lastRow][col]);
        }
        for (let row = firstRow; row <= lastRow; row++) {
            sets.left.add(matrix[row][firstCol]);
            sets.right.add(matrix[row][lastCol]);
        }
        const resolveCornerDuplicate = (hSet, vSet) => {
            for (const cell of vSet.intersection(hSet)) {
                const cellLeft = xs[cell.col];
                const cellRight = xs[cell.col + cell.colspan];
                const cellTop = ys[cell.row];
                const cellBottom = ys[cell.row + cell.rowspan];
                const hContribution = Math.max(
                    0,
                    Math.min(cellRight, boundingClientRect.right) -
                        Math.max(cellLeft, boundingClientRect.left)
                );
                const vContribution = Math.max(
                    0,
                    Math.min(cellBottom, boundingClientRect.bottom) -
                        Math.max(cellTop, boundingClientRect.top)
                );
                if (this.isZero(hContribution - vContribution) || hContribution < vContribution) {
                    hSet.delete(cell);
                } else {
                    vSet.delete(cell);
                }
            }
        };
        resolveCornerDuplicate(sets.top, sets.left);
        resolveCornerDuplicate(sets.top, sets.right);
        resolveCornerDuplicate(sets.bottom, sets.left);
        resolveCornerDuplicate(sets.bottom, sets.right);
        for (const side of DIRECTION_VARIANTS) {
            for (const cell of sets[side]) {
                if (cell.emailNode) {
                    // never force a style on a non-spacer cell
                    continue;
                }
                for (const feature of CONTOUR_VARIANTS) {
                    const propertyName = `border-${side}-${feature}`;
                    const oppositeName = `border-${OPPOSITE_DIRECTION[side]}-${feature}`;
                    const propertyValue = borderStyleInfo.getPropertyValue(propertyName);
                    if (propertyValue) {
                        cell.styleInfo.setProperty(oppositeName, propertyValue);
                    }
                }
            }
        }
    }

    handleOverlappingBorders({ ancestorNode, cell, tableMeasures }) {
        if (!this.hasVisibleBorder(ancestorNode)) {
            return;
        }
        const borderStyleInfo = this.getNormalizedSimpleBorderStyleInfo(ancestorNode);
        const boundingClientRect = this.getBoundingClientRect(ancestorNode);
        // TODO EGGMAIL: check if this needs defensive programming
        // against forcing a border on a non-spacer cell
        this.assignBorderStyleInfo({
            cell,
            borderStyleInfo,
            boundingClientRect,
            tableMeasures,
        });
    }

    handleOverlappingBackgroundColors({ ancestorNode, cell, tableMeasures }) {}

    processCellAncestors(tableMeasures) {
        const { cells, emailNode } = tableMeasures;
        const containerNode = emailNode.lastReferenceNode;
        const handledNodes = new Set([
            containerNode,
            [...cells].map((cell) => cell.emailNode.lastReferenceNode),
        ]);
        for (const cell of cells) {
            const { referenceNode } = cell;
            for (
                let ancestorNode = referenceNode.parentElement;
                !handledNodes.has(ancestorNode);
                ancestorNode = ancestorNode.parentElement
            ) {
                handledNodes.add(ancestorNode);
                this.trigger("on_measure_ancestor_handlers", {
                    ancestorNode,
                    cell,
                    tableMeasures,
                });
            }
        }

        // go up each cell referenceNode until emailNode lastReferenceNode
        // identify elements with border
        // detect their rectangle
        // detect where each rectangle edge with a border is in the table matrix
        // find the corresponding spacing cell
        // if there is one, mirror the border instruction

        // same-ish strategy for discarded background colors
        return tableMeasures;
    }

    processSyntheticEmailNodes(emailNode) {
        if (!emailNode.analysis.facts.isMosaicContainer) {
            return emailNode;
        }
        const tableMeasures = this.extractTableInfo(emailNode);
        return this.fillMosaicContainer(emailNode, tableMeasures);
    }
    // TODO EGGMAIL:
    // spacer cells contains cells for borders and spacing that are not part
    // of the declared cells => the challenge will be mapping the border color
    // to a background color of that cell.
    // The issue is that a border consideration can be merged with a spacing
    // consideration, or not, depending on the configuration, so maybe not
    // the best idea to keep the current logic as is
    // keep all cells for now, determine later how we want to handle
    // borders, so consider them as spacing for now => maybe these spacing
    // cells can have the border of their sibling?

    /**
     * WORKING HERE
     * LIMITATIONS: border overlapping multiple cells is discarded in general
     *
     * need strategy for:
     * overlapping borders:
     * DONE - (both) draw them mirrored in the spacers around the cell | do not support rounded corners
     *   - overlapping borders providers => give border info and which emailNode should be wrapped
     *   - detect spacers around the cell from that info and apply the rule => no constraint
     *   - WHEN: between extract and fillMosaic (before building emailNodes)
     *
     * borders:
     * DONE -  (masonry) bottom-up constraint to the cell (like table strategy)
     *   OR: direct extraction from the child => no constraint
     *   WHEN: building a cell
     * DONE - (comparison) => no change
     *
     * overlapping background color:
     * - (both) identify every discarded background color
     * - (both) define a colspan/rowspan range, apply on every cell inside in multiple passes (with respect to opacity)
     *   WHEN: background-color provider => give background color and concerned cells, sorted by depth (for alpha compositing)
     *   between extract and fillMosaic (before building emailnodes) => assign a color to each cell
     *
     * background color:
     * DONE - (masonry) bottom-up constraint to the cell (like table strategy)
     *   OR: direct extraction from the child => no constraint
     *   WHEN: building a cell
     * - (comparison)
     *   - card body => up to the cell AND the card-footer
     *   - card footer => replace by color without alpha channel (computing ancestors)
     *   WHEN between extract and fillMosaic (need provider of combo body/bottom, to apply on background color)
     *
     * vertical align:
     * DONE - (masonry) => middle for every cell, forced -> direct
     * DONE - (comparison) => top for card body, bottom for card footer
     *   Need provider for bottom and body, or they should have it as a fact
     *
     */
    fillMosaicContainer(emailNode, tableMeasures) {
        const referenceNode = emailNode.lastReferenceNode;
        const verticalAlign = this.getVerticalAlign(
            this.getStylePropertyValue(referenceNode, "align-items")
        );
        const contextStyleInfo = this.getTableContextStyleInfo(referenceNode);
        const tableNode = this.buildTable();
        const { columnCount, rowCount, matrix } = tableMeasures;
        const placedCells = new Set();
        for (let row = 0; row < rowCount; row++) {
            let rowNode;
            for (let col = 0; col < columnCount; col++) {
                const cellMeasure = matrix[row][col];
                if (placedCells.has(cellMeasure)) {
                    continue;
                }
                placedCells.add(cellMeasure);
                if (!rowNode) {
                    rowNode = this.buildRow();
                    tableNode.appendChild(rowNode);
                }
                let cellNode;
                if (cellMeasure.emailNode) {
                    cellNode = this.buildCell(cellMeasure, { contextStyleInfo, verticalAlign });
                } else {
                    cellNode = this.buildEmptyCell(cellMeasure);
                }
                rowNode.appendChild(cellNode);
            }
        }
        // TODO EGGMAIL: do we need to keep the emailNode if it's a div?
        // at least when it is neutral and has no margin/padding we could
        // replace it by the table directly
        emailNode.spliceChildren(0, emailNode.children.length, tableNode);
        return emailNode;
    }

    buildTable() {
        const layout = new TableLayout();
        const emailNode = new EmailNode({ layout });
        emailNode.analysis.facts.useMosaicStrategy = true;
        return emailNode;
    }

    buildRow() {
        const layout = new RowLayout();
        const emailNode = new EmailNode({ layout });
        emailNode.analysis.facts.useMosaicStrategy = true;
        return emailNode;
    }

    buildEmptyCell(cellMeasure) {
        const { width, widthRatio, hasImplicitHeight, height, rowspan, colspan, styleInfo } =
            cellMeasure;
        const refs = { root: {} };
        const style = { width: `${widthRatio}%` };
        const attributes = { width: `${widthRatio}%`, rowspan, colspan };
        if (!hasImplicitHeight) {
            const formattedHeight = this.formatValue(height, {
                inputUnit: height,
                outputUnit: height,
                precision: 2,
            });
            style.height = `${formattedHeight}px`;
            attributes.height = `${formattedHeight}`;
        }
        const borderWidths = {};
        for (const side of DIRECTION_VARIANTS) {
            borderWidths[side] = parseCssValue(styleInfo.getPropertyValue(`border-${side}-width`));
        }
        const handleBorderCell = (variants, dimension) => {
            let value, side;
            let consumed = 0;
            for (const variant of variants) {
                const borderWidth = borderWidths[variant].number;
                if (borderWidth) {
                    value = borderWidth;
                    side = variant;
                    consumed++;
                }
            }
            if (consumed !== 1) {
                return;
            }
            if (this.isZero((dimension ?? 0) - value)) {
                for (const feature of CONTOUR_VARIANTS) {
                    const propertyName = `border-${side}-${feature}`;
                    const oppositeName = `border-${OPPOSITE_DIRECTION[side]}-${feature}`;
                    const propertyValue = styleInfo.getPropertyValue(propertyName);
                    styleInfo.removeProperty(propertyName);
                    if (propertyValue) {
                        styleInfo.setProperty(oppositeName, propertyValue);
                    }
                }
            }
        };
        handleBorderCell(["top", "bottom"], height);
        handleBorderCell(["left", "right"], width);
        Object.assign(refs.root, { style: StyleInfo.from(style).merge(styleInfo), attributes });
        const analysis = new Analysis({ parsingFacts: { canMerge: true, attemptCellMerge: true } });
        analysis.facts.isEmptyCell = true;
        analysis.facts.useMosaicStrategy = true;
        const layout = new EmptyCellLayout({ refs });
        const cellEmailNode = new EmailNode({ layout, analysis });
        return cellEmailNode;
    }

    buildCell(cellMeasure, { contextStyleInfo, verticalAlign }) {
        // deduce empty cell by the presence/absence of emailNode
        // // need to appendchild said emailNode
        // needs verticalAlign
        const { widthRatio, emailNode, rowspan, colspan, styleInfo } = cellMeasure;
        const refs = { root: {} };
        const style = { width: `${widthRatio}%` };
        const attributes = { width: `${widthRatio}%`, rowspan, colspan };
        if (verticalAlign) {
            style["vertical-align"] = verticalAlign;
            attributes.valign = verticalAlign;
        }
        const defaultOptions = {
            style: StyleInfo.from(style).merge(contextStyleInfo).merge(styleInfo),
            attributes,
        };
        const options = this.processThrough(
            "mosaic_cells_element_options_providers_processors",
            {},
            cellMeasure
        );
        Object.assign(refs.root, assignDefaultElementOptions(options, defaultOptions));
        const analysis = new Analysis({ parsingFacts: { canMerge: true, attemptCellMerge: true } });
        analysis.facts.isCell = true;
        analysis.facts.useMosaicStrategy = true;
        const layout = new CellLayout({ refs });
        // TODO EGGMAIL: do we need to keep the tableStrategyReport block?
        emailNode.analysis.facts.stopTableStrategyReportPropagation = true;
        analysis.facts.stopTableStrategyReportPropagation = true;
        const cellEmailNode = new EmailNode({ layout, analysis });
        cellEmailNode.appendChild(emailNode);
        this.attemptCellMerge(cellEmailNode, emailNode);
        return cellEmailNode;
    }
}

registry
    .category("mail-html-conversion-core-plugins")
    .add(MosaicStrategyPlugin.id, MosaicStrategyPlugin);
