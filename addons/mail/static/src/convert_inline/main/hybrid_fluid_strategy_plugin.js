import { registry } from "@web/core/registry";
import { Plugin } from "@mail/convert_inline/plugin";
import { zip } from "@web/core/utils/arrays";
import {
    HybridFluidTableCell,
    HybridFluidTableRow,
} from "@mail/convert_inline/main/hybrid_fluid_models";
import { parseCssValue } from "@mail/convert_inline/css_parsers";
import { isAllowedContent } from "@html_editor/utils/dom_info";
import { withSequence } from "@html_editor/utils/resource";
import { DEFAULT_SPACING_SEQUENCE } from "@mail/convert_inline/main/spacing_plugin";
import { EmptyCellLayout } from "@mail/convert_inline/main/table_models";
import {
    ALLOWED_MOBILE_MARGINS_SIZES,
    DIMENSIONS,
    DIRECTION_VARIANTS,
} from "@mail/convert_inline/core/utils";

const { DESKTOP, MOBILE } = DIMENSIONS;

export class HybridFluidStrategyPlugin extends Plugin {
    static id = "hybridFluidStrategy";
    static dependencies = [
        "measurementSnapshot",
        "math",
        "render",
        "dimension",
        "responsiveBlock",
        "rules",
        "referenceNode",
        "spacing",
        "tableStrategy",
    ];
    resources = {
        element_layout_analysis_processors: this.analyzeElementLayout.bind(this),
        synthetic_email_node_processors: this.fillHybridFluidContainer.bind(this),
        refine_layout_processors: [
            withSequence(DEFAULT_SPACING_SEQUENCE - 1, this.applyTableSpacing.bind(this)),
            this.forcePercentWidth.bind(this),
        ],
        accept_table_strategy_report_overrides: this.acceptTableStrategyReport.bind(this),
    };

    setup() {
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
            // TODO EGGMAIL: need to find an alternative to this expensive
            // computation (which requires multiple layout trashing since the
            // reference has to be measured in MOBILE mode in the DOM).
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
        const { analysis } = defaultEmailNodeArguments;
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
        Object.assign(analysis.buildDirectives, {
            canMerge: false,
            needSyntheticEmailNode: true,
        });
        analysis.facts.isHybridFluidContainer = true;
        return defaultEmailNodeArguments;
    }

    forcePercentWidth(layout, { emailNode }) {
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
        return this.fillTableContainer(emailNode, rowMeasures, {
            builders: this.tableBuilders,
        });
    }

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

    detectHybridFluidLayout(referenceNode) {
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
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(HybridFluidStrategyPlugin.id, HybridFluidStrategyPlugin);
