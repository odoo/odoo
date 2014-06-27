$(document).ready(function () {

    $('.vote_up ,.vote_down').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        openerp.jsonRpc($link.data('href'), 'call', {})
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
                            'Sorry you must be logged to vote'+
                            '</div>');
                    }
                    else if (data['error'] == 'not_enough_karma') {
                        var $warning = $('<div class="alert alert-danger alert-dismissable" id="vote_alert" style="max-width: 500px; position:absolute; margin-top: -30px; margin-left: 90px;">'+
                            '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                            'Sorry, at least ' + data['karma'] + ' karma is required to vote. You can gain karma by answering questions and receiving votes.'+
                            '</div>');
                    }
                    vote_alert = $link.parent().find("#vote_alert");
                    if (vote_alert.length == 0) {
                        $link.parent().append($warning);
                    }
                } else {
                    $link.parent().find("#vote_count").html(data['vote_count']);
                    if (data['vote_count'] == 0) {
                        $link.parent().find(".text-success").removeClass("text-success");
                        $link.parent().find(".text-warning").removeClass("text-warning");
                    } else {
                        if (data['vote_count'] == 1) {
                            $link.addClass("text-success");
                        } else {
                            $link.addClass("text-warning");
                        }
                    }
                }
            });
        return true;
    });

    $('.accept_answer').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        openerp.jsonRpc($link.data('href'), 'call', {}).then(function (data) {
            if (data['error']) {
                if (data['error'] == 'anonymous_user'){
                    var $warning = $('<div class="alert alert-danger alert-dismissable" id="correct_answer_alert" style="position:absolute; margin-top: -30px; margin-left: 90px;">'+
                        '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                        'Sorry, anonymous users cannot choose correct answer.'+
                        '</div>');
                } else if (data['error'] == 'not_enough_karma') {
                    var $warning = $('<div class="alert alert-danger alert-dismissable" id="vote_alert" style="max-width: 500px; position:absolute; margin-top: -30px; margin-left: 90px;">'+
                        '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                        'Sorry, at least ' + data['karma'] + ' karma is required to accept this answer. You can gain karma by answering questions and receiving votes.'+
                        '</div>');
                }
                correct_answer_alert = $link.parent().find("#correct_answer_alert");
                if (correct_answer_alert.length == 0) {
                    $link.parent().append($warning);
                }
            } else {
                if (data) {
                    $link.addClass("oe_answer_true").removeClass('oe_answer_false');
                } else {
                    $link.removeClass("oe_answer_true").addClass('oe_answer_false');
                }
            }
        });
        return true;
    });

    $('.favourite_question').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        openerp.jsonRpc($link.data('href'), 'call', {}).then(function (data) {
            if (data) {
                $link.addClass("forum_favourite_question")
            } else {
                $link.removeClass("forum_favourite_question")
            }
        });
        return true;
    });

    $('.comment_delete').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        openerp.jsonRpc($link.data('href'), 'call', {}).then(function (data) {
            $link.parents('.comment').first().remove();
        });
        return true;
    });

    $('.notification_close').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        openerp.jsonRpc("/forum/notification_read", 'call', {
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
        // Adds: create tags on space + blur
        $("input.load_tags").on('whitespaceKeyDown blur', function () {
            $(this).textext()[0].tags().addTags([ $(this).val() ]);
            $(this).val("");
        });
        $("input.load_tags").on('isTagAllowed', function(e, data) {
            if (_.indexOf($(this).textext()[0].tags()._formData, data.tag) != -1) {
                data.result = false;
            }
        });
    }

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
        alert("Sorry you need more than " + minKarma + " Karma.");
    }
}

function CKEDITORLoadComplete(){
    "use strict";
    $('.cke_button__link').attr('onclick','IsKarmaValid(33,30)');
    $('.cke_button__unlink').attr('onclick','IsKarmaValid(37,30)');
    $('.cke_button__image').attr('onclick','IsKarmaValid(41,30)');
}
