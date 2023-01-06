/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { renderToString } from "@web/core/utils/render";
import { useDebounced } from "@web/core/utils/timing";

import { Component, useState, useRef, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";

class MenuItem extends Component {}
MenuItem.template = "web.ProfilingQwebView.menuitem";

/**
 * This widget is intended to be used on Text fields. It will provide Ace Editor
 * for display XML and Python profiling.
 */
export class ProfilingQwebView extends Component {
    setup() {
        super.setup();

        this.orm = useService("orm");
        this.ace = useRef("ace");
        this.selector = useRef("selector");

        for (const line of this.profile.data) {
            line.xpath = line.xpath.replace(/([^\]])\//g, "$1[1]/").replace(/([^\]])$/g, "$1[1]");
        }
        this.state = useState({
            viewID: this.profile.data.length ? this.profile.data[0].view_id : 0,
            view: null,
        });

        this.renderProfilingInformation = useDebounced(this.renderProfilingInformation, 100);

        onWillStart(async () => {
            await loadBundle({
                jsLibs: [
                    '/web/static/lib/ace/ace.js',
                    [
                        '/web/static/lib/ace/mode-python.js',
                        '/web/static/lib/ace/mode-xml.js',
                        '/web/static/lib/ace/mode-qweb.js'
                    ],
                ],
            });
            await this._fetchViewData();
            this.state.view = this.viewObjects.find((view) => view.id === this.state.viewID);
        });
        onMounted(() => {
            this._startAce(this.ace.el);
            this._renderView();
        });
        onWillUnmount(() => {
            if (this.aceEditor) {
                this.aceEditor.destroy();
            }
            this._unmoutInfo();
        });
    }

    /**
     * Return JSON values to render the view
     *
     * @returns {archs, data: {template, xpath, directive, time, duration, query }[]}
     */
    get profile() {
        if (this.props.value) {
            return JSON.parse(this.props.value)[0].results;
        }
        return { archs: {}, data: [] };
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Return association of view key, view name, query number and total delay
     *
     * @private
     * @returns {Promise<viewObjects>}
     */
    async _fetchViewData () {
        const viewIDs = Array.from(new Set(this.profile.data.map((line) => line.view_id)));
        const viewObjects = await this.orm.call("ir.ui.view", "search_read", [], {
            fields: ["id", "display_name", "key"],
            domain: [["id", "in", viewIDs]],
        });
        for (const view of viewObjects) {
            view.delay = 0;
            view.query = 0;
            const lines = this.profile.data.filter((l) => l.view_id === view.id);
            const root = lines.find((l) => l.xpath === "");
            if (root) {
                view.delay += root.delay;
                view.query += root.query;
            } else {
                view.delay = lines.map((l) => l.delay).reduce((a, b) => a + b);
                view.query = lines.map((l) => l.query).reduce((a, b) => a + b);
            }
            view.delay = Math.ceil(view.delay * 10) / 10;
        }
        this.viewObjects = viewObjects;
    }

    /**
     * Format delay to readable.
     *
     * @private
     * @param {number} delay
     * @returns {string}
     */
    _formatDelay (delay) {
        return delay ? _.str.sprintf("%.1f", Math.ceil(delay * 10) / 10) : ".";
    }

    /**
     * Starts the ace library on the given DOM element. This initializes the
     * ace editor in readonly mode.
     *
     * @private
     * @param {Node} node - the DOM element the ace library must initialize on
     */
     _startAce (node) {
        this.aceEditor = window.ace.edit(node);
        this.aceEditor.setOptions({
            maxLines: Infinity,
            showPrintMargin: false,
            highlightActiveLine: false,
            highlightGutterLine: true,
            readOnly: true,
        });
        this.aceEditor.renderer.setOptions({
            displayIndentGuides: true,
            showGutter: true,
        });
        this.aceEditor.renderer.$cursorLayer.element.style.display = "none";

        this.aceEditor.$blockScrolling = true;
        this.aceSession = this.aceEditor.getSession();
        this.aceSession.setOptions({
            useWorker: false,
            mode: "ace/mode/qweb",
            tabSize: 2,
            useSoftTabs: true,
        });

        // Ace render 3 times when change the value and 1 time per click.
        this.aceEditor.renderer.on("afterRender", this.renderProfilingInformation.bind(this));
    }

    renderProfilingInformation () {
        this._unmoutInfo();

        let flat = {};
        let arch = [{ xpath: "", children: [] }];
        const rows = this.ace.el.querySelectorAll(".ace_gutter .ace_gutter-cell");
        const elems = this.ace.el.querySelectorAll(".ace_tag-open, .ace_end-tag-close, .ace_end-tag-open, .ace_qweb");
        elems.forEach(node => {
            const parent = arch[arch.length - 1];
            let xpath = parent.xpath;
            if (node.classList.contains("ace_end-tag-close")) {
                // Close tag.
                let previous = node;
                while (previous = previous.previousElementSibling) {
                    if (previous && previous.classList.contains("ace_tag-name")) {
                        break;
                    }
                }
                const tag = previous && previous.textContent;
                if (parent.tag === tag) {
                    // can be different when scroll because ace does not display the previous lines.
                    arch.pop();
                }
            } else if (node.classList.contains("ace_end-tag-open")) {
                // Auto close tag.
                const tag = node.nextElementSibling && node.nextElementSibling.textContent;
                if (parent.tag === tag) {
                    // can be different when scroll because ace does not display the previous lines.
                    arch.pop();
                }
            } else if (node.classList.contains("ace_qweb")) {
                // QWeb attribute.
                const directive = node.textContent;
                parent.directive.push({
                    el: node,
                    directive: directive,
                });

                // Compute delay and query number.
                let delay = 0;
                let query = 0;
                for (const line of this.profile.data) {
                    if (
                        line.view_id === this.state.viewID &&
                        line.xpath === xpath &&
                        line.directive.includes(directive)
                    ) {
                        delay += line.delay;
                        query += line.query;
                    }
                }

                // Render delay and query number in span visible on hover.
                if ((delay || query) && !node.querySelector(".o_info")) {
                    this._renderHover(delay, query, node);
                }
            } else if (node.classList.contains("ace_tag-open")) {
                // Open tag.
                const nodeTagName = node.nextElementSibling;
                const aceLine = nodeTagName.parentNode;
                const index = [].indexOf.call(aceLine.parentNode.children, aceLine);
                const row = rows[index];

                // Add a children to the arch and compute the xpath.
                xpath += "/" + nodeTagName.textContent;
                let i = 1;
                while (flat[xpath + "[" + i + "]"]) {
                    i++;
                }
                xpath += "[" + i + "]";
                flat[xpath] = { xpath: xpath, tag: nodeTagName.textContent, children: [], directive: [] };
                arch.push(flat[xpath]);
                parent.children.push(flat[xpath]);

                // Compute delay and query number.
                const closed = !!row.querySelector(".ace_closed");
                const delays = [];
                const querys = [];
                const groups = {};
                let displayDetail = false;
                for (const line of this.profile.data) {
                    if (
                        line.view_id === this.state.viewID &&
                        (closed ? line.xpath.startsWith(xpath) : line.xpath === xpath)
                    ) {
                        delays.push(line.delay);
                        querys.push(line.query);
                        const directive = line.directive.split("=")[0];
                        if (!groups[directive]) {
                            groups[directive] = {
                                delays: [],
                                querys: [],
                            };
                        } else {
                            displayDetail = true;
                        }
                        groups[directive].delays.push(this._formatDelay(line.delay));
                        groups[directive].querys.push(line.query);
                    }
                }

                // Display delay and query number in front of the line.
                if (delays.length && !row.querySelector(".o_info")) {
                    this._renderInfo(delays, querys, displayDetail, groups, row);
                }
            }
            node.setAttribute("data-xpath", xpath);
        });
    }
    /**
     * Set the view ID and send atch to ACE.
     *
     * @private
     */
    _renderView() {
        const view = this.viewObjects.find((view) => view.id === this.state.viewID);
        if (view) {
            const arch = this.profile.archs[view.id] || "";
            if (this.aceSession.getValue() !== arch) {
                this.aceSession.setValue(arch);
            }
        } else {
            this.aceSession.setValue("");
        }
        this.state.view = view;
    }
    _unmoutInfo() {
        if (this.hover) {
            if (this.ace.el.querySelector('.o_ace_hover')) {
                this.ace.el.querySelector('.o_ace_hover').remove();
            }
        }
        if (this.info) {
            if (this.ace.el.querySelector('.o_ace_info')) {
                this.ace.el.querySelector('.o_ace_info').remove();
            }
        }
    }
    _renderHover(delay, query, node) {
        const xml = renderToString('web.ProfilingQwebView.hover', {
            delay: this._formatDelay(delay),
            query: query,
        });
        const div = new DOMParser().parseFromString(xml, "text/html").querySelector('div');
        node.insertBefore(div, node.firstChild);
    }
    _renderInfo(delays, querys, displayDetail, groups, node) {
        const xml = renderToString('web.ProfilingQwebView.info', {
            delay: this._formatDelay(delays.reduce((a, b) => a + b, 0)),
            query: querys.reduce((a, b) => a + b, 0) || ".",
            displayDetail: displayDetail,
            groups: groups,
        });
        const div = new DOMParser().parseFromString(xml, "text/html").querySelector('div');
        node.insertBefore(div, node.firstChild);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
     _onSelectView (ev) {
        this.state.viewID = +ev.currentTarget.dataset.id;
        this._renderView();
    }
}
ProfilingQwebView.template = "web.ProfilingQwebView";
ProfilingQwebView.components = { MenuItem };

registry.category("fields").add("profiling_qweb_view", ProfilingQwebView);
