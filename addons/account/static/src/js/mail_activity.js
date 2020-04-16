odoo.define('account.activity', function (require) {
    "use strict";

    const AbstractFieldOwl = require('web.AbstractFieldOwl');
    const fieldRegistryOwl = require('web.field_registry_owl');
    const patchMixin = require('web.patchMixin');

    class VatActivity extends AbstractFieldOwl {

        constructor(...args) {
            super(...args);
            this.MAX_ACTIVITY_DISPLAY = 5;
            this.info = JSON.parse(this.value);
            if (this.info) {
                this.info.more_activities = false;
                if (this.info.activities.length > this.MAX_ACTIVITY_DISPLAY) {
                    this.info.more_activities = true;
                    this.info.activities = this.info.activities.slice(0, this.MAX_ACTIVITY_DISPLAY);
                }
            }
        }

        mounted() {
            if (!this.info) {
                this.el.innerHTML = '';
                return;
            }
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        _onOpenActivity(ev) {
            if (!ev.target.classList.contains('see_activity')) {
                return;
            }
            this.trigger('do_action', { 'action': {
                type: 'ir.actions.act_window',
                name: this.env._t('Journal Entry'),
                target: 'current',
                res_id: parseInt(ev.target.getAttribute('data-res-id')),
                res_model: 'account.move',
                views: [[false, 'form']],
            } });
        }

        _onOpenAll(ev) {
            this.trigger('do_action', {'action': {
                type: 'ir.actions.act_window',
                name: this.env._t('Journal Entries'),
                res_model: 'account.move',
                views: [[false, 'kanban'], [false, 'form']],
                search_view_id: [false],
                domain: [['journal_id', '=', this.resId], ['activity_ids', '!=', false]],
            } });
        }

    }

    VatActivity.template = 'accountJournalDashboardActivity';

    fieldRegistryOwl.add('kanban_vat_activity', patchMixin(VatActivity));

    return VatActivity;
});
