import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { patch } from "@web/core/utils/patch";

patch(Orderline, {
    props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                so_reference: { type: String, optional: true },
                details: {
                    type: Array,
                    optional: true,
                    element: {
                        type: Object,
                        shape: {
                            product_uom_qty: Number,
                            product_name: String,
                            total: String,
                        },
                    },
                },
            },
        },
    },
});
