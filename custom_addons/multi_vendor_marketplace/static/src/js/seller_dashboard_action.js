odoo.define('multi_vendor_marketplace.seller_dashboard_action', function (require){
"use strict";
var AbstractAction = require('web.AbstractAction');
var ControlPanel = require('web.ControlPanel');
var core = require('web.core');
var QWeb = core.qweb;
var rpc = require('web.rpc');
var ajax = require('web.ajax');
var CustomDashBoard = AbstractAction.extend({
   template: 'SellerDashBoard',
   //Set the seller dashboard
   start: function() {
        var self = this;
        console.log("started")
        ajax.rpc('/seller_dashboard').then(function (res) {
        console.log("ajax done")
        $('#pending').text(res.pending)
        $('#approved').text(res.approved)
        $('#rejected').text(res.rejected)
        if(res.user_type == false){
        $('#check_user_type').hide()
        }
        $("#product_pending").click(function(){
        console.log("product pending")
        self.do_action({
            name:'Product Pending',
            type: 'ir.actions.act_window',
            res_model: 'product.template',
            view_mode: 'kanban',
            views: [[res.product_kanban_id, 'kanban']],
            domain: [['state', '=', 'pending']],
        })
        })
        $("#product_approved").click(function(){
        console.log("product approved")
        self.do_action({
            name:'Product Approved',
            type: 'ir.actions.act_window',
            res_model: 'product.template',
            view_mode: 'kanban',
            views: [[res.product_kanban_id, 'kanban']],
            domain: [['state', '=', 'approved']],
        })
        })
        $("#product_rejected").click(function(){
        console.log("product rejetced")
        self.do_action({
            name:'Product Rejected',
            type: 'ir.actions.act_window',
            res_model: 'product.template',
            view_mode: 'kanban',
            views: [[res.product_kanban_id, 'kanban']],
            domain: [['state', '=', 'rejected']],
        })
        })
        $('#divseller_pending_count').text(res.seller_pending)
        $('#divseller_approved_count').text(res.seller_approved)
        $('#divseller_rejected_count').text(res.seller_rejected)

        $('#inv_req_pending_count').text(res.inventory_pending)
        $('#inv_req_approved_count').text(res.inventory_approved)
        $('#inv_req_rejected_count').text(res.inventory_rejected)

        $('#div_payment_pending_count').text(res.payment_pending)
        $('#div_payment_approved_count').text(res.payment_approved)
        $('#div_payment_rejected_count').text(res.payment_rejected)

        $('#divorder_pending_count').text(res.order_pending)
        $('#divorder_approved_count').text(res.order_approved)
        $('#divorder_shipped_count').text(res.order_shipped)
        $('#divorder_cancel_count').text(res.order_cancel)
        $("#divseller_rejected").click(function(){
        console.log("seller rejetced")
        self.do_action({
            name:'Seller Rejected',
            type: 'ir.actions.act_window',
            res_model: 'res.partner',
            view_mode: 'kanban,form',
            views: [[false, 'kanban'],[false, 'form']],
            domain: [['state', '=', 'Denied']],
        })
        })
        $("#divseller_approved").click(function(){
        console.log("seller approved")
        self.do_action({
            name:'Seller Approved',
            type: 'ir.actions.act_window',
            res_model: 'res.partner',
            view_mode: 'kanban,form',
            views: [[false, 'kanban'],[false, 'form']],
            domain: [['state', '=', 'Approved']],
        })
        })
        $("#divseller_pending").click(function(){
        console.log("Seller pending")
        self.do_action({
            name:'Seller Pending',
            type: 'ir.actions.act_window',
            res_model: 'res.partner',
            view_mode: 'kanban,form',
            views: [[false, 'kanban'],[false, 'form']],
            domain: [['state', '=', 'Pending for Approval']],
        })
        })
        $("#inv_req_pending").click(function(){
        self.do_action({
            name:'Inventory Request Pending',
            type: 'ir.actions.act_window',
            res_model: 'inventory.request',
            view_mode: 'kanban,form',
            views: [[false, 'kanban'],[false, 'form']],
            domain: [['state', '=', 'Requested']],
        })
        })
        $("#inv_req_approved").click(function(){
        self.do_action({
            name:'Inventory Request Approved',
            type: 'ir.actions.act_window',
            res_model: 'inventory.request',
            view_mode: 'kanban,form',
            views: [[false, 'kanban'],[false, 'form']],
            domain: [['state', '=', 'Approved']],
        })
        })
        $("#inv_req_rejected").click(function(){
        self.do_action({
            name:'Inventory Request Rejected',
            type: 'ir.actions.act_window',
            res_model: 'inventory.request',
            view_mode: 'kanban,form',
            views: [[false, 'kanban'],[false, 'form']],
            domain: [['state', '=', 'Rejected']],
        })
        })
        $("#div_payment_pending").click(function(){
        self.do_action({
            name:'Payment Request Pending',
            type: 'ir.actions.act_window',
            res_model: 'seller.payment',
            view_mode: 'kanban,form',
            views: [[false, 'kanban'],[false, 'form']],
            domain: [['state', '=', 'Requested']],
        })
        })
        $("#div_payment_approved").click(function(){
        self.do_action({
            name:'Payment Request Approved',
            type: 'ir.actions.act_window',
            res_model: 'seller.payment',
            view_mode: 'kanban,form',
            views: [[false, 'kanban'],[false, 'form']],
            domain: [['state', '=', 'Validated']],
        })
        })
        $("#div_payment_rejected").click(function(){
        self.do_action({
            name:'Payment Request Rejected',
            type: 'ir.actions.act_window',
            res_model: 'seller.payment',
            view_mode: 'kanban,form',
            views: [[false, 'kanban'],[false, 'form']],
            domain: [['state', '=', 'Rejected']],
        })
        })
        $("#divorder_pending").click(function(){
        self.do_action({
            name:'Sale Order Pending',
            type: 'ir.actions.act_window',
            res_model: 'sale.order.line',
            view_mode: 'kanban,form',
            views: [[res.sale_order_kanban_id, 'kanban'],[res.sale_order_form_id, 'form']],
            domain: [['state', '=', 'pending']],
        })
        })
        $("#divorder_approved").click(function(){
        self.do_action({
            name:'Sale Order Approved',
            type: 'ir.actions.act_window',
            res_model: 'sale.order.line',
            view_mode: 'kanban,form',
            views: [[res.sale_order_kanban_id, 'kanban'],[res.sale_order_form_id, 'form']],
            domain: [['state', '=', 'approved']],
        })
        })
        $("#divorder_shipped").click(function(){
        self.do_action({
            name:'Sale Order Shipped',
            type: 'ir.actions.act_window',
            res_model: 'sale.order.line',
            view_mode: 'kanban,form',
            views: [[res.sale_order_kanban_id, 'kanban'],[res.sale_order_form_id, 'form']],
            domain: [['state', '=', 'shipped']],
        })
        })
        $("#divorder_cancel").click(function(){
        self.do_action({
            name:'Sale Order cancelled',
            type: 'ir.actions.act_window',
            res_model: 'sale.order.line',
            view_mode: 'kanban,form',
            views: [[res.sale_order_kanban_id, 'kanban'],[res.sale_order_form_id, 'form']],
            domain: [['state', '=', 'cancel']],
        })
        })
        })
    },
})
core.action_registry.add('seller_dashboard_tag', CustomDashBoard);
return CustomDashBoard
})
