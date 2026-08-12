import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";

export class MosaicStrategyPlugin extends Plugin {
    static id = "mosaicStrategy";
    static dependencies = ["math", "measurementSnapshot", "hybridFluidStrategy", "tableStrategy"];
    resources = {
        element_layout_analysis_processors: this.analyzeElementLayout.bind(this),
        synthetic_email_node_processors: this.fillMosaicContainer.bind(this),
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
    fillMosaicContainer(emailNode) {
        if (!emailNode.analysis.facts.isMosaicContainer) {
            return emailNode;
        }
        // TODO EGGMAIL: while skipping nodes, we may loose background color
        // or border info or outside-paddings think of a way to recover them
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
        const columnCount = xs.length - 1;
        const rowCount = ys.length - 1;
        const cells = rects.map((rect) => {
            const col = xs.findIndex((x) => this.isZero(rect.left - x));
            const row = ys.findIndex((y) => this.isZero(rect.top - y));
            const nextCol = xs.findIndex((x) => this.isZero(rect.right - x));
            const nextRow = ys.findIndex((y) => this.isZero(rect.bottom - y));
            const colspan = nextCol - col;
            const rowspan = nextRow - row;
            return { col, row, colspan, rowspan, emailNode: rectToEmailNode.get(rect) };
        });
        const occupied = Array.from({ length: rowCount }, () => Array(columnCount).fill(null));
        for (const cell of cells) {
            for (let row = cell.row; row < cell.row + cell.rowspan; row++) {
                for (let col = cell.col; col < cell.col + cell.colspan; col++) {
                    occupied[row][col] = cell;
                }
            }
        }
        const spacerCells = [];
        for (let col = 0; col < columnCount; col++) {
            let cell;
            for (let row = 0; row < rowCount; row++) {
                if (occupied[row][col] === null) {
                    if (cell && cell.row + cell.rowspan === row) {
                        cell.rowspan++;
                        occupied[row][col] = cell;
                    } else {
                        cell = { col, row, colspan: 1, rowspan: 1 };
                        occupied[row][col] = cell;
                        spacerCells.push(cell);
                    }
                } else {
                    cell = undefined;
                }
            }
        }
        // TODO EGGMAIL:
        // spacer cells contains cells for borders and spacing that are not part
        // of the declared cells => the challenge will be mapping the border color
        // to a background color of that cell.
        // The issue is that a border consideration can be merged with a spacing
        // consideration, or not, depending on the configuration, so maybe not
        // the best idea to keep the current logic as is
        // TODO EGGMAIL:
        // currently we have the table layout, but dimensions are not properly
        // assigned.
        // we want % values for every cell width, and height px value for spacer cells
        // with rowspan = 1 and only have spacer cells on the same row

        // working here
        // keep all cells for now, determine later how we want to handle
        // borders, so consider them as spacing for now => maybe these spacing
        // cells can have the border of their sibling?
        console.log(cells.concat(spacerCells));
        return emailNode;
    }
}

registry
    .category("mail-html-conversion-core-plugins")
    .add(MosaicStrategyPlugin.id, MosaicStrategyPlugin);
