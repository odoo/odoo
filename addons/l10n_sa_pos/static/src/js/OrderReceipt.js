odoo.define('l10n_sa_pos.pos', function (require) {
"use strict";

const { Gui } = require('point_of_sale.Gui');
var models = require('point_of_sale.models');
var rpc = require('web.rpc');
var session = require('web.session');
var core = require('web.core');
var utils = require('web.utils');

var _t = core._t;
var round_di = utils.round_decimals;


var _super_order = models.Order.prototype;
models.Order = models.Order.extend({
    export_for_printing: function() {
      var result = _super_order.export_for_printing.apply(this,arguments);
      if (this.pos.company.country.code === 'SA') {
          const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter()
          let qr_values = this.compute_sa_qr_code(result.company.name, result.company.vat, result.date.isostring, result.total_with_tax, result.total_tax);
          let qr_code_svg = new XMLSerializer().serializeToString(codeWriter.write(qr_values, 150, 150));
          result.qr_code = "data:image/svg+xml;base64,"+ window.btoa(qr_code_svg);
      }
      return result;
    },
    compute_sa_qr_code(name, vat, date_isostring, amount_total, amount_tax) {
        /* Generate the qr code for Saudi e-invoicing. Specs are available at the following link at page 23
        https://zatca.gov.sa/ar/E-Invoicing/SystemsDevelopers/Documents/20210528_ZATCA_Electronic_Invoice_Security_Features_Implementation_Standards_vShared.pdf
        */
        const seller_name_enc = this._compute_qr_code_field(1, name);
        const company_vat_enc = this._compute_qr_code_field(2, vat);
        const timestamp_enc = this._compute_qr_code_field(3, date_isostring);
        const invoice_total_enc = this._compute_qr_code_field(4, amount_total.toString());
        const total_vat_enc = this._compute_qr_code_field(5, amount_tax.toString());

        const str_to_encode = seller_name_enc.concat(company_vat_enc, timestamp_enc, invoice_total_enc, total_vat_enc);

        let binary = '';
        for (let i = 0; i < str_to_encode.length; i++) {
            binary += String.fromCharCode(str_to_encode[i]);
        }
        return btoa(binary);
    },

    _compute_qr_code_field(tag, field) {
        const textEncoder = new TextEncoder();
        const name_byte_array = Array.from(textEncoder.encode(field));
        const name_tag_encoding = [tag];
        const name_length_encoding = [name_byte_array.length];
        return name_tag_encoding.concat(name_length_encoding, name_byte_array);
    },

});

});
