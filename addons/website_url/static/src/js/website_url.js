(function () {
   'use strict';

    var QWeb = openerp.qweb;

    openerp.website_url = {};
    
    openerp.website_url.RecentLinkBox = openerp.Widget.extend({
        template: 'website_url.RecentLink',
        init: function(link_obj) {
            this.link_obj = link_obj;
        },
        start: function() {
            var self = this;

            new ZeroClipboard(this.$('.btn_shorten_url_clipboard'));

            this.$('.archive').click(function(event) {
                event.preventDefault();
                self.archive();
            });

            this.$('.btn_shorten_url_clipboard').click(function() {
                self.toggle_copy_button();
            });
        },
        archive: function() {
            var self = this;

            openerp.jsonRpc('/r/archive', 'call', {'code' : self.link_obj.code})
                .then(function(result) {
                    self.$el.remove();
                });
        },
        toggle_copy_button: function() {
            var self = this;

            this.clipboard_btn = this.$('.btn_shorten_url_clipboard');
            this.clipboard_btn.text("Copied to clipboard").removeClass("btn-primary").addClass("btn-success");

            setTimeout(function() {
                self.clipboard_btn.text("Copy link to clipboard").removeClass("btn-success").addClass("btn-primary");
            }, '5000');
        },
        remove: function() {
            this.$el.remove();
        },
    });

    openerp.website_url.RecentLinks = openerp.Widget.extend({
        init: function() {
            this.links = [];
        },
        start: function() {
            var self = this;

            openerp.website.add_template_file('/website_url/static/src/xml/recent_link.xml')
                .then(function() {
                    self.get_recent_links();
                });
        },
        get_recent_links: function() {
            var self = this;

            openerp.jsonRpc('/r/recent_links', 'call')
                .then(function(result) {
                    var $recent_links = $('#recent_links');
                    for(var  i = 0 ; i < result.length ; i++) {
                        self.add_link(result[i]);
                    }
                });
        },
        add_link: function(link) {
            var self = this;

            // Check if the link is already showed to the user and remove it if it's the case
            for(var i = 0 ; i < this.links.length ; i++) {
                if(self.links[i].link_obj.code == link.code) {
                    self.links[i].remove();
                }
            }

            var recent_link_box = new openerp.website_url.RecentLinkBox(link);
            recent_link_box.prependTo($('#recent_links'));

            this.links.push(recent_link_box);
        },
    });

    openerp.website_url.SelectBox = openerp.Widget.extend({
        init: function(path) {
            this.path = path;
        },
        start: function($element) {
            var self = this;
            this.$element = $element;

            this.fetch_objects().then(function(results) {
                self.objects = results;

                $element.select2({
                    initSelection: {id: 0, text: 'Test'},
                    createSearchChoice:function(term, data) {
                        if(self.object_exists(term)) { 
                            return null; 
                        }

                        return {id:term, text:_.str.sprintf("Create '%s'", term)};
                    },
                    createSearchChoicePosition: 'bottom',
                    multiple: false,
                    data: self.objects,
                });

                $element.on('change', function(e) {
                    self.on_change(e);
                });
            });
        },
        fetch_objects: function() {
            return openerp.jsonRpc('/r/' + this.path, 'call').then(function(results) {

                var objects = [];
                for(var i = 0 ; i < results.length ; i++) {
                    objects.push({id: results[i].id, text: results[i].name});
                }
                return objects;
            });
        },
        object_exists: function(query) {
            var self = this;

            for(var i = 0 ; i < self.objects.length ; i++) {
                if(self.objects[i].text.toLowerCase() == query.toLowerCase()) {
                    return true;
                }
            }
            return false;
        },
        on_change: function(e) {
            var self = this;

            if(_.isString(e.added.id)) {
                self.create_object(e.added.id);
            }
        },
        create_object: function(name) {
            var self = this;

            openerp.jsonRpc('/r/' + this.path + '/new', 'call', {name: name})
                .then(function(result) {
                        self.$element.attr('value', result);
                    });
        },
    });

    $(document).ready(function() {

        var recent_links = new openerp.website_url.RecentLinks;
        recent_links.start();

        ZeroClipboard.config(
            {swfPath: location.origin + "/website_url/static/src/js/ZeroClipboard.swf" }
        );

        var client = new ZeroClipboard($("#btn_shorten_url"));

        // Add the RecentLinkBox widget and send the form when the user generate the link
        $("#btn_shorten_url").click( function() {
            if($(this).attr('class').indexOf('btn_copy') === -1) {
                var url = $("#url").val();
                var campaign_id = $('#campaign-select').attr('value');
                var medium_id = $('#channel-select').attr('value');
                var source_id = $('#source-select').attr('value');

                var params = {};
                params.url = $("#url").val();
                if(campaign_id != '') {
                    params.campaign_id = campaign_id;
                }

                if(medium_id != '') {
                    params.medium_id = medium_id;
                }

                if(source_id != '') {
                    params.source_id = source_id;
                }

                openerp.jsonRpc("/r/new", 'call', params)
                    .then(function (result) {
                        
                        if('error' in result) {
                            var $url_form_group = $('#url-form-group')
                            $url_form_group.addClass('has-error');
                        }
                        else {
                            var link = result[0];
                            $("#url").data("last_result", link.short_url).val(link.short_url).focus().select();
                            $("#btn_shorten_url").text("Copy to clipboard").removeClass("btn_shorten btn-primary").addClass("btn_copy btn-success");
                            recent_links.add_link(link);
                        }
                    });
            }
        });

        $("#url").on("change keyup paste mouseup", function() {
            if ($(this).data("last_result") != $("#url").val()) {
                $("#btn_shorten_url").text("Get short link").removeClass("btn_copy btn-success").addClass("btn_shorten btn-primary");
                $('#url-form-group').removeClass('has-error');
            }
        });


        var campaign_select = new openerp.website_url.SelectBox('campaigns');
        campaign_select.start($("#campaign-select"));

        var source_select = new openerp.website_url.SelectBox('sources');
        source_select.start($("#source-select"));

        var medium_select = new openerp.website_url.SelectBox('mediums');
        medium_select.start($("#channel-select"));

        // $("#campaign-select").select2();
        // $("#channel-select").select2();
        // $("#source-select").select2();
    });
})();






