$(document).ready(function () {

    $('.fa-thumbs-up ,.fa-thumbs-down').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var value = $link.attr("value")
        openerp.jsonRpc("/forum/post_vote/", 'call', {
                'post_id': $link.attr("id"),
                'vote': value})
            .then(function (data) {
                if (data == false){
                    vote_alert = $link.parents().find("#vote_alert");
                    if (vote_alert.length <= 1) {
                        var $warning = $('<div class="alert alert-danger alert-dismissable" id="vote_alert" style="position:absolute; margin-top: -30px; margin-left: 90px;">'+
                            '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                            'Sorry, you cannot vote for your own posts'+
                            '</div>');
                        $link.parents().find("#post_vote").append($warning);
                    }
                } else {
                    $link.parent().find("#vote_count").html(data['vote_count']);
                    if (data == 0) {
                        $link.parent().find(".text-success").removeClass("text-success");
                        $link.parent().find(".text-warning").removeClass("text-warning");
                    } else {
                        if (value == 1) {
                            $link.addClass("text-success");
                        } else {
                            $link.addClass("text-warning");
                        }
                    }
                }
            });
        return true;
    });

    $('.delete').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        openerp.jsonRpc("/forum/post_delete/", 'call', {
            'post_id': $link.attr("id")})
            .then(function (data) {
                $link.parents('#answer').remove();
            });
        return false;
    });

    $('.fa-check').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        openerp.jsonRpc("/forum/correct_answer/", 'call', {
              'post_id': $link.attr("id")})
              .then(function (data) {
                  par = $link.parents().find(".oe_answer_true")
                  $link.parents().find(".oe_answer_true").removeClass("oe_answer_true").addClass('oe_answer_false')
                  if (data) {
                    $link.removeClass("oe_answer_false").addClass('oe_answer_true');
                  }
             });
        return false;
    });

    $('.comment_delete').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        openerp.jsonRpc("/forum/message_delete/", 'call', {
            'message_id': $link.attr("id")})
            .then(function (data) {
                $link.parents('#comment').remove();
            });
        return true;
    });

    $('.notification_close').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        openerp.jsonRpc("/forum/notification_read/", 'call', {
            'notification_id': $link.attr("id")})
        return true;
    });

    if($('input.load_tags').length){
        openerp.jsonRpc('/forum/get_tags/','call' ,{}).then(function(data){
            var previous_tags = $("input.load_tags").val();
            $("input.load_tags").val("");
            $("input.load_tags").textext({
                plugins : 'tags suggestions autocomplete',
                tagsItems : previous_tags.split(","),
                suggestions :data,
            });
        return true;
        })
    };

});