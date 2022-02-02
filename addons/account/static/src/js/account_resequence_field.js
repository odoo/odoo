odoo.define('account.ShowResequenceRenderer', function (require) {
"use strict";

const AbstractFieldOwl = require('web.AbstractFieldOwl');
const field_registry = require('web.field_registry_owl');

const { Component, onWillUpdateProps } = owl;

class ChangeLine extends Component { }
ChangeLine.template = 'account.ResequenceChangeLine';
ChangeLine.props = ["changeLine", 'ordering'];


class ShowResequenceRenderer extends AbstractFieldOwl {
    setup() {
        super.setup();
        this.data = this.value ? JSON.parse(this.value) : {
            changeLines: [],
            ordering: 'date',
        };
        onWillUpdateProps(() => {
            Object.assign(this.data, JSON.parse(this.value));
        });
    }
}
ShowResequenceRenderer.template = 'account.ResequenceRenderer';
ShowResequenceRenderer.components = { ChangeLine }

field_registry.add('account_resequence_widget', ShowResequenceRenderer);
return ShowResequenceRenderer;
});
