/** @odoo-module */

import { AbstractBehavior } from "@knowledge/components/behaviors/abstract_behavior/abstract_behavior";
import { HEADINGS, fetchValidHeadings } from "@knowledge/js/tools/knowledge_tools";
import {
    onWillStart,
    useEffect,
    useState } from "@odoo/owl";

export class TableOfContentBehavior extends AbstractBehavior {
    static template = "knowledge.TableOfContentBehavior";

    setup () {
        super.setup();
        this.state = useState({
            toc: []
        });
        if (!this.props.readonly) {
            useEffect(() => {
                /**
                 * When the user drags a link from the table of content and drop
                 * it on the table of content, the editor was duplicating the link.
                 * To prevent that behavior, we will stop the propagation of the
                 * drop event.
                 * @param {Event} event
                 */
                const onDrop = event => {
                    event.preventDefault();
                    event.stopPropagation();
                };
                const observer = this.setMutationObserver();
                this.props.anchor.addEventListener('drop', onDrop);
                return () => {
                    observer.disconnect();
                    this.props.anchor.removeEventListener('drop', onDrop);
                };
            });
        }

        onWillStart(() => {
            this._updateTableOfContents();
        });
    }

    //--------------------------------------------------------------------------
    // TECHNICAL
    //--------------------------------------------------------------------------

    /**
     * Observes the changes made to the titles of the editor.
     * @returns {MutationObserver}
     */
    setMutationObserver () {
        const observer = new MutationObserver(mutationList => {
            const update = mutationList.find(mutation => {
                if (Array.from(mutation.addedNodes).find(node => HEADINGS.includes(node.tagName)) ||
                    Array.from(mutation.removedNodes).find(node => HEADINGS.includes(node.tagName))) {
                    // We just added/removed a header node -> update the ToC
                    return true;
                }

                // Powerbox is open -> do not attempt to update the ToC
                if (this.editor.powerbox.isOpen) {
                    if (this.updateTimeout) {
                        window.clearTimeout(this.updateTimeout);
                    }
                    return false;
                }

                // check if we modified the content of a header element
                const target = mutation.target;
                const headerNode = this._findClosestHeader(target);

                return headerNode && headerNode.parentElement === this.props.root;
            });
            if (update) {
                this.delayedUpdateTableOfContents();
            }
        });
        observer.observe(this.props.root, {
            childList: true,
            attributes: false,
            subtree: true,
            characterData: true,
        });
        return observer;
    }

    //--------------------------------------------------------------------------
    // BUSINESS
    //--------------------------------------------------------------------------

    /**
     * Allows to debounce the update of the Table of Content to avoid updating whenever every single
     * character is typed. The debounce is set to 500ms.
     */
    delayedUpdateTableOfContents() {
        if (this.updateTimeout) {
            window.clearTimeout(this.updateTimeout);
        }
        this.updateTimeout = window.setTimeout(this._updateTableOfContents.bind(this), 500);
    }

    /**
     * Helper methods that fetches the closest Header Element based on a target Node.
     *
     * @param {Node} node
     * @returns {Element} the closest header or undefined if not found
     */
    _findClosestHeader(node) {
        if (node && node.nodeType === Node.TEXT_NODE) {
            // we are modifying the text of a Node, check its parent
            node = node.parentElement;
        }

        if (node && node.nodeType === Node.ELEMENT_NODE) {
            if (!HEADINGS.includes(node.tagName)) {
                // this node is not a direct header node, but it could be *inside* a header node
                // -> check closest header node
                node = node.closest(HEADINGS.join(','));
            }

            if (node && HEADINGS.includes(node.tagName)) {
                return node;
            }
        }

        return undefined;
    }

    /**
     * Updates the Table of Content to match the document headings.
     * We pause our observer during the process.
     *
     * We have a 'depth' system for headers, the depth of a header is simply how much left-padding
     * it is showing to give an impression of hierarchy, e.g:
     * - Header 1
     *   - Sub-Header 1
     *     - Sub-sub-header 1
     *   - Sub-Header 2
     * - Header 2
     *   - Sub-Header 3
     *
     * The logic is as follows:
     * - If it is the same tag as 'the previous one' in the loop
     *   -> keep the same depth
     * - If the header tag is "bigger" than the previous one (a H5 compared to H4)
     *   -> Increase the depth by one
     *      /!\ We only increase by one, even if we are comparing a H5 to a H3
     *          This avoids some strange spacing and lets the user choose its headers style
     * - If the header tag is "smaller" than the previous one
     *   -> When going down, check if our current "tree" (our hierarchy starting with the highest
     *      tag) already has this type of tag at a certain depth, and use that.
     *      Otherwise use the depth of the tag (0 for h1, 1 for h2, 2 for h3, ...).
     *
     * Some examples of non-trivial header hierarchy can be found in the QUnit tests of this method.
     */
    _updateTableOfContents () {

        let currentDepthByTag = {};
        let previousTag = undefined;
        let previousDepth = -1;
        let index = 0;

        this.state.toc = fetchValidHeadings(this.props.root).map(heading => {
            let depth = HEADINGS.indexOf(heading.tagName);
            if (depth !== previousDepth && heading.tagName === previousTag) {
                depth = previousDepth;
            } else if (depth > previousDepth) {
                if (heading.tagName !== previousTag && HEADINGS.indexOf(previousTag) < depth) {
                    depth = previousDepth + 1;
                } else {
                    depth = previousDepth;
                }
            } else if (depth < previousDepth) {
                if (currentDepthByTag.hasOwnProperty(heading.tagName)) {
                    depth = currentDepthByTag[heading.tagName];
                }
            }

            previousTag = heading.tagName;
            previousDepth = depth;

            // going back to 0 depth, wipe-out the 'currentDepthByTag'
            if (depth === 0) {
                currentDepthByTag = {};
            }
            currentDepthByTag[heading.tagName] = depth;

            return {
                depth: depth,
                index: index++,
                name: heading.innerText,
                tagName: heading.tagName,
            };
        });
    }

    //--------------------------------------------------------------------------
    // HANDLERS
    //--------------------------------------------------------------------------

    /**
     * Scroll through the view to display the matching heading.
     * Adds a small highlight in/out animation using a class.
     *
     * @param {Event} event
     */
    _onTocLinkClick (event) {
        event.preventDefault();
        const headingIndex = parseInt(event.target.getAttribute('data-oe-nodeid'));
        const targetHeading = fetchValidHeadings(this.props.root)[headingIndex];
        if (targetHeading){
            targetHeading.scrollIntoView({
                behavior: 'smooth',
            });
            targetHeading.classList.add('o_knowledge_header_highlight');
            window.setTimeout(() => {
                targetHeading.classList.remove('o_knowledge_header_highlight');
            }, 2000);
        } else {
            this._updateTableOfContents();
        }
    }
}
