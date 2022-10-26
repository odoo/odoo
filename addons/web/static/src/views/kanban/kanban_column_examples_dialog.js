/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { Notebook } from "@web/core/notebook/notebook";
import { _lt } from "@web/core/l10n/translation";

const { Component, useRef } = owl;

const random = (min, max) => Math.floor(Math.random() * (max - min) + min);

class KanbanExamplesNotebookTemplate extends Component {
    setup() {
        this.columns = [];
        const hasBullet = this.props.bullets && this.props.bullets.length;
        for (const title of this.props.columns) {
            const col = { title, records: [] };
            this.columns.push(col);
            for (let i = 0; i < random(1, 5); i++) {
                const rec = { id: i };
                if (hasBullet && Math.random() > 0.3) {
                    rec.bullet = _.sample(this.props.bullets);
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
KanbanColumnExamplesDialog.title = _lt("Kanban Examples");
