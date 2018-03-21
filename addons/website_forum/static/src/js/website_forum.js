odoo.define('website_forum.website_forum', function (require) {
    'use strict';

    require('web.dom_ready');
    var ajax = require('web.ajax');
    var core = require('web.core');

    var _t = core._t;

    var lastsearch;

    if (!$('.website_forum').length) {
        return $.Deferred().reject("DOM doesn't contain '.website_forum'");
    }

    // pull-left class messes up the post layout OPW 769721
    $('span[data-oe-model="forum.post"][data-oe-field="content"]').find('img.pull-left').removeClass('pull-left');

    $("[data-toggle='popover']").popover();
    $('.karma_required').on('click', function (ev) {
        var karma = $(ev.currentTarget).data('karma');
        if (karma) {
            ev.preventDefault();
            var msg = karma + ' ' + _t(' karma is required to perform this action. You can earn karma by having your answers upvoted by the community.');
            if ($('a[href*="/login"]').length) {
                msg = _t('Sorry you must be logged in to perform this action');
            }
            var $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert mt8" id="karma_alert">'+
                '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                msg + '</div>');
            var $voteAlert = $('#karma_alert');
            if ($voteAlert.length) {
                $voteAlert.remove();
            }
            $(ev.currentTarget).after($warning);
        }
    });

    $('.o_js_forum_tag_follow').hover(
        function(event) {
            $(this).find('.o_forum_tag_follow_box').stop().fadeIn().css('display','block');
        },
        function(event) {
            $(this).find('.o_forum_tag_follow_box').stop().fadeOut().css('display','none');
    });

    $('.o_forum_profile_pic_edit').on('click', function(ev) {
        ev.preventDefault();
        $(this).closest('form').find('.o_forum_file_upload').trigger('click');
    });

    $('.o_forum_file_upload').on('change', function() {
        if (this.files.length) {
            var $form = $(this).closest('form');
            var reader = new window.FileReader();
            reader.onload = function(ev) {
                $form.find('.o_forum_avatar_img').attr('src', ev.target.result);
            };
            reader.readAsDataURL(this.files[0]);
            $form.find('#forum_clear_image').remove();
        }
    });

    $('.o_forum_profile_pic_clear').click(function() {
        var $form = $(this).closest('form');
        $form.find('.o_forum_avatar_img').attr("src", "/web/static/src/img/placeholder.png");
        $form.append($('<input/>', {
            name: 'clear_image',
            id: 'forum_clear_image',
            type: 'hidden',
        }));
    });

    // Extended user biography toogle
    $('.o_forum_user_info').hover(
        function () {
           $(this).parent().find('.o_forum_user_bio_expand').delay(500).toggle('fast');
        },
        function () {
            $(this).parent().find('.o_forum_user_bio_expand').clearQueue();
        }
    );

    $('.o_forum_user_bio_expand').hover(
        function () {},
        function () {
            $(this).fadeOut('fast');
        }
    );

    $('.flag').not('.karma_required').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        ajax.jsonRpc($link.data('href'), 'call', {})
            .then(function (data) {
                if(data.error) {
                    var $warning;
                    if(data.error === 'anonymous_user') {
                        $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert" id="flag_alert">'+
                            '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                            _t('Sorry you must be logged to flag a post') +
                            '</div>');
                    } else if(data.error === 'post_already_flagged') {
                        $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert" id="flag_alert">'+
                            '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                            _t('This post is already flagged') +
                            '</div>');
                    } else if(data.error === 'post_non_flaggable') {
                        $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert" id="flag_alert">'+
                            '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                            _t('This post can not be flagged') +
                            '</div>');
                    }
                    var flag_alert = $link.parent().find("#flag_alert");
                    if (flag_alert.length === 0) {
                        $link.parent().append($warning);
                    }
                } else if(data.success) {
                    var elem = $link;
                    if(data.success === 'post_flagged_moderator') {
                        elem.html(' Flagged');
                        var c = parseInt($('#count_flagged_posts').html(), 10);
                        c++;
                        $('#count_flagged_posts').html(c);
                    } else if(data.success === 'post_flagged_non_moderator') {
                        elem.html(' Flagged');
                        var forum_answer = elem.closest('.forum_answer');
                        forum_answer.fadeIn(1000);
                        forum_answer.slideUp(1000);
                    }
                }
            });
    });

    $('.vote_up,.vote_down').not('.karma_required').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        ajax.jsonRpc($link.data('href'), 'call', {})
            .then(function (data) {
                if (data.error){
                    var $warning;
                    if (data.error === 'own_post'){
                        $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert" id="vote_alert">'+
                            '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                            _t('Sorry, you cannot vote for your own posts') +
                            '</div>');
                    } else if (data.error === 'anonymous_user'){
                        $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert" id="vote_alert">'+
                            '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                            _t('Sorry you must be logged to vote') +
                            '</div>');
                    }
                    var vote_alert = $link.parent().find("#vote_alert");
                    if (vote_alert.length === 0) {
                        $link.parent().append($warning);
                    }
                } else {
                    $link.parent().find(".vote_count").html(data['vote_count']);
                    if (data.user_vote === 0) {
                        $link.parent().find(".text-success").removeClass("text-success");
                        $link.parent().find(".text-warning").removeClass("text-warning");
                    } else {
                        if (data.user_vote === 1) {
                            $link.addClass("text-success");
                        } else {
                            $link.addClass("text-warning");
                        }
                    }
                }
            });
    });

    $(".o_js_validation_queue a[href*='/validate']").on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var self = $(this);
        $(this).parents('.post_to_validate').hide();
        $.get($link.attr('href'))
            .fail(function() {
                self.parents('.o_js_validation_queue > div').addClass('panel-danger').css('background-color', '#FAA');
                self.parents('.post_to_validate').show();
            })
            .done(function() {
                var left = $('.o_js_validation_queue:visible').length;
                var type = $('h2.page-header li.active a').data('type');
                $('#count_post').text(left);
                $('#moderation_tools a[href*="/'+type+'_"]').find('strong').text(left);
            });

    });

    $('.accept_answer').not('.karma_required').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        ajax.jsonRpc($link.data('href'), 'call', {}).then(function (data) {
            if (data.error) {
                if (data.error === 'anonymous_user') {
                    var $warning = $('<div class="alert alert-danger alert-dismissable" id="correct_answer_alert" style="position:absolute; margin-top: -30px; margin-left: 90px;">'+
                        '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                        _t('Sorry, anonymous users cannot choose correct answer.') +
                        '</div>');
                }
                var correct_answer_alert = $link.parent().find("#correct_answer_alert");
                if (correct_answer_alert.length === 0) {
                    $link.parent().append($warning);
                }
            } else {
                if (data) {
                    $(".oe_answer_true").addClass('oe_answer_false').removeClass("oe_answer_true");
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
        ajax.jsonRpc($link.data('href'), 'call', {}).then(function (data) {
            $link.toggleClass("forum_favourite_question", !!data);
        });
    });

    $('.comment_delete').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        ajax.jsonRpc($link.closest('form').attr('action'), 'call', {}).then(function () {
            $link.parents('.comment').first().remove();
        });
    });

    $('.notification_close').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        ajax.jsonRpc("/forum/notification_read", 'call', {
            'notification_id': $link.attr("id")});
    });

    $('.send_validation_email').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        ajax.jsonRpc("/forum/send_validation_email", 'call', {
            'forum_id': $link.attr('forum-id'),
        }).then(function (data) {
            if (data) {
                $('button.validation_email_close').click();
            }
        });
    });

    $('.validated_email_close').on('click', function (ev) {
        ajax.jsonRpc("/forum/validate_email/close", 'call', {});
    });

    // welcome message action button
    var forum_login = _.string.sprintf('%s/web?redirect=%s',
        window.location.origin, escape(window.location.href));
    $('.forum_register_url').attr('href',forum_login);

    $('.js_close_intro').on('click', function (ev) {
        ev.preventDefault();
        document.cookie = "forum_welcome_message = false";
        $('.forum_intro').slideUp();
        return true;
    });

    $('.link_url, .o_forum_post_link').on('change', function (ev) {  // keep .link_url for compat
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var display_error = function(){
            var $warning = $('<div class="alert alert-danger alert-dismissable" style="position:absolute; margin-top: -180px; margin-left: 90px;">'+
                '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                'Please enter valid URL. Example: http://www.odoo.com'+
                '</div>');
            $link.parent().append($warning);
            $link.parents('form').find('button')[0].disabled = true;

        };
        var url = $link.val();
        if (url.search("^http(s?)://.*")) {
            url = 'http://'+url;
        }

        // https://gist.github.com/dperini/729294
        var regex = new RegExp(
          "^" +
            // protocol identifier
            "(?:(?:https?|ftp)://)" +
            // user:pass authentication
            "(?:\\S+(?::\\S*)?@)?" +
            "(?:" +
              // IP address exclusion
              // private & local networks
              "(?!(?:10|127)(?:\\.\\d{1,3}){3})" +
              "(?!(?:169\\.254|192\\.168)(?:\\.\\d{1,3}){2})" +
              "(?!172\\.(?:1[6-9]|2\\d|3[0-1])(?:\\.\\d{1,3}){2})" +
              // IP address dotted notation octets
              // excludes loopback network 0.0.0.0
              // excludes reserved space >= 224.0.0.0
              // excludes network & broacast addresses
              // (first & last IP address of each class)
              "(?:[1-9]\\d?|1\\d\\d|2[01]\\d|22[0-3])" +
              "(?:\\.(?:1?\\d{1,2}|2[0-4]\\d|25[0-5])){2}" +
              "(?:\\.(?:[1-9]\\d?|1\\d\\d|2[0-4]\\d|25[0-4]))" +
            "|" +
              // host name
              "(?:(?:[a-z\\u00a1-\\uffff0-9]-*)*[a-z\\u00a1-\\uffff0-9]+)" +
              // domain name
              "(?:\\.(?:[a-z\\u00a1-\\uffff0-9]-*)*[a-z\\u00a1-\\uffff0-9]+)*" +
              // TLD identifier
              "(?:\\.(?:[a-z\\u00a1-\\uffff]{2,}))" +
              // TLD may end with dot
              "\\.?" +
            ")" +
            // port number
            "(?::\\d{2,5})?" +
            // resource path
            "(?:[/?#]\\S*)?" +
          "$", "i"
        );

        if(regex.test(url)){
            ajax.jsonRpc("/forum/get_url_title", 'call', {'url': url}).then(function (data) {
                if (data) {
                    $("input[name='post_name']")[0].value = data;
                    $link.parents('form').find('button')[0].disabled = false;
                } else {
                    display_error();
                }

            });
        } else {
            display_error();
        }
    });

    $('input.js_select2').select2({
        tags: true,
        tokenSeparators: [",", " ", "_"],
        maximumInputLength: 35,
        minimumInputLength: 2,
        maximumSelectionSize: 5,
        lastsearch: [],
        createSearchChoice: function (term) {
            if ($(lastsearch).filter(function () { return this.text.localeCompare(term) === 0;}).length === 0) {
                //check Karma
                if (parseInt($("#karma").val()) >= parseInt($("#karma_edit_retag").val())) {
                    return {
                        id: "_" + $.trim(term),
                        text: $.trim(term) + ' *',
                        isNew: true,
                    };
                }
            }
        },
        formatResult: function(term) {
            if (term.isNew) {
                return '<span class="label label-primary">New</span> ' + _.escape(term.text);
            }
            else {
                return _.escape(term.text);
            }
        },
        ajax: {
            url: '/forum/get_tags',
            dataType: 'json',
            data: function(term) {
                return {
                    q: term,
                    l: 50
                };
            },
            results: function(data) {
                var ret = [];
                _.each(data, function(x) {
                    ret.push({ id: x.id, text: x.name, isNew: false });
                });
                lastsearch = ret;
                return { results: ret };
            }
        },
        // Take default tags from the input value
        initSelection: function (element, callback) {
            var data = [];
            _.each(element.data('init-value'), function(x) {
                data.push({ id: x.id, text: x.name, isNew: false });
            });
            element.val('');
            callback(data);
        },
    });

    $('textarea.load_editor').each(function () {
        var $textarea = $(this);
        var editor_karma = $textarea.data('karma') || 30;  // default value for backward compatibility
        if (!$textarea.val().match(/\S/)) {
            $textarea.val("<p><br/></p>");
        }
        var $form = $textarea.closest('form');
        var toolbar = [
                ['style', ['style']],
                ['font', ['bold', 'italic', 'underline', 'clear']],
                ['para', ['ul', 'ol', 'paragraph']],
                ['table', ['table']],
                ['history', ['undo', 'redo']],
            ];
        if (parseInt($("#karma").val()) >= editor_karma) {
            toolbar.push(['insert', ['link', 'picture']]);
        }
        $textarea.summernote({
                height: 150,
                toolbar: toolbar,
                styleWithSpan: false
            });

        // pull-left class messes up the post layout OPW 769721
        $form.find('.note-editable').find('img.pull-left').removeClass('pull-left');
        $form.on('click', 'button, .a-submit', function () {
            $textarea.html($form.find('.note-editable').code());
        });
    });

});
