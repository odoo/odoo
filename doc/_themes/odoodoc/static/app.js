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

    // lang switcher
    function findSheet(pattern, fromSheet) {
        if (fromSheet) {
            for(var i=0; i<fromSheet.cssRules.length; ++i) {
                var rule = fromSheet.cssRules[i];
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
    if ($('div.document-super').hasClass('stripe')) { (function () {
        var sheet = findSheet(/style\.css$/);
        if (!sheet) { return; }

        // collect languages
        var languages = {};
        $('div.switchable').each(function () {
            var classes = this.className.split(/\s+/);
            for (var i = 0; i < classes.length; ++i) {
                var cls = classes[i];
                if (!/^highlight-/.test(cls)) { continue; }
                languages[cls.slice(10)] = true;
            }
        });

        $(buildSwitcher(Object.keys(languages)))
            .prependTo('div.documentwrapper')
            .on('click', 'li', function (e) {
                $(e.target).addClass('active')
                    .siblings().removeClass('active');
                var id = e.target.textContent;
                var lastIndex = sheet.cssRules.length - 1;
                var content = sheet.cssRules[lastIndex].style.cssText;
                var sel = [
                    '.stripe .only-', id, ', ',
                    '.stripe .highlight-', id, ' > .highlight'
                ].join('');
                sheet.deleteRule(lastIndex);
                sheet.insertRule(sel + '{' + content + '}', lastIndex);
        });
    })(); }

    // Config ZeroClipboard
    ZeroClipboard.config({
        moviePath: '_static/ZeroClipboard.swf',
        hoverClass: 'btn-clipboard-hover'
    });

    // Insert copy to clipboard button before .highlight or .example
    $('.highlight-html, .highlight-scss').each(function () {
        var highlight = $(this);
        var previous = highlight.prev();
        var btnHtml = '<div class="zero-clipboard"><span class="btn-clipboard">Copy</span></div>';

        if (previous.hasClass('example')) {
            previous.before(btnHtml.replace(/btn-clipboard/, 'btn-clipboard with-example'));
        } else {
            highlight.before(btnHtml);
        }
    });
    var zeroClipboard = new ZeroClipboard($('.btn-clipboard'));
    var htmlBridge = $('#global-zeroclipboard-html-bridge');

    // Handlers for ZeroClipboard
    zeroClipboard.on('load', function () {
        htmlBridge
            .data('placement', 'top')
            .attr('title', 'Copy to clipboard')
            .tooltip();
    });

    // Copy to clipboard
    zeroClipboard.on('dataRequested', function (client) {
        var highlight = $(this).parent().nextAll('.highlight').first();
        client.setText(highlight.text());
    });

    // Notify copy success and reset tooltip title
    zeroClipboard.on('complete', function () {
        htmlBridge
            .attr('title', 'Copied!')
            .tooltip('fixTitle')
            .tooltip('show')
            .attr('title', 'Copy to clipboard')
            .tooltip('fixTitle');
    });

    // Notify copy failure
    zeroClipboard.on('noflash wrongflash', function () {
        htmlBridge.attr('title', 'Flash required')
            .tooltip('fixTitle')
            .tooltip('show');
    });
});
