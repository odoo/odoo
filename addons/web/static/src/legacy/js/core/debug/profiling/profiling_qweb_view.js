/** @odoo-module **/

/* eslint-disable comma-dangle */

import registry from "web.field_registry";
import basicFfields from "web.basic_fields";
import core from "web.core";
const qweb = core.qweb;

/**
 * This widget is intended to be used on Text fields. It will provide Ace Editor
 * for display XML and Python profiling.
 */
const ProfilingQwebView = basicFfields.AceEditor.extend({
    template: "web.ProfilingQwebView",
    xmlDependencies: ["/web/static/src/xml/debug.xml"],
    events: _.extend({}, basicFfields.AceEditor.prototype.events, {
        "click .dropdown-menu a": "_onSelectView",
    }),
    /**
     * @override
     * @params parent {Widget}
     */
    init: function () {
        this._super.apply(this, arguments);
        // {template, xpath, directive, time, duration, query }[]
        const results = (this.value && JSON.parse(this.value)[0].results) || {
            archs: {},
            data: [],
        };
        this.profileLines = results.data;
        this.viewArch = results.archs;
        this.viewIDs = Array.from(new Set(this.profileLines.map((line) => line.view_id)));
        for (const line of this.profileLines) {
            line.xpath = line.xpath.replace(/([^\]])\//g, "$1[1]/").replace(/([^\]])$/g, "$1[1]");
        }
        this.viewID = this.profileLines.length ? this.profileLines[0].view_id : 0;
        this.mode = "readonly";
    },
    /**
     * Search xml view
     *
     * @override
     * @returns {Promise}
     */
    willStart: async function () {
        const _super = this._super;
        this.views = await this._rpc({
            model: "ir.ui.view",
            method: "search_read",
            fields: ["id", "display_name", "key"],
            domain: [["id", "in", this.viewIDs]],
        });
        for (const view of this.views) {
            view.delay = 0;
            view.query = 0;
            const lines = this.profileLines.filter((l) => l.view_id === view.id);
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
        await _super.call(this);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Set view to render
     *
     * @override
     * @returns {Promise}
     */
    _render: function () {
        this.view = this.views.find((view) => view.id === this.viewID);
        if (this.view) {
            const content = this.$(".dropdown-menu a[data-id=" + this.view.id + "]").html();
            this.$(".dropdown-toggle").empty().append(content);
            const arch = this.viewArch[this.view.id] || "";
            if (this.aceSession.getValue() !== arch) {
                this.aceSession.setValue(arch);
            }
        } else {
            this.aceSession.setValue("");
        }
    },
    _renderProfilingInformation: function () {
        let flat = {};
        let arch = [{ xpath: "", children: [] }];
        const $rows = this.$(".ace_gutter .ace_gutter-cell");
        $rows.find(".o_info").remove();

        this.$(".ace_tag-open, .ace_end-tag-close, .ace_end-tag-open, .ace_qweb").each(
            (i, node) => {
                const $node = $(node);
                const parent = arch[arch.length - 1];
                let xpath = parent.xpath;
                if ($node.hasClass("ace_end-tag-close")) {
                    // Close tag.
                    const tag = $node.prevAll(".ace_tag-name:first").text();
                    if (parent.tag === tag) {
                        // can be different when scroll because ace does not display the previous lines.
                        arch.pop();
                    }
                } else if ($node.hasClass("ace_end-tag-open")) {
                    // Auto close tag.
                    const tag = $node.next().text();
                    if (parent.tag === tag) {
                        // can be different when scroll because ace does not display the previous lines.
                        arch.pop();
                    }
                } else if ($node.hasClass("ace_qweb")) {
                    // QWeb attribute.
                    const directive = $node.text();
                    parent.directive.push({
                        el: node,
                        directive: directive,
                    });

                    // Compute delay and query number.
                    let delay = 0;
                    let query = 0;
                    for (const line of this.profileLines) {
                        if (
                            line.view_id === this.viewID &&
                            line.xpath === xpath &&
                            line.directive.includes(directive)
                        ) {
                            delay += line.delay;
                            query += line.query;
                        }
                    }

                    // Render delay and query number in span visible on hover.
                    if ((delay || query) && !$node.children(".o_info").length) {
                        $(
                            qweb.render("web.ProfilingQwebView.hover", {
                                delay: this._formatDelay(delay),
                                query: query,
                            })
                        ).prependTo($node);
                    }
                } else if ($node.hasClass("ace_tag-open")) {
                    // Open tag.
                    const $tag = $node.next(".ace_tag-name");
                    const tag = $tag.text();
                    const $row = $($rows[$tag.parent(".ace_line").index()]);

                    // Add a children to the arch and compute the xpath.
                    xpath += "/" + tag;
                    let i = 1;
                    while (flat[xpath + "[" + i + "]"]) {
                        i++;
                    }
                    xpath += "[" + i + "]";
                    flat[xpath] = { xpath: xpath, tag: tag, children: [], directive: [] };
                    arch.push(flat[xpath]);
                    parent.children.push(flat[xpath]);

                    // Compute delay and query number.
                    const closed = !!$row.find(".ace_closed").length;
                    const delays = [];
                    const querys = [];
                    const groups = {};
                    let displayDetail = false;
                    for (const line of this.profileLines) {
                        if (
                            line.view_id === this.viewID &&
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
                    if (delays.length && !$row.children(".o_info").length) {
                        $(
                            qweb.render("web.ProfilingQwebView.info", {
                                delay: this._formatDelay(delays.reduce((a, b) => a + b, 0)),
                                query: querys.reduce((a, b) => a + b, 0) || ".",
                                detail: displayDetail,
                                groups: groups,
                            })
                        ).prependTo($row);
                    }
                }
                $node.attr("data-xpath", xpath);
            }
        );
    },
    _formatDelay: function (delay) {
        return delay ? _.str.sprintf("%.1f", Math.ceil(delay * 10) / 10) : ".";
    },
    /**
     * Starts the ace library on the given DOM element. This initializes the
     * ace editor in readonly mode.
     *
     * @private
     * @param {Node} node - the DOM element the ace library must initialize on
     */
    _startAce: function (node) {
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
        this.aceEditor.renderer.$gutter.removeAttribute("aria-hidden");
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
        this.aceEditor.renderer.on("afterRender", this._renderProfilingInformation.bind(this));
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onSelectView: function (ev) {
        ev.preventDefault();
        this.viewID = +$(ev.currentTarget).data("id");
        this._render();
    },
});

registry.add("profiling_qweb_view", ProfilingQwebView);
