odoo.define('multi_vendor_marketplace.rating', function(require) {
    "use strict";
    var session = require('web.session')
    var rpc = require('web.rpc')
    $(document).ready(function() {
        $('.prod_redirect').on('click', function() {
            var url = $(this).attr("href");
            var newUrl = url.replaceAll(' ', '-');
            $(this).attr("href", newUrl);
        });
        $("#post").on('click', function() {
            var seller_id = $("#seller").val()
            var customer_id = $("#customer").val()
            var message_id = $("#msg").val()
            if (message_id == '') {
                swal({
                    text: "Please Fill Your Comments!",
                    button: "Close!",
                });
            } else {
                var rating = 0
                if ($("#rating11").prop("checked")) {
                    rating = $("#rating11").val()
                }
                if ($("#rating12").prop("checked")) {
                    rating = $("#rating12").val()
                }
                if ($("#rating13").prop("checked")) {
                    rating = $("#rating13").val()
                }
                if ($("#rating14").prop("checked")) {
                    rating = $("#rating14").val()
                }
                if ($("#rating15").prop("checked")) {
                    rating = $("#rating15").val()
                }
                rpc.query({
                    model: 'seller.review',
                    method: 'rate_review',
                    args: [{
                        'seller_id': seller_id,
                        'customer_id': customer_id,
                        'rating': rating,
                        'message': message_id
                    }],
                }).then(function(data) {
                    console.log(data);
                });
                swal({
                    title: "Rated!",
                    text: "Thank You For Your Rating!",
                    icon: "success",
                    button: "Close!"
                }).then(function() {
                    location.reload();
                });
            }
        });
        $("#post_yes").on('click', function() {
            var seller_id = $("#seller").val();
            var customer_id = $("#customer").val();
            rpc.query({
                model: 'seller.recommend',
                method: 'recommend_func',
                args: [{
                    'seller_id': seller_id,
                    'customer_id': customer_id,
                    'recommend': 'yes',
                }],
            }).then(function(data) {
                swal({
                    text: "Thank You!",
                    button: "Close!",
                });
            });
        });
        $("#post_no").on('click', function() {
            var seller_id = $("#seller").val();
            var customer_id = $("#customer").val();
            rpc.query({
                model: 'seller.recommend',
                method: 'recommend_func',
                args: [{
                    'seller_id': seller_id,
                    'customer_id': customer_id,
                    'recommend': 'no',
                }],
            }).then(function(data) {
                swal({
                    text: "Thank You!",
                    button: "Close!",
                });
            });
        });
    });
});
