/** @odoo-module */

import { listView } from "@web/views/list/list_view";

const props = listView.props;
listView.props = function (genericProps, view) {
    const result = props(genericProps, view);
    return {
        ...result,
        allowSelectors: false,
    };
};
