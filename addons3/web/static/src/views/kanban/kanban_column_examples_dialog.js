/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { Notebook } from "@web/core/notebook/notebook";
import { _t } from "@web/core/l10n/translation";

import { Component, useRef } from "@odoo/owl";

const random = (min, max) => Math.floor(Math.random() * (max - min) + min);

class KanbanExamplesNotebookTemplate extends Component {
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
                    const sampleId = Math.floor(Math.random() * this.props.bullets.length);
                    rec.bullet = this.props.bullets[sampleId];
                }
                col.records.push(rec);
            }
        }
    }
}
KanbanExamplesNotebookTemplate.template = "web.KanbanExamplesNotebookTemplate";

export class KanbanColumnExamplesDialog extends Component {
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

    onPageUpdate(page) {
        this.activePage = page;
    }

    applyExamples() {
        const index = this.props.examples.findIndex((e) => e.name === this.activePage);
        this.props.applyExamples(index);
        this.props.close();
    }
}
KanbanColumnExamplesDialog.template = "web.KanbanColumnExamplesDialog";
KanbanColumnExamplesDialog.components = { Dialog, Notebook };
KanbanColumnExamplesDialog.title = _t("Kanban Examples");
