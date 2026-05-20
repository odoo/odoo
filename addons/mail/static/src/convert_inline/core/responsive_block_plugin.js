import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";
import { memoize } from "@web/core/utils/functions";
import { Band, Block, Cluster } from "./responsive_models";

export class ResponsiveBlockPlugin extends Plugin {
    static id = "responsiveBlock";
    static dependencies = ["measurementSnapshot", "math", "referenceNode"];
    static shared = ["getLayoutBlock"];
    resources = {
        on_parse_layout_with_dimensions_handlers: this.computeBlocks.bind(this),
        on_layout_dimensions_updated_handlers: this.onLayoutDimensionsUpdated.bind(this),
    };

    setup() {
        this.layoutToFilters = new Map(); // layoutDimensions (desktop/mobile) -> filterClusterNodes function
        this.layoutToBlocks = new Map(); // layoutDimensions (desktop/mobile) -> map: element -> Block
        this.layoutToClusters = new Map(); // layoutDimensions (desktop/mobile) -> map: parent -> Array<Cluster>
    }

    /**
     * @param {HTMLElement} element
     * @param {Object} [layoutDimensions]
     * @returns {Block}
     */
    getLayoutBlock(element, layoutDimensions) {
        const layoutToBlocks = this.getLayoutToBlocks(layoutDimensions);
        return layoutToBlocks.get(element);
    }

    /**
     * @param {Object} [layoutDimensions]
     * @returns {WeakMap} elementToBlocks for requested layoutDimensions
     */
    getLayoutToBlocks(layoutDimensions) {
        if (!layoutDimensions) {
            layoutDimensions = this.layoutDimensions;
        }
        if (!this.layoutToBlocks.has(layoutDimensions)) {
            this.layoutToBlocks.set(layoutDimensions, new WeakMap());
        }
        return this.layoutToBlocks.get(layoutDimensions);
    }

    getLayoutToClusters() {
        if (!this.layoutToClusters.has(this.layoutDimensions)) {
            this.layoutToClusters.set(this.layoutDimensions, new WeakMap());
        }
        return this.layoutToClusters.get(this.layoutDimensions);
    }

    getLayoutFilter() {
        if (!this.layoutToFilters.has(this.layoutDimensions)) {
            const ignoredNodes = new WeakSet();
            const filterClusterNodes = memoize((node) => {
                this.computeClusters(node, ignoredNodes);
            });
            this.layoutToFilters.set(this.layoutDimensions, (node) => {
                if (ignoredNodes.has(node)) {
                    return NodeFilter.FILTER_REJECT;
                }
                filterClusterNodes(node);
                return NodeFilter.FILTER_ACCEPT;
            });
        }
        return this.layoutToFilters.get(this.layoutDimensions);
    }

    // Algorithm to organize blocks between each other in a email sensible way.
    // It will completely disregard the style of the reference, and only
    // consider the desktop dimensions as well as the mobile dimensions of each
    // block. It will consider overlapping blocks as a whole if they overlap in
    // mobile and in desktop modes

    /**
     * TODO EGGMAIL: DISCLAIMER:
     * Only consider clusters of elements that are direct childNodes of their parent
     * any style that disregard the DOM hierarchy (eg position: absolute) is not
     * supported
     */
    computeClusters(parent, ignoredInlineNodes) {
        const clusters = [];
        this.processChildNodes(parent, (child) => {
            const isBlock = this.isBlock(child);
            const prevCluster = clusters.at(-1);
            const cluster =
                isBlock || !prevCluster || prevCluster.isBlock
                    ? new Cluster([child], isBlock)
                    : prevCluster;
            if (!isBlock) {
                ignoredInlineNodes.add(child);
            }
            if (cluster !== prevCluster) {
                clusters.push(cluster);
            } else {
                cluster.nodes.push(child);
            }
        });
        this.getLayoutToClusters().set(parent, clusters);
        return clusters;
    }

    /**
     * TODO EGGMAIL: consider cases where content overflows from its container block
     * is the computation here broken? What is the boundingclientrect of an
     * overflowing content?
     */
    computeLayoutBands(clusters) {
        let bands = new Set();
        for (const cluster of clusters) {
            const nodes = cluster.nodes;
            cluster.rect = this.getBoundingClientRect(
                cluster.isBlock
                    ? cluster.nodes[0]
                    : this.getNodeClusterRange(nodes.at(0), nodes.at(-1))
            );
            if (cluster.rect.height === 0 || cluster.rect.width === 0) {
                continue;
            }
            const bandCandidates = [];
            for (const band of bands) {
                if (this.overlapY(band, cluster.rect)) {
                    bandCandidates.push(band);
                }
            }
            let band = bandCandidates.shift();
            if (!band) {
                band = new Band();
                bands.add(band);
            }
            bands = bands.difference(new Set(bandCandidates));
            for (const candidate of bandCandidates) {
                band.merge(candidate);
            }
            band.addCluster(cluster);
        }
        for (const band of bands) {
            // TODO EGGMAIL: sorting is not perfect (clusters with same center position are "identical")
            band.clusters.sort((cluster1, cluster2) => {
                const { left: l1, width: w1 } = cluster1;
                const { left: l2, width: w2 } = cluster2;
                return l1 + w1 / 2 - (l2 + w2 / 2);
            });
        }
        return Array.from(bands).sort((band1, band2) => band1.top - band2.top);
    }

    computeBlock(element, bands) {
        const block = new Block(element, bands, this.getBoundingClientRect(element));
        const firstBand = block.bands.at(0);
        const lastBand = block.bands.at(-1);
        const rect = block.rect;
        const bandsRect = {
            top: firstBand?.top ?? rect.top,
            bottom: lastBand?.bottom ?? rect.bottom,
        };
        for (const band of bands) {
            for (const cluster of band.clusters) {
                if (bandsRect.left === undefined || cluster.rect.left < bandsRect.left) {
                    bandsRect.left = cluster.rect.left;
                }
                if (bandsRect.right === undefined || cluster.rect.right > bandsRect.right) {
                    bandsRect.right = cluster.rect.right;
                }
            }
        }
        bandsRect.left ??= rect.left;
        bandsRect.right ??= rect.right;
        block.padding = this.containerPadding(rect, bandsRect);
        return block;
    }

    computeBlocks() {
        const elementToBlocks = this.getLayoutToBlocks();
        const filter = this.getLayoutFilter();
        const treeWalker = this.createReferenceTreeWalker(filter);
        let element = treeWalker.root;
        filter(element);
        do {
            const clusters = this.getLayoutToClusters().get(element);
            const bands = this.computeLayoutBands(clusters);
            const block = this.computeBlock(element, bands);
            elementToBlocks.set(element, block);
        } while ((element = treeWalker.nextNode()));
    }

    onLayoutDimensionsUpdated(layoutDimensions) {
        this.layoutDimensions = layoutDimensions;
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(ResponsiveBlockPlugin.id, ResponsiveBlockPlugin);
