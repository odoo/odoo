/**
 * Layout Cluster, nodes agglomeration akin to a block element.
 * - one block element
 * - multiple agglomerated inline nodes
 */
export class Cluster {
    // implicit positioning:
    // margin-top => cluster.top - band.top
    // margin-bottom => same
    // gapX with previous/next cluster
    nodes = [];
    isBlock;
    rect;
    constructor(nodes, isBlock) {
        this.nodes = nodes;
        this.isBlock = isBlock;
    }
}

/**
 * Horizontal layout Band, composed of every cluster inside a region delimited
 * by 2 straight horizontal lines.
 */
export class Band {
    // implicit positioning:
    // margin-left => band.left - (block.left + block.padding.left)
    // margin-right same
    // gapY with previous/next band
    top;
    bottom;
    clusters = [];

    addCluster(cluster) {
        this.clusters.push(cluster);
        this.top ??= cluster.rect.top;
        this.top = Math.min(this.top, cluster.rect.top);
        this.bottom ??= cluster.rect.bottom;
        this.bottom = Math.max(this.bottom, cluster.rect.bottom);
    }

    merge(band) {
        for (const cluster of band.clusters) {
            this.addCluster(cluster);
        }
    }
}

/**
 * Layout Block, related to one block element (parent)
 * Composed of horizontal layout bands
        +--------------------------------------+
        | ___________________________________  |
        | +---------+ +---------+ +---------+  |
        | |         | |         | |         |  |
        | |         | |         | |         |  |
        | +---------+ +---------+ +---------+  |
        | ___________________________________  |
        | +---------+ +---------+ +---------+  |
        | |         | |         | |         |  |
        | |         | |         | |         |  |
        | +---------+ +---------+ +-Cluster-+  |
        | _______________Band________________  |
        +---Block------------------------------+
 */
export class Block {
    element;
    bands = []; // Array<Band>
    rect;
    padding = { top: 0, bottom: 0, left: 0, right: 0 };
    constructor(element, bands, rect) {
        this.element = element;
        this.bands = bands;
        this.rect = rect;
    }
}
