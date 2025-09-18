// @ts-check

/** @module @web/views/kanban/kanban_column_examples_dialog - Dialog showcasing example column layouts for kanban board setup */

import { Component, useRef } from "@odoo/owl";
import { Notebook } from "@web/components/notebook/notebook";
import { Dialog } from "@web/ui/dialog/dialog";

/**
 * @param {number} min - Inclusive lower bound.
 * @param {number} max - Exclusive upper bound.
 * @returns {number} Random integer in [min, max).
 */
const random = (min, max) => Math.floor(Math.random() * (max - min) + min);

/** Renders a single example tab with randomized placeholder records. */
class KanbanExamplesNotebookTemplate extends Component {
    static template = "web.KanbanExamplesNotebookTemplate";
    static props = ["*"];
    static defaultProps = {
        columns: [],
        foldedColumns: [],
    };
    setup() {
        this.columns = [];
        const hasBullet = this.props.bullets && this.props.bullets.length;
        const allColumns = [...this.props.columns, ...this.props.foldedColumns];
        for (const title of allColumns) {
            const col = { title, records: [] };
            this.columns.push(col);
            for (let i = 0; i < random(1, 5); i++) {
                const rec = { id: i };
                if (hasBullet && Math.random() > 0.3) {
                    const sampleId = Math.floor(
                        Math.random() * this.props.bullets.length,
                    );
                    rec.bullet = this.props.bullets[sampleId];
                }
                col.records.push(rec);
            }
        }
    }
}

/**
 * Dialog that presents predefined column layout examples for kanban views.
 *
 * Users pick an example tab and click "Apply" to auto-create columns
 * matching the selected layout. Used when a grouped kanban has no columns yet.
 */
export class KanbanColumnExamplesDialog extends Component {
    static template = "web.KanbanColumnExamplesDialog";
    static components = { Dialog, Notebook };
    static props = ["*"];

    setup() {
        this.navList = useRef("navList");
        this.pages = [];
        this.activePage = null;
        this.props.examples.forEach((eg) => {
            this.pages.push({
                Component: KanbanExamplesNotebookTemplate,
                title: eg.name,
                props: eg,
                id: eg.name,
            });
        });
    }

    /**
     * Track the currently selected notebook tab.
     * @param {string} page - Tab identifier (example name).
     */
    onPageUpdate(page) {
        this.activePage = page;
    }

    /** Apply the selected example layout and close the dialog. */
    applyExamples() {
        const index = this.props.examples.findIndex((e) => e.name === this.activePage);
        this.props.applyExamples(index);
        this.props.close();
    }
}