// $(document).ready( function() {


//     ZeroClipboard.config(
//         {swfPath: location.origin + "/website_url/static/src/js/ZeroClipboard.swf" }
//     );
//     var client = new ZeroClipboard($("#btn_shorten_url"));
//     $("#btn_shorten_url").click( function() {
//         if($(this).attr('class').indexOf('btn_copy') === -1) {
//             var url = $("#url").val();
//             openerp.jsonRpc("/r/new", 'call', {'url' : url})
//                 .then(function (result) {
//                     $("#url").data("last_result", result).val(result).focus().select();
//                     $("#btn_shorten_url").text("Copy").removeClass("btn_shorten btn-primary").addClass("btn_copy btn-success");
//                 });
//         }
//     });
//     $("#url").on("change keyup paste mouseup", function() {
//         if ($(this).data("last_result") != $("#url").val()) {
//             $("#btn_shorten_url").text("Shorten").removeClass("btn_copy btn-success").addClass("btn_shorten btn-primary");
//         }
//     });
//
//     //Testing Data
//     var pie_data = [
//             {
//                 "label" : "India",
//                 "value" : 5
//             },
//             {
//                 "label" : "Africa",
//                 "value" : 10
//             }
//         ];
//     var all_chart_data = [
//     {
//     "key": "Series 1",
//     "values": [ [ 1025409600000 , 0] , [ 1028088000000 , 20] , [ 1030766400000 , 7] , [ 1033358400000 , 1]]
//   },];
//     var hour_chart_data = [
//     {
//     "key": "Series 2",
//     "values": [ [ 1025409600000 , 20] , [ 1028088000000 , 22] , [ 1030766400000 , 23] , [ 1033358400000 , 24]]
//   },];
//   var today_chart_data = [
//     {
//     "key": "Series 1",
//     "values": [ [ 1025409600000 , 0] , [ 1028088000000 , -6.3382185140371] , [ 1030766400000 , -5.9507873460847] , [ 1033358400000 , -11.569146943813]]
//   },];
//   var week_chart_data = [
//     {
//     "key": "Series 1",
//     "values": [ [ 1025409600000 , 0] , [ 1028088000000 , -6.3382185140371] , [ 1030766400000 , -5.9507873460847] , [ 1033358400000 , -11.569146943813]]
//   },];
//   var month_chart_data = [
//     {
//     "key": "Series 1",
//     "values": [ [ 1025409600000 , 0] , [ 1028088000000 , -6.3382185140371] , [ 1030766400000 , -5.9507873460847] , [ 1033358400000 , -11.569146943813]]
//   },];

//     nv.addGraph(function() {
//   var chart = nv.models.pieChart()
//       .x(function(d) { return d.label })
//       .y(function(d) { return d.value })
//       .showLabels(true);


//     d3.select("#pie_chart svg")
//         .datum(pie_data)
//         .transition().duration(1200)
//         .call(chart);

//   return chart;
// });
// nv.addGraph(function() {
//   var chart = nv.models.cumulativeLineChart()
//     .x(function(d) { return d[0] })
//     .y(function(d) { return d[1]})
//     .color(d3.scale.category10().range())
//     .useInteractiveGuideline(true)
//     ;

//   chart.xAxis
//     .tickFormat(function(d) {
//       return d3.time.format('%x')(new Date(d))
//     });

//   d3.select('#all_chart svg')
//     .datum(all_chart_data)
//     .transition().duration(500)
//     .call(chart)
//     ;

//   nv.utils.windowResize(chart.update);

//   return chart;
// });
// nv.addGraph(function() {
//   var chart = nv.models.cumulativeLineChart()
//     .x(function(d) { return d[0] })
//     .y(function(d) { return d[1]})
//     .color(d3.scale.category10().range())
//     .useInteractiveGuideline(true)
//     ;

//   chart.xAxis
//     .tickFormat(function(d) {
//       return d3.time.format('%x')(new Date(d))
//     });

//   d3.select('#hour_chart svg')
//     .datum(hour_chart_data)
//     .transition().duration(500)
//     .call(chart)
//     ;

//   nv.utils.windowResize(chart.update);

//   return chart;
// });
// });
