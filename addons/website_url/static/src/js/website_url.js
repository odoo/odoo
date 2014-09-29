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

            this.$('.archive').click(function(event) {
                event.preventDefault();
                self.archive();
            });
        },
        archive: function() {
            var self = this;

            openerp.jsonRpc('/r/archive', 'call', {'code' : self.link_obj.code})
                .then(function(result) {
                    self.$el.remove();
                });
        },
    });

    $(document).ready(function() {

        ZeroClipboard.config(
            {swfPath: location.origin + "/website_url/static/src/js/ZeroClipboard.swf" }
        );

        // Add the RecentLinkBox widget and send the form when the user generate the link
        var client = new ZeroClipboard($("#btn_shorten_url"));
        $("#btn_shorten_url").click( function() {
            if($(this).attr('class').indexOf('btn_copy') === -1) {
                var url = $("#url").val();
                var campaign_id = $('#campaign-select').children(":selected").attr('id');
                var medium_id = $('#channel-select').children(":selected").attr('id');
                var source_id = $('#source-select').children(":selected").attr('id');

                openerp.jsonRpc("/r/new", 'call', {'url' : url, 'campaign_id':campaign_id, 'medium_id':medium_id, 'source_id':source_id})
                    .then(function (result) {
                        console.log(result);

                        var link = result[0];

                        $("#url").data("last_result", link.short_url).val(link.short_url).focus().select();
                        $("#btn_shorten_url").text("Copy").removeClass("btn_shorten btn-primary").addClass("btn_copy btn-success");
                        return link;
                    })
                    .then(function(link) {
                        console.log(link);
                        var recent_link_box = new openerp.website_url.RecentLinkBox(link);
                        recent_link_box.prependTo($('#recent_links'));
                    });
            }
        });

        $("#url").on("change keyup paste mouseup", function() {
            if ($(this).data("last_result") != $("#url").val()) {
                $("#btn_shorten_url").text("Shorten").removeClass("btn_copy btn-success").addClass("btn_shorten btn-primary");
            }
        });

        // Show the recent links   
        openerp.website.add_template_file('/website_url/static/src/xml/recent_link.xml')
            .then(function() {
                openerp.jsonRpc('/r/recent_links', 'call')
                    .then(function(result) {
                        var $recent_links = $('#recent_links');
                        for(var  i = 0 ; i < result.length ; i++) {
                            var recent_link_box = new openerp.website_url.RecentLinkBox(result[i]);
                            recent_link_box.prependTo($recent_links);
                        }
                    });
            });

        // Select with search on the campaign fields
        $("#campaign-select").select2();
        $("#channel-select").select2();
        $("#source-select").select2();
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
