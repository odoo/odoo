$(function () {
    var $body = $(document.body);
    $body.scrollspy({ target: '.sphinxsidebarwrapper' });
    $(window).on('load', function () {
        $body.scrollspy('refresh');
    });

    // Sidenav affixing
    setTimeout(function () {
        var $sideBar = $('.sphinxsidebarwrapper');

        $sideBar.affix({
            offset: {
                top: function () {
                    var offsetTop = $sideBar.offset().top;
                    var sideBarMargin = parseInt($sideBar.children(0).css('margin-top'), 10);
                    var navOuterHeight = $('.docs-nav').height();

                    return (this.top = offsetTop - navOuterHeight - sideBarMargin);
                },
                bottom: function () {
                    return (this.bottom = $('div.footer').outerHeight(true));
                }
            }
        });
    }, 100);

    // stripe page stuff
    if ($('div.document-super').hasClass('stripe')) { (function () {
        // iterate on highlighted PL blocks (but not results because that'd
        // be gross), extract all switchable PLs in the document and add
        // clipboard-copy buttons
        var languages = {};
        $('div.switchable').each(function () {
            var language = getHighlightLanguage(this);
            if (language) {
                languages[language] = true;
            }
        });

        // if can't find CSS where base rule lives something's probably
        // broken, bail
        var sheet = findSheet(/style\.css$/);
        if (!sheet) { return; }
        // build PL switcher UI and hook toggle event
        var $switcher = $(buildSwitcher(Object.keys(languages)))
            .prependTo('div.documentwrapper')
            .on('click', 'li', function (e) {
                $(e.target).addClass('active')
                    .siblings().removeClass('active');
                var id = e.target.textContent;
                var lastIndex = sheet.cssRules.length - 1;
                var content = sheet.cssRules[lastIndex].style.cssText;
                // change rule in CSS because why not (also can add new
                // languages without having to e.g. change CSS or anything)
                var sel = [
                    '.stripe .only-', id, ', ',
                    '.stripe .highlight-', id, ' > .highlight'
                ].join('');
                sheet.deleteRule(lastIndex);
                sheet.insertRule(sel + '{' + content + '}', lastIndex);
            });
        $switcher.affix();

        $('<button type="button" class="btn-show-setup">Toggle Setup Code</button>')
            .prependTo('.switchable:not(.setup) .highlight');
        $(document).on('click', '.btn-show-setup', function (e) {
            var $target = $(e.target);
            var switchable = $target.closest('.switchable:not(.setup)').get(0);
            // not in a switchable (???)
            if (!switchable) { return; }

            var lang = getHighlightLanguage(switchable);
            if (!lang) {
                // switchable without highlight (e.g. language-specific notes),
                // don't munge
                return;
            }

            var $following_siblings = $target.nextAll();
            if ($following_siblings.length > 1) {
                // remove all but the very last following sibling (which
                // should be the non-setup <pre>)
                $following_siblings.slice(0, -1).remove();
            } else {
                // otherwise insert setupcode
                $('.setupcode.highlight-' + lang + ' pre').clone().insertAfter($target);
            }
        });
    })(); }

    /**
     * @param {Node} node highlight node to get the language of
     * @returns {String|null} either the highlight language or null
     */
    function getHighlightLanguage(node) {
        var classes = node.className.split(/\s+/);
        for (var i = 0; i < classes.length; ++i) {
            var cls = classes[i];
            if (/^highlight-/.test(cls)) {
                return cls.slice(10);
            }
        }
        return null;
    }
    // programming language switcher
    function findSheet(pattern, fromSheet) {
        if (fromSheet) {
            // cssRules may be `null` in iOS safari (?)
            var rules = fromSheet.cssRules || [];
            for(var i=0; i<rules.length; ++i) {
                var rule = rules[i];
                if (rule.type !== CSSRule.IMPORT_RULE) { continue; }
                if (pattern.test(rule.href)) {
                    return rule.styleSheet;
                }
            }
            return null;
        }
        var sheets = document.styleSheets;
        for(var j=0; j<sheets.length; ++j) {
            var sheet = sheets[j];
            if (pattern.test(sheet.href)) {
                return sheet;
            }
            var subSheet;
            if (subSheet = findSheet(pattern, sheet)) {
                return subSheet;
            }
        }
        return null;
    }
    function buildSwitcher(languages) {
        var root = document.createElement('ul');
        root.className = "switcher";
        for(var i=0; i<languages.length; ++i) {
            var item = document.createElement('li');
            item.textContent = languages[i];
            if (i === 0) {
                item.className = "active";
            }
            root.appendChild(item);
        }
        return root;
    }
});
