import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { CellLayout, EmptyCellLayout, RowLayout, TableLayout } from "./table_models";
import { Analysis, EmailNode } from "../core/render_models";
import { StyleInfo } from "../core/style_models";

export class MosaicStrategyPlugin extends Plugin {
    static id = "mosaicStrategy";
    static dependencies = [
        "contextStyle",
        "math",
        "measurementSnapshot",
        "hybridFluidStrategy",
        "tableStrategy",
    ];
    resources = {
        element_layout_analysis_processors: this.analyzeElementLayout.bind(this),
        synthetic_email_node_processors: (emailNode) => {
            if (!emailNode.analysis.facts.isMosaicContainer) {
                return emailNode;
            }
            const tableMeasures = this.extractTableInfo(emailNode);
            return this.fillMosaicContainer(emailNode, tableMeasures);
        },
    };

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
        const columnCount = xs.length - 1;
        const rowCount = ys.length - 1;
        const cells = rects.map((rect) => {
            const col = xs.findIndex((x) => this.isZero(rect.left - x));
            const row = ys.findIndex((y) => this.isZero(rect.top - y));
            const nextCol = xs.findIndex((x) => this.isZero(rect.right - x));
            const nextRow = ys.findIndex((y) => this.isZero(rect.bottom - y));
            const colspan = nextCol - col;
            const rowspan = nextRow - row;
            return {
                col,
                row,
                colspan,
                rowspan,
                emailNode: rectToEmailNode.get(rect),
                ...getWidth(col, colspan),
            };
        });
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
                        cell = { col, row, colspan: 1, rowspan: 1, ...getWidth(col, 1) };
                        cell.height = heights[row].height;
                        occupied[row][col] = cell;
                        spacerCells.add(cell);
                    }
                } else {
                    cell = undefined;
                }
            }
        }
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
            (rowsWithoutHeight.size !== lastSize || rowspan + 1 <= rowCount)
        );
        // Remove all unnecessary heights on spacers (a spacer that does not
        // define the height of a rowspan should not have a set height)
        for (const cell of spacerCells) {
            delete cell.height;
        }
        return {
            columnCount,
            rowCount,
            matrix: occupied,
        };
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
     * LIMITATIONS: border overlapping multiple cells is discarded in general
     *
     * TODO EGGMAIL WORKING HERE
     * need strategy for:
     * border => for masonry => cell border should move up to the cell
     * => for comparisons => don't handle cell borders
     * => for both, spanning borders need to be displayed => background-color strategy works, but
     * not always, if border is packaged with any spacing, it won't work, also when stretched it
     * won't work either => decision: don't support overlapping border colors for now.
     * background => issue with discarded ancestor background color (is lost)
     * => background color should be applied on the cell (same as with table strategy)
     * verticalAlign => specifically for masonry, force a vertical-align middle on cells
     * unless specified directly by align-items or align-self
     * => specifically for s_comparisons, we would like vertical-align top for the card body
     * and vertical-align bottom for the card footer, and we don't want to propagate the background
     * color of the footer, but we want the footer cell background to be the same as the parent.
     * But if we do that with alpha colors, then it won't work, so we have to force a non-alpha color
     * => seems very complex, evaluate what can be done without going too far
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
        const { widthRatio, height, rowspan, colspan } = cellMeasure;
        const refs = { root: {} };
        const style = { width: `${widthRatio}%` };
        const attributes = { width: `${widthRatio}%`, rowspan, colspan };
        if (height) {
            const formattedHeight = this.formatValue(height, {
                inputUnit: height,
                outputUnit: height,
                precision: 2,
            });
            style.height = `${formattedHeight}px`;
            attributes.height = `${formattedHeight}`;
        }
        Object.assign(refs.root, { style, attributes });
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
        // needs to define isCell so that align-self constraint can work
        const { widthRatio, emailNode, rowspan, colspan } = cellMeasure;
        const refs = { root: {} };
        const style = { width: `${widthRatio}%` };
        const attributes = { width: `${widthRatio}%`, rowspan, colspan };
        if (verticalAlign) {
            style["vertical-align"] = verticalAlign;
            attributes.valign = verticalAlign;
        }
        Object.assign(refs.root, {
            style: StyleInfo.from(style).merge(contextStyleInfo),
            attributes,
        });
        const analysis = new Analysis({ parsingFacts: { canMerge: true, attemptCellMerge: true } });
        analysis.facts.isCell = true;
        analysis.facts.useMosaicStrategy = true;
        const layout = new CellLayout({ refs });
        const cellEmailNode = new EmailNode({ layout, analysis });
        cellEmailNode.appendChild(emailNode);
        this.attemptCellMerge(cellEmailNode, emailNode);
        return cellEmailNode;
    }
}

registry
    .category("mail-html-conversion-core-plugins")
    .add(MosaicStrategyPlugin.id, MosaicStrategyPlugin);
