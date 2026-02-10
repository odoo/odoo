import { BasePlugin } from "@html_editor/base_plugin";
import { registry } from "@web/core/registry";
import { EMAIL_DESKTOP_DIMENSIONS, EMAIL_MOBILE_DIMENSIONS } from "../hooks";
import { containsAnyNonPhrasingContent } from "@html_editor/utils/dom_info";
import { childNodes } from "@html_editor/utils/dom_traversal";
import { memoize } from "@web/core/utils/functions";

const DIMENSIONS = {
    desktop: EMAIL_DESKTOP_DIMENSIONS,
    mobile: EMAIL_MOBILE_DIMENSIONS,
};
export class ResponsivePlugin extends BasePlugin {
    static id = "ResponsivePlugin";
    resources = {
        reference_content_loaded_handlers: this.computeEmailHtmlStructure.bind(this),
        update_layout_dimensions_handlers: this.onUpdateLayoutDimensions.bind(this),
    };

    setup() {
        this.layoutDimensions = { width: 0, height: 0 };
        this.htmlStructures = new Map();
        this.phrasingContent = new Set();
        this.filterPhrasingContentNodes = memoize((node) => {
            const result = containsAnyNonPhrasingContent(node);
            if (!result) {
                for (const child of childNodes(node)) {
                    this.phrasingContent.add(child);
                }
            }
        });
    }

    // Algorithm to organize blocks between each other in a email sensible way.
    // It will completely disregard the style of the reference, and only
    // consider the desktop dimensions as well as the mobile dimensions of each
    // block. It will consider overlapping blocks as a whole if they overlap in
    // mobile and in desktop modes

    // does the algo need computed style or style? no, totally independent, it will
    // only do measurements => perfect hook
    computeEmailHtmlStructure() {
        this.parseWithLayout("desktop");
        this.parseWithLayout("mobile");

        // simpler algo:
        // identify "horizontal clusters of blocks (flow elements)"
        // go through every node in the tree
        // mark its relation with previous and next element sibling -> problem
        // when identifying spans that are siblings of text nodes (or sometimes not)
        // and inside spans...
    }

    parseWithLayout(layoutType) {
        const originalDimensions = this.layoutDimensions;
        const dimensions = DIMENSIONS[layoutType];
        if (this.layoutDimensions.width !== dimensions.width) {
            this.config.updateLayoutDimensions(dimensions);
        }
        this.identifyHorizontalClusters(layoutType);
        if (this.layoutDimensions.width !== originalDimensions.width) {
            this.config.updateLayoutDimensions(originalDimensions);
        }
    }

    identifyHorizontalClusters(layoutType) {
        const referenceToInfo = new WeakMap();
        const clientRectCache = new WeakMap();
        const getClientRect = (el) => {
            if (!el) {
                return;
            }
            if (!clientRectCache.has(el)) {
                clientRectCache.set(el, el.getBoundingClientRect());
            }
            return clientRectCache.get(el);
        };
        const treeWalker = this.config.referenceDocument.createTreeWalker(
            this.config.reference,
            NodeFilter.SHOW_ELEMENT,
            (node) => {
                if (this.phrasingContent.has(node)) {
                    return NodeFilter.FILTER_REJECT;
                }
                // Disregard phasing content children
                // TODO EGGMAIL: filterPhrasingContentNodes is too restrictive, some phrasing content
                // could have been "dressed" as a block, do we want to support that?
                // if so, filterPhrasingContentNodes should be reworked in consequence.
                this.filterPhrasingContentNodes(node);
                return NodeFilter.FILTER_ACCEPT;
            }
        );
        let el;
        while ((el = treeWalker.nextNode())) {
            const rect = getClientRect(el);
            const prev = getClientRect(el.previousElementSibling);
            const next = getClientRect(el.nextElementSibling);
            const parent = getClientRect(el.parentElement);
            if (prev) {
                // compare alignment (vertical/horizontal)
                // mark parent as horizontal cluster if horizontal
            } else {
                // check for left offset with parent
                // mark parent left padding value, check if already set
                // if parent right padding change in mobile mode, mark as horizontal cluster (potential offset-x)
                // take care of padding in relative units? Ignore?
            }
            if (next) {
                // compare alignment (vertical/horizontal)
                // mark parent as horizontal cluster if horizontal
            } else {
                // check for right offset with parent
                // mark parent right padding value, check if already set
                // if parent right padding change in mobile mode, mark as horizontal cluster (potential unfinished row)
                // take care of padding in relative units? Ignore?
            }
            // mark width and compare with mobile mode -> same => fixed width, different => % width or no width (start/end of row if some fixed width)

            // if sibling => comparison heuristic (left/right/top/bottom)

            // if no previousSibling => compare x position (left) with parent to check for offset
            // if no nextSibling => compare x position (right) with parent to check for isolated col-md-10

            // how to differenciate with padding?
            // -> if the padding value is not identical, could be approximated with a padding constant + an offset column.
            // -> Take care of padding values in % or other relative units.

            // how to differenciate with margin-auto?
            // -> does not even seem to work currently
            // -> investigate what is supposed to happen with that, maybe it shouldn't be there at all
            // -> all media queries from bootstrap seem to wrongly be there?
            // -> no usage of horizontal margins in the normal editor (to verify), and if they are detected, they should be handled as an "offset" so it's not wrong not to consider them I guess

            // Any variation in padding create a cluster candidate => to be determined later

            // do we need the mobile interpretation at this stage? Yes, it will
            // add some missing clusters without any conclusion, and we can easily check
            // if an element is a cluster in both, only in desktop, or only in mobile
        }
        this.htmlStructures.set(layoutType, undefined);
    }

    onUpdateLayoutDimensions(layoutDimensions) {
        this.layoutDimensions = Object.assign({}, layoutDimensions);
    }
}

registry.category("mail-html-conversion-plugins").add(ResponsivePlugin.id, ResponsivePlugin);
