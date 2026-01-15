/* © 2026 Jbnegoc SPA - Todos los derechos reservados
 * Desarrollado por: Jbnegoc SPA
 * Módulo: Auditoría de Eliminaciones en Punto de Venta
 */

odoo.define('pos_audit_deleted_items.pos_audit', function (require) {
"use strict";

var models = require('point_of_sale.models');
var screens = require('point_of_sale.screens');
var gui = require('point_of_sale.gui');
var PopupWidget = require('point_of_sale.popups');
var rpc = require('web.rpc');
var core = require('web.core');
var _t = core._t;

// ========================================================================
// Extender PosModel para cargar justificaciones y configuración de usuario
// ========================================================================

var _super_posmodel = models.PosModel.prototype;
models.PosModel = models.PosModel.extend({
    initialize: function(session, attributes) {
        var self = this;

        // Agregar modelos a cargar
        models.load_models({
            model: 'pos.deletion.reason',
            fields: ['name', 'sequence', 'active'],
            domain: [['active', '=', true]],
            order: [['sequence', 'asc'], ['name', 'asc']],
            loaded: function(self, deletion_reasons) {
                self.deletion_reasons = deletion_reasons;
                console.log('POS Audit: Loaded ' + deletion_reasons.length + ' deletion reasons');
            },
        });

        // Cargar campos adicionales del usuario
        models.load_fields('res.users', ['pos_audit_enabled', 'pos_audit_can_delete']);

        return _super_posmodel.initialize.call(this, session, attributes);
    },

    /**
     * Verifica si la auditoría está habilitada para el usuario actual
     */
    is_audit_enabled: function() {
        var user = this.get_cashier() || this.user;
        return user && user.pos_audit_enabled;
    },

    /**
     * Obtiene las justificaciones de eliminación disponibles
     */
    get_deletion_reasons: function() {
        return this.deletion_reasons || [];
    },
});

// ========================================================================
// Extender Order para almacenar items eliminados temporalmente
// ========================================================================

var _super_order = models.Order.prototype;
models.Order = models.Order.extend({
    initialize: function(attributes, options) {
        _super_order.initialize.call(this, attributes, options);

        // Array temporal para almacenar items eliminados antes de sincronizar
        this.audit_deleted_items = [];
    },

    /**
     * Agrega un item eliminado al registro temporal de auditoría
     */
    add_deleted_item_audit: function(product, qty_deleted, price_unit, reason) {
        if (!this.pos.is_audit_enabled()) {
            return;
        }

        var user = this.pos.get_cashier() || this.pos.user;
        var audit_item = {
            product_id: product.id,
            product_name: product.display_name,
            qty_deleted: Math.abs(qty_deleted),
            price_unit: price_unit,
            user_id: user.id,
            deletion_reason: reason,
            deletion_datetime: new Date().toISOString(),
        };

        // Agregar mesa si existe (restaurante)
        if (this.table) {
            audit_item.table_id = this.table.id;
        }

        this.audit_deleted_items.push(audit_item);
        console.log('POS Audit: Added deletion record', audit_item);
    },

    /**
     * Sobrescribe export_as_JSON para incluir items eliminados
     */
    export_as_JSON: function() {
        var json = _super_order.export_as_JSON.call(this);

        // Agregar items eliminados al JSON si existen
        if (this.audit_deleted_items && this.audit_deleted_items.length > 0) {
            json.audit_deleted_items = this.audit_deleted_items;
        }

        return json;
    },

    /**
     * Sobrescribe init_from_JSON para restaurar items eliminados
     */
    init_from_JSON: function(json) {
        _super_order.init_from_JSON.call(this, json);
        this.audit_deleted_items = json.audit_deleted_items || [];
    },
});

// ========================================================================
// Extender Orderline para detectar eliminaciones
// ========================================================================

var _super_orderline = models.Orderline.prototype;
models.Orderline = models.Orderline.extend({
    /**
     * Sobrescribe set_quantity para interceptar eliminaciones
     */
    set_quantity: function(quantity) {
        var self = this;
        var pos = this.pos;
        var order = this.order;

        // Si no está habilitada la auditoría, funciona normal
        if (!pos.is_audit_enabled()) {
            return _super_orderline.set_quantity.call(this, quantity);
        }

        // Guardar cantidad actual antes del cambio
        var old_quantity = this.quantity || 0;

        // Detectar si es una eliminación (disminución de cantidad o 'remove')
        var is_deletion = false;
        var qty_deleted = 0;

        if (quantity === 'remove') {
            // Eliminación completa de la línea
            is_deletion = true;
            qty_deleted = old_quantity;
        } else {
            var new_quantity = parseFloat(quantity) || 0;
            if (new_quantity < old_quantity && old_quantity > 0) {
                // Disminución de cantidad
                is_deletion = true;
                qty_deleted = old_quantity - new_quantity;
            }
        }

        // Si es una eliminación, solicitar justificación
        if (is_deletion && qty_deleted > 0) {
            // Mostrar popup de justificación
            pos.gui.show_popup('deletion-reason-popup', {
                orderline: this,
                quantity: quantity,
                qty_deleted: qty_deleted,
                old_quantity: old_quantity,
                callback: function(reason) {
                    if (reason) {
                        // Registrar la eliminación con la justificación
                        order.add_deleted_item_audit(
                            self.product,
                            qty_deleted,
                            self.get_unit_price(),
                            reason
                        );

                        // Proceder con el cambio de cantidad
                        _super_orderline.set_quantity.call(self, quantity);
                    }
                    // Si no hay reason (usuario canceló), no hacer nada
                }
            });
        } else {
            // No es eliminación, proceder normal (incremento de cantidad o cantidad = 0)
            return _super_orderline.set_quantity.call(this, quantity);
        }
    },
});

// ========================================================================
// Popup personalizado para solicitar justificación de eliminación
// ========================================================================

var DeletionReasonPopup = PopupWidget.extend({
    template: 'DeletionReasonPopup',

    events: _.extend({}, PopupWidget.prototype.events, {
        'click .reason-button': 'click_reason',
        'click .confirm': 'click_confirm',
        'click .cancel': 'click_cancel',
    }),

    init: function(parent, args) {
        this._super(parent, args);
        this.options = {};
    },

    show: function(options) {
        options = options || {};
        this._super(options);

        var self = this;
        this.options = options;
        this.orderline = options.orderline || null;
        this.quantity = options.quantity || 0;
        this.qty_deleted = options.qty_deleted || 0;
        this.old_quantity = options.old_quantity || 0;
        this.callback = options.callback || function() {};

        // Obtener justificaciones predeterminadas
        this.deletion_reasons = this.pos.get_deletion_reasons();

        // Renderizar el popup
        this.renderElement();

        // Focus en el textarea
        this.$('textarea[name="deletion_reason"]').focus();
    },

    /**
     * Obtiene el nombre del producto
     */
    get_product_name: function() {
        return this.orderline ? this.orderline.get_product().display_name : '';
    },

    /**
     * Obtiene la cantidad eliminada formateada
     */
    get_qty_deleted_str: function() {
        return this.qty_deleted ? this.qty_deleted.toFixed(2) : '0';
    },

    /**
     * Maneja el clic en un botón de justificación predeterminada
     */
    click_reason: function(event) {
        var reason = $(event.currentTarget).data('reason');
        var $textarea = this.$('textarea[name="deletion_reason"]');
        var current_text = $textarea.val().trim();

        // Si el textarea está vacío, usar la razón directamente
        // Si tiene texto, agregar la razón al final
        if (current_text) {
            $textarea.val(current_text + '\n' + reason);
        } else {
            $textarea.val(reason);
        }

        // Focus en el textarea
        $textarea.focus();
    },

    /**
     * Maneja el clic en confirmar
     */
    click_confirm: function() {
        var reason = this.$('textarea[name="deletion_reason"]').val().trim();

        if (!reason) {
            this.gui.show_popup('error', {
                'title': _t('Justificación Requerida'),
                'body': _t('Debe ingresar una justificación para eliminar el producto.'),
            });
            return;
        }

        if (reason.length < 5) {
            this.gui.show_popup('error', {
                'title': _t('Justificación muy corta'),
                'body': _t('La justificación debe tener al menos 5 caracteres.'),
            });
            return;
        }

        // Llamar al callback con la justificación
        if (this.callback) {
            this.callback(reason);
        }

        this.gui.close_popup();
    },

    /**
     * Maneja el clic en cancelar
     */
    click_cancel: function() {
        // Llamar al callback sin justificación (null) para cancelar
        if (this.callback) {
            this.callback(null);
        }

        this.gui.close_popup();
    },
});

gui.define_popup({name:'deletion-reason-popup', widget: DeletionReasonPopup});

// ========================================================================
// Extender sincronización de órdenes para guardar auditorías
// ========================================================================

var _super_posmodel_push_order = models.PosModel.prototype.push_order;
models.PosModel.prototype.push_order = function(order, opts) {
    var self = this;
    var pushed = _super_posmodel_push_order.call(this, order, opts);

    // Si la orden tiene items eliminados, enviarlos al backend
    if (order && order.audit_deleted_items && order.audit_deleted_items.length > 0) {
        pushed.then(function(server_ids) {
            if (server_ids && server_ids.length > 0) {
                var order_server_id = server_ids[0].id;

                // Enviar registros de auditoría al backend
                rpc.query({
                    model: 'pos.order',
                    method: 'create_audit_records_from_ui',
                    args: [order_server_id, order.audit_deleted_items],
                }).then(function(result) {
                    console.log('POS Audit: Saved ' + result.length + ' deletion records to backend');
                }).catch(function(error) {
                    console.error('POS Audit: Error saving deletion records', error);
                });
            }
        });
    }

    return pushed;
};

console.log('POS Audit Deleted Items: Module loaded successfully');

return {
    DeletionReasonPopup: DeletionReasonPopup,
};

});
