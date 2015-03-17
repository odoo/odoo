
    openerp.website.if_dom_contains('.website_forum', function () {
        var _t = openerp._t;
        $("[data-toggle='popover']").popover();
        $('.karma_required').on('click', function (ev) {
            var karma = $(ev.currentTarget).data('karma');
            if (karma) {
                ev.preventDefault();
                var $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert" id="karma_alert">'+
                    '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                    karma + _t(' karma is required to perform this action. You can earn karma by having your answers upvoted by the community.')+
                            '</div>');
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
                                _t('Sorry, you cannot vote for your own posts')+
                                '</div>');
                        } else if (data['error'] == 'anonymous_user'){
                            var $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert" id="vote_alert">'+
                                '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                                _t('Sorry you must be logged to vote')+
                                '</div>');
                        }
                        vote_alert = $link.parent().find("#vote_alert");
                        if (vote_alert.length == 0) {
                            $link.parent().append($warning);
                        }
                    } else {
                        $link.parent().find(".vote_count").html(data['vote_count']);
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
                            _t('Sorry, anonymous users cannot choose correct answer.')+
                            '</div>');
                    }
                    correct_answer_alert = $link.parent().find("#correct_answer_alert");
                    if (correct_answer_alert.length == 0) {
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
            openerp.jsonRpc($link.parent('form').attr('action'), 'call', {}).then(function (data) {
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


        $('.link_url').on('change', function (ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            var display_error = function(){
                var $warning = $('<div class="alert alert-danger alert-dismissable" style="position:absolute; margin-top: -180px; margin-left: 90px;">'+
                    '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>'+
                    'Please enter valid URL. Example: http://www.odoo.com'+
                    '</div>');
                $link.parent().append($warning);
                $("button#btn_post_your_article")[0].disabled = true;
            };
            var url = $link.val();
            if (url.search("^http(s?)://.*")) {
                url = 'http://'+url;
            }
            var regex = /(http(s)?:\/\/.)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)/g;
            if(regex.test(url)){
                openerp.jsonRpc("/forum/get_url_title", 'call', {'url': url}).then(function (data) {
                    if(data){
                        $("input[name='post_name']")[0].value = data;
                        $('button#btn_post_your_article').prop('disabled', false);
                    }else{
                        display_error();
                    }
                });
            }else{
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
                    if (parseInt($("#karma").val()) >= parseInt($("#karma_retag").val())) {
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
                data: function(term, page) {
                    return {
                        q: term,
                        l: 50
                    };
                },
                results: function(data, page) {
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
                    ['table', ['table']]
                ];
            if (parseInt($("#karma").val()) >= editor_karma) {
                toolbar.push(['insert', ['link', 'picture']]);
            }
            $textarea.summernote({
                    height: 150,
                    toolbar: toolbar
                });
            $form.on('click', 'button, .a-submit', function () {
                $textarea.html($form.find('.note-editable').code());
            });
        });
    });

