odoo.define('mk_fiscal_printer.Printer', function (require) {
    "use strict";
    var core = require('web.core');

    return core.Class.extend({
        init(ip, fp) {
            this.fp = fp

            this.paymentLines = null;
            this.products = [];
            this.subtotal = 0;
            this.total_discount = 0;
            this.total_paid = 0;
            this.total_rounded = 0;
            this.total_tax = 0;
            this.total_with_tax = 0;
            this.total_without_tax = 0;
            this.VATS = {
                18: 'А', 10: 'В', 5: 'Б', 0: 'Г',
            }
            this.paymentMethod = {
                'Cash': 0, 'Bank': 1, 'Credit Card': 1,
            }
            try {
                var configIp = ip.split(':');
                this.fp.ServerSetSettings(configIp[0], configIp[1]);
                this.fp.ServerFindDevice();
            } catch (ex) {
                console.log(ex);
            }
        },

        createOrder(order) {
            this.paymentLines = order.paymentlines;
            this.products = order.orderlines;
            this.subtotal = order.subtotal;
            this.total_discount = order.total_discount;
            this.total_paid = order.total_paid;
            this.total_rounded = order.total_rounded;
            this.total_tax = order.total_tax;
            this.total_with_tax = order.total_with_tax;
            this.total_without_tax = order.total_without_tax;

            this.openReceiptOrStorno();
            this.prepareProducts();
            this.preparePaymentMethod();
            this.CloseReceipt();
        },


        /**
         *  - '0' - Cash
         *  - '1' - Card
         *  - '2' - Voucher
         *  - '3' - Credit
         *  - '4' - Currency
         */
        preparePaymentMethod() {
            this.paymentLines.map(payment => {
                this.Payment(this.paymentMethod[payment.name], Math.abs(payment.amount));
            })
        },

        prepareProducts() {
            this.products.map(async product => {
                this.SellPLUwithSpecifiedVAT(product.product_name, this.prepareVAT(Math.abs(product.price_without_tax), Math.abs(product.tax)), Math.abs(product.taxed_lst_unit_price), 1, Math.abs(product.quantity), '', Math.abs(product.discount) ? `-${Math.abs(product.discount)}` : '')
            })
        }, prepareVAT(price, tax) {
            const percentage = parseFloat(tax) / parseFloat(price) * 100;
            let vat = this.VATS[percentage];
            return vat ?? 'А';
        },

        /**
         * OperNum - Symbol from 1 to 20 corresponding to operator's number
         * OperPass - 4 symbols for operator's password
         * OptionReceiptType - 1 symbol with value:
         *  - '1' - Sale
         *  - '0' - Storno
         * OptionPrintType - 1 symbol with value
         *  - '0' - Step by step printing
         *  - '2' - Postponed printing
         */
        openReceiptOrStorno(OptionReceiptType = 1, OptionPrintType = 2) {
            this.fp.do('OpenReceiptOrStorno', 'OperNum', 2, 'OperPass', '1234', 'OptionReceiptType', OptionReceiptType, 'OptionPrintType', OptionPrintType);

        }, /**
         * NamePLU - 36 symbols for article's name
         * OptionVATClass - 1 character for VAT class:
         *  - 'А' - VAT Class 0
         *  - 'Б' - VAT Class 1
         *  - 'В' - VAT Class 2
         *  - 'Г' - VAT Class 3
         * Price - Up to 10 symbols for article's price.
         * OptionGoodsType - 1 symbol with value:
         *  - '1' - macedonian goods
         *  - '0' - importation
         * Quantity - Up to 10 symbols for quantity
         * DiscAddP - Up to 7 symbols for percentage of discount/addition.
         * Use minus sign '-' for discount
         * DiscAddV - Up to 8 symbols for value of discount/addition.
         * Use minus sign '-' for discount
         */
        SellPLUwithSpecifiedVAT(NamePLU = '', OptionVATClass = '', Price = '', OptionGoodsType = 0, Quantity = 1, DiscAddP = '', DiscAddV = '') {
            this.fp.do('SellPLUwithSpecifiedVAT', 'NamePLU', NamePLU, 'OptionVATClass', OptionVATClass, 'Price', Price, 'OptionGoodsType', OptionGoodsType, 'Quantity', Quantity, 'DiscAddP', DiscAddP, 'DiscAddV', DiscAddV);
        }, ClearDisplay() {
            this.fp.do('ClearDisplay')
        }, /**
         * OptionPaymentType - 1 symbol with values
         *  - '0' - Cash
         *  - '1' - Card
         *  - '2' - Voucher
         *  - '3' - Credit
         *  - '4' - Currency
         */
        PayExactSum() {
            this.fp.do('PayExactSum', 'OptionPaymentType', 0)
        }, /**
         * OptionPaymentType - 1 symbol with values
         *  - '0' - Cash
         *  - '1' - Card
         *  - '2' - Voucher
         *  - '3' - Credit
         *  - '4' - Currency
         * OptionChange - Default value is 0, 1 symbol with value:
         *  - '0 - With Change
         *  - '1' - Without Change
         * Amount - Up to 10 characters for received amount
         * OptionChangeType - 1 symbols with value:
         *  - '0' - Change In Cash
         *  - '1' - Same As The payment
         *  - '2' - Change In Currency
         */
        Payment(OptionPaymentType = 0, Amount = 0, OptionChange = 0, OptionChangeType = 0) {
            this.fp.do('Payment', 'OptionPaymentType', OptionPaymentType, 'OptionChange', OptionChange, 'Amount', Amount, 'OptionChangeType', OptionChangeType)
        }, CashPayCloseReceipt() {
            this.fp.do('CashPayCloseReceipt')
        }, CloseReceipt() {
            this.fp.do('CloseReceipt')
        }, CutPaper() {
            this.fp.do('CutPaper')
        }, PaperFeed() {
            this.fp.do('PaperFeed')
        }, printDiagnostics() {
            this.fp.do('PrintDiagnostics')
        }, PrintDailyReport() {
            this.fp.do('PrintDailyReport', 'OptionZeroing', 'Z');
        }
    });
})