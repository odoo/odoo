import { models } from "@web/../tests/web_test_helpers";

export class PosConfig extends models.ServerModel {
    _name = "pos.config";

    notify_synchronisation(session_id, login_number, records = {}) {
        return true;
    }

    _load_pos_data_fields() {
        return [];
    }

    read_config_open_orders(configId) {
        // We can read everything since its only related to the current test.
        const orderIds = this.env["pos.order"].search_read([], ["id"]).map((order) => order.id);
        return {
            deleted_record_ids: {},
            dynamic_records: {
                ...this.env["pos.order"].read_pos_data(orderIds, [], configId),
            },
        };
    }

    _load_pos_data_read(data) {
        data[0]["_partner_commercial_fields"] = [];
        data[0]["_server_version"] = "18.3+e";
        data[0]["_base_url"] = "http://localhost:4444";
        data[0]["_data_server_date"] = "2025-07-03 12:40:15";
        data[0]["_has_cash_move_perm"] = true;
        data[0]["_has_available_products"] = true;
        data[0]["_pos_special_products_ids"] = [];
        return data;
    }

    _records = [
        {
            id: 1,
            display_name: "Hoot",
            access_token: "test_access_token",
            name: "Hoot",
            printer_ids: [],
            is_order_printer: false,
            is_installed_account_accountant: true,
            picking_type_id: 9,
            journal_id: 1,
            invoice_journal_id: 1,
            currency_id: 1,
            iface_cashdrawer: false,
            iface_electronic_scale: false,
            iface_print_via_proxy: false,
            iface_scan_via_proxy: false,
            iface_big_scrollbars: false,
            iface_print_auto: false,
            iface_print_skip_screen: true,
            iface_tax_included: "total",
            iface_available_categ_ids: [],
            customer_display_bg_img: false,
            customer_display_bg_img_name: false,
            restrict_price_control: false,
            is_margins_costs_accessible_to_every_user: false,
            cash_control: true,
            set_maximum_difference: false,
            receipt_header: false,
            receipt_footer: false,
            basic_receipt: false,
            proxy_ip: false,
            active: true,
            uuid: "6f9034bb-faf8-4875-b216-dafb78982918",
            sequence_id: false,
            sequence_line_id: false,
            session_ids: [1],
            current_session_id: 1,
            current_session_state: "opening_control",
            number_of_rescue_session: 0,
            last_session_closing_cash: 0.0,
            last_session_closing_date: false,
            pos_session_username: "Administrator",
            pos_session_state: "opening_control",
            pos_session_duration: "0",
            pricelist_id: false,
            available_pricelist_ids: [1],
            company_id: 250,
            group_pos_manager_id: false,
            group_pos_user_id: false,
            iface_tipproduct: false,
            tip_product_id: 1,
            fiscal_position_ids: [],
            default_fiscal_position_id: false,
            default_bill_ids: [],
            use_pricelist: true,
            use_presets: true,
            default_preset_id: 1,
            available_preset_ids: [1, 2],
            tax_regime_selection: false,
            limit_categories: false,
            module_pos_restaurant: false,
            module_pos_avatax: false,
            module_pos_discount: false,
            module_pos_appointment: false,
            module_pos_iot: false,
            is_header_or_footer: false,
            module_pos_hr: false,
            amount_authorized_diff: 0.0,
            payment_method_ids: [2, 1],
            company_has_template: true,
            current_user_id: 2,
            other_devices: false,
            rounding_method: false,
            cash_rounding: false,
            only_round_cash_method: false,
            has_active_session: true,
            manual_discount: true,
            ship_later: false,
            warehouse_id: false,
            route_id: false,
            picking_policy: "direct",
            auto_validate_terminal_payment: true,
            trusted_config_ids: [],
            show_product_images: true,
            show_category_images: true,
            note_ids: [],
            module_pos_sms: false,
            is_closing_entry_by_product: false,
            order_edit_tracking: false,
            last_data_change: "2025-07-03 14:35:55",
            fallback_nomenclature_id: false,
            create_date: "2025-07-03 12:40:00",
            write_date: "2025-07-03 14:35:55",
            epson_printer_ip: false,
        },
    ];
}
