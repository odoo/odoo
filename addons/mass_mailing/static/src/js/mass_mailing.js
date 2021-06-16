odoo.define('mass_mailing.mass_mailing', function (require) {
"use strict";

const ListController = require('web.ListController');
const ListView = require('web.ListView');

const KanbanController = require('web.KanbanController');
const KanbanView = require('web.KanbanView');
const KanbanColumn = require('web.KanbanColumn');

const viewRegistry = require('web.view_registry');

function renderCreateABTesting (mailing_type) {
    if (this.$buttons) {
        this.$buttons.on('click', '.o_button_create_ab_testing', () => {
            this.do_action({
                name: 'Create A/B Testing',
                type: 'ir.actions.act_window',
                res_model: 'mailing.ab.testing',
                views: [[false, 'form']],
                context: this.model.loadParams.context,
            });
        });
    }
}

const MassMailingListController = ListController.extend({
    willStart: function () {
        var self = this;
        const ready = this.getSession().user_has_group('mass_mailing.group_mass_mailing_ab_testing')
            .then(function (ab_testing_enabled) {
                if (ab_testing_enabled) {
                    self.buttons_template = 'mass_mailing.list.buttons';
                }
            });
        return Promise.all([this._super(...arguments), ready]);
    },
    renderButtons: function () {
        this._super(...arguments);
        renderCreateABTesting.apply(this, arguments);
    },
});

const MassMailingListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: MassMailingListController,
    }),
});

const MassMailingKanbanController = KanbanController.extend({
    willStart: function () {
        var self = this;
        const ready = this.getSession().user_has_group('mass_mailing.group_mass_mailing_ab_testing')
            .then(function (ab_testing_enabled) {
                if (ab_testing_enabled) {
                    self.buttons_template = 'mass_mailing.kanban.buttons';
                }
            });
        return Promise.all([this._super(...arguments), ready]);
    },
    renderButtons: function () {
        this._super(...arguments);
        renderCreateABTesting.apply(this, arguments);
    },
});

const MassMailingKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: MassMailingKanbanController,
    }),
});

KanbanColumn.include({
    init: function () {
        this._super.apply(this, arguments);
        if (this.modelName in ['mailing.mailing', 'mailing.ab.testing']) {
            this.draggable = false;
        }
    },
});

viewRegistry.add('mass_mailing_tree', MassMailingListView);
viewRegistry.add('mass_mailing_kanban', MassMailingKanbanView);
});
