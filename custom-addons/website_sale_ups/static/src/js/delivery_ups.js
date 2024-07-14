/** @odoo-module **/

    import { jsonrpc } from "@web/core/network/rpc_service";

    $(document).ready(function () {

        $('#service_type select[name="ups_service_type"]').on('change', function () {
            var apply_button = $('.o_apply_ups_bill_my_account');
            var sale_id = $('#service_type input[name="sale_order_id"]').val();
            apply_button.prop("disabled", true);

            jsonrpc('/shop/ups_check_service_type', {'sale_id': sale_id}).then(function (data) {
                var ups_service_error = $('#ups_service_error');
                if(data.error){
                    ups_service_error.html('<strong>' +data.error+ '</strong>').removeClass('d-none');
                }
                else {
                    ups_service_error.addClass('d-none');
                    apply_button.prop("disabled", false);
                }
            });
        });
        $('#delivery_carrier .o_delivery_carrier_select a').on('click', function (ev) {
          if ($(ev.currentTarget).attr('href') && $(ev.currentTarget).attr('href') != "#"){
              ev.stopPropagation();
          }
        });
    });
