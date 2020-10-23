odoo.define('l10n_de_pos_cert.pos', function(require) {
    "use strict";

    const models = require('point_of_sale.models');
    const { uuidv4 } = require('l10n_de_pos_cert.utils');

    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize() {
            _super_order.initialize.apply(this,arguments);
            this.uuid = uuidv4();
            this.txLastRevision = null;
            this.transactionStarted = false;    // Used to know when we need to create the fiskaly transaction
            this.tseInformation = {
                'number': { 'name': 'TSE-Transaktion', 'value': null },
                'timeStart': { 'name': 'TSE-Start', 'value': null },
                'timeEnd': { 'name': 'TSE-Stop', 'value': null },
                'certificateSerial': { 'name': 'TSE-Seriennummer', 'value': null },
                'timestampFormat': { 'name': 'TSE-Zeitformat', 'value': null },
                'signatureValue': { 'name': 'TSE-Signatur', 'value': null },
                'signatureAlgorithm': { 'name': 'TSE-Hashalgorithmus', 'value': null },
                'signaturePublickKey': { 'name': 'TSE-PublicKey', 'value': null },
                'clientSerialnumber': { 'name': 'ClientID / KassenID', 'value': null },
                'erstBestellung': { 'name': 'TSE-Erstbestellung', 'value': null } // ???? Todo TBD
            };
            this.save_to_db();
        },
        getUuid() {
            return this.uuid;
        },
//      only useful for restaurant
        startTransaction() {
            this.transactionStarted  = true;
        },
        isTransactionStarted() {
            return this.transactionStarted;
        },
        setLastRevision(revision) {
            this.txLastRevision = revision;
        },
        getLastRevision() {
            return this.txLastRevision;
        },
        setTseInformation(key, value) {
            this.tseInformation[key].value = value;
        },
        export_for_printing() {
            const receipt = _super_order.export_for_printing.apply(this,arguments);
            receipt['tse'] = {};
            $.extend(true, receipt['tse'], this.tseInformation);
            return receipt;
        }
    });
});
