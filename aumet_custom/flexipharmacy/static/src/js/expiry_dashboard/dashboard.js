odoo.define('flexipharmacy.dashboard', function (require) {
    "use strict";


    var AbstractAction = require('web.AbstractAction');
    // var ControlPanelMixin = require('web.ControlPanelMixin');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var _t = core._t;
    var session = require('web.session');
        
    var ProductExpiryDashboard = AbstractAction.extend({
        title: core._t('Product Expiry Dashboard'),
        template: 'ProductExpiryDashboard',
        events: {
            'click #expired_product': 'open_expire',
            'click #today_expired_product': 'open_today_expire',
            'click .user_data': 'user_master',
        },
        open_today_expire: function(){
            var self = this;
            var expiration_from = moment().format("MM/DD/YYYY 00:00:00");
            var expiration_to = moment().format("MM/DD/YYYY 23:59:59");
            self.do_action({
                   name : _t('Today Expire Product'),
                   views: [[false, 'list'],[false, 'form']],
                   res_model: 'stock.production.lot',
                   type: 'ir.actions.act_window',
                   target: 'new',
                   domain:[['state_check','=','Expired'], ['expiration_date', '<=', expiration_to], ['expiration_date', '>=', expiration_from]],
            });
        },
        init: function (parent, params) {
            this._super.apply(this, arguments);
            var company_id;
        },
        open_expire: function(){
            var self = this;
            var expiration_from = moment().format("MM/DD/YYYY 00:00:00");
            var expiration_to = moment().format("MM/DD/YYYY 23:59:59");
            self.do_action({
                   name : _t('Today Expire Product'),
                   views: [[false, 'list'],[false, 'form']],
                   res_model: 'stock.production.lot',
                   type: 'ir.actions.act_window',
                   target: 'new',
                   domain:[['state_check','=','Expired'], ['expiration_date', '<=', expiration_to], ['expiration_date', '>=', expiration_from]],
            });
        },
        start: function () {
            this._super.apply(this, arguments);
            var breadcrumbs = this.action_manager && this.action_manager.get_breadcrumbs() || [{
                title: this.title,
                action: this
            }];
            // this.update_control_panel({breadcrumbs: breadcrumbs, search_view_hidden: true}, {clear: true});
        },
        user_master : function(e){
             var company = $( e.currentTarget).data('company_id');
             this.company_id = company;
            this.renderElement();
        },
        location_expire: function(result){
            var self = this;
            self.do_action({
                   name : _t('Nearly Expire Product'),
                   views: [[false, 'list'],[false, 'form']],
                   res_model: 'stock.quant',
                   type: 'ir.actions.act_window',
                   target: 'new',
                   domain:[['state_check','=','Near Expired'],['location_id','=',parseInt(result)]],
            });
        },

        categ_div_id : function (result){
            var self = this;
            self.do_action({
                   name : _t('Expire category'),
                   views: [[false, 'list'],[false, 'form']],
                   res_model: 'stock.production.lot',
                   type: 'ir.actions.act_window',
                   target: 'new',
                   domain:[['id','in',result]],
                   flags: {action_buttons: true, headless: true},
            });
        },

        product_div_id : function(result,days){
            var self = this;
            self.do_action({
                   name : _t("Expire In "+days+ " Days"),
                   // view_mode: 'kanban,list,form',
                   views: [[false, 'list'],[false, 'form']],
                   res_model: 'stock.production.lot',
                   type: 'ir.actions.act_window',
                   target: 'new',
                   domain:[['id','in',result]],
                   flags: {action_buttons: true, headless: true},
            });
        },

        open_near_expire: function (result) {
            var self = this;
            self.do_action({
                   name : _t('Today Expire Product'),
                   views: [[false, 'list'],[false, 'form']],
                   res_model: 'stock.production.lot',
                   type: 'ir.actions.act_window',
                   target: 'new',
                   domain:[['id','in',result]],
            });
        },

        renderElement: function () {
            var self = this;
            this._super.apply(this, arguments);
            self.render_header();

            setTimeout(function(){
               var params = {
               model: 'product.product',
               method: 'search_product_expiry',
            }
           rpc.query(params, {async: false})
           .then(function(records){
                 var options = {
                   valueNames: [
                       'location_id',
                       'location_name',
                       'expire_count',
                       ],
                   item: '<tr class="filter-task-by-user location_id location" style="cursor:pointer;width:100%;float:left;"><td style="width:50%;float:left;" class="filter-task-by-user location_id hide-row hidden" data-id="location_id"></td><td style="width:50%;float:left;"class="location_name"></td><td style="width:50%;float:left;" class="expire_count"><span class="label label-warning"></span></td></tr>',

               };
               var values = records['location_wise_expire'];
               var userList = new List('location', options, values);
                var options = {
                   valueNames: [
                       'location_id',
                       'warehouse_name',
                       'expire_count',
                       ],
                   item: '<tr class="filter-task-by-user location_id warehouse" style="cursor:pointer;width:100%;float:left;"><td style="width:50%;float:left;" class="filter-task-by-user location_id hide-row hidden" data-id="location_id"></td><td style="width:50%;float:left;" class="warehouse_name"></td><td style="width:50%;float:left;" class="expire_count"><span class="label label-warning"></span></td></tr>',
               };
               var values = records['warehouse_wise_expire'];
               var userList = new List('warehouse', options, values);
                   $('#expired_product').text(records['expired']);
                   $('#today_expired_product').text(records['today_expired']);

                   $('#near_expired').text(records['near_expired']);
                   var output = document.getElementById('categ_div_id');
                   var category_color = ['ffffb3','ecc6d9','d9ffb3','d9ffb3','ccffff','ffffb3']

                   var links = Object.keys(records['day_wise_expire']).map(function(key) {
                        var html = "<div class='col-md-4 col-sm-6 col-xs-12 ng-scope'>";
                        html += "<div class='content' data-days='"+key+"'data-product-id='"+records['day_wise_expire'][key]['product_id']+"'>"
                        if(records['day_wise_expire'][key]['color']){

                            if(records['day_wise_expire'][key]['text_color']){
                                html += "<div class='info-box'> <span class='info-box-icon product_config' id='product_expiry_data' style='cursor:pointer;background-color:"+records['day_wise_expire'][key]['color']+";color:"+records['day_wise_expire'][key]['text_color']+"'>"+records['day_wise_expire'][key]['product_id'].length + "</span>";
                            }
                            else{
                                html += "<div class='info-box'> <span class='info-box-icon product_config' id='product_expiry_data' style='cursor:pointer;background-color:"+records['day_wise_expire'][key]['color']+"'>"+records['day_wise_expire'][key]['product_id'].length + "</span>";
                            }
                        }else{
                            if(records['day_wise_expire'][key]['text_color']){
                                html += "<div class='info-box'> <span class='info-box-icon product_config' id='product_expiry_data' style='cursor:pointer;background-color:white; color:"+records['day_wise_expire'][key]['text_color']+"'>"+records['day_wise_expire'][key]['product_id'].length + "</span>";
                            }
                            else{
                                html += "<div class='info-box'> <span class='info-box-icon product_config' id='product_expiry_data' style='cursor:pointer;background-color:white;color:black;'>"+records['day_wise_expire'][key]['product_id'].length + "</span>";
                            }

                        }
                        html += "<div class='wrimagecard-topimage_title'> <h4>Expire In "+ key+ " Days</h4>";
                        html += "</div></div></div>"
                        $('.product_expiry_con').append(html)
                   });

                   for(var data=0;data<records['category_near_expire'].length;data++){
                        var html = "<div class='col-md-4 col-sm-6 col-xs-12 ng-scope custome_hide' style='width: 1060px;'>";
                        html += "<div class='content categ-search' data-categ_id='"+records['category_near_expire'][data]['id']+"'><div class='info-box'>";
                        html += "<span class='info-box-icon categ_click' id='expire_in_60_days' style='cursor:pointer;background:#"+category_color[data]+";'>"+records['category_near_expire'][data]['qty']+"</span>";
                        html += "<div class='wrimagecard-topimage_title search_categ_name'>";
                        html += "<h4>"+records['category_near_expire'][data]['categ_name']+"</h4>";
                        html += "</div>";
                        html += "</div>";
                        html += "</div></div>";
                        $("#categ_div_id").append(html);
                   }
                   $(document).ready(function () {
                        $('#near_expired').click(function(){
                            self.open_near_expire(records['near_expire_display'])
                        });
                        $('.product_config').click(function(event){
                            var product_ids = $(event.target).parent().parent().attr('data-product-id');
                            var expiry_day = $(event.target).parent().parent().attr('data-days');
                            var event = JSON.parse("[" + product_ids + "]");
                            self.product_div_id(event, expiry_day)
                        });

                        $('.categ_click').click(function(event){
                            var categ_ids = $(event.target).parent().parent().attr('data-categ_id');
                            var event = JSON.parse("[" + categ_ids + "]");
                            self.categ_div_id(event)
                        });
                        $('#search').on("keyup", function() {
                            var text = $(this).val().toLowerCase();
//                            $('.content').parent('.custome_hide').addClass('hidden')
                            $(".search_categ_name").each( function() {
                                var div_con = $(this).text().toLowerCase();
                                if (div_con.indexOf(text)!=-1) {
                                    $(this).parent().parent().parent().show();
//                                    $(this).closest('.content').parents('.custome_hide').removeClass('hidden')
                                }
                                else {
                                    $(this).parent().parent().parent().hide();

                                }
                            });
                        });
                        $('.location').click(function(e){
                            var titleElement = e.currentTarget;
                            var titleChildren = titleElement.getElementsByTagName("td");
                            self.location_expire(titleChildren[0].innerHTML)
                        })
                        $('.warehouse').click(function(e){
                            var titleElement = e.currentTarget;
                            var titleChildren = titleElement.getElementsByTagName("td");
                            self.location_expire(titleChildren[0].innerHTML)
                        })
                        $(function() {
                            var start = moment().subtract(29, 'days');
                            var end = moment();
                            function cb(start, end) {
                                $('#reportrange span').html(start.format('MMMM D, YYYY') + ' - ' + end.format('MMMM D, YYYY'));
                                rpc.query({
                                    model: 'product.product',
                                    method: 'graph_date',
                                    args: [false,start.format('YYYY-MM-D'),end.format('YYYY-MM-D')],
                                    }, {async: false})
                                    .then(function (res) {
                                        var total_quantity = []
                                        var product_name = []
                                        var color_bar = []
                                        var color_pie = []
                                        for(var data=0;data<res.length;data++){
                                            var html = "<div class='col-xs-3 col-item'>";
                                            html += "<small>"+res[data]['product_name']+"</small>";
                                            html += "<span>"+res[data]['qty']+"</span>";
                                            html += "</div>";
                                            $(".pie-graph").append(html);
                                            total_quantity.push(res[data]['qty']);
                                            product_name.push(res[data]['product_name']);
                                            color_pie.push('#'+Math.floor(100000 + Math.random() * 800000));
                                            color_bar.push('rgba('
                                                        + (Math.floor(Math.random() * 256)) + ','
                                                        + (Math.floor(Math.random() * 256)) + ','
                                                        + (Math.floor(Math.random() * 256)) + ','
                                                        + '0.6'+ ')')
                                        }
                                        function BarGraphPrepare(){
//                                        document.getElementById("aaa").innerHTML = "Nearly Expire Product Quantity Graph";
                                        $("#near_expiry_graph_panel").show();
                                        $('#product_graph_display').remove();
                                        $('#display_pie').removeClass('btn btn-secondary fa fa-pie-chart-o o_graph_button active');
                                        $('#display_pie').addClass('btn btn-secondary fa fa-pie-chart-o o_graph_button inactive');
                                        $('#display_bar').removeClass('btn btn-secondary fa fa-bar-chart-o o_graph_button inactive');
                                        $('#display_bar').addClass('btn btn-secondary fa fa-bar-chart-o o_graph_button active');
                                        $('#BarChart_canvas').append("<canvas id='product_graph_display'></canvas>");
                                             new Chart(document.getElementById("product_graph_display").getContext('2d'), {
                                                type: 'bar',
                                                data: {
                                                      labels: product_name,
                                                      datasets: [
                                                            {
                                                              label: "Product Quantity",
                                                              backgroundColor: color_bar,
                                                              data: total_quantity,
                                                            }
                                                      ]
                                                },
                                                options: {
                                                    responsive: true,
                                                    title: {
                                                        display: true,
                                                        position: "top",
                                                        text: "",
                                                        fontSize: 18,
                                                        fontColor: "#111"
                                                    },
                                                    legend: {
                                                        display: false,
                                                    },
                                                    scales: {
                                                        yAxes: [{
                                                            scaleLabel: {
                                                                display: true,
                                                                fontColor: "black",
                                                                fontSize : 15,
                                                                labelString: "Quantity",
                                                                barThickness: '50px'
                                                            },
                                                            ticks: {
                                                            fontColor: "black",
                                                            beginAtZero:true,
                                                            }
                                                        }],
                                                        xAxes: [{
                                                            barPercentage: 0.3,
                                                            scaleLabel: {
                                                                display: true,
                                                                fontColor: "black",
                                                                fontSize : 12,
                                                                labelString: "Product",
                                                            },
                                                            ticks: {
                                                                autoSkip: false,
                                                                beginAtZero:true,
                                                            }
                                                        }]
                                                    }
                                                },
                                            });
                                            function done(){
                                                alert(chart.toBase64Image());
                                            }
                                        }
                                        if(res.length >= 1){
                                        BarGraphPrepare();
                                        }
                                        else{
                                         $('#product_graph_display').remove();
                                         $('#BarChart_canvas').append("<canvas id='product_graph_display'></canvas>");
                                        }
                                        $('#display_bar').click(function(){
//                                        document.getElementById("aaa").innerHTML = "Nearly Expire Product Quantity Graph";
                                            if(res.length >= 1){
                                                BarGraphPrepare();
                                            }
                                            else {
                                             $('#product_graph_display').remove();
                                             $('#BarChart_canvas').append("<canvas id='product_graph_display'></canvas>");
                                            }
                                        });
                                        $('#display_pie').click(function(){
//                                        document.getElementById("aaa").innerHTML = "Nearly Expire Product Quantity Graph";
                                        $("#near_expiry_graph_panel").show();
                                        var $this = $(this);
                                        $('#display_bar').removeClass('btn btn-secondary fa fa-bar-chart-o o_graph_button active');
                                        $('#display_bar').addClass('btn btn-secondary fa fa-bar-chart-o o_graph_button inactive');
                                        $('#display_pie').removeClass('btn btn-secondary fa fa-pie-chart-o o_graph_button inactive');
                                        $('#display_pie').addClass('btn btn-secondary fa fa-pie-chart-o o_graph_button active');
                                        if (res.length >= 1){
                                        $('#product_graph_display').remove();
                                         $('#BarChart_canvas').append("<canvas id='product_graph_display'></canvas>");
                                        new Chart(document.getElementById("product_graph_display"), {
                                            type: 'pie',
                                            data: {
                                                  labels: product_name,
                                                  datasets: [
                                                        {
                                                          label: "Product Quantity",
                                                          backgroundColor: color_pie,
                                                          data: total_quantity
                                                        }
                                                  ]
                                            },
                                            options: {
                                              legend: {display: true },
                                              title: {
                                                display: true,
                                                text: ''
                                              }
                                            },
                                        });
                                        }
                                        else{
                                         $('#product_graph_display').remove();
                                         $('#BarChart_canvas').append("<canvas id='product_graph_display'></canvas>");
                                        }
                                        });
                                    })
                            }
                            $('#reportrange').daterangepicker({
                                startDate: start,
                                endDate: end,
                                ranges: {
                                   'Today': [moment(), moment()],
                                   'Yesterday': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
                                   'Last 7 Days': [moment().subtract(6, 'days'), moment()],
                                   'Last 30 Days': [moment().subtract(29, 'days'), moment()],
                                   'This Month': [moment().startOf('month'), moment().endOf('month')],
                                   'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
                                }
                            }, cb);
                            cb(start, end);
                        });

                        var lineHeight = 100;
                        $('.readmore-category').readmore({
                          speed: 1000,
                          collapsedHeight: 140,
                          heightMargin: lineHeight * 1
                        });
                        $('.readmore-product').readmore({
                          speed: 1000,
                          collapsedHeight: lineHeight * 1,
                          heightMargin: lineHeight * 1
                        });
                        var warehouserows = document.getElementById("location-table").getElementsByTagName("tbody")[0].getElementsByTagName("tr").length;
                        if (warehouserows >=10){
                            $('#warehouse-table').readmore({
                          speed: 1000,
                          collapsedHeight: 400,
                          heightMargin: 65 * 1
                        });
                        }
                        var locationrows = document.getElementById("location-table").getElementsByTagName("tbody")[0].getElementsByTagName("tr").length;
                        if (locationrows >=10){
                            $('#location-table').readmore({
                          speed: 1000,
                          collapsedHeight: 400,
                          heightMargin: 65 * 1
                        });
                        }

                        $("#panel-fullscreen").click(function (e) {
                            e.preventDefault();
                            var $this = $(this);
                            if ($this.children('i').hasClass('fa fa-expand'))
                            {
                                $this.children('i').removeClass('fa fa-expand');
                                $this.children('i').addClass('fa fa-compress');
                            }
                            else if ($this.children('i').hasClass('fa fa-compress'))
                            {
                                $this.children('i').removeClass('fa fa-compress');
                                $this.children('i').addClass('fa fa-expand');
                            }
                            $(this).closest('#near_expiry_panel').toggleClass('panel-fullscreen');
                        });
                        $("#panel-toggle").click(function (e) {
                            e.preventDefault();
                            $(".panel-body-product").slideToggle();
                            var $this = $(this);

                            if ($this.children('i').hasClass('fa fa-chevron-up'))
                            {

                                $this.children('i').removeClass('fa fa-chevron-up');
                                $this.children('i').addClass('fa fa-chevron-down');
                            }
                            else if ($this.children('i').hasClass('fa fa-chevron-down'))
                            {
                                var a = document.getElementById("panel-fullscreen").disabled = true;
                                $('#panel-fullscreen').disabled = true;
                                $this.children('i').removeClass('fa fa-chevron-down');
                                $this.children('i').addClass('fa fa-chevron-up');
                            }
                        });
                         $("#panel-close").click(function (e) {
                            e.preventDefault();
                            $("#near_expiry_panel").remove();
                        });
                        $("#panel-close_category").click(function (e) {
                            e.preventDefault();
                            $("#near_expiry_category_panel").remove();
                        });
                        $("#panel-toggle_category").click(function (e) {
                            e.preventDefault();
                            $(".panel-body-category").slideToggle();
                            var $this = $(this);
                            if ($this.children('i').hasClass('fa fa-chevron-up'))
                            {
                                $this.children('i').removeClass('fa fa-chevron-up');
                                $this.children('i').addClass('fa fa-chevron-down');
                            }
                            else if ($this.children('i').hasClass('fa fa-chevron-down'))
                            {
                                $this.children('i').removeClass('fa fa-chevron-down');
                                $this.children('i').addClass('fa fa-chevron-up');
                            }
                        });
                        $("#panel-fullscreen_category").click(function (e) {
                            e.preventDefault();
                            var $this = $(this);
                            if ($this.children('i').hasClass('fa fa-expand'))
                            {
                                $this.children('i').removeClass('fa fa-expand');
                                $this.children('i').addClass('fa fa-compress');
                            }
                            else if ($this.children('i').hasClass('fa fa-compress'))
                            {
                                $this.children('i').removeClass('fa fa-compress');
                                $this.children('i').addClass('fa fa-expand');
                            }
                            $(this).closest('#near_expiry_category_panel').toggleClass('panel-fullscreen');
                        });
                        $("#panel-close-graph").click(function (e) {
                            e.preventDefault();
                            $("#near_expiry_graph_panel").hide();
                        });
                        $("#panel-toggle-graph").click(function (e) {
                            e.preventDefault();
                            $(".panel-body-graph").slideToggle();
                            var $this = $(this);
                            if ($this.children('i').hasClass('fa fa-chevron-up'))
                            {
                                $this.children('i').removeClass('fa fa-chevron-up');
                                $this.children('i').addClass('fa fa-chevron-down');
                            }
                            else if ($this.children('i').hasClass('fa fa-chevron-down'))
                            {
                                $this.children('i').removeClass('fa fa-chevron-down');
                                $this.children('i').addClass('fa fa-chevron-up');
                            }
                        });
                        $("#panel-fullscreen-graph").click(function (e) {
                            e.preventDefault();
                            var $this = $(this);
                            if ($this.children('i').hasClass('fa fa-expand'))
                            {
                                $this.children('i').removeClass('fa fa-expand');
                                $this.children('i').addClass('fa fa-compress');
                            }
                            else if ($this.children('i').hasClass('fa fa-compress'))
                            {
                                $this.children('i').removeClass('gfa fa-compress');
                                $this.children('i').addClass('fa fa-expand');
                            }
                            $(this).closest('#near_expiry_graph_panel').toggleClass('panel-fullscreen');
                        });
                        $("#panel-close_location").click(function (e) {
                            e.preventDefault();
                            $("#near_expiry_location_panel").remove();
                        });
                        $("#panel-toggle_location").click(function (e) {
                            e.preventDefault();
                            $(".panel-body-location").slideToggle();
                            var $this = $(this);
                            if ($this.children('i').hasClass('fa fa-chevron-up'))
                            {
                                $this.children('i').removeClass('fa fa-chevron-up');
                                $this.children('i').addClass('fa fa-chevron-down');
                            }
                            else if ($this.children('i').hasClass('fa fa-chevron-down'))
                            {
                                $this.children('i').removeClass('fa fa-chevron-down');
                                $this.children('i').addClass('fa fa-chevron-up');
                            }
                        });
                        $("#panel-fullscreen_location").click(function (e) {
                            e.preventDefault();
                            var $this = $(this);
                            if ($this.children('i').hasClass('fa fa-expand'))
                            {
                                $this.children('i').removeClass('fa fa-expand');
                                $this.children('i').addClass('fa fa-compress');
                            }
                            else if ($this.children('i').hasClass('fa fa-compress'))
                            {
                                $this.children('i').removeClass('fa fa-compress');
                                $this.children('i').addClass('fa fa-expand');
                            }
                            $(this).closest('#near_expiry_location_panel').toggleClass('panel-fullscreen');
                        });
                        $("#panel-close_warehouse").click(function (e) {
                            e.preventDefault();
                            $("#near_expiry_warehouse_panel").remove();
                        });
                        $("#panel-toggle_warehouse").click(function (e) {
                            e.preventDefault();
                            $(".panel-body-warehouse").slideToggle();
                            var $this = $(this);
                            if ($this.children('i').hasClass('fa fa-chevron-up'))
                            {
                                $this.children('i').removeClass('fa fa-chevron-up');
                                $this.children('i').addClass('fa fa-chevron-down');
                            }
                            else if ($this.children('i').hasClass('fa fa-chevron-down'))
                            {
                                $this.children('i').removeClass('fa fa-chevron-down');
                                $this.children('i').addClass('fa fa-chevron-up');
                            }
                        });
                        $("#panel-fullscreen_warehouse").click(function (e) {
                            e.preventDefault();
                            var $this = $(this);
                            if ($this.children('i').hasClass('fa fa-expand'))
                            {
                                $this.children('i').removeClass('fa fa-expand');
                                $this.children('i').addClass('fa fa-compress');
                            }
                            else if ($this.children('i').hasClass('fa fa-compress'))
                            {
                                $this.children('i').removeClass('fa fa-compress');
                                $this.children('i').addClass('fa fa-expand');
                            }
                            $(this).closest('#near_expiry_warehouse_panel').toggleClass('panel-fullscreen');
                        });
                        $(".sort").click(function (e) {
                            e.preventDefault();
                            var $this = $(this);
                            if ($this.children('i').hasClass('fa fa-sort-asc'))
                            {
                                $this.children('i').removeClass('fa fa-sort-asc');
                                $this.children('i').addClass('fa fa-sort-desc');
                            }
                            else if ($this.children('i').hasClass('fa fa-sort-desc'))
                            {
                                $this.children('i').removeClass('fa fa-sort-desc');
                                $this.children('i').addClass('fa fa-sort-asc');
                            }
                        });
                   });
               });
           });
        },
        render_header: function () {
            var self = this;
            rpc.query({
                model: 'res.users',
                method: 'read',
                args: [[session.uid]],
            }, {async: false})
                .then(function (res) {
                    self.$el.find('.welcome-text').html('<p><br/>' +
                        '<small>Hello' +
                        '</small>' +
                        '<br/><b>' +res[0].name +
                        '</b></p>');
                });
        },
    });
    core.action_registry.add('open_product_expiry_dashboard', ProductExpiryDashboard);
    return {
        ProductExpiryDashboard: ProductExpiryDashboard,
    };
});