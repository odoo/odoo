odoo.define('advanced_dynamic_dashboard.Dashboard', function (require) {
    "use strict";
    var AbstractAction = require('web.AbstractAction');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var QWeb = core.qweb;
    var Dialog = require('web.Dialog');
    var DynamicDashboard = AbstractAction.extend({
        template: 'advanced_dynamic_dashboard',
        events: {
            'click .add_block': '_onClick_add_block',
            'click .block_setting': '_onClick_block_setting',
            'click .dashboard_pdf': '_onClick_dashboard_pdf',
            'click .dashboard_mail': '_onClick_create_pdf',
            'click .block_delete': '_onClick_block_delete',
            'click #search-button': 'search_chart',
            'click #searchclear': 'clear_search',
            'click #dropdownNavbar': 'navbar_toggle',
            'click #dropdownMenuButton': 'dropdown_toggle',
            'click .chart_item_export': 'export_item',
            'click #edit_layout': '_onClick_edit_layout',
            'click #save_layout': '_onClick_save_layout',
            'change #theme-toggle': 'switch_mode',
            'change #start-date': '_onchangeFilter',
            'change #end-date': '_onchangeFilter',
            'mouseenter #theme-change-icon': 'show_mode_text',
            'mouseleave #theme-change-icon': 'hide_mode_text',
            'click .tile': '_onClick_tile',
        },
        init: function (parent, context) {//Function to Initializes all the values while loading the file
            this.action_id = context['id'];
            this._super(parent, context);
            this.block_ids = [];
        },
        willStart: function () {//Returns the function fetch_data when page load.
            var self = this;
            return $.when(this._super()).then(function () {
                return self.fetch_data();
            });
        },
        start: function () {//Function return render_dashboards() and gridstack_init()
            self = this;
            this.set("title", 'Dashboard');
            return this._super().then(function () {
                self.render_dashboards();
            });
        },
        fetch_data: function () {//Fetch data and call rpc query to create chart or tile. return block_ids
            self = this;
            var def1 = this._rpc({
                model: 'dashboard.block',
                method: 'get_dashboard_vals',
                args: [[], this.action_id]
            }).then(function (result) {
                self.block_ids = result;
            });
            return $.when(def1);
        },
        show_mode_text: function () {//Function change text of dark and light mode while clicking the dark and light button.
            this.$el.find('.theme_icon').next(this.el.querySelector('.theme-text')).remove();
            if ( this.$el.find('#theme-toggle').is(':checked')) {//Set text "Light Mode"
                this.$el.find('.theme_icon').after('<span style="color: #d6e7ff" class="theme-text">⠀Light Mode</span>');
            } else {//Set text "Dark Mode"
                this.$el.find('.theme_icon').after('<span style="color: #000000" class="theme-text">⠀Dark Mode</span>');
            }
            this.$el.find('.theme_icon').next(this.el.querySelector('.theme-text')).fadeIn();
        },
        hide_mode_text: function () {//While click button, hide the mode icon and text
            this.$el.find('.theme_icon').next(this.el.querySelector('.theme-text')).fadeOut(function () {
                $(this).remove();
            });
        },
        switch_mode: function (ev) {//Function to change dashboard theme dark and light mode.
            this.$el.find('.theme_icon').next('.theme-text').remove();
            const isDarkTheme = this.$el.find('#theme-toggle').is(':checked');
            $(this.el.parentElement).toggleClass('dark-theme', isDarkTheme);
            this.$el.find('.theme_icon').toggleClass('bi-sun-fill', isDarkTheme);
            this.$el.find('.theme_icon').toggleClass('bi-moon-stars-fill', !isDarkTheme);
            this.$el.find('.dropdown-export').toggleClass('dropdown-menu-dark', isDarkTheme);
        },
        _onchangeFilter: function() {
        // Function for changing the filter
            this.$('#edit_layout').show();
            var start_date = $('#start-date').val();
            var end_date = $('#end-date').val();
            var self = this;
                if (!start_date) {
                    start_date = "null";
                }
                if (!end_date) {
                    end_date = "null";
                }
                this._rpc({
                    model: 'dashboard.block',
                    method: 'get_dashboard_vals',
                    args: [[], this.action_id, start_date, end_date],
                }).then(function (result) {
                    self.block_ids = result;
                    self.$('.o_dynamic_dashboard').empty(); // Clear existing blocks before rendering
                    self.render_dashboards(); // Re-render the dashboard with updated data
                });
        },
        get_colors: function (x_axis) {//Function fetch random color values and set chart color
            return x_axis.map(() => `rgb(${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)})`);
        },

        get_values_bar: function (block) {//Set bar chart label, color, data and options. And return data and options
            var data = {
                labels: block.x_axis,
                datasets: [{
                    data: block.y_axis,
                    backgroundColor: this.get_colors(block.x_axis),
                    borderColor: 'rgba(200, 200, 200, 0.75)',
                    borderWidth: 1
                }]
            };
            var options = {
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            };
            return [data, options];
        },
        get_values_pie: function (block) {//Set pie chart data and options. And return data and options.
            var data = {
                labels: block['x_axis'],
                datasets: [{
                    label: '',
                    data: block['y_axis'],
                    backgroundColor: this.get_colors(block['x_axis']),
                    hoverOffset: 4
                }]
            };
            return [data, {}];
        },
        get_values_line: function (block) {//Set line chart label, data and options. And return data and options.
            var data = {
                labels: block['x_axis'],
                datasets: [{
                    label: '',
                    data: block['y_axis'],
                    fill: false,
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }]
            };
            return [data, {}];
        },
        get_values_doughnut: function (block) {// Set doughnut chart data and options. And return data and options.
            var data = {
                labels: block['x_axis'],
                datasets: [{
                    label: '',
                    data: block['y_axis'],
                    backgroundColor: this.get_colors(block['x_axis']),
                    hoverOffset: 4
                }]
            };
            return [data, {}];
        },
        get_values_polarArea: function (block) {// Set polarArea chart data and options. And return data and options.
            var data = {
                labels: block['x_axis'],
                datasets: [{
                    label: '',
                    data: block['y_axis'],
                    backgroundColor: this.get_colors(block['x_axis']),
                    hoverOffset: 4
                }]
            };
            return [data, {}];
        },
        get_values_radar: function (block) {// Set radar chart data and options. And return data and options.
            var data = {
                labels: block['x_axis'],
                datasets: [{
                    label: '',
                    data: block['y_axis'],
                    fill: true,
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    borderColor: 'rgb(255, 99, 132)',
                    pointBackgroundColor: 'rgb(255, 99, 132)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgb(255, 99, 132)'
                }]
            };
            var options = {
                    elements: {
                        line: {
                            borderWidth: 3
                        }
                    }
                }
            return [data, options];
        },
        gridstack_init: function (self) {// Used gridstack to drag and resize chart and tile.
            self.$('.grid-stack').gridstack({
                animate: true,
                duration: 200,
                handle: '.grid-stack-item-content',
                draggable: {
                    handle: '.grid-stack-item-content',
                    scroll: true
                },
                alwaysShowResizeHandle: /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent),
                float: true
            });
            self.gridstack_off(self);
        },
        gridstack_on: function (self) {// Enable move and resize functionality
            var gridstack = self.$('.grid-stack').data('gridstack');
            gridstack.enableMove(true);
            gridstack.enableResize(true);
        },
        gridstack_off: function (self) {// Disable move and resize functionality
            var gridstack = self.$('.grid-stack').data('gridstack');
            gridstack.enableMove(false);
            gridstack.enableResize(false);
        },
        render_dashboards: function () {
            self = this;
            self.$("#save_layout").hide();//Hide save_layout button
            _.each(this.block_ids, function (block) {//Loop all chart and tile
                if (block['type'] == 'tile') {
                    self.$('.o_dynamic_dashboard').append(QWeb.render('DynamicDashboardTile', {widget: block}));
                } else {//Block type = 'chart'
                    self.$('.o_dynamic_dashboard').append(QWeb.render('DynamicDashboardChart', {widget: block}));
                    if (!('x_axis' in block)) {
                        return false
                    }
                    var type = block['graph_type']
                    var chart_type = 'self.get_values_' + `${type}(block)`
                    new Chart(self.$('.chart_graphs').last(), {
                        type: type,
                        data: eval(chart_type)[0],
                        options: eval(chart_type)[1]
                    });
                }
            });
            // Toggling dropdown for exporting, clicked item, closing all others
            // When clicked on one, also when mouse leaves parent.
            self.$(".block_export").on({
                click: function () {//Show the export dropdown.
                    if ($(this).next(".dropdown-export").is(':visible')) {
                        $(this).next(".dropdown-export").hide();
                    } else {
                        $(this).next('.dropdown-export').hide();
                        $(this).next(".dropdown-export").show();
                    }
                }
            });
            self.$(".grid-stack-item").on({//Function to hide dropdown-export list while mouse leave the block.
                mouseleave: function () {
                   self.$('.dropdown-export').hide();
                }
            });
            self.$(".dropdown-addblock").on({//Function to hide dropdown-addblock list if mouse leave dropdown list.
                mouseleave: function () {
                    self.$(".dropdown-addblock").hide();
                }
            });
            self.gridstack_init(self);
            if (localStorage.getItem("toggleState") == 'true') {
                self.$(".toggle").prop('checked', true)
                $(self.el.parentElement).addClass('dark-theme');
                self.$(".theme_icon").removeClass('bi-moon-stars-fill');
                self.$(".theme_icon").addClass('bi-sun-fill');
                self.$(".dropdown-export").addClass('dropdown-menu-dark');
            } else {
                $(self.el.parentElement).removeClass('dark-theme');
                self.$(".theme_icon").removeClass('bi-sun-fill');
                self.$(".theme_icon").addClass('bi-moon-stars-fill');
                self.$(".dropdown-export").removeClass('dropdown-menu-dark');
            }
        },
        navbar_toggle: function () {//Function to toggle the navbar.
            this.$('.navbar-collapse').toggle();
        },
        export_item: function (e) {//Function to export chart into jpg, png or csv formate.
            var type = $(e.currentTarget).attr('data-type');
            var canvas = $(e.currentTarget).closest('.export_option').siblings('.row').find('#canvas')[0];
            var dataTitle = canvas.getAttribute("data-title");
            // Create a new canvas with a white background
            var bgCanvas = document.createElement("canvas");
            bgCanvas.width = canvas.width;
            bgCanvas.height = canvas.height;
            var bgCtx = bgCanvas.getContext("2d");
            bgCtx.fillStyle = "white";
            bgCtx.fillRect(0, 0, canvas.width, canvas.height);
            // Draw the chart onto the new canvas
            bgCtx.drawImage(canvas, 0, 0);
            // Export the new canvas as an image
            var imgData = bgCanvas.toDataURL("image/png");
            if (type === 'png') {
                this.$el.find('.chart_png_export').attr({
                    href: imgData,
                    download: `${dataTitle}.png`
                });
            }
            if (type === 'pdf') {
                var pdf = new jsPDF();
                pdf.addImage(bgCanvas.toDataURL("image/png"), 'PNG', 0, 0);
                pdf.save(`${dataTitle}.pdf`);
            }
            if (type === 'csv') {
                var rows = [];
                // Check if the id inside the object is equal to this id
                for (var obj of this.block_ids) {
                    if (obj.id == $(e.currentTarget).attr('data-id')) {
                        rows.push(obj.x_axis);
                        rows.push(obj.y_axis);
                    }
                }
                let csvContent = "data:text/csv;charset=utf-8,";
                rows.forEach(function (rowArray) {
                    let row = rowArray.join(",");
                    csvContent += row + "\r\n";
                });
                var link = document.createElement("a");
                link.setAttribute("href", encodeURI(csvContent));
                link.setAttribute("download", `${dataTitle}.csv`);
                document.body.appendChild(link);
                link.click();
            }
            if (type === 'xlsx'){
                var rows = [];
                for (var obj of this.block_ids) {
                    if (obj.id == $(e.currentTarget).attr('data-id')) {
                        rows.push(obj.x_axis);
                        rows.push(obj.y_axis);
                    }
                }
                // Prepare the workbook
                const workbook = new ExcelJS.Workbook();
                const worksheet = workbook.addWorksheet('My Sheet');
                for(let i = 0; i < rows.length; i++){
                    worksheet.addRow(rows[i]);
                }
                const image = workbook.addImage({
                  base64: imgData,
                  extension: 'png',
                });
                worksheet.addImage(image, {
                  tl: { col: 0, row: 4 },
                  ext: { width: canvas.width, height: canvas.height }
                });
                // Save workbook to a file
                workbook.xlsx.writeBuffer()
                .then((buffer) => {
                    // Create a Blob object from the buffer
                    let blob = new Blob([buffer], {type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
                    let link = document.createElement('a');
                    link.href = window.URL.createObjectURL(blob);
                    link.setAttribute("download", `${dataTitle}.xlsx`);
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                })
            }
        },
        dropdown_toggle: function () {//Function to toggle the button Add Items.
            this.$el.find('.dropdown-addblock').toggle();
        },
        on_reverse_breadcrumb: function () {//Function return all block in exact position.
            self = this;
            this.fetch_data().then(function () {//Fetch all datas
                self.render_dashboards();
                self.gridstack_init(self);
                location.reload();
            });
        },
        search_chart: function (e) {// Fetch search input value and filter the chart and tile.
            e.stopPropagation()
            self = this;
            $(this).next("#theme-change-icon").hide();
            this.$("#edit_layout").hide();
            this.$("#save_layout").hide();
            this.myDiv = this.$('.o_dynamic_dashboard');
            this.$('.o_dynamic_dashboard').empty();
            ajax.jsonRpc("/custom_dashboard/search_input_chart", 'call', {//Ajax call to get filtered data
                'search_input': self.$("#search-input-chart").val()
            }).then(function (res) {
                _.each(self.block_ids, function (block) {
                    if (res.includes(block['id'])) {
                        if (block['type'] == 'tile') {
                            self.$('.o_dynamic_dashboard').append(QWeb.render('DynamicDashboardTile', {widget: block}));
                        } else {
                            self.$('.o_dynamic_dashboard').append(QWeb.render('DynamicDashboardChart', {widget: block}));
                            if (!('x_axis' in block)) {
                                return false
                            }
                            var chart_type = 'self.get_values_' + `${block['graph_type']}(block)`
                            new Chart(self.$('.chart_graphs').last(), {
                                type: block['graph_type'],
                                data: eval(chart_type)[0],
                                options: eval(chart_type)[1]
                            });
                        }
                    }
                });
            });
        },
        clear_search: function () {//Function to clear search box and call the functon on_reverse_breadcrumb().
            self = this;
            self.$("#search-input-chart").val("");
            self.$("#theme-change-icon").show();
            self.$("#edit_layout").show();
            self.$("#save_layout").hide();
            this.block_ids = [];
            self.on_reverse_breadcrumb();
        },
        _onClick_block_setting: function (event) {//Function to edit blocks and redirect to the model dashboard.block
            event.stopPropagation();
            self = this;
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'dashboard.block',
                view_mode: 'form',
                res_id: parseInt($(event.currentTarget).closest('.block').attr('data-id')),
                views: [[false, 'form']],
                context: {'form_view_initial_mode': 'edit'},
            }, {on_reverse_breadcrumb: self.on_reverse_breadcrumb})
        },
        _onClick_block_delete: function (event) {//While click on cross icon, the block will be deleted.
            event.stopPropagation();
            self = this;
            bootbox.confirm({//Popup to conform delete
                message: "Are you sure you want to delete this item?",
                title: "Delete confirmation",
                buttons: {
                    cancel: {
                        label: 'NO, GO BACK',
                        className: 'btn-primary'
                    },
                    confirm: {
                        label: 'YES, I\'M SURE',
                        className: 'btn-danger'
                    }
                },
                callback: function (result) {//Function to unlink block
                    if (result) {
                        rpc.query({
                            model: 'dashboard.block',
                            method: 'unlink',
                            args: [parseInt($(event.currentTarget).closest('.block').attr('data-id'))], // ID of the record to unlink
                        }).then(function (result) {
                             location.reload()
                            self.on_reverse_breadcrumb();
                        }).catch(function (error) {
                        });
                    } else {
                        // Do nothing
                    }
                }
            });
        },
        _onClick_add_block: function (e) {//Fetch data and create chart or tile
            self = this;
            var type = $(e.currentTarget).attr('data-type');
            if (type == 'graph') {
                var chart_type = $(e.currentTarget).attr('data-chart_type');
            }
            if (type === 'tile') {
                var randomColor = '#' + ('000000' + Math.floor(Math.random() * 16777216).toString(16)).slice(-6);
                this.do_action({// Redirect to dashboard.block
                    type: 'ir.actions.act_window',
                    res_model: 'dashboard.block',
                    view_mode: 'form',
                    views: [[false, 'form']],
                    context: {
                        'form_view_initial_mode': 'edit',
                        'default_name': 'New Tile',
                        'default_type': type,
                        'default_height': 2,
                        'default_width': 2,
                        'default_tile_color': randomColor,
                        'default_text_color': '#FFFFFF',
                        'default_fa_icon': 'fa fa-bar-chart',
                        'default_client_action_id': parseInt(self.action_id)
                    }},{
                    on_reverse_breadcrumb: this.on_reverse_breadcrumb
                });
            } else {
                this.do_action({
                    type: 'ir.actions.act_window',
                    res_model: 'dashboard.block',
                    view_mode: 'form',
                    views: [[false, 'form']],
                    context: {
                        'form_view_initial_mode': 'edit',
                        'default_name': 'New ' + chart_type,
                        'default_type': type,
                        'default_height': 5,
                        'default_width': 4,
                        'default_graph_type': chart_type,
                        'default_fa_icon': 'fa fa-bar-chart',
                        'default_client_action_id': parseInt(self.action_id)
                    }
                },
                {
                    on_reverse_breadcrumb: this.on_reverse_breadcrumb
                });
            }
            // FETCHING SAVED LAYOUT FROM LOCAL STORAGE MEMORY
        },
        _onClick_dashboard_pdf: function (e){
        // Function for printing the pdf of the dashboard
            var newElement = document.createElement('div');
            newElement.className = 'pdf';
            var parentElements = $('.grid-stack-item')
            parentElements.each(function(index, parent){
                var parentWidth = $(parent).width();
                var parentHeight = $(parent).height();
                $(parent).children().first().css('width', parentWidth);
                $(parent).children().first().css('height', parentHeight);
                $(parent).children().first().css('margin', '10px');
                newElement.appendChild($(parent)[0].children[0]);
            })
            var opt = {
                margin:       8,
                filename:     'Dashboard.pdf',
                image:        { type: 'jpeg', quality: 1 },
                html2canvas:  { scale: 1 },
                jsPDF:        { unit: 'mm', format: 'a3', orientation: 'portrait' }
            };
            html2pdf().set(opt).from(newElement).save()
            .then(()=>{
                window.location.reload()
            })
        },
        _onClick_create_pdf: function(e){
        // Function for creating pdf in datauristring format
            self = this;
            var newElement = document.createElement('div');
            newElement.className = 'pdf';
            var parentElements = $('.grid-stack-item')
            parentElements.each(function(index, parent){
                var parentWidth = $(parent).width();
                var parentHeight = $(parent).height();
                $(parent).children().first().css('width', parentWidth);
                $(parent).children().first().css('height', parentHeight);
                $(parent).children().first().css('margin', '10px');
                newElement.appendChild($(parent)[0].children[0]);
            })
            var opt = {
                margin:       0.3,
                filename:     'Dashboard.pdf',
                image:        { type: 'jpeg', quality: 1 },
                html2canvas:  { scale: 1 },
                jsPDF:        { unit: 'mm', format: 'a3', orientation: 'portrait' }
            };
            var pdf = html2pdf().set(opt).from(newElement).toPdf().output('datauristring')
            .then(function(pdfOutput) {
                self.dashboard_mail(pdfOutput)
            })
        },

        dashboard_mail: function(pdfData){
        // Function for sending mail to the selected users
            var base64code = pdfData.split(',')[1];
            self.do_action({
                type: 'ir.actions.act_window',
                name: 'SEND MAIL',
                res_model: 'dashboard.mail',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    'default_base64code': base64code,
                }
            });
        },

        _onClick_edit_layout: function (e) {
        // Function to hide edit_layout button and show save_layout button. and also work the function gridstack_on(self)
            e.stopPropagation();
            self = this;
            self.$("#edit_layout").hide();
            self.$("#save_layout").show();
            self.gridstack_on(self);
        },
        _onClick_save_layout: function (e) {
        //Function to save the edited value
            e.stopPropagation();
            self = this;
            self.$("#edit_layout").show();
            self.$("#save_layout").hide();
            var grid_data_list = [];
            this.$el.find('.grid-stack-item').each(function () {
                grid_data_list.push({
                    'id': $(this).data('id'),
                    'x': $(this).data('gs-x'),
                    'y': $(this).data('gs-y'),
                    'width': $(this).data('gs-width'),
                    'height': $(this).data('gs-height')
                })
            });
            this._rpc({
                model: 'dashboard.block',
                method: 'get_save_layout',
                args: [[], this.action_id, grid_data_list]
            });
            self.gridstack_off(self);
        },
        _onClick_tile: function (e) {
        // Function to view the tree view of the tile.
            e.stopPropagation();
            self = this;
            ajax.jsonRpc('/tile/details', 'call', {
                'id': $(e.currentTarget).attr('data-id')
            }).then(function (result) {
                if (result['model_name']) {
                    self.do_action({
                        name: result['model_name'],
                        type: 'ir.actions.act_window',
                        res_model: result['model'],
                        view_mode: 'tree,form',
                        views: [[false, 'list'], [false, 'form']],
                        domain: result['filter']
                    });
                } else {
                    Dialog.alert(this, "Configure the tile's model and parameters.");
                }
            });
        },
    });
    core.action_registry.add('advanced_dynamic_dashboard', DynamicDashboard);
    return DynamicDashboard;
});
