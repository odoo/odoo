
/** @odoo-module */

import core from 'web.core';
import { ContentsContainerBehavior } from './knowledge_behaviors.js';

const qweb = core.qweb;

const HEADINGS = [
    'H1',
    'H2',
    'H3',
    'H4',
    'H5',
    'H6',
];
/**
 * A behavior for the /toc command @see Wysiwyg . This behavior use a
 * mutationObserver to listen to changes on <h1> -> <h6> nodes, and create
 * a table of contents. It is an extension of @see ContentsContainerBehavior
 */
const TableOfContentsBehavior = ContentsContainerBehavior.extend({
    //--------------------------------------------------------------------------
    // 'ContentsContainerBehavior' overrides
    //--------------------------------------------------------------------------

    /**
     * Initialize the editor content observer.
     * It listens to changes on H1 through H6 tags and updates a Table of Content accordingly.
     *
     * @override
     */
    init: function () {
        this.observer = new MutationObserver((mutationList) => {
            const update = mutationList.find(mutation => {
                if (Array.from(mutation.addedNodes).find((node) => HEADINGS.includes(node.tagName)) ||
                    Array.from(mutation.removedNodes).find((node) => HEADINGS.includes(node.tagName))) {
                    // We just added/removed a header node -> update the ToC
                    return true;
                }

                // Command bar is active -> do not attempt to update the ToC
                if (this.handler.editor.commandBar._active) {
                    if (this.updateTimeout) {
                        clearTimeout(this.updateTimeout);
                    }
                    return false;
                }

                let target = mutation.target;
                if (target) {
                    // the text node is the actual text of the header element, we need the tag element
                    if (target.nodeType === Node.TEXT_NODE && target.parentElement) {
                        target = target.parentElement;
                    }
                    return target.parentElement === this.handler.field && target.nodeType === Node.ELEMENT_NODE && HEADINGS.includes(target.tagName);
                }
                return false;
            });

            if (update) {
                this.delayedUpdateTableOfContents();
            }
        });

        this._super.apply(this, arguments);
    },

    /**
     * Adds the ToC click listener to scroll towards to associated heading tag.
     * Also adds the listener that will update the ToC as the user is typing.
     *
     * @override
     */
    applyListeners: function () {
        this._super.apply(this, arguments);
        $(this.anchor).on('click', '.o_toc_link', this._onTocLinkClick.bind(this));
        if (this.mode === 'edit') {
            this.observer.observe(this.handler.field, {
                childList: true,
                attributes: false,
                subtree: true,
                characterData: true,
            });

            this._updateTableOfContents();
        }
    },
    /**
     * @override
     */
    disableListeners: function () {
        $(this.anchor).off('click', '.o_toc_link');
        if (this.mode === 'edit') {
            this.observer.disconnect();
        }
    },

    //--------------------------------------------------------------------------
    // Table of content - BUSINESS LOGIC
    //--------------------------------------------------------------------------

    /**
     * Allows to debounce the update of the Table of Content to avoid updating whenever every single
     * character is typed. The debounce is set to 500ms.
     */
    delayedUpdateTableOfContents() {
        if (this.updateTimeout) {
            clearTimeout(this.updateTimeout);
        }
        this.updateTimeout = setTimeout(this._updateTableOfContents.bind(this), 500);
    },

    /**
     * Updates the Table of Content to match the document headings.
     * We pause our observer during the process.
     */
    _updateTableOfContents: function () {
        this.handler.editor.observerUnactive('knowledge_toc_update');

        const allHeadings = Array.from(this.handler.field.querySelectorAll('h1,h2,h3,h4,h5,h6'))
            .filter((heading) => heading.innerText.trim().length > 0);

        let currentDepthByTag = {};
        let previousTag = undefined;
        let previousDepth = -1;
        let index = 0;
        const headingStructure = allHeadings.map((heading) => {
            let depth = HEADINGS.indexOf(heading.tagName)
            // Compute the 'depth' we want to display when increasing
            if (depth !== previousDepth && heading.tagName === previousTag) {
                // Same tag name as previous one -> use same depth
                depth = previousDepth;
            } else if (depth > previousDepth) {
                // This is done only when changing tags, as 2 h4 in our previous example
                // need to be at the same depth
                if (heading.tagName !== previousTag) {
                    // We only go max +1 depth at the time, meaning if a h4 follows a h1,
                    // we want only one extra depth
                    depth = previousDepth + 1;
                }
            } else if (depth < previousDepth) {
                // When going down, it's different, we need to see if our current tree already
                // has this tag at a certain depth, and use that
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
            }
        });

        const updatedToc = qweb.render('knowledge.knowledge_table_of_content', {
            'headings': headingStructure
        });
        const knowledgeToCElement = this.handler.field.getElementsByClassName('o_knowledge_toc_content');
        if (knowledgeToCElement.length !== 0) {
            knowledgeToCElement[0].innerHTML = updatedToc;
        }

        this.handler.editor.observerActive('knowledge_toc_update');
    },

    //--------------------------------------------------------------------------
    // Table of content - HANDLERS
    //--------------------------------------------------------------------------

    /**
     * Scroll through the view to display the matching heading.
     * Adds a small highlight in/out animation using a class.
     *
     * @param {Event} event
     */
    _onTocLinkClick: function (event) {
        event.preventDefault();
        const headingIndex = parseInt(event.target.getAttribute('data-oe-nodeid'));
        const targetHeading = Array.from(this.handler.field.querySelectorAll('h1, h2, h3, h4, h5, h6'))
            .filter((heading) => heading.innerText.trim().length > 0)[headingIndex];
        if (targetHeading){
            targetHeading.scrollIntoView({
                behavior: 'smooth',
            });
            targetHeading.setAttribute('highlight', true);
            setTimeout(() => {
                targetHeading.removeAttribute('highlight');
            }, 2000);
        } else {
            this._updateTableOfContents();
        }
    },
});

export { TableOfContentsBehavior };
