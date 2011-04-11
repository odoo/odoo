// = im.js =
//
// **Copyright &copy; 2005 &ndash; 2010 Joshua Gross**\\
// //MIT Licensed//
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
// 
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
// THE SOFTWARE.
//
// This is the main library for Ajax IM. It encompasses the UI controls,
// and connecting with the server. It does //not// handle registration or
// account management.

(function($, _instance) {
    AjaxIM = function(options, actions) {
        if(this instanceof AjaxIM) {
            var self = this;
            
            // === {{{ defaults }}} ===
            //
            // These are the available settings for Ajax IM, and the associated
            // defaults:
            //
            // * {{{pollType}}} determines the way in which the client will talk to
            // the server.
            // ** {{{comet}}} will use http streaming, wherein a connection to the server will be held open indefinitely, and the server will push down new events (messages, status updates) as they occur.
            // ** {{{long}}} will hold open a connection with the server for as long as possible, or until a new event is received. Upon the server sending an event or closing the connection, the client will automatically&mdash;and immediately&mdash;reconnect.
            // ** {{{short}}} will open a connection, and the server (if this method is supported) will //immediately// provide a response as to whether or not there are any new events. Once a response is received, the client will wait 5 seconds, and then reconnect.
            // * {{{pollServer}}} is the default URL to which all actions refer. It is
            // possible to specify certain action URLs separately (as is used with the
            // NodeJS server).
            // * {{{cookieName}}} is the name of the session cookie used by the server.
            // If this is not set properly, the IM engine will not be able to automatically
            // reinitialize sessions.
            // * {{{theme}}} is the name of the theme folder that defines the HTML and
            // CSS of the IM bar and chat boxes. Usually, themes are deposited in the
            // provided "themes" folder and specified by that path, e.g. {{{themes/default}}}.
            // Theme files within the theme folder must be named {{{theme.html}}} and
            // {{{theme.css}}}.
            // * {{{storageMethod}}} defines the way in which data (chat sessions) are
            // temporarily stored client-side. By default, {{{"flash"}}} is used because
            // it is the most widely supported method. However,
            // [[http://eric.garside.name/docs.html?p=jstore#js-engines|other storage engines]]
            // are available, with their respective up- and down-sides
            // outlined, on the jStore website.
            // * {{{storeSession}}} (**not implemented**) sets the number of days to
            // retain stored chat session data before it should be deleted.
            // * {{{checkResume}}} is a flag that sets whether or not the client should
            // make a call to the server before resuming the session (such as on a page
            // reload). This will ensure that the session has not expired. If set to {{{false}}},
            // a call to the server will not be made, and the session will be assumed to
            // be active.
            var defaults = {
                pollType: 'long',
                pollServer: './ajaxim.php',
                cookieName: 'ajaxim_session',
                theme: 'themes/default',
                storageMethod: 'auto',
                flashStorage: 'js/jStore.Flash.html',
                storeSession: 5, // number of days to store chat data (0 for current session only)
                checkResume: true
            };

            // === {{{AjaxIM.}}}**{{{settings}}}** ===
            //
            // These are the settings for the IM. If particular options are not specified,
            // the defaults (see above) will be used. //These options will be defined
            // upon calling the initialization function, and not set directly.//
            this.settings = $.extend(defaults, options);

            // === {{{AjaxIM.}}}**{{{actions}}}** ===
            //
            // Each individual action that the IM engine can execute is predefined here.
            // By default, it merely appends the action onto the end of the {{{pollServer}}} url,
            // however, it is possible to define actions individually. //The alternative actions
            // will be defined upon calling the initialization function, and not set directly.//
            //
            // Should you define an action at a different URL, Ajax IM will determine whether
            // or not this URL is within the current domain. If it is within a subdomain of
            // the current domain, it will set the document.domain variable for you,
            // to match a broader hostname scope; the action will continue to use {{{$.post}}}
            // (the default AJAX method for Ajax IM).
            //
            // On the other hand, should you choose a URL outside the current domain
            // Ajax IM will switch to {{{$.getJSON}}} (a get request) to avoid
            // cross-domain scripting issues. This means that a server on a different
            // port or at a different address will need to be able to handle GET
            // requests rather than POST requests (such as how the Node.JS Ajax IM
            // server works).
            this.actions = $.extend({
                login: this.settings.pollServer + '/login',
                logout: this.settings.pollServer + '/logout',
                register: this.settings.pollServer + '/register',
                poll: this.settings.pollServer + '/poll?method=' + this.settings.pollType,
                send: this.settings.pollServer + '/send',
                status: this.settings.pollServer + '/status',
                resume: this.settings.pollServer + '/resume'
            }, actions);

            var httpRx = new RegExp('^http://', 'i'),
                slashslashRx = new RegExp('^//', 'i'),
                queryStrRx = new RegExp('[?](.+)$'),
                subdomainRx = new RegExp('((http[s]?:)?//)?(.+?)[.]' + window.location.host, 'i');
            $.each(this.actions, function(name, action) {
                if(name == 'poll') {
                    if(self.settings.pollType != 'comet')
                        action += (queryStrRx.test(action[1]) ? '&' : '?') + 'callback=?';
                        
                    action = ['jsonp', action];
                } else {
                    action = ['ajax', action];
                    if(subdomainRx.test(action[1])) {
                        document.domain = '.' + window.location.host;
                    } else if((http = httpRx.test(action[1])) || slashslashRx.test(action[1])) {
                        if(!(new RegExp('//' + window.location.host + '/', 'i')).test(action[1])) {
                            action[1] += (queryStrRx.test(action[1]) ? '&' : '?') + 'callback=?';
                            action = ['jsonp', action[1]];
                        }
                    }
                }
                
                self.actions[name] = action;
            });
            
            // We load the theme dynamically based on the passed
            // settings. If the theme is set to false, we assume
            // that the user is going to load it himself.
            this.themeLoaded = false;
            if(this.settings.theme) {
                $('<div></div>').appendTo('body').load(this.settings.theme + '/theme.html #imjs-bar, .imjs-tooltip',
                    function() {
                        self.themeLoaded = true;
                        setup.apply(self);
                    }
                );
                if(typeof document.createStyleSheet == 'function')
                    document.createStyleSheet(this.settings.theme + '/theme.css');
                else
                    $('body').append('<link rel="stylesheet" href="' +
                        this.settings.theme + '/theme.css" />');
            } else {
                this.themeLoaded = true;
                setup.apply(this);
            }
            
            // Client-side storage for keeping track of
            // conversation states, active tabs, etc.
            // The default is flash storage, however, other
            // options are available via the jStore library.
            if(this.settings.storageMethod) {
                this.storageBrowserKey = 'unknown';
                this.storeKey = '';
                
                $.each($.browser, function(k, v) {
                    if(k == 'version') return true;
                    else if(v == true) {
                        self.storageBrowserKey = k;
                        return false;
                    }
                });
            
                if(this.settings.storageMethod == 'auto') {
                    $.each(['ie', 'html5', 'local', 'flash'], function() {
                        if($.jStore.Availability[this]()) {
                            self.settings.storageMethod = this;
                            return false;
                        }
                    });
                }
            
                $.extend($.jStore.defaults, {
                    project: 'im.js',
                    engine: this.settings.storageMethod,
                    flash: this.settings.flashStorage
                });
                    
                this.storageReady = false;
                
                if(this.settings.storageMethod == 'flash') {                    
                    $.jStore.ready(function(engine) {
                        $.jStore.flashReady(function() {
                            self.storageReady = true;
                            setup.apply(self);
                        });
                    })
                } else {
                    $.jStore.ready(function(engine) {
                        self.storageReady = true;
                        setup.apply(self);
                    });
                }
                
                $.jStore.load();
            } else {
                this.storageReady = true;
                setup.apply(this);
            }

            // Allow a chatbox to me minimized
            $('.imjs-chatbox').live('click', function(e) {
                e.preventDefault();
                return false;
            });
            
            $('.imjs-chatbox .imjs-minimize').live('click', function() {
                $(this).parents('.imjs-chatbox').data('tab').click();
            });
            
            // Allow a chatbox to be closed
            $('.imjs-chatbox .imjs-close').live('click', function() {
                var chatbox = $(this).parents('.imjs-chatbox');
                chatbox.data('tab')
                    .data('state', 'closed').css('display', 'none');
                    
                if(self.settings.storageMethod && self.storageReady) {
                    delete self.chatstore[chatbox.data('username')];
                    if(self.storageReady) {
                        $.jStore.store(
                            self.storageBrowserKey + '-' +
                            self.username + '-chats',
                            self.chatstore);
                    }
                }
            });
            
            // Setup message sending for all chatboxes
            $('.imjs-chatbox .imjs-input').live('keydown', function(event) {               
                var obj = $(this);
                if(event.keyCode == 13 && !($.browser.msie && $.browser.version < 8)) {
                    self.send(obj.parents('.imjs-chatbox').data('username'), obj.val());
                }
            }).live('keyup', function(event) {
                if(event.keyCode == 13) {
                    if($.browser.msie && $.browser.version < 8) {
                        var obj = $(this);
                        self.send(obj.parents('.imjs-chatbox').data('username'), obj.val());
                    }

                    var obj = $(this);
                    obj.val('');
                    obj.height(obj.data('height'));
                }
            }).live('keypress', function(e) {
                var obj = $(this);
                if(!($.browser.msie && $.browser.opera)) obj.height(0);
                if(this.scrollHeight > obj.height() || this.scrollHeight < obj.height()) {
                    obj.height(this.scrollHeight);
                }
            });
            
            $('.imjs-msglog').live('click', function() {
                var chatbox = $(this).parents('.imjs-chatbox');
                chatbox.find('.imjs-input').focus();
            });
            
            // Create a chatbox when a buddylist item is clicked
            $('.imjs-friend').live('click', function() {
                var chatbox = self._createChatbox($(this).data('friend'));
                
                if(chatbox.data('tab').data('state') != 'active')
                    chatbox.data('tab').click();
                    
                chatbox.find('.imjs-input').focus();
            });
            
            // Setup and hide the scrollers
            $('.imjs-scroll').css('display', 'none');
            $('#imjs-scroll-left').live('click', function() {
                var hiddenTab = $('#imjs-bar li.imjs-tab:visible').slice(-1)
                    .next('#imjs-bar li.imjs-tab:hidden')
                    .filter(function() {
                        return $(this).data('state') != 'closed'
                    })
                    .not('.imjs-default').slice(-1).css('display', '');
                    
                if(hiddenTab.length) {
                    $('#imjs-bar li.imjs-tab:visible').eq(0).css('display', 'none');
                    $(this).html(parseInt($(this).html()) - 1);
                    $('#imjs-scroll-right').html(parseInt($('#imjs-scroll-right').html()) + 1);
                }

                return false;
            });
            $('#imjs-scroll-right').live('click', function() {
                var hiddenTab = $('#imjs-bar li.imjs-tab:visible').eq(0)
                    .prev('#imjs-bar li.imjs-tab:hidden')
                    .filter(function() {
                        return $(this).data('state') != 'closed'
                    })
                    .not('.imjs-default').slice(-1).css('display', '');
                    
                if(hiddenTab.length) {
                    $('#imjs-bar li.imjs-tab:visible').slice(-1).css('display', 'none');
                    $(this).html(parseInt($(this).html()) - 1);
                    $('#imjs-scroll-left').html(parseInt($('#imjs-scroll-left').html()) + 1);
                }
                
                return false;
            });
            
            // Initialize the chatbox hash
            this.chats = {};
            
            // Try to resume any existing session
            this.resume();
            
            $(window).resize(function() {
                self.bar._scrollers();
            });
        } else
            return AjaxIM.init(options);
    };
    
    // We predefine all public functions here...
    // If they are called before everything (theme, storage engine) has loaded,
    // then they get put into a "prequeue" and run when everything *does*
    // finally load.
    //
    // This ensures that nothing loads without all of the principal components
    // being pre-loaded. If that were to occur (without this prequeue), things
    // would surely break.
    var prequeue = [];
    var empty = function() {
        var func = this;
        return function() { prequeue.push([func, arguments]) };
    };
    $.extend(AjaxIM.prototype, {
        settings: {},
        friends: {},
        chats: {},
        
        storage: empty.apply('storage'),
        login: empty.apply('login'),
        logout: empty.apply('logout'),
        resume: empty.apply('resume'),
        form: empty.apply('form'),
        poll: empty.apply('poll'),
        incoming: empty.apply('incoming'),
        send: empty.apply('send'),
        status: empty.apply('status'),
        statuses: {},
        bar: {
            initialize: empty.apply('bar.initialize'),
            activateTab: empty.apply('bar.activateTab'),
            closeTab: empty.apply('bar.closeTab'),
            addTab: empty.apply('bar.addTab'),
            notification: empty.apply('bar.notification'),
            _scrollers: empty.apply('bar._scrollers')
        }
    });
    
    setup = (function() {
    var self = this;
    if(!this.storageReady || !this.themeLoaded) return;
    
    $(self).trigger('loadComplete');
    $(window).resize();
    
    $.extend(AjaxIM.prototype, {        
        // == Cookies ==
        //
        // The "cookies" functions can be used to set, get, and erase JSON-based cookies.
        // These functions are primarily used to manage and read the server-set cookie
        // that handles the user's chat session ID.
        cookies: {
            // === {{{AjaxIM.}}}**{{{cookies.set(name, value, days)}}}** ===
            //
            // Sets a cookie, stringifying the JSON value upon storing it.
            //
            // ==== Parameters ====
            // * {{{name}}} is the cookie name.\\
            // * {{{value}}} is the cookie data that you would like to store.\\
            // * {{{days}}} is the number of days that the cookie will be stored for.
            set: function(name, value, days) {
                if (days) {
                    var date = new Date();
                    date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
                    var expires = "; expires=" + date.toGMTString();
                } else var expires = "";
                document.cookie = name + "=" + $.compactJSON(value) + expires + "; path=/";
            },
            
            // === {{{AjaxIM.}}}**{{{cookies.get(name)}}}** ===
            //
            // Gets a cookie, decoding the JSON value before returning the data.
            //
            // ==== Parameters ====
            // * {{{name}}} is the cookie name that you would like to retrieve.
            get: function(name) {
                var nameEQ = name + "=";
                var ca = document.cookie.split(';');
                for(var i = 0; i < ca.length; i++) {
                    var c = ca[i];
                    while (c.charAt(0) == ' ') c = c.substring(1, c.length);
                    if (c.indexOf(nameEQ) == 0) {
                      var cval = decodeURIComponent(c.substring(nameEQ.length, c.length));
                      return $.secureEvalJSON(cval);
                    }
                }
                return null;
            },
            
            // === {{{AjaxIM.}}}**{{{cookies.erase(name)}}}** ===
            //
            // Deletes a cookie.
            //
            // {{{name}}} is the existing cookie that you would like to delete.
            erase: function(name) {
                self.cookies.set(name, '', -1);
            }
        },

        // == Main ==
        
        // === {{{AjaxIM.}}}**{{{storage()}}}** ===
        //
        // Retrieves chat session data from whatever storage engine is enabled
        // (provided that one is enabled at all). If a page reloads, this function
        // is called to restore the user's chat state (existing conversations, active tab).
        // This function is called //automatically//, upon initialization of the IM engine.
        storage: function() {
            if(!self.storeKey.length) return;
            
            try {
                var chatstore = $.jStore.store(self.storeKey + 'chats') || {};
            } catch(e) {
                $.jStore.remove(self.storeKey + 'chats');
                var chatstore = {};
            }

            if(this.chatstore) {            
                $.each(this.chatstore, function(username, convo) {
                    if(username in chatstore)
                        chatstore[username] = $.merge(chatstore[username], self.chatstore[username]);
                    else
                        chatstore[username] = self.chatstore[username];
                });
                                
                this.chatstore = chatstore;
                $.jStore.store(self.storeKey + 'chats', chatstore);
            } else {
                this.chatstore = chatstore;
            }
            
            $.each(this.chatstore, function(username, convo) {
                if(!convo.length) return;
                
                var chatbox = self._createChatbox(username, true);
                chatbox.data('lastDateStamp', null).css('display', 'none');
                
                // Remove the automatic date stamp
                chatbox.find('.imjs-msglog').empty();
                
                // Restore all messages, date stamps, and errors
                $.each(convo, function() {
                    switch(this[0]) {
                        case 'error':
                            self._addError(chatbox, decodeURIComponent(this[2]), this[3]);
                        break;
                        
                        case 'datestamp':
                            self._addDateStamp(chatbox, this[3]);
                        break;
                        
                        case 'a':
                        case 'b':
                            self._addMessage(this[0], chatbox, this[1],
                                decodeURIComponent(this[2]), this[3]);
                        break;
                    }
                });
                
                $(self).trigger('chatRestored', [username, chatbox]);
            });
            
            var activeTab = $.jStore.store(self.storeKey + 'activeTab') || [];
            if(activeTab.length && (activeTab = activeTab[0]) && activeTab in this.chats) {
                this.chats[activeTab].data('tab').click();
                var msglog = this.chats[activeTab].find('.imjs-msglog');
                msglog[0].scrollTop = msglog[0].scrollHeight;
            }
        },
        
        // === {{{AjaxIM.}}}**{{{login(username, password)}}}** ===
        //
        // Authenticates a user and initializes the IM engine. If the user is
        // already logged in, [s]he is logged out, the session is cleared, and
        // the new user is logged in.
        //
        // Returns the user's properly formatted username, session ID, and online
        // friends in JSON, if successful; e.g.:\\
        // {{{ {u: 'username', s: 'longsessionid', f: [{u: 'friend', s: 1, g: 'group'}]} }}}
        //
        // If unsuccessful, {{{false}}} is returned.
        //
        // ==== Parameters ====
        // * {{{username}}} is the user's username.\\
        // * {{{password}}} is the user's password. This password will be MD5 hashed
        // before it is sent to the server.
        login: function(username, password) {
            if(!username) username = '';
            if(!password) password = '';
            
            if(this.username)
                return true; // Already logged in!
        
            // hash password before sending it to the server
            password = $.md5(password);

            // authenticate
            AjaxIM.request(
                this.actions.login,
                {'username': username, 'password': password},
                function(auth) {
                    if(auth.r == 'logged in') {
                        self.username = ('u' in auth ? auth.u : username);
                        
                        if(self.settings.storageMethod)
                            self.storeKey = [self.storageBrowserKey, self.username, ''].join('-');
                            
                        var existing = self.cookies.get(self.settings.cookieName);
                        self.storage();
                        
                        // Begin the session
                        $.each(auth.f, function() {
                            self.friends[this.u] = {status: [this.s, ''], group: this.g};
                        });
                        self._session(self.friends);
                        self._storeFriends();
                        
                        $(self).trigger('loginSuccessful', [auth]);
                        
                        return auth;
                    } else {
                        $(self).trigger('loginError', [auth]);
                    }
                    
                    return false;
                }
            );
        },
        
        // === {{{AjaxIM.}}}**{{{logout()}}}** ===
        //
        // Logs the user out and removes his/her session cookie. As well, it
        // will close all existing chat windows, clear the storage engine, and
        // remove the IM bar.
        logout: function() {
            AjaxIM.request(
                this.actions.logout,
                {},
                function(done) {
                    if(done) {
                        self.cookies.erase(self.settings.cookieName);
                        self._clearSession();
                        $(self).trigger('logoutSuccessful');
                        return true;
                    } else {
                        $(self).trigger('logoutError');
                        return false;
                    }
                }
            );
        },
        
        // === {{{AjaxIM.}}}**{{{resume()}}}** ===
        //
        // Resumes an existing session based on a session ID stored in the
        // server-set cookie. This function is called //automatically// upon IM
        // engine (re-)initialization, so the user does not need to re-login
        // should a session already exist.
        resume: function() {
            var session = this.cookies.get(this.settings.cookieName);
            
            if(session && session.sid) {
                this.username = session.user;
                
                this.storeKey = [this.storageBrowserKey, this.username, ''].join('-');
                
                var friends = $.jStore.store(this.storeKey + 'friends') || [];
                if(self.settings.checkResume) {
                    AjaxIM.request(
                        this.actions.resume,
                        {},
                        function(response) {
                            if(response.r == 'connected') {
                                self._session(friends);
                                self.storage();
                            } else {
                                var username = this.username;
                                self._clearSession();
                                $(self).trigger('sessionNotResumed', [username]);
                            }
                        }
                    );
                } else {
                    self._session(friends);
                    self.storage();
                }
            } else {
                $(self).trigger('noSession');
            }
        },
        
        // === //private// {{{AjaxIM.}}}**{{{_session(friends)}}}** ===
        //
        // Restores session data (username, friends) and begins polling the server.
        // Called only by {{{AjaxIM.resume()}}}.
        //
        // ==== Parameters ====
        // * {{{friends}}} is a list of "friend" objects, e.g.:\\
        // {{{[{u: 'friend', s: 1, g: 'group'}, ...]}}}
        // ** {{{u}}} being the friend's username.
        // ** {{{s}}} being one of the available status codes (see {{{AjaxIM.statuses}}}), depending on the friend's current status.
        // ** {{{g}}} being the group that the friend is in.
        _session: function(friends) {
            $('#imjs-friends-panel .imjs-header span').html(this.username);
            $('#imjs-friends').removeClass('imjs-not-connected');
            
            $.each(friends, function(friend, info) {
                self.addFriend.apply(self, [friend, info.status, info.group]);
            });
            self._storeFriends();
            
            $(self).trigger('sessionResumed', [this.username]);
            
            setTimeout(function() { self.poll(); }, 0);
        },
        
        // === //private// {{{AjaxIM.}}}**{{{_clearSession()}}}** ===
        //
        // Clears all session data from the last known user.
        _clearSession: function() {                    
            if(self.settings.storageMethod && self.storageReady) {
                $.jStore.remove(self.storeKey + 'chats');
                $.jStore.remove(self.storeKey + 'friends');
                $.jStore.remove(self.storeKey + 'activeTab');
            }
            
            self.chats = {};
            $('.imjs-tab').not('.imjs-tab.imjs-default').remove();
            
            self.cookies.erase('ajaxim_session');
            delete self.username;
        },
        
        // === {{{AjaxIM.}}}**{{{form(element)}}}** ===
        //
        // Loads a login and registration form into the specified element
        // or, if no element is supplied, to the location on the page from
        // which this function was called.
        form: function(element) {
            $(element).load(this.settings.theme + '/theme.html #imjs-lr', function() {
                $('#imjs-lr .error').hide();
                
                if(self.username) {
                    $('#imjs-register, #imjs-login fieldset').hide();
                    $('#imjs-logged-in')
                        .show()
                        .html($('#imjs-logged-in').html().replace('{username}', self.username));
                } else {
                    $('#imjs-logged-in').hide();
                }

                // Handle logout success                
                $(self).bind('logoutSuccessful', function() {
                    $('#imjs-login fieldset').slideDown();
                    $('#imjs-register').slideDown();
                    
                    $('#imjs-logged-in')
                        .html($('#imjs-logged-in strong').html('{username}'))
                        .slideUp();
                });
                $('#imjs-logged-in a').click(function() {
                    self.logout();
                    return false;
                });

                // Handle login error or success
                $(self).bind('loginError', function() {
                    $('#imjs-login .error').html(AjaxIM.i18n.authInvalid).slideDown('fast');
                    $('#imjs-login input')
                        .addClass('imjs-lr-error')
                        .blur(function() { $(this).removeClass('imjs-lr-error'); });
                }).bind('loginSuccessful', function() {
                    $('#imjs-login fieldset').slideUp();
                    $('#imjs-register').slideUp();
                    
                    $('#imjs-logged-in')
                        .html($('#imjs-logged-in').html().replace('{username}', self.username))
                        .slideDown();
                });
                var login = function() {
                    self.login($('#imjs-login-username').val(), $('#imjs-login-password').val());
                    return false;
                };
                $('#imjs-login').submit(login);
                $('#imjs-login-submit').click(login);
                
                var regIssues = false;
                var regError = function(error, fields) {
                    $('#imjs-register .error')
                        .append(AjaxIM.i18n['register' + error] + ' ')
                        .slideDown();
                    $(fields)
                        .addClass('imjs-lr-error')
                        .blur(function() { $(this).removeClass('imjs-lr-error'); });
                    regIssues = true;
                };
                
                var register = function() {
                    $('#imjs-register .error').empty();
                    
                    regIssues = false;
                    
                    var username = $('#imjs-register-username').val();
                    var password = $('#imjs-register-password').val();
                    
                    if(password.length < 4)
                        regError('PasswordLength', '#imjs-register-password');
                
                    if(password != $('#imjs-register-cpassword').val())
                        regError('PasswordMatch', '#imjs-register-password, #imjs-register-cpassword');
                    
                    if(username.length <= 2 ||
                        !$('#imjs-register-username').val().match(/^[A-Za-z0-9_.]+$/))
                        regError('UsernameLength', '#imjs-register-username');
                    
                    if(!regIssues) {
                        AjaxIM.request(
                            self.actions.register,
                            {username: username, password: password},
                            function(response) {
                                if(response.r == 'registered') {
                                    self.login(username, password);
                                } else if(response.r == 'error') {
                                    switch(response.e) {
                                        case 'unknown':
                                            regError('Unknown', '');
                                        break;
                                        
                                        case 'invalid password':
                                            regError('PasswordLength', '#imjs-register-password');
                                        break;
                                        
                                        case 'invalid username':
                                            regError('UsernameLength', '#imjs-register-username');
                                        break;
                                        
                                        case 'username taken':
                                            regError('UsernameTaken', '#imjs-register-username');
                                        break;
                                    }
                                }
                            },
                            function(error) {
                                regError('Unknown', '');
                            }
                        );
                    }
                    
                    return false;
                };
                $('#imjs-register').submit(register);
                $('#imjs-register-submit').click(register);
            });
        },
        
        // === {{{AjaxIM.}}}**{{{poll()}}}** ===
        //
        // Queries the server for new messages. If a 'long' or 'short' poll
        // type is used, jQuery's {{{$.post}}} or {{{$.getJSON}}} will be
        // used. If 'comet' is used, the server connection will be deferred
        // to the comet set of functions.
        poll: function() {
            if(/^(short|long)$/.test(this.settings.pollType)) {
                AjaxIM.request(
                    this.actions.poll,
                    {},
                    function(response) {
                        if(!response['e']) {
                            if(response.length)
                                self._parseMessages(response);
                                
                            setTimeout(function() { self.poll(); }, 0);                            
                        } else {
                            switch(response.e) {
                                case 'no session found':
                                    self._notConnected();
                                break;
                            }
                            
                            $(self).trigger('pollFailed', [response.e]);
                        }
                    },
                    function(error) {
                        self._notConnected();
                        $(self).trigger('pollFailed', ['not connected']);
                        // try reconnecting?
                    }
                );
            } else if(this.settings.pollType == 'comet') {
                this.comet.connect();
            }
        },
        
        // === //private// {{{AjaxIM.}}}**{{{_parseMessages(messages)}}}** ===
        //
        // Handles an incoming message array:\\
        // {{{[{t: 'type', s: 'sender', r: 'recipient', m: 'message'}, ...]}}}
        //
        // * {{{t}}} (message type) is one of:
        // ** {{{m}}} &mdash; a standard message
        // ** {{{s}}} &mdash; a user's status update
        // ** {{{b}}} &mdash; a broadcasted message (sent to many users simultaneously)
        // * {{{s}}} is the sender of the message.
        // * {{{r}}} is the intended recipient of the message. Most of the time, this will
        // simply be the logged in user, however, a broadcasted message may not specify
        // a recipient or may specify a different recipient. Also provides future
        // compatability for chatrooms.
        // * {{{m}}} is the actual message. For something such as a status update, this can
        // be a JSON object or parsable string; e.g. {{{"2:I'm away."}}}
        //
        // ==== Parameters ====
        // * {{{messages}}} is the message array
        _parseMessages: function(messages) {
            if($.isArray(messages)) {
                $.each(messages, function() {
                    $(self).trigger('parseMessage', [this]);
                    
                    switch(this.t) {
                        case 'm':
                            self.incoming(this.s, this.m);
                        break;
                        
                        case 's':
                            var status = this.m.split(':');
                            if(this['g'])
                                self.addFriend(this.s, status, this.g);
                            self._friendUpdate(this.s, status[0], status.slice(1).join(':'));
                            self._storeFriends();
                        break;
    
                        case 'b':
                        break;
                        
                        default:
                        break;
                    }
                });
            }
        },
        
        // === {{{AjaxIM.}}}**{{{incoming(from, message)}}}** ===
        //
        // Handles a new message from another user. If a chatbox for that
        // user does not yet exist, one is created. If it does exist, but
        // is minimized, the user is notified but the chatbox is not brought
        // to the front. This function also stores the message, if a storage
        // method is set.
        //
        // ==== Parameters ====
        // * {{{from}}} is the username of the sender.
        // * {{{message}}} is the body.
        incoming: function(from, message) {
            // check if IM exists, otherwise create new window
            // TODO: If friend is not on the buddylist,
            // should add them to a temp list?
            var chatbox = this._createChatbox(from);
            
            if(!$('#imjs-bar .imjs-selected').length) {
                chatbox.data('tab').click();
            } else if(chatbox.data('tab').data('state') != 'active') {
                this.bar.notification(chatbox.data('tab'));
            }
            
            var time = this._addMessage('b', chatbox, from, message);
            this._storeMessage('b', chatbox, from, message, time);
        },
        
        // === {{{AjaxIM.}}}**{{{addFriend(username, group)}}}** ===
        //
        // Inserts a new friend into the friends list. If the group specified
        // doesn't exist, it is created. If the friend is already in this group,
        // they aren't added again, however, the friend item is returned.
        //
        // ==== Parameters ====
        // * {{{username}}} is the username of the new friend.
        // * {{{status}}} is the current status of the friend.
        // * {{{group}}} is the user group to which the friend should be added.
        addFriend: function(username, status, group) {
            var status_name = 'available';
            $.each(this.statuses,
                function(key, val) { if(status[0] == val) { status_name = key; return false; } });

            var group_id = 'imjs-group-' + $.md5(group);
            
            if(!(group_item = $('#' + group_id)).length) {
                var group_item = $('.imjs-friend-group.imjs-default').clone()
                        .removeClass('imjs-default')
                        .attr('id', group_id)
                        .data('group', group)
                        .appendTo('#imjs-friends-list');
                        
                var group_header = group_item.find('.imjs-friend-group-header');
                group_header.html(group_header.html().replace('{group}', group));
            }
            
            var user_id = 'imjs-friend-' + $.md5(username + group);
            
            if(!$('#' + user_id).length) {
                var user_item = group_item.find('ul li.imjs-default').clone()
                        .removeClass('imjs-default')
                        .addClass('imjs-' + status_name)
                        .attr('id', user_id)
                        .data('friend', username)
                        .appendTo(group_item.find('ul'));
                if(status[0] == 0) user_item.hide();
                user_item.html(user_item.html().replace('{username}', username));
            }
                        
            this.friends[username] = {'status': status, group: group};
            
            this._updateFriendCount();
            
            return this.friends[username];
        },
        
        // === //private// {{{AjaxIM.}}}**{{{_updateFriendCount()}}}** ===
        //
        // Counts the number of online friends and updates the friends count
        // in the friend tab.
        _updateFriendCount: function() {
            var friendsLength = 0;
            for(var f in this.friends) {
                if(this.friends[f].status[0] != 0)
                    friendsLength++;
            }
            $('#imjs-friends .imjs-tab-text span span').html(friendsLength);
        },
        
        // === //private// {{{AjaxIM.}}}**{{{_storeFriends()}}}** ===
        //
        // If a storage method is enabled, the current state of the
        // user's friends list is stored.
        _storeFriends: function() {
            if(this.settings.storageMethod && this.storageReady)
                $.jStore.store(this.storeKey + 'friends', this.friends);
        },
        
        // === //private// {{{AjaxIM.}}}**{{{_createChatbox(username)}}}** ===
        //
        // Builds a chatbox based on the default chatbox HTML and CSS defined
        // in the current theme. Should a chatbox for this user already exist,
        // a new one is not created. Instead, it is either given focus (should
        // no other windows already have focus), or a notification is issued.
        //
        // As well, if the chatbox does not exist, an associated tab will be
        // created.
        //
        // ==== Parameters ====
        // * {{{username}}} is the name of the user for whom the chatbox is intended
        // for.
        // * {{{no_stamp}}} sets whther or not to add a date stamp to the chatbox
        // upon creation.
        //
        // //Note:// New chatboxes are given an automatically generated ID in the
        // format of {{{#imjs-[md5 of username]}}}.
        _createChatbox: function(username, no_stamp) {
            var chatbox_id = 'imjs-' + $.md5(username);
            if(!(chatbox = $('#' + chatbox_id)).size()) {
                // add a tab
                var tab = this.bar.addTab(username, '#' + chatbox_id);
                var chatbox = tab.find('.imjs-chatbox');
                chatbox.attr('id', chatbox_id);

                chatbox.data('tab', tab);
                
                // remove default items from the message log
                var message_log = chatbox.find('.imjs-msglog').empty();
                
                // setup the chatbox header
                var cb_header = chatbox.find('.imjs-header');
                cb_header.html(cb_header.html().replace('{username}', username));
                
                if(!no_stamp) {
                    // add a date stamp
                    var time = this._addDateStamp(chatbox);
                    this._storeNonMessage('datestamp', username, null, time);
                }
                
                // associate the username with the object and vice-versa
                this.chats[username] = chatbox;
                chatbox.data('username', username);
                
                // did this chatbox fall down?
                this.bar._scrollers();
                
                if(username in this.friends) {
                    status = this.friends[username].status;
                    var status_name = 'available';
                    $.each(this.statuses,
                        function(key, val) { if(status[0] == val) { status_name = key; return false; } });
                    tab.addClass('imjs-' + status_name);
                }
                
                // store inputbox height
                //var input = chatbox.find('.imjs-input');
                //input.data('height', input.height());
            } else if(chatbox.data('tab').data('state') == 'closed') {
                chatbox.find('.imjs-msglog > *').addClass('imjs-msg-old');
                
                var tab = chatbox.data('tab');
                if(tab.css('display') == 'none')
                    tab.css('display', '').removeClass('imjs-selected')
                        .appendTo('#imjs-bar');
                
                if(!no_stamp) {
                    // possibly add a date stamp
                    var time = this._addDateStamp(chatbox);
                    this._storeNonMessage('datestamp', username, null, time);
                }
                    
                if(!$('#imjs-bar .imjs-selected').length) {
                    tab.click();
                } else {
                    this.bar.notification(tab);
                }
            }
            
            return chatbox;
        },
        
        // === //private// {{{AjaxIM.}}}**{{{_addDateStamp(chatbox)}}}** //
        //
        // Adds a date/time notifier to a chatbox. These are generally
        // inserted upon creation of a chatbox, or upon the date changing
        // since the last time a date stamp was added. If a date stamp for
        // the current date already exists, a new one will not be added.
        //
        // ==== Parameters ====
        // * {{{chatbox}}} refers to the jQuery-selected chatbox DOM element.
        // * {{{time}}} is the date/time the date stamp will show. It is specified
        // in milliseconds since the Unix Epoch. This is //only// defined when
        // date stamps are being restored from storage; if not specified, the
        // current computer time will be used.
        _addDateStamp: function(chatbox, time) {
            var message_log = $(chatbox).find('.imjs-msglog');
            if(!time)
               time = (new Date()).getTime();
 
            var date_stamp = $('.imjs-tab.imjs-default .imjs-chatbox .imjs-msglog .imjs-date').clone();
            var date_stamp_time = date_stamp.find('.imjs-msg-time');
            if(date_stamp_time.length)
                date_stamp_time.html(AjaxIM.dateFormat(time, date_stamp_time.html()));
            
            var date_stamp_date = date_stamp.find('.imjs-date-date');
            var formatted_date = AjaxIM.dateFormat(time, date_stamp_date.html());
            if(chatbox.data('lastDateStamp') != formatted_date) {
                if(date_stamp_date.length)
                    date_stamp_date.html(AjaxIM.dateFormat(time, date_stamp_date.html()));
            
                chatbox.data('lastDateStamp', formatted_date);
                date_stamp.appendTo(message_log);
            } else {
                //$('<div></div>').appendTo(message_log);
            }
            
            return time;
        },
        
        // === //private// {{{AjaxIM.}}}**{{{_addError(chatbox, error)}}}** //
        //
        // Adds an error to a chatbox. These are generally inserted after
        // a user sends a message unsuccessfully. If an error message
        // was already added, another one will be added anyway.
        //
        // ==== Parameters ====
        // * {{{chatbox}}} refers to the jQuery-selected chatbox DOM element.
        // * {{{error}}} is the error message string.
        // * {{{time}}} is the date/time the error occurred. It is specified in
        // milliseconds since the Unix Epoch. This is //only// defined when
        // errors are being restored from storage; if not specified, the current
        // computer time will be used.
        _addError: function(chatbox, error, time) {
            var message_log = $(chatbox).find('.imjs-msglog');
 
            var error_item =
                $('.imjs-tab.imjs-default .imjs-chatbox .imjs-msglog .imjs-error').clone();
                
            var error_item_time = error_item.find('.imjs-msg-time');
            if(error_item_time.length) {
                if(!time)
                    time = (new Date()).getTime();
                error_item_time.html(AjaxIM.dateFormat(time, error_item_time.html()));
            }

            error_item.find('.imjs-error-error').html(error);
            error_item.appendTo(message_log);
            
            message_log[0].scrollTop = message_log[0].scrollHeight;
        },
        
        // === //private// {{{AjaxIM.}}}**{{{_addMessage(ab, chatbox, username, message, time)}}}** //
        //
        // Adds a message to a chatbox. Depending on the {{{ab}}} value,
        // the color of the username may change as a way of visually
        // identifying users (however, this depends on the theme's CSS).
        // A timestamp is added to the message, and the chatbox is scrolled
        // to the bottom, such that the new message is visible.
        //
        // Messages will be automatically tag-escaped, so as to prevent
        // any potential cross-site scripting problems. Additionally,
        // URLs will be automatically linked.
        //
        // ==== Parameters ====
        // * {{{ab}}} refers to whether the user is "a" or "b" in a conversation.
        // For the general case, "you" are "a" and "they" are "b".
        // * {{{chatbox}}} refers to the jQuery-selected chatbox DOM element.
        // * {{{username}}} is the username of the user who sent the message.
        // * {{{time}}} is the time the message was sent in milliseconds since
        // the Unix Epoch. This is //only// defined when messages are being 
        // restored from storage. For new messages, the current computer
        // time is automatically used.
        _addMessage: function(ab, chatbox, username, message, time) {
            var last_message = chatbox.find('.imjs-msglog > *:last-child');
            if(last_message.hasClass('imjs-msg-' + ab)) {
                // Last message was from the same person, so let's just add another imjs-msg-*-msg
                var message_container = (last_message.hasClass('imjs-msg-' + ab + '-container') ?
                    last_message :
                    last_message.find('.imjs-msg-' + ab + '-container'));
                    
                var single_message =
                    $('.imjs-tab.imjs-default .imjs-chatbox .imjs-msglog .imjs-msg-' + ab + '-msg')
                    .clone().appendTo(message_container);
                
                single_message.html(single_message.html().replace('{username}', username));
            } else if(!last_message.length || !last_message.hasClass('imjs-msg-' + ab)) {
                var message_group = $('.imjs-tab.imjs-default .imjs-chatbox .imjs-msg-' + ab)
                    .clone().appendTo(chatbox.find('.imjs-msglog'));
                message_group.html(message_group.html().replace('{username}', username));
                
                var single_message = message_group.find('.imjs-msg-' + ab + '-msg');
            }
            
            // clean up the message
            message = message.replace(/</g, '&lt;').replace(/>/g, '&gt;')
                        .replace(/(^|.*)\*([^*]+)\*(.*|$)/, '$1<strong>$2</strong>$3');
            
            // autolink URLs
            message = message.replace(
                new RegExp('([A-Za-z][A-Za-z0-9+.-]{1,120}:[A-Za-z0-9/]' +
                '(([A-Za-z0-9$_.+!*,;/?:@&~=-])|%[A-Fa-f0-9]{2}){1,333}' +
                '(#([a-zA-Z0-9][a-zA-Z0-9$_.+!*,;/?:@&~=%-]{0,1000}))?)', 'g'),
                '<a href="$1" target="_blank">$1</a>');
            
            // insert the message
            single_message.html(single_message.html().replace('{message}', message));
            
            // set the message time
            var msgtime = single_message.find('.imjs-msg-time');
            if(!time)
                time = new Date();
        
            if(typeof time != 'string')
                time = AjaxIM.dateFormat(time, msgtime.html());
            
            msgtime.html(time);
            
            var msglog = chatbox.find('.imjs-msglog');
            msglog[0].scrollTop = msglog[0].scrollHeight;
            
            return time;
        },
        
        // === //private// {{{AjaxIM.}}}**{{{_storeNonMessage(type, username, data, time)}}}** ===
        //
        // **Redundant?**\\
        // Similar to {{{AjaxIM._storeMessage}}}, but stores items that aren't messages,
        // such as datestamps and errors.
        //
        // ==== Parameters ====
        // * {{{type}}} is the type of non-message (error, datestamp).
        // * {{{username}}} is the username of the user being chatted with.
        // * {{{data}}} is the (optional) data of the non-message to be stored.
        // * {{{time}}} is the time of the message.
        _storeNonMessage: function(type, username, data, time) {
            // If storage is on & ready, store the non-message
            if(this.settings.storageMethod) {
                if(!this.chatstore) this.chatstore = {};                 
                if(!(username in this.chatstore)) this.chatstore[username] = [];
                
                // If the chat store gets too long, it becomes slow to load.
                if(this.chatstore[username].length > 300)
                    this.chatstore[username].shift();
                
                // For some reason, if we don't encode and decode the message, it *will* break
                // (at least) the Flash storage engine's retrieval. Gah!
                this.chatstore[username].push(
                    [type, username, encodeURIComponent(data), time]);
                
                if(this.storageReady) $.jStore.store(self.storeKey + 'chats', this.chatstore);
            }
        },
        
        // === //private// {{{AjaxIM.}}}**{{{_storeMessage(ab, chatbox, username, message, time)}}}** ===
        //
        // Taking the same arguments as {{{AjaxIM._addMessage}}}, {{{_storeMessage}}} pushes a message
        // into the storage hash, if storage is enabled.
        //
        // Messages are added to a message array, by username. The entire chat hash is stored as
        // a {{{'chats'}}} object in whatever storage engine is enabled.
        _storeMessage: function(ab, chatbox, username, message, time) {
            // If storage is on & ready, store the message
            if(this.settings.storageMethod) {
                if(!this.chatstore) this.chatstore = {}; 
                
                message = message.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                
                if(!(username in this.chatstore)) {
                    this.chatstore[username] = [];
                } else if(this.chatstore[username].length > 300) {
                    // If the chat store gets too long, it becomes slow to load.
                    this.chatstore[username].shift();
                }
                
                // For some reason, if we don't encode and decode the message, it *will* break
                // (at least) the Flash storage engine's retrieval. Gah!
                this.chatstore[chatbox.data('username')].push(
                    [ab, username, encodeURIComponent(message), time]);
                
                if(this.storageReady) $.jStore.store(this.storeKey + 'chats', this.chatstore);
            }
        },
        
        // === //private// {{{AjaxIM.}}}**{{{_friendUpdate(friend, status, statusMessage)}}}** ===
        //
        // Called when a friend's status is updated. This function will update all locations
        // where a status icon is displayed (chat tab, friends list), as well as insert
        // a notification, should a chatbox be open.
        //
        // ==== Parameters ====
        // * {{{friend}}} is the username of the friend.
        // * {{{status}}} is the new status code. See {{{AjaxIM.statuses}}} for a list of available
        // codes. //Note: If an invalid status is specified, no action will be taken.//
        // * {{{statusMessage}}} is a message that was, optionally, specified by the user. It will be
        // used should "you" send the user an IM while they are away, or if their status is viewed
        // in another way (such as via the friends list [**not yet implemented**]).
        _friendUpdate: function(friend, status, statusMessage) {
            // add friend to buddylist, update their status, etc.           
            var status_name = 'available';
            $.each(this.statuses,
                function(key, val) { if(status == val) { status_name = key; return false; } });

            if(this.chats[friend]) {
                var tab = this.chats[friend].data('tab');
                var tab_class = 'imjs-tab';
                if(tab.data('state') == 'active') tab_class += ' imjs-selected';
                tab_class += ' imjs-' + status_name;
                
                tab.attr('class', tab_class);
                
                // display the status in the chatbox
                var date_stamp =
                    $('.imjs-tab.imjs-default .imjs-chatbox .imjs-msglog .imjs-date').clone();
                    
                var date_stamp_time = date_stamp.find('.imjs-msg-time');
                if(date_stamp_time.length)
                    date_stamp_time.html(AjaxIM.dateFormat(date_stamp_time.html()));
                
                var date_stamp_date = date_stamp.find('.imjs-date-date').html(
                    AjaxIM.i18n[
                        'chat' + status_name[0].toUpperCase() + status_name.slice(1)
                    ].replace(/%s/g, friend));
                
                var msglog = this.chats[friend].find('.imjs-msglog');
                date_stamp.appendTo(msglog);
                msglog[0].scrollTop = msglog[0].scrollHeight;
            }
            
            if(this.friends[friend]) {
                var friend_id = 'imjs-friend-' + $.md5(friend + this.friends[friend].group);
                $('#' + friend_id).attr('class', 'imjs-friend imjs-' + status_name);
                
                if(status == 0) {
                    $('#' + friend_id + ':visible').slideUp();
                    $('#' + friend_id + ':hidden').hide();
                } else if(!$('#' + friend_id + ':visible').length) {
                    $('#' + friend_id).slideDown();
                }
                
                this.friends[friend].status = [status, statusMessage];
                this._updateFriendCount();
            }
        },
        
        // === //private// {{{AjaxIM.}}}**{{{_notConnected()}}}** ===
        //
        // Puts the user into a visible state of disconnection. Sets the
        // friends list to "not connected" and empties it; disallows new messages
        // to be sent.
        _notConnected: function() {
            $('#imjs-friends').addClass('imjs-not-connected').unbind('click', this.activateTab);
        },
        
        // === {{{AjaxIM.}}}**{{{send(to, message)}}}** ===
        //
        // Sends a message to another user. The message will be added
        // to the chatbox before it is actually sent, however, if an
        // error occurs during sending, that will be indicated immediately
        // afterward.
        //
        // After sending the message, one of three status codes should be
        // returned as a JSON object, e.g. {{{{r: 'code'}}}}:
        // * {{{ok}}} &mdash; Message was sent successfully.
        // * {{{offline}}} &mdash; The user is offline or unavailable to
        // receive messages.
        // * {{{error}}} &mdash; a problem occurred, unrelated to the user
        // being unavailable.
        //
        // ==== Parameters ====
        // * {{{to}}} is the username of the recipient.
        // * {{{message}}} is the content to be sent.
        send: function(to, message) {         
            if(!message) return;
               
            if(this.chats[to]) { // REMOVE ME?
                // possibly add a datestamp
                var time = self._addDateStamp(this.chats[to]);
                this._storeNonMessage('datestamp', to, null, time);
                
                time = this._addMessage('a', this.chats[to], this.username, message);                
                this._storeMessage('a', this.chats[to], this.username, message, time);
            }
            
            $(self).trigger('sendingMessage', [to, message]);
            
            AjaxIM.request(
                this.actions.send,
                {'to': to, 'message': message},
                function(result) {
                    switch(result.r) {
                        case 'ok':
                            $(self).trigger('sendMessageSuccessful', [to, message]);
                        break;
                        
                        case 'offline':
                            $(self).trigger('sendMessageFailed', ['offline', to, message]);
                        break;
                        
                        case 'error':
                        default:
                            if(result.e == 'no session found') {
                                self._notConnected();
                                self._addError(self.chats[to], AjaxIM.i18n.notConnected);
                                self._storeNonMessage('error', to,
                                    AjaxIM.i18n.notConnected, (new Date()).getTime());
                            }
                            
                            $(self).trigger('sendMessageFailed', [result.e, to, message]);
                        break;
                    }
                },
                function(error) {
                    self._notConnected();
                    self._addError(self.chats[to], AjaxIM.i18n.notConnected);
                    self._storeNonMessage('error', to,
                        AjaxIM.i18n.notConnected, (new Date()).getTime());
                        
                    $(self).trigger('sendMessageFailed', ['not connected', to, message]);
                }
            );
        },
        
        // === {{{AjaxIM.}}}**{{{status(s, message)}}}** ===
        //
        // Sets the user's status and status message. It is possible to not
        // set a status message by setting it to an empty string. The status
        // will be sent to the server, where upon the server will broadcast
        // the update to all individuals with "you" on their friends list.
        //
        // ==== Parameters ====
        // * {{{s}}} is the status code, as defined by {{{AjaxIM.statuses}}}.
        // * {{{message}}} is the custom status message.
        status: function(s, message) {
            // update status icon(s)
            if(!this.statuses[s])
                return;
                
            $('#imjs-friends').attr('class', 'imjs-' + s);
            
            $(self).trigger('changingStatus', [s, message]);
            
            AjaxIM.request(
                this.actions.status,
                {'status': this.statuses[s], 'message': message},
                function(result) {
                    switch(result.r) {
                        case 'ok':
                            $(self).trigger('changeStatusSuccessful', [s, message]);
                        break;
                        
                        case 'error':
                        default:
                            $(self).trigger('changeStatusFailed', [result.e, s, message]);
                        break;
                    }
                },
                function(error) {
                    $(self).trigger('changeStatusFailed', ['not connected', s, message]);
                }
            );
        },
        
        // === {{{AjaxIM.}}}**{{{statuses}}}** ===
        //
        // These are the available status codes and their associated identities:
        // * {{{offline}}} (0) &mdash; Only used when signing out/when another
        // user has signed out, as once this status is set, the user is removed
        // from the server and friends will be unable to contact the user.
        // * {{{available}}} (1) &mdash; The user is online and ready to be messaged.
        // * {{{away}}} (2) &mdash; The user is online but is not available. Others
        // may still contact this user, however, the user may not respond. Anyone
        // contacting an away user will receive a notice stating that the user is away,
        // and (if one is set) their custom status message.
        // * {{{invisible}}} (3; **not yet implemented**) &mdash; The user is online,
        // but other users are made unaware, and the user will be represented
        // as being offline. It is still possible to contact this user, and for this
        // user to contact others; no status message or notice will be sent to others
        // messaging this user.
        statuses: {offline: 0, available: 1, away: 2, invisible: 3},
        
        // == Footer bar ==
        //
        // The footer bar is the bar that sits at the bottom of the page, in a fixed
        // position. It contains a tab for the friends list, and tabs for any open
        // chat boxes. It is also possible to add custom tabs for other functionality.
        bar: {
            // === {{{AjaxIM.}}}**{{{bar.initialize()}}}** ===
            //
            // Setup the footer bar and enable tab actions. This function
            // uses {{{jQuery.live}}} to set hooks on any bar tabs created
            // in the future.
            initialize: function() {
                // Set up your standard tab actions
                $('.imjs-tab')
                    .live('click', this.activateTab);
                    
                $('.imjs-tab .imjs-close')
                    .live('click', this.closeTab);
            
                // Set up the friends list actions
                var self = this;
                $(document).click(function(e) {
                    if(e.target.id == 'imjs-friends' ||
                        $(e.target).parents('#imjs-friends').length) {    
                        return;
                    }
                    
                    if($('#imjs-friends').data('state') == 'active')
                        self.activateTab.call($('#imjs-friends'));
                });
                $('#imjs-friends')
                    .data('state', 'minimized')
                    .click(function(e) {
                        if(!$(this).hasClass('imjs-not-connected') &&
                            e.target.id != 'imjs-friends-panel' &&
                            !$(e.target).parents('#imjs-friends-panel').length)
                            self.activateTab.call(this);
                    })
                    .mouseenter(function() {
                        if($(this).hasClass('imjs-not-connected')) {
                            $('.imjs-tooltip').css('display', 'block');
                            $('.imjs-tooltip p').html(AjaxIM.i18n.notConnectedTip);

                            var tip_left = $(this).offset().left -
                                $('.imjs-tooltip').outerWidth() +
                                ($(this).outerWidth() / 2);
                            var tip_top = $(this).offset().top -
                                $('.imjs-tooltip').outerHeight(true);

                            $('.imjs-tooltip').css({
                                    left: tip_left,
                                    top: tip_top
                                });
                        }
                    })
                    .mouseleave(function() {
                        if($(this).hasClass('imjs-not-connected')) {
                            $('.imjs-tooltip').css('display', '');
                        }
                    });
                $('#imjs-friends-panel')
                    .data('tab', $('#imjs-friends'))
                    .css('display', 'none');
            },
            
            // === {{{AjaxIM.}}}**{{{bar.activateTab()}}}** ===
            //
            // Activate a tab by setting it to the 'active' state and
            // showing any related chatbox. If a chatbox is available
            // for this tab, also focus the input box.
            //
            // //Note:// {{{this}}}, here, refers to the tab DOM element.
            activateTab: function() {
                var chatbox = $(this).find('.imjs-chatbox') || false;

                if($(this).data('state') != 'active') {
                    if($(this).attr('id') != 'imjs-friends') {
                        $('#imjs-bar > li')
                            .not($(this))
                            .not('#imjs-friends')
                            .removeClass('imjs-selected')
                            .each(function() {
                                if($(this).data('state') != 'closed') {
                                    $(this).data('state', 'minimized');
                                    var chatbox = $(this).find('.imjs-chatbox');
                                    if(chatbox.length)
                                        chatbox.css('display', 'none');
                                }
                            });
                    }
                    
                    if(chatbox && chatbox.css('display') == 'none')
                        chatbox.css('display', '');
                    
                    // set the tab to active...
                    var tab = $(this).addClass('imjs-selected').data('state', 'active');
                    
                    // ...and hide and reset the notification icon
                    tab.find('.imjs-notification').css('display', 'none')
                        .data('count', 0);
                    
                    if(self.settings.storageMethod && self.storageReady &&
                        chatbox && (username = chatbox.data('username'))) { 
                        $.jStore.store(self.storeKey + 'activeTab', [username]);
                    }
                    
                    $(self).trigger('tabToggled', ['activated', tab]);
                } else {
                    var tab = $(this).removeClass('imjs-selected').data('state', 'minimized');
                    
                    if(chatbox && chatbox.css('display') != 'none')
                        chatbox.css('display', 'none');
                    
                    if(self.settings.storageMethod && self.storageReady) { 
                        $.jStore.store(self.storeKey + 'activeTab', ['*']);
                    }
                    
                    $(self).trigger('tabToggled', ['minimized', tab]);
                }
                
                if(chatbox) {
                    if(!(input = chatbox.find('.imjs-input')).data('height')) {
                        // store the height for resizing later
                        input.data('height', input.height());
                    }
                    
                    try {
                        var msglog = chatbox.find('.imjs-msglog');
                        msglog[0].scrollTop = msglog[0].scrollHeight;
                    } catch(e) {}
                    
                    try { chatbox.find('.imjs-input').focus(); } catch(e) {}
                }
            },
            
            // === {{{AjaxIM.}}}**{{{bar.closeTab()}}}** ===
            //
            // Close a tab and hide any related chatbox, such that
            // the chatbox can not be reopened without reinitializing
            // the tab.
            //
            // //Note:// {{{this}}}, here, refers to the tab DOM element.
            closeTab: function() {
                var tab = $(this).parents('.imjs-tab');
                tab.css('display', 'none').data('state', 'closed');

                if(self.settings.storageMethod && self.storageReady) {
                    delete self.chatstore[tab.find('.imjs-chatbox').data('username')];
                    if(self.storageReady) $.jStore.store(self.storeKey + 'chats', self.chatstore);
                }

                $(self).trigger('tabToggled', ['closed', tab]);

                self.bar._scrollers();

                return false;
            },
            
            // === {{{AjaxIM.}}}**{{{bar.addTab(label, action, closable)}}}** ===
            //
            // Adds a tab to the tab bar, with the label {{{label}}}. When
            // clicked, it will call a callback function, {{{action}}}. If
            // {{{action}}} is a string, it is assumed that the string is
            // referring to a chatbox ID.
            //
            // ==== Parameters ====
            // * {{{label}}} is the text that will be displayed on the tab.\\
            // * {{{action}}} is the callback function, if it is a non-chatbox
            // tab, or a string if it //is// a chatbox tab.\\
            // * {{{closable}}} is a boolean value that determines whether or not
            // it is possible for a user to close this tab.
            //
            // //Note:// New tabs are given an automatically generated ID
            // in the format of {{{#imjs-tab-[md5 of label]}}}.
            addTab: function(label, action, closable) {
                var tab = $('.imjs-tab.imjs-default').clone().insertAfter('#imjs-scroll-right');
                tab.removeClass('imjs-default')
                    .attr('id', 'imjs-tab-' + $.md5(label))
                    .html(tab.html().replace('{label}', label))
                    .data('state', 'minimized');
                    
                var notification = tab.find('.imjs-notification');
                notification.css('display', 'none')
                    .data('count', 0)
                    .data('default-text', notification.html())
                    .html(notification.html().replace('{count}', '0'));
                
                if(closable === false)
                    tab.find('.imjs-close').eq(0).remove();
                
                if(typeof action == 'string') {
                    //tab.data('chatbox', action);
                } else {
                    tab.find('.imjs-chatbox').remove();
                    tab.click(action);
                }
                
                return tab;
            },
            
            // === {{{AjaxIM.}}}**{{{bar.notification(tab)}}}** ===
            //
            // Displays a notification on a tab. Generally, this is called when
            // a tab is minimized to let the user know that there is an update
            // for them. The way the notification is displayed depends on the
            // theme CSS.
            //
            // ==== Parameters ====
            // * {{{tab}}} is the jQuery-selected tab DOM element.
            notification: function(tab) {
                var notify = tab.find('.imjs-notification');
                var notify_count = notify.data('count') + 1;
                
                notify.data('count', notify_count)
                    .html(notify.data('default-text').replace('{count}', notify_count))
                    .css('display', '');
            },
            
            // === //private// {{{AjaxIM.}}}**{{{bar._scrollers()}}}** ===
            //
            // Document me!
            _scrollers: function() {
                var needScrollers = false;
                $('.imjs-tab').filter(function() {
                    return $(this).data('state') != 'closed'
                }).css('display', '');
                
                $.each(self.chats, function(username, chatbox) {
                    var tab = chatbox.data('tab');
                    if(tab.data('state') == 'closed') return true;
                    
                    if(tab.position().top > $('#imjs-bar').height()) {
                        $('.imjs-scroll').css('display', '');
                        tab.css('display', 'none');
                        needScrollers = true;
                    } else {
                        tab.css('display', '');
                    }
                });
                
                if(!needScrollers) {
                    $('.imjs-scroll').css('display', 'none');
                }
                
                if($('#imjs-scroll-left').css('display') != 'none' &&
                    $('#imjs-scroll-left').position().top > $('#imjs-bar').height()) {
                    $('#imjs-bar li.imjs-tab:visible').slice(-1).css('display', 'none');
                }
                
                var hiddenLeft = $('#imjs-bar li.imjs-tab:visible').slice(-1)
                    .nextAll('#imjs-bar li.imjs-tab:hidden')
                    .not('.imjs-default')
                    .filter(function() {
                        return $(this).data('state') != 'closed'
                    }).length;
                    
                var hiddenRight = $('#imjs-bar li.imjs-tab:visible').eq(0)
                    .prevAll('#imjs-bar li.imjs-tab:hidden')
                    .not('.imjs-default')
                    .filter(function() {
                        return $(this).data('state') != 'closed'
                    }).length;
                    
                $('#imjs-scroll-left').html(hiddenLeft);
                $('#imjs-scroll-right').html(hiddenRight);
            }
        },
        
        // == Comet ==
        //
        // Comet, or HTTP streaming, holds open a connection between the client and
        // the server indefinitely. As the server receives new messages or events,
        // they are passed down to the client in a {{{&lt;script&gt;}}}
        // tag which calls the {{{AjaxIM.incoming()}}} function. The connection is
        // opened using either an {{{iframe}}} (in Opera or Internet Explorer) or
        // an {{{XMLHTTPRequest}}} object. Due to the extra flexibility necessary
        // with the {{{XMLHTTPRequest}}} object, jQuery's {{{$.ajax}}} is not used.
        comet: {
            type: '',
            obj: null,
        
            onbeforeunload: null,
            onreadystatechange: null,
            
            iframe: function() {                
                if(/loaded|complete/i.test(this.obj.readyState))
                    throw new Error("IM server not available!");
            },

            // === {{{AjaxIM.}}}**{{{comet.connect()}}}** ===
            //
            // Creates and initializes the object and connection between the server
            // and the client. For Internet Explorer and Opera, we use an
            // {{{&lt;iframe&gt;}}} element; for all other browsers, we create an
            // {{{XMLHTTPRequest}}} object. The server connects to the URI defined
            // as the "poll" action. This function is called automatically, when
            // the IM engine is initialized and the {{{AjaxIM.poll()}}} function
            // is called.
            connect: function() {
                var self = _instance;
                
                if($.browser.opera || $.browser.msie) {
                    var iframe = $('<iframe></iframe>');
                    with(iframe) {
                        css({
                            position: 'absolute',
                            visibility: 'visible',
                            display: 'block',
                            left: '-10000px',
                            top: '-10000px',
                            width: '1px',
                            height: '1px'
                        });
                        
                        attr('src', self.actions.poll[1]);
                        appendTo('body');
                        
                        bind('readystatechange',
                            self.comet.onreadystatechange = function() { self.comet.iframe() });
                        bind('beforeunload',
                            self.comet.onbeforeunload = function() { self.comet.disconnect() });
                    }
                    
                    self.comet.type = 'iframe';
                    self.comet.obj = iframe;
                } else {
                    var xhr = new XMLHttpRequest;
                    var length = 1029;
                    var code = /^\s*<script[^>]*>parent\.(.+);<\/script><br\s*\/>$/;
                    
                    xhr.open('get', self.actions.poll[1], true);
                    xhr.onreadystatechange = function(){
                        if(xhr.readyState > 2) {
                            if(xhr.status == 200) {
                                responseText = xhr.responseText.substring(length);
                                length = xhr.responseText.length;
                                if(responseText != ' ') 
                                    eval(responseText.replace(code, "$1"));
                            }
                            // We need an "else" here. If the state changes to
                            // "loaded", the user needs to know they're
                            // disconnected.
                        }
                    };
                    
                    self.comet.type = 'xhr';
                    self.comet.obj = xhr;
                    
                    addEventListener('beforeunload',
                        self.comet.beforeunload = function() { self.comet.disconnect(); }, false);
                    setTimeout(function() { xhr.send(null) }, 10);
                }
            },

            // === {{{AjaxIM.}}}**{{{comet.disconnect()}}}** ===
            //
            // Disconnect from the server and destroy the connection object. This
            // function is called before the page unloads, so that we plug up and
            // potential leaks and free memory.
            disconnect: function() {
                var self = _instance.comet;
                
                if(!this.type || !this.obj)
                    return;
                
                if(this.type == 'iframe') {
                    detachEvent('onreadystatechange', this.onreadystatechange);
                    detachEvent('onbeforeunload', this.onbeforeunload);
                    this.obj.src = '.';
                    $(this.obj).remove();
                } else {
                    removeEventListener('beforeunload', this.onbeforeunload, false);
                    this.obj.onreadystatechange = function(){};
                    this.obj.abort();
                }
                
                delete this.obj;
            }
        }
    })
        
    self.bar.initialize();
    
    if(prequeue.length) {
        $.each(prequeue, function() {
            var func = this[0].split('.');
            if(func.length > 1)
                self[func[0]][func[1]].apply(self, this[1]);
            else
                self[func[0]].apply(self, this[1]);
        });
    }
    });
    
    // == Static functions and variables ==
    //
    // The following functions and variables are available outside of an initialized
    // {{{AjaxIM}}} object.
    
    // === {{{AjaxIM.}}}**{{{client}}}** ===
    //
    // Once {{{AjaxIM.init()}}} is called, this will be set to the active AjaxIM
    // object. Only one AjaxIM object instance can exist at a time. This variable
    // can and should be accessed directly.
    AjaxIM.client = null;
    
    // === {{{AjaxIM.}}}**{{{init(options, actions)}}}** ===
    //
    // Initialize the AjaxIM client object and engine. Here, you can define your
    // options and actions as outlined at the top of this documentation.
    //
    // ==== Parameters ====
    // * {{{options}}} is the hash of custom settings to initialize Ajax IM with.
    // * {{{actions}}} is the hash of any custom action URLs.
    AjaxIM.init = function(options, actions) {
        if(!_instance) {
            _instance = new AjaxIM(options, actions);
            AjaxIM.client = _instance;
        }
        
        return _instance;
    }
    
    
    // === {{{AjaxIM.}}}**{{{request(url, data, successFunc, failureFunc)}}}** ===
    //
    // Wrapper around {{{$.jsonp}}}, the JSON-P library for jQuery, and {{{$.ajax}}},
    // jQuery's ajax library. Allows either function to be called, automatically,
    // depending on the request's URL array (see {{{AjaxIM.actions}}}).
    //
    // ==== Parameters ====
    // {{{url}}} is the URL of the request.
    // {{{data}}} are any arguments that go along with the request.
    // {{{success}}} is a callback function called when a request has completed
    // without issue.
    // {{{_ignore_}}} is simply to provide compatability with {{{$.post}}}.
    // {{{failure}}} is a callback function called when a request hasn't not
    // completed successfully.
    AjaxIM.request = function(url, data, successFunc, failureFunc) {
        if(typeof failureFunc != 'function');
            failureFunc = function(){};

        $[url[0]]({
            'url': url[1],
            'data': data,
            dataType: (url[0] == 'ajax' ? 'json' : 'jsonp'),
            type: 'POST',
            cache: false,
            timeout: 60000,
            callback: 'jsonp' + (new Date()).getTime(),
            success: function(json, textStatus) {
                successFunc(json);
            },
            error: function(xOptions, error) {
                failureFunc(error);
            }
        });
        
        // This prevents Firefox from spinning indefinitely
        // while it waits for a response. Why? Fuck if I know.
        if(url[0] == 'jsonp' && $.browser.mozilla) {
            $.jsonp({
                'url': 'about:',
                timeout: 0
            });
        }
    };
    
    // === {{{AjaxIM.}}}**{{{incoming(data)}}}** ===
    //
    // Never call this directly. It is used as a connecting function between
    // client and server for Comet.
    //
    // //Note:// There are two {{{AjaxIM.incoming()}}} functions. This one is a
    // static function called outside of the initialized AjaxIM object; the other
    // is only called within the initalized AjaxIM object.
    AjaxIM.incoming = function(data) {
        if(!_instance)
            return false;
        
        if(data.length)
            _instance._parseMessages(data);
    }
    
    // === {{{AjaxIM.}}}**{{{loaded}}}** ===
    //
    // If Ajax IM has been loaded with the im.load.js file, this function will be
    // called when the library is finally loaded and ready for use. Similar to
    // jQuery's $(document).ready(), but for Ajax IM.
    AjaxIM.loaded = function() {
        if(typeof AjaxIMLoadedFunction == 'function') {
            AjaxIMLoadedFunction();
            delete AjaxIMLoadedFunction; // clean up the global namespace
        }
    };
    
    // === {{{AjaxIM.}}}**{{{dateFormat([date,] [mask,] utc)}}}** ===
    //
    // Date Format 1.2.3\\
    // &copy; 2007-2009 Steven Levithan ([[http://blog.stevenlevithan.com/archives/date-time-format|stevenlevithan.com]])\\
    // MIT license
    //
    // Includes enhancements by Scott Trenda
    // and Kris Kowal ([[http://cixar.com/~kris.kowal/|cixar.com/~kris.kowal/]])
    //
    // Accepts a date, a mask, or a date and a mask and returns a formatted version
    // of the given date.
    //
    // ==== Parameters ====
    // * {{{date}}} is a {{{Date()}}} object. If not specified, the date defaults to the
    // current date/time.
    // * {{{mask}}} is a string that defines the formatting of the date. Formatting
    // options can be found in the
    // [[http://blog.stevenlevithan.com/archives/date-time-format|Date Format]]
    // documentation. If not specified, the mask defaults to {{{dateFormat.masks.default}}}.
    
    AjaxIM.dateFormat = function () {
        var token = /d{1,4}|m{1,4}|yy(?:yy)?|([HhMsTt])\1?|[LloSZ]|"[^"]*"|'[^']*'/g,
            timezone = new RegExp('\b(?:[PMCEA][SDP]T|(?:Pacific|Mountain|Central|Eastern|Atlantic) ' +
                                  '(?:Standard|Daylight|Prevailing) Time|(?:GMT|UTC)(?:[-+]\d{4})?)\b',
                                  'g'),
            timezoneClip = /[^-+\dA-Z]/g,
            pad = function (val, len) {
                val = String(val);
                len = len || 2;
                while (val.length < len) val = "0" + val;
                return val;
            };
    
        // Regexes and supporting functions are cached through closure
        return function (date, mask, utc) {
            var dF = AjaxIM.dateFormat;
    
            // You can't provide utc if you skip other args (use the "UTC:" mask prefix)
            if (arguments.length == 1 && Object.prototype.toString.call(date) ==
                  "[object String]" && !/\d/.test(date)) {
                mask = date;
                date = undefined;
            }
    
            // Passing date through Date applies Date.parse, if necessary
            date = date ? new Date(date) : new Date;
            if (isNaN(date)) throw SyntaxError("invalid date");
    
            mask = String(dF.masks[mask] || mask || dF.masks["default"]);
    
            // Allow setting the utc argument via the mask
            if (mask.slice(0, 4) == "UTC:") {
                mask = mask.slice(4);
                utc = true;
            }
    
            var _ = utc ? "getUTC" : "get",
                d = date[_ + "Date"](),
                D = date[_ + "Day"](),
                m = date[_ + "Month"](),
                y = date[_ + "FullYear"](),
                H = date[_ + "Hours"](),
                M = date[_ + "Minutes"](),
                s = date[_ + "Seconds"](),
                L = date[_ + "Milliseconds"](),
                o = utc ? 0 : date.getTimezoneOffset(),
                flags = {
                    d:    d,
                    dd:   pad(d),
                    ddd:  AjaxIM.i18n.dayNames[D],
                    dddd: AjaxIM.i18n.dayNames[D + 7],
                    m:    m + 1,
                    mm:   pad(m + 1),
                    mmm:  AjaxIM.i18n.monthNames[m],
                    mmmm: AjaxIM.i18n.monthNames[m + 12],
                    yy:   String(y).slice(2),
                    yyyy: y,
                    h:    H % 12 || 12,
                    hh:   pad(H % 12 || 12),
                    H:    H,
                    HH:   pad(H),
                    M:    M,
                    MM:   pad(M),
                    s:    s,
                    ss:   pad(s),
                    l:    pad(L, 3),
                    L:    pad(L > 99 ? Math.round(L / 10) : L),
                    t:    H < 12 ? "a"  : "p",
                    tt:   H < 12 ? "am" : "pm",
                    T:    H < 12 ? "A"  : "P",
                    TT:   H < 12 ? "AM" : "PM",
                    Z:    utc ? "UTC" :
                            (String(date).match(timezone) || [""])
                            .pop().replace(timezoneClip, ""),
                    o:    (o > 0 ? "-" : "+") +
                            pad(Math.floor(Math.abs(o) / 60) * 100 + Math.abs(o) % 60, 4),
                    S:    ["th", "st", "nd", "rd"][d % 10 > 3 ?
                            0 :
                            (d % 100 - d % 10 != 10) * d % 10]
                };
    
            return mask.replace(token, function ($0) {
                return $0 in flags ? flags[$0] : $0.slice(1, $0.length - 1);
            });
        };
    }();
    
    // Some common format strings
    AjaxIM.dateFormat.masks = {
        "default":      "ddd mmm dd yyyy HH:MM:ss",
        shortDate:      "m/d/yy",
        mediumDate:     "mmm d, yyyy",
        longDate:       "mmmm d, yyyy",
        fullDate:       "dddd, mmmm d, yyyy",
        shortTime:      "h:MM TT",
        mediumTime:     "h:MM:ss TT",
        longTime:       "h:MM:ss TT Z",
        isoDate:        "yyyy-mm-dd",
        isoTime:        "HH:MM:ss",
        isoDateTime:    "yyyy-mm-dd'T'HH:MM:ss",
        isoUtcDateTime: "UTC:yyyy-mm-dd'T'HH:MM:ss'Z'"
    };

    // === {{{AjaxIM.}}}**{{{i18n}}}** ===
    //
    // Text strings used by Ajax IM. Should you want to translate Ajax IM into
    // another language, merely change these strings.
    // 
    // {{{%s}}} denotes text that will be automatically replaced when the string is
    // used.
    AjaxIM.i18n = {
        dayNames: [
            "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat",
            "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"
        ],
        monthNames: [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
            "January", "February", "March", "April", "May", "June", "July", "August", "September",
            "October", "November", "December"
        ],
        
        chatOffline: '%s signed off.',
        chatAvailable: '%s became available.',
        chatAway: '%s went away.',
        
        notConnected: 'You are currently not connected or the server is not available. ' +
                      'Please ensure that you are signed in and try again.',
        notConnectedTip: 'You are currently not connected.',
        
        authInvalid: 'Invalid username or password.',
        
        registerPasswordLength: 'Passwords must be more than 4 characters in length.',
        registerUsernameLength: 'Usernames must be more than 2 characters in length and ' +
                        ' contain only A-Z, a-z, 0-9, underscores (_) and periods (.).',
        registerPasswordMatch: 'Entered passwords do not match.',
        registerUsernameTaken: 'The chosen username is already in use; please choose another.',
        registerUnknown: 'An unknown error occurred. Please try again.'
    }
})(jQuery, false);
