/** @odoo-module **/

import clientAction from 'report.client_action';
import core from 'web.core';

const qweb = core.qweb;

const ReceptionReport = clientAction.extend({
    /**
     * @override
     */
    init: function (parent, action, options) {
        this._super(...arguments);
        this.context = Object.assign(action.context || {}, {
            active_ids: action.context.default_picking_ids,
        });
        this.report_name = `stock.report_reception`;
        this.report_url = `/report/html/${this.report_name}/?context=${JSON.stringify(this.context)}`;
        this._title = action.name;
    },

    /**
     * @override
     */
     start: function () {
        return Promise.all([
            this._super(...arguments),
        ]).then(() => {
            this._renderButtons();
        });
    },

    /**
     * @override
     */
    on_attach_callback: function () {
        this._super();
        this.iframe.addEventListener("load",
            () => this._bindAdditionalActionHandlers(),
            { once: true }
        );
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Renders extra report buttons in control panel
     */
     _renderButtons: function () {
        this.$buttons.append(qweb.render('reception_report_buttons', {}));
        this.$buttons.on('click', '.o_report_reception_assign', this._onClickAssign.bind(this));
        this.$buttons.on('click', '.o_print_label', this._onClickPrintLabel.bind(this));
        this.controlPanelProps.cp_content = {
            $buttons: this.$buttons,
        };
    },

    /**
     * Bind additional <button> action handlers
     */
    _bindAdditionalActionHandlers: function () {
        const rr = $(this.iframe).contents().find('.o_report_reception');
        rr.on('click', '.o_report_reception_assign', this._onClickAssign.bind(this));
        rr.on('click', '.o_report_reception_unassign', this._onClickUnassign.bind(this));
        rr.on('click', '.o_report_reception_forecasted', this._onClickForecastReport.bind(this));
        rr.on('click', '.o_print_label', this._onClickPrintLabel.bind(this));
    },


    _switchButton: function (button) {
        button.innerText = button.innerText.includes('Unassign') ? "Assign" : "Unassign";
        button.name = button.name === 'assign_link' ? 'unassign_link' : 'assign_link';
        button.classList.toggle("o_report_reception_assign");
        button.classList.toggle("o_report_reception_unassign");
    },

    /**
     * Assign the specified move(s)
     *
     * @returns {Promise}
     */
    _onClickAssign: function (ev) {
        const el = ev.currentTarget;
        const quantities = []; // incoming qty amounts to assign
        const moveIds = [];
        const inIds = [];
        let nodeToAssign = [];
        if (el.name === 'assign_link') { // One line "Assign"
            nodeToAssign = [el];
            el.closest('tbody').previousElementSibling.querySelectorAll('.o_print_label_all').forEach(button => button.removeAttribute('disabled'));
        } else {
            el.style.display = 'none';
            if (el.name === "assign_all_link") { // Global "Assign All"
                const iframe = this.iframe.contentDocument;
                iframe.querySelectorAll('.o_assign_all').forEach(button => button.style.display = 'none');
                iframe.querySelectorAll('.o_print_label_all').forEach(button => button.removeAttribute('disabled'));
                nodeToAssign = iframe.querySelectorAll('.o_report_reception_assign:not(.o_assign_all)');
            } else { // Local assign all
                nodeToAssign = el.closest('thead').nextElementSibling.querySelectorAll('.o_report_reception_assign:not(.o_assign_all)');
                const thead = el.closest('thead');
                thead.querySelector('.o_print_label_all').removeAttribute('disabled');
                thead.nextElementSibling.querySelectorAll('.o_print_label_all').forEach(button => button.removeAttribute('disabled'));
            }
        }
        nodeToAssign.forEach(node => {
            node.closest('td').nextElementSibling.querySelectorAll('.o_print_label').forEach(button => button.removeAttribute('disabled'));
            moveIds.push(parseInt(node.getAttribute('move-id')));
            quantities.push(parseFloat(node.getAttribute('qty')));
            inIds.push(JSON.parse(node.getAttribute('move-ins-ids')));
            this._switchButton(node);
        });

        return this._rpc({
            model: 'report.stock.report_reception',
            args: [false, moveIds, quantities, inIds],
            method: 'action_assign'
        });
    },

    /**
     * Unassign the specified move
     *
     * @returns {Promise}
     */
     _onClickUnassign: function (ev) {
        const el = ev.currentTarget;
        const quantity = parseFloat(el.getAttribute('qty'));
        const modelId = parseInt(el.getAttribute('move-id'));
        const inIds = JSON.parse("[" + el.getAttribute('move-ins-ids') + "]");
        return this._rpc({
            model: 'report.stock.report_reception',
            args: [false, modelId, quantity, inIds[0]],
            method: 'action_unassign'
        }).then(() => {
            // only switch buttons if successful
            this._switchButton(el);
            el.closest('td').nextElementSibling.querySelectorAll('.o_print_label').forEach(button => button.setAttribute('disabled', true));
        });
    },

    /**
     * Open the forecast report for the product of the selected move.
     *
     * @returns {Promise}
     */
    _onClickForecastReport: function (ev) {
        const modelId = parseInt(ev.currentTarget.getAttribute('move-id'));
        return this._rpc({
            model: 'stock.move',
            args: [[modelId]],
            method: 'action_product_forecast_report'
        }).then((action) => {
            return this.do_action(action);
        });
    },

    /**
     * Print the corresponding source label
     */
    _onClickPrintLabel: function (ev) {
        const el = ev.currentTarget;
        const modelIds = [];
        const productQtys = [];
        const report_file = 'stock.report_reception_report_label';
        let nodeToPrint = [];

        if (el.name === 'print_label') { // One line print
            nodeToPrint = [el];
        } else {
            if (el.name === "print_all_labels") { // Global "Print Labels"
                nodeToPrint = this.iframe.contentDocument.querySelectorAll('.o_print_label:not(.o_print_label_all):not(:disabled)');
            } else { // Local "Print Labels"
                nodeToPrint = el.closest('thead').nextElementSibling.querySelectorAll('.o_print_label:not(.o_print_label_all):not(:disabled)');
            }
        }

        nodeToPrint.forEach(node => {
            modelIds.push(parseInt(node.getAttribute('move-id')));
            productQtys.push(Math.ceil(node.getAttribute('qty')) || '1');
        });

        if (!modelIds.length) { // Nothing to print for this model.
            return Promise.resolve();
        }
        const report_name = `${report_file}?docids=${modelIds}&report_type=qweb-pdf&quantity=${productQtys}`;
        const action = {
            type: 'ir.actions.report',
            report_type: 'qweb-pdf',
            report_name,
            report_file,
        };
        return this.do_action(action);
    }

});

core.action_registry.add('reception_report', ReceptionReport);

export default ReceptionReport;
