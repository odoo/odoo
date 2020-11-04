odoo.define('l10n_de_pos_cert.errors', function(require) {

    class TaxError extends Error {
        constructor(product) {
            super(`The tax for the product '${product.display_name}' with id ${product.id} is not allowed.`)
        }
    }

    return { TaxError };
});