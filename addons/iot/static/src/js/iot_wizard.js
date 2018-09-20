odoo.define('iot.wizard', function (require) {
"use strict";
var KanbanController = require('web.KanbanController');
var KanbanView = require('web.KanbanView');
var view_registry = require('web.view_registry');
var ListController = require('web.ListController');
var ListView = require('web.ListView');



function boxRenderButtons($node) {
        var self = this;
        this.$buttons = $('<div/>');
        this.$buttons.html('<button class="btn btn-primary type="button">CONNECT</button>');
        this.$buttons.on('click', function () {
            self.do_action('iot.action_add_iot_box');
        });
        this.$buttons.appendTo($node);
}

var BoxKanbanController = KanbanController.extend({
    renderButtons: function ($node) {
        return boxRenderButtons.apply(this, arguments);
    },
});

var BoxKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: BoxKanbanController,
    }),
});

var BoxListController = ListController.extend({
    renderButtons: function ($node) {
        return boxRenderButtons.apply(this, arguments);
    },
});

var BoxListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: BoxListController,
    }),
});

view_registry.add('box_kanban_view', BoxKanbanView);
view_registry.add('box_list_view', BoxListView);




});