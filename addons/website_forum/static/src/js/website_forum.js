$(document).ready(function () {

    $('.fa-thumbs-up ,.fa-thumbs-down').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var value = $link.attr("value")
        
        openerp.jsonRpc("/forum/post_vote/", 'call', {
                'post_id': $link.attr("id"),
                'vote': value})
            .then(function (data) {
                if (data['error']){
                    if (data['error'] == 'own_post'){
                        var $warning = $('<div class="alert alert-danger alert-dismissable" id="vote_alert" style="position:absolute; margin-top: -30px; margin-left: 90px;">'+
                            '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                            'Sorry, you cannot vote for your own posts'+
                            '</div>');
                    } else if (data['error'] == 'anonymous_user'){
                        var $warning = $('<div class="alert alert-danger alert-dismissable" id="vote_alert" style="position:absolute; margin-top: -30px; margin-left: 90px;">'+
                            '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                            'Sorry, anonymous users cannot vote'+
                            '</div>');
                    }
                    else if (data['error'] == 'lessthen_10_karma')
                    {
                        var $warning = $('<div class="alert alert-danger alert-dismissable" id="vote_alert" style="position:absolute; margin-top: -30px; margin-left: 90px;">'+
                            '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                            '10 karma required to downvote'+
                            '</div>');
                    }
                    vote_alert = $link.parent().find("#vote_alert");
                    if (vote_alert.length == 0) {
                        $link.parent().append($warning);
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
        var tags = $("input.load_tags").val();
        $("input.load_tags").val("");
        set_tags(tags);
    };

    function set_tags(tags) {
        $("input.load_tags").textext({
            plugins: 'tags focus autocomplete ajax',
            tagsItems: tags.split(","),
            //Note: The following list of keyboard keys is added. All entries are default except {32 : 'whitespace!'}.
            keys: {8: 'backspace', 9: 'tab', 13: 'enter!', 27: 'escape!', 37: 'left', 38: 'up!', 39: 'right',
                40: 'down!', 46: 'delete', 108: 'numpadEnter', 32: 'whitespace!'},
            ajax: {
                url: '/forum/get_tags',
                dataType: 'json',
                cacheResults: true
            }
        });
        // Note: Adding event handler of whitespaceKeyDown event.
        $("input.load_tags").bind("whitespaceKeyDown",function () {
            $(this).textext()[0].tags().addTags([ $(this).val() ]);
            $(this).val("");
        });
    }

    $('.post_history').change(function (ev) {
        var $option = $(ev.currentTarget);
        openerp.jsonRpc("/forum/selecthistory", 'call', {
            'history_id': $option.attr("value")})
            .then(function (data) {
                var $input = $('<input type="text" name="question_tag" class="form-control col-md-9 load_tags" placeholder="Tags"/>')
                $option.parent().find(".text-core").replaceWith($input);
                set_tags(data['tags']);
                $option.parent().find("#question_name").attr('value', data['name']);
                CKEDITOR.instances['content'].setData(data['content'])
            })
        return true;
    });

    if ($('textarea.load_editor').length) {
        var editor = CKEDITOR.instances['content'];
        editor.on('instanceReady', CKEDITORLoadComplete);
    }
});

function IsKarmaValid(eventNumber,minKarma){
    "use strict";
    if(parseInt($("#karma").val()) >= minKarma){
        CKEDITOR.tools.callFunction(eventNumber,this);
        return false;
    } else {
        alert("Sorry you need more than 30 Karma.");
    }
}

function CKEDITORLoadComplete(){
    "use strict";
    $('.cke_button__link').attr('onclick','IsKarmaValid(33,30)');
    $('.cke_button__unlink').attr('onclick','IsKarmaValid(37,30)');
    $('.cke_button__image').attr('onclick','IsKarmaValid(41,30)');
}
