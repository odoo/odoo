/* global posmodel */
export function patchAndMockOnlinePayment() {
    return [
        {
            content: "Mock online payment by patching the method used to confirm it",
            trigger: "body",
            run: function () {
                posmodel.update_online_payments_data_with_server = async function (order, amount) {
                    const opData = {
                        id: order.id,
                        is_paid: true,
                        paid_order: [
                            {
                                id: order.id,
                                name: order.name,
                                account_move: {
                                    id: 500,
                                    name: "INV/2025/001",
                                },
                            },
                        ],
                    };
                    return posmodel.process_online_payments_data_from_server(order, opData);
                };
            },
        },
    ];
}
