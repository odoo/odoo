odoo.define('account.ShowGroupedList', function (require) {
"use strict";

const { Component } = owl;
const { useState } = owl.hooks;
const AbstractFieldOwl = require('web.AbstractFieldOwl');
const field_registry = require('web.field_registry_owl');

class ListItem extends Component { }
ListItem.template = 'account.GroupedItemTemplate';
ListItem.props = ["item_vals", "options"];

class ListGroup extends Component { }
ListGroup.template = 'account.GroupedItemsTemplate';
ListGroup.components = { ListItem }
ListGroup.props = ["group_vals", "options"];


class ShowGroupedList extends AbstractFieldOwl {
    constructor(...args) {
        super(...args);
        this.data = this.value ? JSON.parse(this.value) : {
            groups_vals: [],
            options: {
                discarded_number: '',
                columns: [],
            },
        };
    }
    async willUpdateProps(nextProps) {
        await super.willUpdateProps(nextProps);
        Object.assign(this.data, JSON.parse(this.value));
    }
}
ShowGroupedList.template = 'account.GroupedListTemplate';
ShowGroupedList.components = { ListGroup }

field_registry.add('grouped_view_widget', ShowGroupedList);
return ShowGroupedList;
});
