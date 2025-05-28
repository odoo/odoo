/** @odoo-module **/
import { registry } from '@web/core/registry';
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { View } from "@web/views/view";
const { Component, useSubEnv } = owl;

class FormListView extends Component {
    setup(){
        useSubEnv({
            config:{},
        });
    }

    get bankReconcileListViewProps(){
        return{
            type:'list',
            display:{
                controlPanel:{
                    "top-left":false,
                    "bottom-left":false,
                }
            },
            resModel:this.props.resModel,
            searchMenuTypes:["filter"],
            allowSelectors:false,
            searchViewId:false,
            searchViewArch: `
                <search>
                    <field name="name" string="Journal Item"/>
                    <field name="journal_id"/>
                    <field name="account_id"/>
                    <field name="partner_id"/>
                    <field name="move_id"/>
                    <field name="currency_id" groups="base.group_multi_currency"/>
                    <field name="date" string="Date"/>
                    <separator/>
                    <filter name="amount_received" string="Incoming" domain="[('balance','>',0.0)]"/>
                    <filter name="amount_paid" string="Outgoing" domain="[('balance','&lt;',0.0)]"/>
                    <separator name="inject_after"/>
                    <filter name="date" string="Date" date="date"/>
                    <filter string="Customer/Vendor" name="partner_id" domain="[]"/>
                    <filter string="Miscellaneous" domain="[('journal_id.type', '=', 'general')]" name="misc_filter"/>
                </search>
            `,
            searchViewFields: {
                name: {
                    name:"name",
                    string:"Journal Item",
                    type:"char",
                    store: true,
                    sortable: true,
                    searchable: true,
                },
                date: {
                    name: "date",
                    string: "Date",
                    type: "date",
                    store: true,
                    sortable: true,
                    searchable: true,
                },
                journal_id: {
                    name: "journal_id",
                    string: "Journal",
                    type: "many2one",
                    store: true,
                    sortable: true,
                    searchable: true,
                },
                account_id: {
                    name: "account_id",
                    string: "Account",
                    type: "many2one",
                    store: true,
                    sortable: true,
                    searchable: true,
                },
                partner_id: {
                    name: "partner_id",
                    string: "Partner",
                    type: "many2one",
                    store: true,
                    sortable: true,
                    searchable: true,
                    group_by:"partner_id",
                },
                currency_id: {
                    name: "currency_id",
                    string: "Currency",
                    type: "many2one",
                    store: true,
                    sortable: true,
                    searchable: true,
                },
                move_id: {
                    name:"move_id",
                    string:"Journal Entry",
                    type:"many2one",
                    store:true,
                    sortable:true,
                    searchable:true,
                    filter_domain:"['|',('move_id.name','ilike',self),('move_id.ref','ilike',self)]",
                },
            },
            context:{
                list_view_ref:"base_accounting_kit.account_move_line_view_tree",
            }
        }
    }

}
FormListView.template = "base_accounting_kit.FormListView";
FormListView.components = { View };
FormListView.props = {
    ...standardWidgetProps,
    resModel: { type: String },
};
export const formListView = {
    component: FormListView,
    extractProps: ({ attrs }) => ({
        resModel: attrs.resModel,
    }),
};
registry.category("view_widgets").add("form_list_view", formListView);
