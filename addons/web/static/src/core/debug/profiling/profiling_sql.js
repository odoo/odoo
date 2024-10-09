/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Component, useRef } from "@odoo/owl";


export class ProfilingSQLLine extends Component {
    setup() {
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.rootRef = useRef("root");
    }
    showExplain() {
        this.dialog.add(AlertDialog, {
            title: "EXPLAIN",
            body: this.props.query.explain,
            contentClass: 'sql-profile',
        });
    }
    showExplainVisualizer() {
        this.action.doAction({
            type: 'ir.actions.act_url',
            url: `/web/pev2/${this.__owl__.parent.props.record.data.id}/${this.props.query.start}`,
        });
    }
    showFullQuery() {
        this.dialog.add(AlertDialog, {
            title: "Full query",
            body: this.beautify(this.props.query.full_query),
            contentClass: 'sql-profile',
        });
    }
    beautify(query) {
        // Library is added in `web_editor`
        return window.vkbeautify ? window.vkbeautify.sql(query) : query;
    }
    toggleState() {
        $(this.rootRef.el).toggleClass('active');
    }
}
ProfilingSQLLine.template = "web.ProfilingSQLLine";
ProfilingSQLLine.props = {
    query: { type: Object },
    totalTime: { type: Number },
}

export class ProfilingSQL extends Component {
    setup() {
        this.queries = this.props.value ? JSON.parse(this.props.value).sort((a, b) => a.time < b.time) : [];
        this.totalTime = this.queries.reduce((acc, val) => acc + val.time, 0);
    }
}
ProfilingSQL.components = { ProfilingSQLLine }
ProfilingSQL.template = "web.ProfilingSQL";

registry.category("fields").add("profiling_sql", ProfilingSQL);
