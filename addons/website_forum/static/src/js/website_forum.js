function open_share_dialog(social_network, text_to_share, url) {
    'use strict';
    var social_networks = {
        'facebook': ['https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(url), '600', '750'],
        'twitter': ['https://twitter.com/intent/tweet?original_referer=' + encodeURIComponent(url) + '&amp;text=' + encodeURIComponent(text_to_share), '300', '600'],
        'linkedin': ['https://www.linkedin.com/shareArticle?mini=true&url=' + encodeURIComponent(url) + '&title=' + encodeURIComponent(text_to_share) + '&summary=Odoo Forum&source=Odoo forum', '500', '600'],
    };
    if (_.contains(_.keys(social_networks),  social_network)) {
        window.open(social_networks[social_network][0], '', 'menubar=no, toolbar=no, resizable=yes, scrollbar=yes, height=' + social_networks[social_network][1] + ', width=' + social_networks[social_network][2]);
    }
}

function updateDatabase( button, post_id, media) {
    "use strict";
    if (button.data('shared') === false) {
        openerp.jsonRpc('/forum/' + button.data('forum') + '/' + post_id + '/share', 'call', {'media' : media}).then(function () {
            button.data('shared', true);
        });
    }
}

function redirect_user(form, type, Qweb) {
    "use strict";
    var text, post_id, _t = openerp._t, redirect_url, data;
    $.post(form.data("target"), form.serializeArray(), function (result) {
        post_id = (result.answer_id) ? result.answer_id : result.question_id, redirect_url = "/forum/" + result.forum_id + "/question/" + result.question_id;
        if(type === 'question') {
            data = {'type' : type, 'forum_id' : result.forum_id , 'website_name' : form.data('website_name'), 'percentage' : result.stat_data[result.forum_id].percentage, 'average' : result.stat_data[result.forum_id].average, 'probability' : result.stat_data[result.forum_id].probability};
        } else if(type === 'answer') {
            data = {'type' : type, 'forum_id' : result.forum_id , 'website_name' : form.data('website_name'), 'karma' : result.karma};
        }
        $('body').append($.parseHTML(Qweb.render('share_dialog', data)));
        $('#share_dialog_box').data({"url" : redirect_url, "post_id" : post_id}).on('hidden.bs.modal', function () {
            window.location = redirect_url;
        }).modal("show");
    }, 'json');
}

$(document).ready(function () {
    var Qweb = openerp.qweb;
    Qweb.add_template('/website_forum/static/src/xml/website_forum_dialog.xml');
    if ($('.website_forum').length){
        if ($("#promote_sharing").length) {
            $("#promote_sharing_body").append($($("#promote_sharing").data("content")).clone());
            $("#promote_sharing_body > " + $("#promote_sharing").data("content")).addClass("text-center").removeClass("collapse oe_comment_grey");
        }

        $('body').on('click', '.share', function() {
            var media = $(this).data('media'), question = $(this).data('question'), dialog = $(this).data('dialog'),
                url = location.origin, post_id = (dialog) ? $("#share_dialog_box").data('post_id') : $(this).data("id"), text_to_share='';
            if(question) {
                if(dialog) {
                    url = url + $('#share_dialog_box').data('url');
                    data={
                        'twitter' : [url, $('#question_name_ask').val() + ' #' + $(this).data('website_name') + ' #question ' + url],
                        'facebook' : [url + '/dialog', ''],
                        'linkedin' : [url ,$('#question_name_ask').val() + ' : ' + url]
                    }
                } else {
                    url = url + location.pathname;
                    data={
                        'twitter' : [url, $('#question_name').text() + ' #' + $(this).data('website_name') + ' #question ' + url],
                        'facebook' : [($(this).data("author")) ? url + "/dialog" : url, ''],
                        'linkedin' : [url, $('#question_name').text() + ' : ' + url],
                    }
                }
            } else {
                var hash_tag = (dialog) ? "#answered" : ($(this).data("author")) ? "#answered" : "#answer";
                    url = url + location.pathname;
                if(dialog) {
                    data={
                        'facebook' : [url + '/answer/' + post_id + '/dialog/no_author', ''],
                        'linkedin' : [url, 'Find my answer for '],
                    }
                } else {
                    data={
                       'facebook' : [($(this).data("author")) ? url + '/answer/' + post_id + '/no_dialog/author' : url + '/answer/' + post_id + '/no_dialog/no_author', ''],
                       'linkedin' : [url, ($(this).data("author")) ? 'Find my answer for ' : 'Find an interesting answer to '],
                    }
                }
                 data['twitter'] = [url, $('#question_name').text().replace('?', '') + '? ' + hash_tag + ' #' + $(this).data('website_name') + ' ' + url],
                 data['linkedin'][1] = data['linkedin'][1] + $('#question_name').text() + ' on ' + url;
            }
            open_share_dialog(media, data[media][1], data[media][0]);
            updateDatabase($(this), post_id, media);
        });

        $(":not(li .share_link)").click(function () {
            $("li .share_link").popover("hide");
        });

        $("li .share_link").click(function (e) {
            e.stopPropagation();
        });

        $("li .share_link").each(function () {
            var target = $(this).data('target');
            $(this).popover({
                html : true,
                content : function() {
                    return $(target).html();
                }
            });
        });

        $(".tag_text").submit(function (event) {
            event.preventDefault();
            CKEDITOR.instances['content'].destroy();
            redirect_user($(this), 'question', Qweb);
        });

        $("#forum_post_answer").submit(function (event) {
            event.preventDefault();
            CKEDITOR.instances[$(this).children('.load_editor').attr('id')].destroy();
            redirect_user($(this), 'answer', Qweb);
        });

        $('.karma_required').on('click', function (ev) {
            var karma = $(ev.currentTarget).data('karma');
            if (karma) {
                ev.preventDefault();
                var $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert" id="karma_alert">'+
                    '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                    karma + ' karma is required to perform this action. You can earn karma by having '+
                            'your answers upvoted by the community.</div>');
                var vote_alert = $(ev.currentTarget).parent().find("#vote_alert");
                if (vote_alert.length == 0) {
                    $(ev.currentTarget).parent().append($warning);
                }
            }
        });

        $('.vote_up,.vote_down').not('.karma_required').on('click', function (ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            openerp.jsonRpc($link.data('href'), 'call', {})
                .then(function (data) {
                    if (data['error']){
                        if (data['error'] == 'own_post'){
                            var $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert" id="vote_alert">'+
                                '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                                'Sorry, you cannot vote for your own posts'+
                                '</div>');
                        } else if (data['error'] == 'anonymous_user'){
                            var $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert" id="vote_alert">'+
                                '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                                'Sorry you must be logged to vote'+
                                '</div>');
                        }
                        vote_alert = $link.parent().find("#vote_alert");
                        if (vote_alert.length == 0) {
                            $link.parent().append($warning);
                        }
                    } else {
                        $link.parent().find("#vote_count").html(data['vote_count']);
                        if (data['user_vote'] == 0) {
                            $link.parent().find(".text-success").removeClass("text-success");
                            $link.parent().find(".text-warning").removeClass("text-warning");
                        } else {
                            if (data['user_vote'] == 1) {
                                $link.addClass("text-success");
                            } else {
                                $link.addClass("text-warning");
                            }
                        }
                    }
                });
        });

        $('.accept_answer').not('.karma_required').on('click', function (ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            openerp.jsonRpc($link.data('href'), 'call', {}).then(function (data) {
                if (data['error']) {
                    if (data['error'] == 'anonymous_user') {
                        var $warning = $('<div class="alert alert-danger alert-dismissable" id="correct_answer_alert" style="position:absolute; margin-top: -30px; margin-left: 90px;">'+
                            '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                            'Sorry, anonymous users cannot choose correct answer.'+
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
        });

        $('.comment_delete').on('click', function (ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            openerp.jsonRpc($link.data('href'), 'call', {}).then(function (data) {
                $link.parents('.comment').first().remove();
            });
        });

        $('.notification_close').on('click', function (ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            openerp.jsonRpc("/forum/notification_read", 'call', {
                'notification_id': $link.attr("id")});
        });

        $('.send_validation_email').on('click', function (ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            openerp.jsonRpc("/forum/send_validation_email", 'call', {
                'forum_id': $link.attr('forum-id'),
            }).then(function (data) {
                if (data) {
                    $('button.validation_email_close').click();
                }
            });
        });

        $('.validated_email_close').on('click', function (ev) {
            openerp.jsonRpc("/forum/validate_email/close", 'call', {});
        });

        $('.js_close_intro').on('click', function (ev) {
            ev.preventDefault();
            document.cookie = "no_introduction_message = false";
            return true;
        });

        $('.link_url').on('change', function (ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            if ($link.attr("value").search("^http(s?)://.*")) {
                var $warning = $('<div class="alert alert-danger alert-dismissable" style="position:absolute; margin-top: -180px; margin-left: 90px;">'+
                    '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                    'Please enter valid URl.'+
                    '</div>');
                $link.parent().append($warning);
                $link.parent().find("button#btn_post_your_article")[0].disabled = true;
                $link.parent().find("input[name='content']")[0].value = '';
            } else {
                openerp.jsonRpc("/forum/get_url_title", 'call', {'url': $link.attr("value")}).then(function (data) {
                    $link.parent().find("input[name='content']")[0].value = data;
                    $('button').prop('disabled', false);
                    $('input').prop('readonly', false);
                });
            }
        });

        function set_tags(tags) {
            $("input.load_tags").textext({
                plugins: 'tags focus autocomplete ajax',
                ext: {
                    autocomplete: {
                        onSetSuggestions : function(e, data) {
                            var self        = this,
                                val         = self.val(),
                                suggestions = self._suggestions = data.result;
                            if(data.showHideDropdown !== false)
                                self.trigger(suggestions === null || suggestions.length === 0 && val.length === 0 ? "hideDropdown" : "showDropdown");
                        },
                        renderSuggestions: function(suggestions) {
                            var self = this,
                                val  = self.val();
                            self.clearItems();
                            $.each(suggestions || [], function(index, item) {
                                self.addSuggestion(item);
                            });
                            var lowerCasesuggestions = $.map(suggestions, function(n,i){return n.toLowerCase();});
                            if(jQuery.inArray(val.toLowerCase(), lowerCasesuggestions) ==-1) {
                                self.addSuggestion("Create '" + val + "'");
                            }
                        },
                    },
                    tags: {
                        onEnterKeyPress: function(e) {
                            var self = this,
                                val  = self.val(),
                                tag  = self.itemManager().stringToItem(val);

                            if(self.isTagAllowed(tag)) {
                                tag = tag.replace(/Create\ '|\'|'/g,'');
                                self.addTags([ tag ]);
                                // refocus the textarea just in case it lost the focus
                                self.core().focusInput();
                            }
                        },
                    }
                },
                tagsItems: tags.split(","),
                //Note: The following list of keyboard keys is added. All entries are default except {32 : 'whitespace!'}.
                keys: {8: 'backspace', 9: 'tab', 13: 'enter!', 27: 'escape!', 37: 'left', 38: 'up!', 39: 'right',
                    40: 'down!', 46: 'delete', 108: 'numpadEnter', 32: 'whitespace'},
                ajax: {
                    url: '/forum/get_tags',
                    dataType: 'json',
                    cacheResults: true
                }
            });

            $("input.load_tags").on('isTagAllowed', function(e, data) {
                if (_.indexOf($(this).textext()[0].tags()._formData, data.tag) != -1) {
                    data.result = false;
                }
            });
        }
        if($('input.load_tags').length){
            var tags = $("input.load_tags").val();
            $("input.load_tags").val("");
            set_tags(tags);
        };
        if ($('textarea.load_editor').length) {
            $('textarea.load_editor').each(function () {
                if (this['id']) {
                    CKEDITOR.replace(this['id']).on('instanceReady', CKEDITORLoadComplete);
                }
            });
        }
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
