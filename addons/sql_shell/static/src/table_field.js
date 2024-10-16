/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { qweb } from 'web.core';
import { ScriptSafe } from "@web/core/utils/strings";

export class TableRow extends Component {}
TableRow.template = "sql_shell.TableRow";
TableRow.props = ['row'];

export class Table extends Component {
    showExplainVisualizer() {
        const tab = window.open('about:blank', '_blank');
        tab.document.write(qweb.render('sql_shell.Explain', {
            cdn: 'https://unpkg.com',
            query: ScriptSafe(JSON.stringify({
                query: this.props.record.data.query,
                plan: this.props.record.data.result.rows.join('\n'),
            })),
        }));
        tab.document.close();
    }
}
Table.components = { TableRow };
Table.template = "sql_shell.Table";
Table.supportedTypes = ["json"];

registry.category("fields").add("table", Table);
