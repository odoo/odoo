import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { zip } from "@web/core/utils/arrays";
import { DIMENSIONS } from "../hooks";
import {
    CellLayout,
    EmptyCellLayout,
    EmptyRowLayout,
    RowLayout,
    TableLayout,
} from "./table_models";
import { EmailNode } from "../core/render_models";
import { withSequence } from "@html_editor/utils/resource";
import { DEFAULT_SPACING_SEQUENCE } from "./spacing_plugin";
import { StyleInfo } from "../core/style_models";

const { DESKTOP, MOBILE } = DIMENSIONS;

const VERTICAL_ALIGN = {
    start: "top",
    end: "bottom",
    center: "middle",
    "flex-start": "top",
    "flex-end": "bottom",
};
/**
 * TODO EGGMAIL: WORKING HERE
 */
export class TableStrategyPlugin extends Plugin {
    static id = "tableStrategy";
    static dependencies = [
        "math",
        "measurementSnapshot",
        "responsiveBlock",
        "referenceNode",
        "spacing",
    ];
    static shared = ["extractRowsFromBands", "fillTableContainer"];
    resources = {
        element_layout_analysis_processors: this.analyzeElementLayout.bind(this),
        synthetic_email_node_processors: (emailNode) => {
            if (!emailNode.analysis.facts.isTableContainer) {
                return;
            }
            const rowMeasures = this.extractRowsFromBands(emailNode);
            return this.fillTableContainer(emailNode, rowMeasures);
        },
        refine_layout_processors: withSequence(
            DEFAULT_SPACING_SEQUENCE - 1,
            this.applyTableSpacing.bind(this)
        ),
    };

