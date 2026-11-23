/** @odoo-module **/

const PRODUCTION_DECORATORS = {
    draft: "muted",
    confirmed: "info",
    progress: "warning",
    done: "success",
    to_close: "success",
    cancel: "danger",
};

const PURCHASE_DECORATORS = {
    draft: "info",
    sent: "info",
    ['to approve']: "info",
    purchase: "info",
    done: "info",
    cancel: "muted",
};

const PICKING_DECORATORS = {
    draft: "muted",
    waiting: "warning",
    confirmed: "warning",
    assigned: "info",
    done: "success",
    cancel: "danger",
};

const OPERATION_DECORATORS = {
    pending: "info",
    waiting: "info",
    ready: "info",
    progress: "warning",
    done: "success",
    cancel: "muted",
};

const PRODUCT_DECORATORS = {
    to_order: "danger",
};

export function getStateDecorator(model, state) {
    let decorators = null;
    switch (model) {
        case "mrp.production":
            decorators = PRODUCTION_DECORATORS;
            break;
        case "mrp.workorder":
            decorators = OPERATION_DECORATORS;
            break;
        case "stock.picking":
            decorators = PICKING_DECORATORS;
            break;
        case "purchase.order":
            decorators = PURCHASE_DECORATORS;
            break;
        case "product.product":
            decorators = PRODUCT_DECORATORS;
            break;
    }
    return decorators ? `text-bg-${decorators[state]}` : "";
}