    setup() {
        this.builders = {
            row: this.buildRow.bind(this),
            table: this.buildTable.bind(this),
            cell: this.buildCell.bind(this),
            emptyCell: this.buildEmptyCell.bind(this),
            cellWithOffset: this.buildCellWithOffset.bind(this),
        };
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
        // apply cell margin bottom
        // - identify that the node is a tableLayout cell or a hybridTableLayout cell
        // - add the hardcoded mass_mailing_mail.scss class for the closest equivalent margin
        // DONE
        if (emailNode.analysis.facts.acceptCellMobileMarginBottom) {
            this.applyCellMobileMarginBottom(layout, { emailNode });
        }
        // apply vertical padding between rows
        // - identify that the node is a tablelayout Row
        // - splice vertical padding rows with 1 cell inside the table
        // DONE
        if (emailNode.analysis.facts.acceptRowDesktopMarginBottom) {
            this.applyRowDesktopMarginBottom(layout, { emailNode });
        }
        // apply horizontal padding between cells
        // - identify that the node is a tableLayout Cell or a hybridTableLayout Cell
        // - splice horizontal padding cells inside the row
        // DONE
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

    applyRowDesktopMarginBottom(layout, { emailNode }) {
        const parent = emailNode.parent;
        if (!parent) {
            return;
        }
        // TODO EGGMAIL: replace test value
        parent.spliceChildren(
            parent.children.indexOf(emailNode) + 1,
            0,
            new EmailNode({
                layout: new EmptyRowLayout({
                    refs: {
                        root: {
                            style: { height: "16px" },
                            attributes: { height: "16" },
                        },
                    },
                }),
            })
        );
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

    // TODO EGGMAIL NOW: special case for the first element inside the reference:
    // - basic editor case (investigate)
    // - builder case (convert to mega wrapper table + background color -> smaller table (mail_wrapper) with margin)
    // - unknown case (add mega wrapper table -> can use "reference" element for this, if mega table strategy was not applied
    // below)
    analyzeElementLayout({ layout, analysis }, { referenceNode, parentEmailNode }) {
        // TODO EGGMAIL: enable this function when ready
        return;
        // TODO EGGMAIL NOW: check that `hasTableLayout` can capture a table
        // if so, maybe we shouldn't hardcode "table" here, because we want to
        // allow a table to be an "hybrid" and match other strategies.
        if (analysis.facts.isMainTable || !this.detectTableLayout(referenceNode)) {
            // See MainTableStrategyPlugin (more specific representation of a table)

            // look at element tag, if it's a table.
            // look in // at desktopBlocks and mobileBlocks, they should have:
            // - always the same amount of bands, and the same amount of clusters per band?
            // parent should only have bands with 1 block cluster
            // block cluster should have only 1 band, and at least 1 block cluster band should have 2 clusters
            // look for a block with multiple bands, every band has 1 cluster
            return;
        }
        if (parentEmailNode.layout.descendantTag === "TABLE") {
            analysis.parsingFacts.canParentMerge = true;
        }
        analysis.parsingFacts.canMerge = false;
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
        let isTableCandidate;
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
            if (
                dBand.clusters.length === 1 &&
                dBand.clusters[0].isBlock &&
                mBand.clusters[0].isBlock
            ) {
                // matching a real table row
                const dRowEl = dBand.clusters[0].nodes[0];
                const mRowEl = mBand.clusters[0].nodes[0];
                const dRowBlock = this.getLayoutBlock(dRowEl, MOBILE);
                const mRowBlock = this.getLayoutBlock(mRowEl, DESKTOP);
                if (
                    !dRowBlock ||
                    !mRowBlock ||
                    dRowBlock.bands.length !== mRowBlock.bands.length ||
                    dRowBlock.bands.length !== 1 ||
                    dRowBlock.bands[0].clusters.length !== dRowBlock.bands[0].clusters.length
                ) {
                    return;
                }
                if (dRowBlock.bands[0].clusters.length > 1) {
                    isTableCandidate = true;
                }
            } else if (
                dBand.clusters.length === mBand.clusters.length &&
                dBand.clusters.length > 1
            ) {
                // matching a table-like row where the row is implicit
                // matching a table-like (eg bootstrap) where rows are implicit
                // (need synthetic nodes)
                isTableCandidate = true;
            } else {
                return;
            }
        }
        // TODO EGGMAIL: enable when ready
        // return isTableCandidate;
    }

    // TODO EGGMAIL NOW (remark from hybrid_fluid_strategy_plugin)
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
    fillTableContainer(
        emailNode,
        rowMeasures,
        { withTable = true, builders = this.builders } = {}
    ) {
        const rows = [];
        for (const rowMeasure of rowMeasures) {
            const width = rowMeasure.width;
            let ratio = 100;
            const rowEmailNode = builders["row"](rowMeasure);
            rows.push(rowEmailNode);
            for (const cellMeasure of rowMeasure.children) {
                const widthRatio = this.ratioPercentage(cellMeasure.width, width, ratio);
                cellMeasure.widthRatio = widthRatio;
                ratio -= widthRatio;
                if (cellMeasure.type === "cellWithOffset") {
                    cellMeasure.offsetWidthRatio = this.ratioPercentage(
                        cellMeasure.offsetWidth,
                        width,
                        ratio
                    );
                    ratio -= cellMeasure.offsetWidthRatio;
                    for (const cell of builders["cellWithOffset"](cellMeasure)) {
                        rowEmailNode.appendChild(cell);
                    }
                } else if (cellMeasure.type === "emptyCell") {
                    rowEmailNode.appendChild(builders["emptyCell"](cellMeasure));
                } else if (cellMeasure.type === "cell") {
                    rowEmailNode.appendChild(builders["cell"](cellMeasure));
                }
            }
        }
        let children = rows;
        if (withTable) {
            const tableNode = builders["table"](rows);
            children = [tableNode];
        }
        emailNode.spliceChildren(0, emailNode.children.length, ...children);
    }

    extractRowsFromBands(emailNode) {
        const referenceNode = emailNode.lastReferenceNode;
        const desktopBlock = this.getLayoutBlock(referenceNode, DESKTOP);
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
            const row = { verticalAlign, children: [] };
            rowMeasures.push(row);
            let width = 0;
            let prevCluster;
            const hasLastOffset = !this.isZero(desktopBlock.padding.right);
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
                width += measures.width;
                if (!this.isZero(desktopBlock.padding.left)) {
                    const offsetWidth = desktopBlock.padding.left;
                    width += offsetWidth;
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
                width += measures.width;
                if (gap > 0) {
                    width += gap;
                    row.children.push(
                        Object.assign({ type: "cellWithOffset", offsetWidth: gap }, measures)
                    );
                } else {
                    row.children.push(Object.assign({ type: "cell" }, measures));
                }
                prevCluster = cluster;
            }
            if (hasLastOffset) {
                width += desktopBlock.padding.right;
                row.children.push({
                    type: "emptyCell",
                    width: desktopBlock.padding.right,
                    isLast: true,
                    verticalAlign,
                });
            }
            row.width = width;
        }
        const lastRowMeasure = rowMeasures.at(-1);
        if (lastRowMeasure) {
            lastRowMeasure.isLast = true;
        }
        return rowMeasures;
    }

    buildTable(rows) {
        const layout = new TableLayout();
        const tableNode = new EmailNode({ layout });
        tableNode.analysis.facts.acceptTableOuterSpacing = true;
        tableNode.analysis.facts.useTableStrategy = true;
        tableNode.spliceChildren(0, 0, ...rows);
        return tableNode;
    }

    buildRow({ isLast }) {
        const layout = new RowLayout();
        const emailNode = new EmailNode({ layout });
        if (!isLast) {
            emailNode.analysis.facts.acceptRowDesktopMarginBottom = true;
        }
        emailNode.analysis.facts.useTableStrategy = true;
        return new EmailNode({ layout });
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
            cellEmailNode.appendChild(child);
        }
        if (!isLast) {
            cellEmailNode.analysis.facts.acceptCellMobileMarginBottom = true;
            cellEmailNode.analysis.facts.acceptCellPaddingRight = true;
        }
        emailNode.analysis.facts.useTableStrategy = true;
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
